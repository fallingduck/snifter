import snifter
import snifter.session


snifter.session.SESSION_MAX_AGE = 10


app = snifter.App()


@app.get('/')
def home():
    return 'Hello, world!'


@app.route('/redirect')
def redirect():
    raise snifter.Redirect('/redirected')


@app.route('/redirected')
def yep():
    raise snifter.HTTPResponse(405, 'Yay?')


@app.get('/whoami', wants=('response', 'request'))
@app.get('/whoami/', wants=('response', 'request'))
def whoami(response, request):
    response['Content-type'] = 'text/plain'
    return request['REMOTE_ADDR']


@app.route('/generator')
def generator():
    yield 'a'
    yield 'b'
    yield 'c'


@app.route('/cookietest', wants=('request', 'response'))
def cookietest(request, response):
    if request.get_cookie('hello'):
        return request.get_cookie('hello')
    else:
        response.set_cookie('hello', 'world')
        return 'Please reload!'


@app.route('/readme', wants='staticfile')
def readme(static_file):
    return static_file('README.md', '.', 'text/x-markdown')


@app.route('/sessstart', wants='session')
def sessstart(session):
    session['in'] = True
    return '<a href="/sessnext">Go to secret page</a>'


@app.route('/sessnext', wants='session')
def sessnext(session):
    if not session.get('in'):
        raise snifter.Redirect('/sessstart')
    return '<a href="/sessend">End session</a>'


@app.route('/sessend', wants='session')
def sessend(session):
    session.destroy()
    raise snifter.Redirect('/sessnext')


@app.error(404)
def error(error):
    return 'Ouch!'


app.run()
