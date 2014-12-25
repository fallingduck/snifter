import bottle
import snifter
from gevent.wsgi import WSGIServer


app = bottle.Bottle()


@app.route('/')
def home():
    session = bottle.request['snifter.session']
    if session.get('name') is None:
        session['name'] = 'World'
        return 'Please refresh!'
    return 'Hello, %s!' % session['name']


server = WSGIServer(('localhost', 3030), snifter.session_middleware(app))
server.serve_forever()
