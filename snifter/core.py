from __future__ import print_function

import sys
assert sys.version_info > (2,5), 'Snifter requires Python 2.6 or greater or Python 3.2 or greater to run properly'
py3 = sys.version_info >= (3,0)

import wsgiref.headers
import collections
import re
import functools
import traceback

if py3:
    import http.client as httplib
    import http.cookies as Cookie
else:
    import httplib
    import Cookie

from wsgiref.simple_server import WSGIServer, make_server

from .error import HTTPResponse, Redirect
from .utils import parse_return, FieldStorage
from .session import start, sessiongc
from .static import static_file


Route = collections.namedtuple('Route', ('path', 'method', 'callback'))


class Request(dict):

    def __init__(self, request):
        dict.__init__(self, request)
        self.forms = FieldStorage(fp=request['wsgi.input'], environ=request)
        self.cookies = Cookie.SimpleCookie(request.get('HTTP_COOKIE', {}))

    def get_cookie(self, name):
        try:
            return self.cookies[name].value
        except KeyError:
            pass


class Response(wsgiref.headers.Headers):

    def __init__(self, headers):
        wsgiref.headers.Headers.__init__(self, headers)
        self.cookies = Cookie.SimpleCookie()
        self.status = '200 OK'

    def set_status(self, status):
        self.status = '{0} {1}'.format(status, httplib.responses[status])

    def set_cookie(self, name, value, max_age=None, expires=None, path='/', comment=None, domain=None, secure=False,
                   httponly=False, version=1):
        self.cookies[name] = value
        if max_age:
            self.cookies[name]['max-age'] = max_age
        if expires:
            self.cookies[name]['expires'] = expires
        if path:
            self.cookies[name]['path'] = path
        if comment:
            self.cookies[name]['comment'] = comment
        if domain:
            self.cookies[name]['domain'] = domain
        if secure:
            self.cookies[name]['secure'] = secure
        if httponly:
            self.cookies[name]['httponly'] = httponly
        if version:
            self.cookies[name]['version'] = version
        return self.cookies[name]

    def prepare(self):
        for morsel in self.cookies.values():
            header = morsel.output().split(': ')
            self.add_header(*header)


class App(object):

    def __init__(self):
        self._routes = []
        self._errors = {}
        self._usessessions = False

    def __call__(self, request, start_response):
        headers = [('Content-type', 'text/html')]
        request = Request(request)
        response = Response(headers)
        try:
            for route, method, callback in self._routes:
                if request['REQUEST_METHOD'] != method:
                    continue
                match = route.match(request['PATH_INFO'])
                if match is not None:
                    content = self._handle_callback(callback, request, response, *match.groups(), **match.groupdict())
                    break
            else:
                raise HTTPResponse(404)

        except Exception as e:
            if type(e) is Redirect:
                content = self._handle_redirect(response, e)
            elif type(e) is HTTPResponse:
                content = self._handle_error(request, response, e)
            else:
                print(traceback.format_exc(e))
                err = HTTPResponse(500, message=str(e))
                content = self._handle_error(request, response, err)

        response.prepare()
        start_response(response.status, headers)
        return parse_return(content)

    def _handle_callback(self, callback, request, response, *args, **kwargs):
        wants = []
        for i in callback.wants:
            if i == 'response':
                wants.append(response)
            elif i == 'request':
                wants.append(request)
            elif i == 'static_file' or i == 'staticfile':
                wants.append(functools.partial(static_file, request, response))
            elif i == 'session':
                if request.get('snifter.session'):
                    wants.append(request['snifter.session'])
                else:
                    wants.append(start(request, response))
        wants.extend(args)
        return callback(*wants, **kwargs)

    def _handle_error(self, request, response, e):
        response.set_status(e.code)
        if e.content is not None:
            return e.content
        callback = self._errors.get(e.code)
        try:
            if callback is not None:
                return self._handle_callback(callback, request, response, e.message)
            raise HTTPResponse(404, message='There was a 404 while accessing the error page.')
        except Exception as e:
            if type(e) is Redirect:
                return self._handle_redirect(response, e)
            elif type(e) is HTTPResponse:
                if e.code == 304 or e.code == 204 or e.code == 205:
                    return ''
                elif e.content is not None:
                    return e.content
                return response.status
            else:
                print(traceback.format_exc(e))
                return response.status

    def _handle_redirect(self, response, e):
        response.set_status(e.code)
        response['Location'] = e.destination
        return ''

    def route(self, path, method='GET', wants=(), cache=False):
        if wants and cache:
            raise RuntimeError('Cached route cannot want')
        path = (path,) if isinstance(path, str) else path
        path = ('^{0}$'.format(i) for i in path)
        class Wrapper(object):
            def __init__(self2, func):
                for p in path:
                    self._routes.append(Route(re.compile(p), method, self2))
                self2.wants = wants if isinstance(wants, tuple) else (wants,)
                if 'session' in self2.wants:
                    self._usessessions = True
                if cache:
                    value = func()
                    self2._func = lambda: value
                else:
                    self2._func = func
            def __call__(self2, *args, **kwargs):
                return self2._func(*args, **kwargs)
        return Wrapper

    def get(self, path, wants=(), cache=False):
        return self.route(path, method='GET', wants=wants, cache=cache)

    def post(self, path, wants=()):
        return self.route(path, method='POST', wants=wants)

    def error(self, code, wants=(), cache=False):
        if wants and cache:
            raise RuntimeError('Cached route cannot want')
        code = (code,) if isinstance(code, int) else code
        class Wrapper(object):
            def __init__(self2, func):
                for c in code:
                    self._errors[c] = self2
                self2.wants = wants if isinstance(wants, tuple) else (wants,)
                if 'session' in self2.wants:
                    self._usessessions = True
                if cache:
                    value = func('')
                    self2._func = lambda: value
                else:
                    self2._func = func
            def __call__(self2, *args, **kwargs):
                return self2._func(*args, **kwargs)
        return Wrapper

    def run(self, host='localhost', port=3030, server=WSGIServer, middleware=None):
        port = int(port)
        app = self
        if middleware and isinstance(middleware, collections.Iterable):
            for mw in middleware:
                if isinstance(mw, tuple) or isinstance(mw, list):
                    app = mw[0](app, *mw[1:])
                else:
                    app = mw(app)
        elif middleware:
            app = middleware(app)
        server = make_server(host, port, app, server)
        print('Serving on http://{0}:{1}...'.format(host, port))
        if self._usessessions:
            with sessiongc():
                server.serve_forever()
        else:
            server.serve_forever()
