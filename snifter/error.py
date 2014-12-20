class HTTPError(Exception):
    def __init__(self, code=500, message=''):
        self.code = code
        self.message = message


class Redirect(HTTPError):
    def __init__(self, destination, code=303):
        self.destination = destination
        self.code = code
