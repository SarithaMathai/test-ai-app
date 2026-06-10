# Phase 2 — Step 2: `ai_core/exceptions.py`

## What Was Done
Created the base exception hierarchy used by all `ai-*` packages.

### File: `libs/ai-core/ai_core/exceptions.py`

```
AIError                  ← base for every exception in this project
├── ConfigError          ← bad/missing configuration
└── ProviderError        ← AI provider call failed (has .provider attribute)
    └── RetryExhaustedError  ← all retries used up
```

### Design decisions
- `AIError` carries `.message` (same as `str(err)`) and optional `.code` for machine-readable error codes.
- `ProviderError` adds `.provider` so callers know which service failed without parsing the message string.
- `RetryExhaustedError` inherits `ProviderError` so `except ProviderError` catches both.
- All exceptions are catchable as `AIError` — one broad catch is always available.

## How to Validate
```
uv run python -c "
from ai_core.exceptions import AIError, ConfigError, ProviderError, RetryExhaustedError
e = RetryExhaustedError('failed', provider='openai')
assert isinstance(e, ProviderError)
assert isinstance(e, AIError)
print('exceptions ok')
"
```
Expected: prints `exceptions ok`.

### Tests
```
uv run pytest libs/ai-core/tests/test_exceptions.py -v
```
Expected: 6 passed.
