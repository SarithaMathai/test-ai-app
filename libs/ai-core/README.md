# ai-core

Shared foundation for every app and lib in this monorepo.

## What's in here

| Module | Purpose |
|---|---|
| `ai_core.config` | `load_settings()` — merges `base.yaml` → `local.yaml` → env vars → secrets |
| `ai_core.exceptions` | Base exception hierarchy (`AIError`, `LLMError`, `ConfigError`, …) |
| `ai_core.logging` | `setup_logging()`, `get_logger()`, `JSONFormatter` |
| `ai_core.llm.base` | `LLMClient` ABC, `ChatRequest`, `ChatResponse`, `NoOpLLMClient` |
| `ai_core.llm.factory` | `build_llm_client(settings)` — returns the configured provider client |
| `ai_core.elastic.client` | `ElasticsearchClient.from_settings(settings)` |
| `ai_core.mongo.client` | `MongoClient.from_settings(settings)` |

## Config sections

```yaml
# config/base.yaml
llm:        provider, model, temperature, max_tokens, request_timeout, max_retries
thinktank:  base_url, chat_endpoint, tenant_id
toss:       token_env_var, is_prod          ← secrets injected from env, not here
openai:     base_url
elasticsearch: url, username, verify_certs, request_timeout
mongo:      url, database
```

## Secret env vars (never in YAML)

| Variable | Used by |
|---|---|
| `THINKTANK_API_KEY` | `settings.toss.api_key` |
| `THINKTANK_OAUTH_CLIENT_ID/SECRET` | `settings.toss.oauth_*` |
| `THINKTANK_OAUTH_NUID_USERNAME/PASSWORD` | `settings.toss.oauth_*` |
| `OPENAI_API_KEY` | read directly by `ai_openai.OpenAIClient` |
| `ELASTICSEARCH__PASSWORD` | read by `ElasticsearchClient.from_settings()` |
| `MONGO__USERNAME` / `MONGO__PASSWORD` | read by `MongoClient.from_settings()` |

## Adding a new LLM provider

1. Create `libs/ai-<name>/ai_<name>/client.py` implementing `LLMClient`
2. Add an `if provider == "<name>"` case in `ai_core/llm/factory.py`
3. Set `llm.provider: <name>` in `config/base.yaml` (or `local.yaml`)
