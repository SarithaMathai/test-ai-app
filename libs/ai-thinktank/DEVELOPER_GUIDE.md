# ai-thinktank — Developer Guide

## Local setup

```bash
git clone git@github.target.com:PLM/plm-ai-apps.git
cd plm-ai-apps

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all workspace packages + dev tools
make init

# Run ai-thinktank tests
make test-ai-thinktank
```

See [apps/plm-think-tank-ai/DEVELOPER_GUIDE.md](../../apps/plm-think-tank-ai/DEVELOPER_GUIDE.md) for credentials and env var setup.

## Design

`ThinkTankClient` is a thin adapter:

1. Receives a `ChatRequest` (from `ai-core`).
2. Translates it to the ThinkTank REST payload format (`/v1/chat/completions`).
3. Delegates the HTTP call to `AuthenticatedHttpClient` (from `ai-core`).
4. Parses the response into `ChatResponse`.

## Payload format

ThinkTank expects OpenAI-compatible `/v1/chat/completions`:

```json
{
  "model": "gpt-4o",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 2048,
  "temperature": 0.0
}
```

The client adds `max_tokens` and `temperature` from `settings.llm`. To add more parameters, extend `ThinkTankClient.chat()` in `ai_thinktank/client.py`.

## Error handling

`ThinkTankClient` converts HTTP and auth errors to `ai-core` exception types:

| Situation | Exception raised |
|---|---|
| Auth fails (401/403) | `AuthenticationError` |
| HTTP 4xx (non-auth) | `ProviderError` |
| HTTP 5xx | `LLMError` |
| Network timeout | `LLMError` |
| Bad response shape | `LLMError` |

Always catch `AIError` (base class) at the application boundary.

## Testing

Unit tests mock `AuthenticatedHttpClient`:

```python
from unittest.mock import MagicMock, patch
from ai_thinktank import ThinkTankClient

def test_chat_returns_content(mock_settings):
    mock_http = MagicMock()
    mock_http.call_chat_completions.return_value = {
        "choices": [{"message": {"content": "Paris"}}],
        "model": "gpt-4o",
        "usage": {},
    }
    with patch("ai_thinktank.client.AuthenticatedHttpClient", return_value=mock_http):
        client = ThinkTankClient(settings=mock_settings)
        response = client.chat(...)
        assert response.content == "Paris"
```

## Adding a new LLM provider

1. Create `libs/ai-<provider>/` as a new workspace member.
2. Implement `LLMClient` ABC from `ai-core`.
3. Register it in `ai_core/llm/factory.py` based on `settings.llm.provider`.
4. Update `.env.example` with any new env vars.
