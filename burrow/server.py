from SocketServer import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server


class ThreadingWSGIServer(WSGIServer, ThreadingMixIn):
    pass
