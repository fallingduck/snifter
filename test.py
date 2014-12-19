import burrow


app = burrow.App()


@app.route('/')
def home():
    return u'Hello, world!'


@app.route('/redirect')
def redirect():
    raise burrow.Redirect('/redirected')


@app.route('/redirected')
def yep():
    raise burrow.HTTPError(405, 'Yay?')


@app.route('/whoami', wants=('response', 'request'))
@app.route('/whoami/', wants=('response', 'request'))
def whoami(response, request):
    response['Content-type'] = 'text/plain'
    return request['REMOTE_ADDR']


@app.route('/generator')
def generator():
    yield u'a'
    yield 'b'
    yield 'c'


@app.error(404)
def error(error):
    return 'Ouch!'


app.run()
