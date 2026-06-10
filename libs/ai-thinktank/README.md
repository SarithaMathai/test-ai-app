# ai-thinktank

ThinkTank / Model Garden chat completion client for this monorepo.

Implements `ai_core.llm.base.LLMClient` — swap to OpenAI by changing one config line.
Uses `ai-toss-utils` for OAuth token management and authenticated HTTP calls.

## Usage

```python
from ai_core.config import get_settings
from ai_core.llm import build_llm_client, ChatMessage, ChatRequest

settings = get_settings()          # llm.provider must be "thinktank"
client   = build_llm_client(settings)

response = client.chat(ChatRequest(
    messages=[
        client.system("You are a helpful assistant."),
        client.user("Summarise this product description."),
    ]
))
print(response.content)
```

## ThinkTank vs OpenAI schema differences

| Field | OpenAI | ThinkTank |
|---|---|---|
| Token limit | `max_tokens` | `max_new_tokens` |
| Extra params | — | `top_p`, `frequency_penalty`, `presence_penalty`, `timeout` |

## Required config (`config/base.yaml`)

```yaml
llm:
  provider: "thinktank"
  model: "llama-3-70b"          # or whatever model is deployed

toss:
  base_url: "https://api.thinktank.example.com"
  chat_endpoint: "/gen_ai_model_requests/v1/chat/completions"
  tenant_id: "your-tenant-id"
```

## Required secrets (`.env`)

```
# Option A — API key (external / dev)
THINKTANK_API_KEY=...

# Option B — OAuth (Target internal)
THINKTANK_OAUTH_CLIENT_ID=...
THINKTANK_OAUTH_CLIENT_SECRET=...
THINKTANK_OAUTH_NUID_USERNAME=...
THINKTANK_OAUTH_NUID_PASSWORD=...
```
