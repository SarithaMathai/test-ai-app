# ai-toss-utils

OAuth token management and authenticated HTTP client for Target's ThinkTank
and Model Garden APIs.

## What's in here

| Module | Purpose |
|---|---|
| `ai_toss_utils.token` | `get_bearer_token(settings)` — OAuth or API key fallback |
| `ai_toss_utils.http` | `AuthenticatedHttpClient` — retrying HTTP client with auto token injection |

## Authentication strategies

`get_bearer_token` tries strategies in order:

1. **OAuth** (Target internal) — uses `pyOauthTarget` + `tgt_certs`.  
   Requires `THINKTANK_OAUTH_CLIENT_ID` and `THINKTANK_OAUTH_CLIENT_SECRET`.  
   Install with: `uv add "ai-toss-utils[target-auth]"`

2. **API key fallback** — returns `Bearer {THINKTANK_API_KEY}`.  
   Works in any environment without Target-internal packages.

## Usage

```python
from ai_core.config import get_settings
from ai_toss_utils.token import get_bearer_token
from ai_toss_utils.http import AuthenticatedHttpClient

settings = get_settings()

# Token only
token = get_bearer_token(settings)   # "Bearer eyJ..."

# Full HTTP client (auto-refreshes token per request)
client = AuthenticatedHttpClient.from_settings(settings)
response = client.call_chat_completions({
    "model": "llama-3-70b",
    "messages": [{"role": "user", "content": "Hello"}],
})
```

## Required env vars

| Variable | Required for |
|---|---|
| `THINKTANK_API_KEY` | API key auth (strategy 2) |
| `THINKTANK_OAUTH_CLIENT_ID` | OAuth (strategy 1) |
| `THINKTANK_OAUTH_CLIENT_SECRET` | OAuth (strategy 1) |
| `THINKTANK_OAUTH_NUID_USERNAME` | OAuth (strategy 1) |
| `THINKTANK_OAUTH_NUID_PASSWORD` | OAuth (strategy 1) |

Config (non-secret, in `base.yaml`):
```yaml
toss:
  base_url: "https://api.thinktank.example.com"
  chat_endpoint: "/gen_ai_model_requests/v1/chat/completions"
  tenant_id: ""
  token_env_var: "THINKTANK_TOKEN"
  is_prod: "false"
```
