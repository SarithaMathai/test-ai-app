# Phase 2 — Step 5: `ai_core/__init__.py`

## What Was Done
Updated `__init__.py` to re-export the full public API so consumers only need one import.

### File: `libs/ai-core/ai_core/__init__.py`

```python
from ai_core.config import Settings, get_settings, load_settings
from ai_core.exceptions import AIError, ConfigError, ProviderError, RetryExhaustedError
from ai_core.logging import get_logger, setup_logging
```

### What other packages can now do
```python
# Short form — everything from ai_core top level
from ai_core import get_settings, get_logger, setup_logging, AIError

# Long form — direct module import also works
from ai_core.config import load_settings
from ai_core.exceptions import ProviderError
```

## How to Validate
```
uv run python -c "
import ai_core
print(dir(ai_core))
"
```
Expected: output includes `AIError`, `ConfigError`, `Settings`, `get_logger`, `get_settings`, `setup_logging`.

```
uv run python -c "
from ai_core import get_settings, get_logger, setup_logging, AIError
print('all exports ok')
"
```
Expected: prints `all exports ok` with no ImportError.
