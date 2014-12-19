import wsgiref.headers
import collections
import re
import httplib

from .server import ThreadingWSGIServer, make_server
from .error import HTTPError, Redirect


Route = collections.namedtuple('Route', ('path', 'method', 'callback'))


class App(object):

    def __init__(self):
        self._routes = []
        self._errors = {}

    def __call__(self, request, start_response):
        headers = [('Content-type', 'text/html')]
        response = wsgiref.headers.Headers(headers)
        status = '200 OK'
        try:
            for route, method, callback in self._routes:
                if request['REQUEST_METHOD'] != method:
                    continue
                match = re.match(route, request['PATH_INFO'])
                if match is not None:
                    content = callback(request, response, *match.groups())
                    break
            else:
                raise HTTPError(404)

        except Exception as e:
            if type(e) is Redirect:
                status, content = self._handle_redirect(response, e)
            elif type(e) is HTTPError:
                status, content = self._handle_error(request, response, e)
            else:
                err = HTTPError(message=str(e))
                status, content = self._handle_error(request, response, err)

        start_response(status, headers)
        return content

    def _handle_error(self, request, response, e):
        status = '{0} {1}'.format(e.code, httplib.responses[e.code])
        callback = self._errors.get(e.code)
        try:
            return status, callback(request, response, e.message)
        except Exception:
            return status, status

    def _handle_redirect(self, response, e):
        status = '{0} {1}'.format(e.code, httplib.responses[e.code])
        response['Location'] = e.destination
        return status, ''

    def route(self, path, method='GET'):
        path = '^{0}$'.format(path)
        def wrapper(func):
            self._routes.append(Route(path, method, func))
            return func
        return wrapper

    def error(self, code):
        def wrapper(func):
            self._errors[code] = func
            return func
        return wrapper

    def run(self, host='localhost', port=3030, server=ThreadingWSGIServer):
        port = int(port)
        server = make_server(host, port, self, server)
        print 'Serving on http://{0}:{1}...'.format(host, port)
        server.serve_forever()
