# Phase 2 — Step 4: `ai_core/logging.py`

## What Was Done
Created a structured JSON logger and setup helpers.

### File: `libs/ai-core/ai_core/logging.py`

### Components

#### `JSONFormatter`
Subclasses `logging.Formatter`. Every log record becomes a single-line JSON object:
```json
{"timestamp": "2026-06-08 12:00:00,000", "level": "INFO", "logger": "ai_core.config", "message": "Settings loaded"}
```
When an exception is attached to the record, an `"exception"` field is added with the traceback string.

#### `setup_logging(level, *, json_format)`
- Clears all existing handlers on the root logger (prevents duplicate output)
- Attaches a `StreamHandler` to `stdout`
- Uses `JSONFormatter` when `json_format=True` (default), plain text otherwise
- Sets the root log level

Call **once** at app startup:
```python
from ai_core.logging import setup_logging
setup_logging(level="INFO")
```

#### `get_logger(name)`
Thin wrapper around `logging.getLogger(name)`. Use at the top of every module:
```python
from ai_core.logging import get_logger
logger = get_logger(__name__)
```

## How to Validate
```
uv run python -c "
from ai_core.logging import setup_logging, get_logger
setup_logging(level='INFO')
log = get_logger('demo')
log.info('Phase 2 complete')
"
```
Expected: prints a JSON line like:
```json
{"timestamp": "...", "level": "INFO", "logger": "demo", "message": "Phase 2 complete"}
```

### Tests
```
uv run pytest libs/ai-core/tests/test_logging.py -v
```
Expected: 8 passed.
