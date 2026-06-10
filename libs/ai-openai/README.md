# ai-openai

OpenAI chat completion client for this monorepo.

Implements `ai_core.llm.base.LLMClient` so the rest of the codebase never
imports from `openai` directly — swap to ThinkTank by changing one config line.

## Usage

```python
from ai_core.config import get_settings
from ai_core.llm import build_llm_client, ChatMessage, ChatRequest

settings = get_settings()          # provider must be "openai" in config
client   = build_llm_client(settings)

response = client.chat(ChatRequest(
    messages=[
        client.system("You are a helpful assistant."),
        client.user("What is 2 + 2?"),
    ]
))
print(response.content)
```

## Required env var

```
OPENAI_API_KEY=sk-...
```

## Optional env vars

```
APP__LLM__MODEL=gpt-3.5-turbo       # override model
APP__OPENAI__BASE_URL=https://...   # Azure OpenAI or proxy endpoint
```

## Corporate SSL inspection

If your network uses SSL inspection (common in corporate environments),
install the optional `truststore` extra so the system cert store is used:

```bash
uv add "ai-openai[truststore]"
```
