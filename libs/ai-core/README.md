# ai-core

Zero-dependency foundation library for PLM AI services.

Provides shared configuration loading, exception hierarchy, LLM client abstraction, and logging setup used by every app and library in this monorepo.

## Public API

```python
# Configuration
from ai_core.config import get_settings, Settings

# Exceptions
from ai_core.exceptions import AIError, ConfigError, AuthenticationError, LLMError

# LLM abstraction
from ai_core.llm.base import LLMClient, ChatRequest, ChatResponse, ChatMessage
from ai_core.llm.factory import build_llm_client

# Logging
from ai_core.logging import setup_logging, get_logger
```

## Configuration system

Settings are loaded from two sources in priority order:
1. YAML file at `APP_CONFIG_DIR/base.yaml` (baked into Docker image)
2. Environment variables (injected by TAP at deploy time, or via `.env` locally)

```python
from ai_core.config import get_settings

cfg = get_settings()
print(cfg.toss.thinktank_url)
print(cfg.app.env)
```

`get_settings()` is LRU-cached — it reads files and env once per process start.

### Key environment variables

| Variable | Description |
|---|---|
| `APP_ENV` | `local`, `dev`, `prod`, etc. Controls logging format. |
| `THINKTANK_API_KEY` | TAP secret: API key for ThinkTank. |
| `THINKTANK_GATEWAY_API_KEY` | TAP secret: gateway-level API key (x-api-key header). |
| `THINKTANK_OAUTH_CLIENT_ID` | TAP secret: OAuth client ID (if using OAuth flow). |
| `THINKTANK_OAUTH_CLIENT_SECRET` | TAP secret: OAuth client secret. |
| `THINKTANK_URL` | ThinkTank base URL (override via YAML or env). |

## LLM abstraction

`LLMClient` is an ABC. `build_llm_client()` returns the configured implementation (currently `ThinkTankClient` from `ai-thinktank`). Tests use `NoOpLLMClient` to avoid network calls.

```python
from ai_core.llm.base import ChatRequest, ChatMessage
from ai_core.llm.factory import build_llm_client

client = build_llm_client()
response = await client.chat(ChatRequest(messages=[ChatMessage(role="user", content="Hello")]))
print(response.content)
```

## Logging

Call `setup_logging()` once at app startup. It detects the environment and configures loguru accordingly.

- **Local/dev** (`APP_ENV=local`): colorized human-readable output to stdout.
- **TAP/prod**: TAP-compatible JSON output to stdout.

```python
from ai_core.logging import setup_logging, get_logger

setup_logging(level="INFO")
log = get_logger(__name__)
log.info("Service started")
```

Third-party loggers (uvicorn, fastapi, httpx) are bridged to loguru automatically.

## Running tests

```bash
# From monorepo root
make test-ai-core

# Or directly
uv run pytest libs/ai-core/tests -v
uv run pytest libs/ai-core/tests -m unit
```
