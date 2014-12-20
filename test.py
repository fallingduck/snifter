import snifter


app = snifter.App()


@app.get('/')
def home():
    return 'Hello, world!'


@app.route('/redirect')
def redirect():
    raise snifter.Redirect('/redirected')


@app.route('/redirected')
def yep():
    raise snifter.HTTPError(405, 'Yay?')


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


@app.error(404)
def error(error):
    return 'Ouch!'


app.run()
