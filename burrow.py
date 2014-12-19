__author__ = 'Jack VanDrunen'
__license__ = 'BSD New'
__version__ = '0.0.1'


import wsgiref.headers
import collections
import re
import httplib


Route = collections.namedtuple('Route', ('route', 'method', 'callback'))


class HTTPError(Exception):
    def __init__(self, code=500):
        self.code = code


class Redirect(HTTPError):
    def __init__(self, destination, code=303):
        self.destination = destination
        self.code = code


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
                    content = callback(request, response, **match.groupdict())
            else:
                raise HTTPError(404)

        except Exception as e:
            if type(e) is Redirect:
                status, content = self._handle_redirect(response, e.destination, e.code)
            elif type(e) is HTTPError:
                status, content = self._handle_error(response, e.code, e)
            else:
                status, content = self._handle_error(response, 500, e)

        start_response(status, headers)
        return content

    def _handle_error(self, response, code, error):
        status = '{0} {1}'.format(code, httplib.responses[code])
        callback = self._errors.get(code)
        try:
            return status, callback(error)
        except Exception:
            return status, status

    def _handle_redirect(self, response, destination, code):
        status = '{0} {1}'.format(code, httplib.responses[code])
        response['Location'] = destination
        return status, ''
