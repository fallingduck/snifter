import burrow


app = burrow.App()


@app.route('/')
def home(request, response):
    return 'Hello, world!'


@app.route('/redirect')
def redirect(request, response):
    raise burrow.Redirect('/redirected')


@app.route('/redirected')
def yep(request, response):
    raise burrow.HTTPError(405, 'Yay?')


@app.error(404)
def error(request, response, error):
    return 'Ouch!'


app.run()
