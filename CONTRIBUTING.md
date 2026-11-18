# Contributing

Issues and pull requests are welcome. Keep routing tools narrow and delegate
entity matching and execution to Home Assistant rather than calling services
from model output directly.

Before submitting a change:

```bash
ruff check custom_components cactus_needle/server.py tests
pytest -q
```

Do not add logging of user utterances or model output. New control actions need
tests, explicit safety analysis, and must continue to honor Home Assistant
Assist exposure rules.

