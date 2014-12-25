import time
import datetime

from .core import Request, Response, py3
from .session import Session, SessionInfo, pysessid


class SessionMiddleware(object):

    def __init__(self, application, session_max_age=900, cookie_max_age=0, https=False, autoclean=True):
        self.SESSION_MAX_AGE = session_max_age
        self.COOKIE_MAX_AGE = cookie_max_age
        self.HTTPS = https
        self.AUTOCLEAN = autoclean
        self.application = application
        self._sessions = {}

    def __call__(self, headers, start_response):
        newcookie = False
        request = Request(headers)
        sessid = request.get_cookie('PYSESSID')
        sessinfo = self._sessions.get(sessid)
        expires = int(time.time()) + self.SESSION_MAX_AGE
        if sessid is None or sessinfo is None or sessinfo[1] < int(time.time()):
            if sessinfo and sessinfo[1] < int(time.time()):
                sessinfo[2].destroy()
            sessid, randval = pysessid(request['REMOTE_ADDR'])
            sessinfo = SessionInfo(randval, expires, Session(sessid, self._sessions))
            if self.COOKIE_MAX_AGE:
                edate = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.COOKIE_MAX_AGE)
                cexpires = edate.strftime("%a, %d %b %Y %H:%M:%S GMT")
            else:
                cexpires = None
            https = self.HTTPS if self.HTTPS else None
            newcookie = True
        self._sessions[sessid] = SessionInfo(sessinfo[0], expires, sessinfo[2])
        if self.AUTOCLEAN:
            for randval, expires, data in (self._sessions.values() if py3 else self._sessions.itervalues()):
                if expires < int(time.time()):
                    data.destroy()

        def start_response_2(status, response_headers, exc_info=None):
            if newcookie:
                response = Response(response_headers)
                response.set_cookie('PYSESSID', sessid, expires=cexpires, secure=https, httponly=True)
                response.prepare()
            return start_response(status, response_headers, exc_info)

        headers['snifter.session'] = sessinfo[2]
        content = self.application(headers, start_response_2)
        return content
