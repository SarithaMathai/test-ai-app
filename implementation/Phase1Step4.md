# Phase 1 — Step 4: `pyproject.toml` for Each Library

## What Was Done
Created a `pyproject.toml` inside each library package. These make the folders recognized as proper Python packages by UV and by build tools.

---

### `libs/ai-core/pyproject.toml`

```toml
[project]
name = "ai-core"
version = "0.1.0"
description = "Shared core utilities for AI applications"
requires-python = ">=3.12,<3.13"
dependencies = []          # no external deps — foundation layer

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["ai_core"]     # tells hatchling where the source is
```

**Key decision:** Zero external dependencies. Everything else depends on `ai-core`, not the other way around.

---

### `libs/ai-openai/pyproject.toml`

```toml
[project]
name = "ai-openai"
dependencies = ["ai-core", "openai>=1.0.0,<2.0.0"]
```

**Key decision:** Pins `openai` to `>=1.0.0,<2.0.0` to stay on the v1 async client API.

---

### `libs/ai-thinktank/pyproject.toml`

```toml
[project]
name = "ai-thinktank"
dependencies = ["ai-core"]
```

**Key decision:** Only depends on `ai-core` for now. ThinkTank-specific SDK added in Phase 4.

---

## How to Validate

### 1 — All three files exist
```
type libs\ai-core\pyproject.toml
type libs\ai-openai\pyproject.toml
type libs\ai-thinktank\pyproject.toml
```
Expected: each prints with `[project]` and `[build-system]` sections.

### 2 — UV recognizes the packages
```
uv sync --dry-run
```
Expected: output lists `ai-core`, `ai-openai`, `ai-thinktank` as workspace members.

### 3 — Names match workspace sources
Check that the `name` field in each `pyproject.toml` exactly matches the keys in the root `[tool.uv.sources]`:
- `ai-core` ✓
- `ai-openai` ✓
- `ai-thinktank` ✓

Mismatch here causes "Package not found in workspace" error.
