from snifter import App, Redirect


app = App()


@app.route('/', wants='staticfile')
def index(static_file):
    return static_file('index.html', 'html')


@app.route(r'/(\w+?)', wants='staticfile')
def doc(static_file, name):
    return static_file('{0}.html'.format(name), 'html')


@app.error(404)
def notfound(error):
    raise Redirect('/')


app.run()
