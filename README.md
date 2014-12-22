# Snifter

This minimalist web microframework has server-side sessions right out of the box. It also has shortcuts to serve new HTML5 features such as server-sent events (SSE). What has *your* framework done lately?

```python
import snifter

app = snifter.App()

@app.route('/')
def hello():
    return 'Hello, world!'

app.run()
```

Check out [docs/](docs/) for documentation (WIP).