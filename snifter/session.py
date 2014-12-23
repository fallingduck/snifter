import sys
py3 = sys.version_info >= (3,0)

import os
import hashlib
import collections
import time
import datetime
import threading
import contextlib


SESSION_MAX_AGE = 900
COOKIE_MAX_AGE = 0
HTTPS = False
AUTOCLEAN = False


_sessions = {}
SessionInfo = collections.namedtuple('SessionInfo', ('randval', 'expires', 'data'))


class Session(dict):

    def __init__(self, sessid):
        dict.__init__(self)
        self.sessid = sessid

    def destroy(self):
        del _sessions[self.sessid]


def pysessid(ip, randval=None):
    randval = os.urandom(16) if randval is None else bytes(randval)
    ip = ip.encode('utf-8')
    hashed = hashlib.sha512(randval + ip).hexdigest()[:40]
    return hashed, randval


def start(request, response):
    sessid = request.get_cookie('PYSESSID')
    sessinfo = _sessions.get(sessid)
    if sessid is None or sessinfo is None or sessinfo[1] < int(time.time()):
        if sessinfo and sessinfo[1] < int(time.time()):
            sessinfo[2].destroy()
        sessid, randval = pysessid(request['REMOTE_ADDR'])
        expires = int(time.time()) + SESSION_MAX_AGE
        _sessions[sessid] = sessinfo = SessionInfo(randval, expires, Session(sessid))
        if COOKIE_MAX_AGE:
            edate = datetime.datetime.utcnow() + datetime.timedelta(seconds=COOKIE_MAX_AGE)
            cexpires = edate.strftime("%a, %d %b %Y %H:%M:%S GMT")
        else:
            cexpires = None
        https = HTTPS if HTTPS else None
        response.set_cookie('PYSESSID', sessid, expires=cexpires, secure=https, httponly=True)
    if AUTOCLEAN:
        for randval, expires, data in (_sessions.values() if py3 else _sessions.itervalues()):
            if expires < int(time.time()):
                data.destroy()
    return sessinfo[2]


class GC(threading.Thread):

    def run(self):
        self.running = threading.Event()
        while True:
            if self.running.wait(SESSION_MAX_AGE):
                break
            for randval, expires, data in (_sessions.values() if py3 else _sessions.itervalues()):
                if expires < int(time.time()):
                    data.destroy()

    def stop(self):
        self.running.set()


@contextlib.contextmanager
def sessiongc():
    gc = GC()
    try:
        gc.start()
        yield
    finally:
        gc.stop()
