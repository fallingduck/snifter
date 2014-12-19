from __future__ import print_function

import sys
py3 = sys.version_info >= (3,0)

import wsgiref.headers
import collections
import re
import cgi

if py3:
    import http.client as httplib
else:
    import httplib

from .server import ThreadingWSGIServer, make_server
from .error import HTTPError, Redirect


Route = collections.namedtuple('Route', ('path', 'method', 'callback'))


if py3:
    def _parse_return(content):
        if isinstance(content, str):
            content = content.encode('utf-8')
        if isinstance(content, bytes):
            return (content,)
        elif isinstance(content, collections.Iterable):
            return (i.encode('utf-8') for i in content)
else:
    def _parse_return(content):
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        if isinstance(content, str):
            return (content,)
        elif isinstance(content, collections.Iterable):
            return (i.encode('utf-8') for i in content)


class Request(wsgiref.headers.Headers):
    def __init__(self, request, headers):
        wsgiref.headers.Headers.__init__(self, headers)
        self.forms = cgi.FieldStorage(fp=request['wsgi.input'], environ=request)


class App(object):

    def __init__(self):
        self._routes = []
        self._errors = {}

    def __call__(self, request, start_response):
        headers = [('Content-type', 'text/html')]
        response = Request(request, headers)
        status = '200 OK'
        try:
            for route, method, callback in self._routes:
                if request['REQUEST_METHOD'] != method:
                    continue
                match = re.match(route, request['PATH_INFO'])
                if match is not None:
                    content = self._handle_callback(callback, request, response, *match.groups())
                    break
            else:
                raise HTTPError(404)

        except Exception as e:
            if type(e) is Redirect:
                status, content = self._handle_redirect(response, e)
            elif type(e) is HTTPError:
                status, content = self._handle_error(request, response, e)
            else:
                print(e)
                err = HTTPError(message=str(e))
                status, content = self._handle_error(request, response, err)

        start_response(status, headers)
        return _parse_return(content)

    def _handle_callback(self, callback, request, response, *args):
        wants = []
        for i in callback.wants:
            if i == 'response':
                wants.append(response)
            if i == 'request':
                wants.append(request)
        wants.extend(args)
        return callback(*wants)

    def _handle_error(self, request, response, e):
        status = '{0} {1}'.format(e.code, httplib.responses[e.code])
        callback = self._errors.get(e.code)
        try:
            return status, self._handle_callback(callback, request, response, e.message)
        except Exception as e:
            print(e)
            return status, status

    def _handle_redirect(self, response, e):
        status = '{0} {1}'.format(e.code, httplib.responses[e.code])
        response['Location'] = e.destination
        return status, ''

    def route(self, path, method='GET', wants=()):
        path = '^{0}$'.format(path)
        class Wrapper(object):
            def __init__(self2, func):
                self._routes.append(Route(path, method, self2))
                self2.wants = wants
                self2._func = func
            def __call__(self2, *args):
                return self2._func(*args)
        return Wrapper

    def error(self, code, wants=()):
        class Wrapper(object):
            def __init__(self2, func):
                self._errors[code] = self2
                self2.wants = wants
                self2._func = func
            def __call__(self2, *args):
                return self2._func(*args)
        return Wrapper

    def run(self, host='localhost', port=3030, server=ThreadingWSGIServer):
        port = int(port)
        server = make_server(host, port, self, server)
        print('Serving on http://{0}:{1}...'.format(host, port))
        server.serve_forever()
