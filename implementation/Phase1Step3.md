# Phase 1 — Step 3: Create All Package Directories

## What Was Done
All `libs/` and `apps/` directories were missing. Created the full folder tree for every workspace member.

### Directories created

```
libs/
  ai-core/
    ai_core/          ← Python source package
    tests/            ← pytest tests for ai-core
  ai-openai/
    ai_openai/        ← Python source package
    tests/            ← pytest tests for ai-openai
  ai-thinktank/
    ai_thinktank/     ← Python source package
    tests/            ← pytest tests for ai-thinktank

apps/
  spark-think-tank-ai/
    spark_think_tank_ai/   ← Python source package
    tests/                 ← pytest tests for spark app
  tcin-impression-mapping/
    tcin_impression_mapping/
      ui/             ← Streamlit UI submodule
    tests/            ← pytest tests for tcin app
```

### Why this layout?
- UV workspace requires each member to be in `apps/*` or `libs/*` (matching the glob in `pyproject.toml`)
- Python package names use underscores (`ai_core`) while project/folder names use hyphens (`ai-core`) — standard Python convention
- `tests/` sits alongside the source package so `make test-core` can target `libs/ai-core/tests`

## How to Validate

### 1 — All directories exist
```
ls libs\
ls apps\
```
Expected: `ai-core`, `ai-openai`, `ai-thinktank` under libs; `spark-think-tank-ai`, `tcin-impression-mapping` under apps.

### 2 — Source package dirs exist
```
ls libs\ai-core\
ls apps\spark-think-tank-ai\
```
Expected: each shows both a `tests/` folder and a Python package folder (e.g. `ai_core/`).

### 3 — No stray files
```
ls libs\ai-core\ai_core\
```
Expected: only `__init__.py` at this stage — no extra files yet (content comes in Phase 2).
