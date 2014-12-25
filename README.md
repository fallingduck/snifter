# Snifter

This minimalist web microframework has server-side sessions and a robust templating engine right out of the box. What has *your* framework done lately?

The server-side sessions are also available as WSGI middleware, so you can use them with your other less-cool frameworks too.

```python
import snifter

app = snifter.App()

@app.route('/')
def hello():
    return 'Hello, world!'

app.run()
```

Check out [docs/](docs/) for documentation (WIP).