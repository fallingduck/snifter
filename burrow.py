__author__ = 'Jack VanDrunen'
__license__ = 'BSD New'
__version__ = '0.0.1'


import wsgiref.headers


class HTTPError(Exception):
    def __init__(self, code=500):
        self.code = code


class Redirect(HTTPError):
    def __init__(self, destination, code=303):
        self.destination = destination
        self.code = code


class App(object):

    def __call__(self, environ, start_response):
        headers = [('Content-type', 'text/html')]
        status = '200 OK'
