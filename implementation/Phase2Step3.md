# Phase 2 — Step 3: `ai_core/config.py`

## What Was Done
Created typed settings models and a loader that merges YAML defaults with env var overrides.

### File: `libs/ai-core/ai_core/config.py`

### Pydantic models (one per section of `config/base.yaml`)

| Model | Fields |
|---|---|
| `AppConfig` | `name`, `env`, `log_level` |
| `LLMConfig` | `provider`, `model`, `temperature`, `max_tokens`, `request_timeout`, `max_retries` |
| `ThinkTankConfig` | `base_url`, `chat_endpoint`, `tenant_id` |
| `OpenAIConfig` | `base_url` |
| `ElasticsearchConfig` | `url`, `username`, `verify_certs`, `request_timeout`, `max_retries` |
| `SparkConfig` | `host`, `port` |
| `TCINConfig` | `data_dir`, `batch_size` |
| `Settings` | Composes all of the above |

### Key functions

```python
load_settings(config_path=None) -> Settings
```
1. Reads YAML file (defaults to `config/base.yaml`; silently skips if missing)
2. Applies `APP__SECTION__KEY=value` env var overrides on top
3. Returns a validated `Settings` instance

```python
get_settings() -> Settings   # @lru_cache — singleton for app use
```

### Env var override format
```
APP__LLM__MODEL=gpt-3.5-turbo      → settings.llm.model
APP__SPARK__PORT=9000              → settings.spark.port (coerced to int)
APP__ELASTICSEARCH__VERIFY_CERTS=false → settings.elasticsearch.verify_certs (coerced to bool)
```
`_coerce()` converts string env values to `bool`, `int`, `float`, or `str` automatically.

### Priority (highest wins)
```
env vars  >  YAML file  >  pydantic defaults
```

## How to Validate
```
uv run python -c "
from ai_core.config import load_settings
s = load_settings()
print(s.app.name, s.llm.provider, s.spark.port)
"
```
Expected: prints `my-test-ai-app thinktank 8000` (from `config/base.yaml`).

```
APP__SPARK__PORT=9999 uv run python -c "
from ai_core.config import load_settings
s = load_settings()
print(s.spark.port)
"
```
Expected: prints `9999`.

### Tests
```
uv run pytest libs/ai-core/tests/test_config.py -v
```
Expected: 9 passed.
