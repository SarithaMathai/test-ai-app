# ai-thinktank

ThinkTank / Model Garden LLM client for PLM AI services.

Implements the `LLMClient` interface from `ai-core` for Target's ThinkTank (internal LLM gateway). This is the **single import point** for all ThinkTank connectivity — apps should import from here, not from `ai-toss-utils` directly.

## Public API

```python
from ai_thinktank import ThinkTankClient, get_bearer_token, AuthenticatedHttpClient
```

| Export | Source | Purpose |
|---|---|---|
| `ThinkTankClient` | `ai_thinktank.client` | High-level LLM chat client |
| `get_bearer_token` | `ai_toss_utils.token` | Re-exported for convenience |
| `AuthenticatedHttpClient` | `ai_toss_utils.http` | Re-exported for convenience |

## Usage

```python
from ai_core.config import get_settings
from ai_core.llm.base import ChatRequest, ChatMessage
from ai_thinktank import ThinkTankClient

settings = get_settings()
client = ThinkTankClient(settings=settings)

response = await client.chat(ChatRequest(
    messages=[
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="What is the capital of France?"),
    ]
))
print(response.content)   # "Paris"
print(response.model)     # e.g. "gpt-4o"
print(response.usage)     # {"prompt_tokens": 20, "completion_tokens": 5, ...}
```

## Configuration

`ThinkTankClient` is configured entirely through `ai-core`'s `Settings`:

| Setting | Env var override | Default |
|---|---|---|
| `toss.thinktank_url` | `THINKTANK_URL` | — |
| `toss.api_key` | `THINKTANK_API_KEY` | `""` |
| `toss.gateway_api_key` | `THINKTANK_GATEWAY_API_KEY` | `""` |
| `toss.oauth_client_id` | `THINKTANK_OAUTH_CLIENT_ID` | `""` |
| `llm.model` | `LLM_MODEL` | `"gpt-4o"` |
| `llm.max_tokens` | `LLM_MAX_TOKENS` | `2048` |
| `llm.temperature` | `LLM_TEMPERATURE` | `0.0` |

## Running tests

```bash
make test-ai-thinktank
# or
uv run pytest libs/ai-thinktank/tests/unit -v
```

Integration tests require live ThinkTank credentials:

```bash
uv run pytest libs/ai-thinktank/tests/integration -v
```
