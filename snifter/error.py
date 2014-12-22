class HTTPResponse(Exception):
    def __init__(self, code, content=None, message=''):
        self.code = code
        self.message = message
        self.content = content


HTTPError = HTTPResponse


class Redirect(HTTPResponse):
    def __init__(self, destination, code=303):
        self.destination = destination
        self.code = code
