# spark-think-tank-ai

FastAPI service that routes user queries to the configured LLM provider (ThinkTank or OpenAI).

## Quick start

```bash
# set your provider secrets in .env, then:
make run-spark
# → http://localhost:8000
```

## API

### `GET /health`
```json
{"status": "ok", "provider": "thinktank", "model": "llama-3-70b"}
```

### `POST /api/v1/chat`
```json
// Request
{
  "operation": "summarise",
  "payload": "Your long text here...",
  "model": null,        // optional override
  "temperature": null,  // optional override
  "max_tokens": null    // optional override
}

// Response
{
  "status": "success",
  "operation": "summarise",
  "result": "A concise summary of...",
  "model": "llama-3-70b",
  "prompt_tokens": 120,
  "completion_tokens": 45
}
```

## Supported operations

| Operation | Response format | Description |
|---|---|---|
| `summarise` | text | 2-3 sentence summary |
| `classify` | JSON `{label, confidence}` | Classify the input |
| `extract` | JSON | Extract structured info |
| `chat` | text | General assistant |

Add new operations in [services/chat_service.py](spark_think_tank_ai/services/chat_service.py) `PROMPT_TEMPLATES`.

## Switching LLM providers

```yaml
# config/base.yaml  (or config/local.yaml for local override)
llm:
  provider: openai      # or: thinktank
  model: gpt-4o
```

No code changes needed — the factory resolves the right client.

## Config reference

See [ARCHITECTURE.md](../../ARCHITECTURE.md) for the full config resolution order.
Non-secret config lives in `config/base.yaml`. Secrets in `.env`.
