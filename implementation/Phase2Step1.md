# Phase 2 — Step 1: Update `ai-core/pyproject.toml`

## What Was Done
Added two runtime dependencies to `libs/ai-core/pyproject.toml`.

### Before
```toml
dependencies = []
```

### After
```toml
dependencies = [
    "pydantic>=2.0.0,<3.0.0",
    "pyyaml>=6.0.0",
]
```

### Why these two?
| Package | Used by |
|---|---|
| `pydantic` | `config.py` — validates and types the Settings models |
| `pyyaml` | `config.py` — parses `config/base.yaml` |

Both were already installed (transitively via `streamlit`), but declaring them explicitly makes `ai-core` independently installable without relying on other packages' transitive deps.

## How to Validate
```
type libs\ai-core\pyproject.toml
```
Expected: `pydantic` and `pyyaml` appear in `dependencies`.

```
uv sync --all-packages --all-groups
```
Expected: resolves without conflict, last line shows `ai-core` rebuilt.
