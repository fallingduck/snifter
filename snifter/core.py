from __future__ import print_function

import sys
py3 = sys.version_info >= (3,0)

import wsgiref.headers
import collections
import re
import cgi
import mimetypes
import os
import time
import functools

if py3:
    import http.client as httplib
    import http.cookies as Cookie
else:
    import httplib
    import Cookie

from .server import ThreadingWSGIServer, make_server
from .error import HTTPError, Redirect
from .utils import parse_return, parse_date, parse_range_header, file_iter_range


Route = collections.namedtuple('Route', ('path', 'method', 'callback'))


class Request(dict):

    def __init__(self, request):
        dict.__init__(self, request)
        self.forms = cgi.FieldStorage(fp=request['wsgi.input'], environ=request)
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

    def prepare(self):
        for morsel in self.cookies.values():
            header = morsel.output().split(': ')
            self.add_header(*header)


class App(object):

    def __init__(self):
        self._routes = []
        self._errors = {}

    def __call__(self, request, start_response):
        headers = [('Content-type', 'text/html')]
        request = Request(request)
        response = Response(headers)
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
                content = self._handle_redirect(response, e)
            elif type(e) is HTTPError:
                content = self._handle_error(request, response, e)
            else:
                print(e)
                err = HTTPError(message=str(e))
                content = self._handle_error(request, response, err)

        response.prepare()
        start_response(response.status, headers)
        return parse_return(content)

    def _handle_callback(self, callback, request, response, *args):
        wants = []
        for i in callback.wants:
            if i == 'response':
                wants.append(response)
            elif i == 'request':
                wants.append(request)
            elif i == 'static_file':
                wants.append(functools.partial(static_file, request, response))
        wants.extend(args)
        return callback(*wants)

    def _handle_error(self, request, response, e):
        response.set_status(e.code)
        callback = self._errors.get(e.code)
        try:
            return self._handle_callback(callback, request, response, e.message)
        except Exception as e:
            print(e)
            return response.status

    def _handle_redirect(self, response, e):
        response.set_status(e.code)
        response['Location'] = e.destination
        return ''

    def route(self, path, method='GET', wants=()):
        path = '^{0}$'.format(path)
        class Wrapper(object):
            def __init__(self2, func):
                self._routes.append(Route(path, method, self2))
                self2.wants = wants if isinstance(wants, tuple) else (wants,)
                self2._func = func
            def __call__(self2, *args):
                return self2._func(*args)
        return Wrapper

    def get(self, path, wants=()):
        return self.route(path, method='GET', wants=wants)

    def post(self, path, wants=()):
        return self.route(path, method='POST', wants=wants)

    def error(self, code, wants=()):
        class Wrapper(object):
            def __init__(self2, func):
                self._errors[code] = self2
                self2.wants = wants if isinstance(wants, tuple) else (wants,)
                self2._func = func
            def __call__(self2, *args):
                return self2._func(*args)
        return Wrapper

    def run(self, host='localhost', port=3030, server=ThreadingWSGIServer):
        port = int(port)
        server = make_server(host, port, self, server)
        print('Serving on http://{0}:{1}...'.format(host, port))
        server.serve_forever()


def static_file(request, response, filename, root, mimetype=None, download=False, charset='UTF-8'):
    """Adapted from Bottle"""
    root = os.path.abspath(root)
    filename = os.path.abspath(os.path.join(root, filename))

    if not filename.startswith(root):
        raise HTTPError(403, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        raise HTTPError(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        raise HTTPError(403, "Access denied.")

    if mimetype is None:
        if download and download is not True:
            mimetype, encoding = mimetypes.guess_type(download)
        else:
            mimetype, encoding = mimetypes.guess_type(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'
        if encoding is not None:
            response['Content-encoding'] = encoding

    if mimetype[:5] == 'text/' and charset and 'charset' not in mimetype:
        mimetype = '{0}; charset={1}'.format(mimetype, charset)
    response['Content-type'] = mimetype

    if download:
        download = os.path.basename(filename if download is True else download)
        response['Content-disposition'] = 'attachment; filename="{0}"'.format(download)

    stats = os.stat(filename)
    clen = stats.st_size
    response['Content-length'] = str(clen)
    last_modified = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(stats.st_mtime))
    response['Last-modified'] = last_modified

    ims = request.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        response['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        raise HTTPError(304)

    body = open(filename, 'rb')
    response["Accept-ranges"] = "bytes"
    if 'HTTP_RANGE' in request:
        ranges = list(parse_range_header(request['HTTP_RANGE'], clen))
        if not ranges:
            raise HTTPError(416, "Requested Range Not Satisfiable")
        offset, end = ranges[0]
        response["Content-range"] = 'bytes {0}-{1}/{2}'.format(offset, end-1, clen)
        response["Content-length"] = str(end-offset)
        body = file_iter_range(body, offset, end-offset)
        response.set_status(206)
        return body
    return body
