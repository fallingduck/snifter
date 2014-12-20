from wsgiref.simple_server import WSGIServer, make_server

import sys
if sys.version_info >= (3,0):
    from socketserver import ThreadingMixIn
else:
    from SocketServer import ThreadingMixIn


class ThreadingWSGIServer(WSGIServer, ThreadingMixIn):
    pass
