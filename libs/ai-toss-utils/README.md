# ai-toss-utils

OAuth token management and authenticated HTTP client for Target AI platform services.

Handles authentication with ThinkTank/Model Garden APIs using two strategies:
1. **pyOauthTarget** — Target's internal OAuth client (preferred in TAP environments)
2. **Static API key fallback** — when `THINKTANK_API_KEY` is set (useful for local dev)

## Public API

```python
from ai_toss_utils import AuthenticatedHttpClient, get_bearer_token
```

## `get_bearer_token(settings)`

Returns a Bearer token string using the configured auth strategy.

```python
from ai_core.config import get_settings
from ai_toss_utils import get_bearer_token

token = get_bearer_token(settings=get_settings())
# Returns e.g. "eyJhbGci..."
```

**Auth priority:**
1. `pyOauthTarget` is available AND OAuth credentials set → exchange client credentials.
2. `tgt-certs` or `THINKTANK_API_KEY` set → return the API key directly.
3. Empty string (no auth — dev only).

## `AuthenticatedHttpClient`

Wraps `requests.Session` with:
- Automatic Bearer token injection per request.
- Optional `x-api-key` header (`gateway_api_key`).
- Retry-with-backoff on 5xx and network errors (via tenacity).
- `x-tgt-application` and `tenant-id` headers.

```python
from ai_core.config import get_settings
from ai_toss_utils import AuthenticatedHttpClient

client = AuthenticatedHttpClient(settings=get_settings())
response = client.call_chat_completions(payload={"messages": [...]})
```

## Headers sent on every request

| Header | Value source |
|---|---|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer <token>` |
| `x-tgt-application` | `settings.toss.application_name` |
| `tenant-id` | `settings.toss.tenant_id` |
| `x-api-key` | `settings.toss.gateway_api_key` (if set) |

## Running tests

```bash
make test-ai-toss-utils
# or
uv run pytest libs/ai-toss-utils/tests/unit -v
```

Integration tests require live credentials:
```bash
uv run pytest libs/ai-toss-utils/tests/integration -v
```
