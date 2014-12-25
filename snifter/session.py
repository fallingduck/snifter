import os
import hashlib
import collections
import time
import datetime
import threading
import contextlib

from .core import py3


SESSION_MAX_AGE = 900
COOKIE_MAX_AGE = 0
HTTPS = False
AUTOCLEAN = False


_sessions = {}
SessionInfo = collections.namedtuple('SessionInfo', ('randval', 'expires', 'data'))


class Session(dict):

    def __init__(self, sessid, sessdict=_sessions):
        dict.__init__(self)
        self.sessid = sessid
        self._sessions = sessdict

    def destroy(self):
        del self._sessions[self.sessid]


def pysessid(ip, randval=None):
    randval = os.urandom(16) if randval is None else bytes(randval)
    ip = ip.encode('utf-8')
    hashed = hashlib.sha512(randval + ip).hexdigest()[:40]
    return hashed, randval


def start(request, response):
    sessid = request.get_cookie('PYSESSID')
    sessinfo = _sessions.get(sessid)
    expires = int(time.time()) + SESSION_MAX_AGE
    if sessid is None or sessinfo is None or sessinfo[1] < int(time.time()):
        if sessinfo and sessinfo[1] < int(time.time()):
            sessinfo[2].destroy()
        sessid, randval = pysessid(request['REMOTE_ADDR'])
        sessinfo = SessionInfo(randval, expires, Session(sessid))
        if COOKIE_MAX_AGE:
            edate = datetime.datetime.utcnow() + datetime.timedelta(seconds=COOKIE_MAX_AGE)
            cexpires = edate.strftime("%a, %d %b %Y %H:%M:%S GMT")
        else:
            cexpires = None
        https = HTTPS if HTTPS else None
        response.set_cookie('PYSESSID', sessid, expires=cexpires, secure=https, httponly=True)
    _sessions[sessid] = SessionInfo(sessinfo[0], expires, sessinfo[2])
    if AUTOCLEAN:
        for randval, expires, data in (_sessions.values() if py3 else _sessions.itervalues()):
            if expires < int(time.time()):
                data.destroy()
    return sessinfo[2]


class GC(threading.Thread):

    def __init__(self, sesslist=_sessions):
        threading.Thread.__init__(self)
        self._sessions = sesslist

    def run(self):
        self.running = threading.Event()
        while True:
            if self.running.wait(SESSION_MAX_AGE):
                break
            for randval, expires, data in (self._sessions.values() if py3 else self._sessions.itervalues()):
                if expires < int(time.time()):
                    data.destroy()

    def stop(self):
        self.running.set()


@contextlib.contextmanager
def sessiongc():
    if AUTOCLEAN:
        yield
    else:
        gc = GC()
        try:
            gc.start()
            yield
        finally:
            gc.stop()
