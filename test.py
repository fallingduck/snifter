import burrow


app = burrow.App()


@app.route('/')
def home(request, response):
    return 'Hello, world!'


@app.error(404)
def error(request, response, error):
    return 'Ouch!'


app.run()
