# Snifter

This minimalist web microframework has server-side sessions and websockets right out of the box. What has *your* framework done lately?

```python
import snifter

app = snifter.App()

@app.route('/')
def hello():
    return 'Hello, world!'

app.run()
```

Check out [docs/](docs/) for documentation (WIP).