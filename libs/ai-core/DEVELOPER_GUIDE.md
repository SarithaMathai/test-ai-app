# ai-core — Developer Guide

## Local setup

```bash
git clone git@github.target.com:PLM/plm-ai-apps.git
cd plm-ai-apps

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all workspace packages + dev tools
make init

# Run ai-core tests
make test-ai-core
```

See [apps/plm-think-tank-ai/DEVELOPER_GUIDE.md](../../apps/plm-think-tank-ai/DEVELOPER_GUIDE.md) for the full credentials and env var setup.

## Overview

`ai-core` is intentionally minimal and has **zero runtime dependencies** beyond Python's standard library and optional `loguru`. Everything else in the monorepo depends on it, not the other way around.

## Adding a new config field

All configuration is defined in `ai_core/config.py`. The `Settings` object is a nested Pydantic model.

1. Add the field to the appropriate nested config class (`AppConfig`, `ThinkTankConfig`, `LLMConfig`, etc.):

```python
class ThinkTankConfig(BaseModel):
    my_new_field: str = ""            # ← add here
```

2. If the value comes from a TAP secret (not YAML), inject it in `_inject_secrets()`:

```python
def _inject_secrets(settings: Settings) -> None:
    if val := os.getenv("MY_NEW_SECRET"):
        settings.thinktank.my_new_field = val
```

3. Add the variable to `.env.example` and `README.md` env-var table.

4. Add a test in `libs/ai-core/tests/unit/test_config_extended.py`.

## Adding a new exception type

Exceptions live in `ai_core/exceptions.py`. All exceptions inherit from `AIError`:

```python
class MyNewError(AIError):
    """Raised when something specific goes wrong."""
    pass
```

Export it in `ai_core/__init__.py`.

## Extending the LLM abstraction

The `LLMClient` ABC is in `ai_core/llm/base.py`:

```python
class LLMClient(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...
```

To add a new provider, create a concrete class in the relevant lib (e.g., `libs/ai-newaiprovider/`) and register it in `ai_core/llm/factory.py`.

`NoOpLLMClient` in `base.py` is a safe no-op for tests — it returns an empty response without making network calls.

## Updating logging

The logging module (`ai_core/logging.py`) uses loguru. Extend `setup_logging()` to add extra sinks (e.g., a file sink in dev):

```python
if _is_local():
    _loguru_logger.add("debug.log", rotation="10 MB", retention="3 days")
```

The `_is_local()` helper reads `APP_ENV` (aliases: `APP__APP__ENV`). It returns `True` for `local`, `dev`, and `development`.

## Testing conventions

- All tests use `pytest`.
- `tests/conftest.py` has an `autouse` fixture `clear_settings_cache` that resets the LRU cache before/after every test. This prevents test ordering bugs.
- Marker `@pytest.mark.unit` for tests that need no network access.
- Marker `@pytest.mark.integration` for tests that touch real external services (skipped in CI unless credentials are present).
- Patch env vars with `monkeypatch.setenv` or `unittest.mock.patch.dict(os.environ, ...)`.

## Development workflow

```bash
# One-time setup from monorepo root
make init

# Run just ai-core tests
make test-ai-core

# Lint + format
make format

# Type check
uv run mypy libs/ai-core/ai_core
```
