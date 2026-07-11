# Local dashboard

The screenshot-style dashboard is a developer demo, separate from the Track 2
submission entrypoint. It is served by `app/demo_server.py` and is excluded
from the Docker image by `.dockerignore`.

## Start it

From the repository root:

```powershell
$env:CLIO_API_KEY = "<your-restricted-novita-key>"
$env:CLIO_ENFORCE_NOVITA = "1"
$env:CLIO_FAST_MODE = "1"
python -m app.demo_server 8787
```

Open <http://127.0.0.1:8787>.

Without an API key, the UI still loads for visual review, but generation
returns a clear configuration message. With a key, the dashboard uses the same
five-anchor, one-call Gemma path as the current release. It does not add a
judge, Claude, Gemini, audio provider, or second caption model.

## Stop it

Press `Ctrl+C` in the terminal running the server. The dashboard is local-only
and binds to `127.0.0.1`; it is not a public deployment or part of the
evaluator's `/input` and `/output` contract.
