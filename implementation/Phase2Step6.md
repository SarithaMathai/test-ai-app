# Phase 2 — Step 6: Tests

## What Was Done
Created 4 test files covering all 3 modules.

---

### `tests/conftest.py`
Defines one `autouse=True` fixture that clears the `get_settings` LRU cache before and after every test. Without this, a cached `Settings` object from one test bleeds into the next.

---

### `tests/test_exceptions.py` — 6 tests

| Test | What it checks |
|---|---|
| `test_ai_error_stores_message` | `str(err)` and `err.message` both return the message |
| `test_ai_error_stores_code` | Optional `code` field is stored |
| `test_config_error_is_ai_error` | `ConfigError` is a subclass of `AIError` |
| `test_provider_error_stores_provider` | `ProviderError.provider` attribute is set |
| `test_retry_exhausted_is_provider_error` | `RetryExhaustedError` is subclass of both `ProviderError` and `AIError` |
| `test_exceptions_are_catchable_as_base` | `except AIError` catches `RetryExhaustedError` |

---

### `tests/test_config.py` — 9 tests

| Test | What it checks |
|---|---|
| `test_settings_defaults_without_yaml` | All pydantic defaults load when no file present |
| `test_load_values_from_yaml` | YAML values override defaults |
| `test_yaml_partial_override_keeps_defaults` | Only specified keys are overridden |
| `test_invalid_yaml_raises_config_error` | Malformed YAML raises `ConfigError` |
| `test_env_override_string` | `APP__LLM__MODEL` overrides `settings.llm.model` |
| `test_env_override_int` | `APP__SPARK__PORT=9999` is coerced to `int` |
| `test_env_override_bool_true` | `APP__ELASTICSEARCH__VERIFY_CERTS=false` is coerced to `bool` |
| `test_env_override_wins_over_yaml` | Env var beats YAML when both set |
| `test_get_settings_returns_same_instance` | `get_settings()` returns the same object on repeated calls |

---

### `tests/test_logging.py` — 8 tests

| Test | What it checks |
|---|---|
| `test_json_formatter_produces_valid_json` | Output parses as valid JSON |
| `test_json_formatter_fields` | All required fields present: `timestamp`, `level`, `logger`, `message` |
| `test_json_formatter_includes_exception` | Exception records include `"exception"` field with traceback |
| `test_setup_logging_sets_level` | Root logger level is set correctly |
| `test_setup_logging_uses_json_formatter` | Handler uses `JSONFormatter` when `json_format=True` |
| `test_setup_logging_clears_existing_handlers` | Repeated calls don't stack handlers |
| `test_get_logger_returns_named_logger` | Returns a `logging.Logger` with correct name |
| `test_get_logger_different_names_are_different_loggers` | Two different names return different objects |

---

## How to Validate

### Run all ai-core tests
```
uv run pytest libs/ai-core/tests -v
```
Expected: **23 passed** in under 1 second.

### Run per-file
```
uv run pytest libs/ai-core/tests/test_exceptions.py -v   # 6 passed
uv run pytest libs/ai-core/tests/test_config.py -v       # 9 passed
uv run pytest libs/ai-core/tests/test_logging.py -v      # 8 passed
```

### Via Makefile
```
make test-core
```
Expected: 23 passed, exit code 0.
