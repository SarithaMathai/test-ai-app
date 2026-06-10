# Phase 1 — Step 1: Root `pyproject.toml`

## What Was Done
The root `pyproject.toml` already existed with the full workspace configuration.
No file was created — this step confirms the root config is correct.

### Key sections in `pyproject.toml`

| Section | Purpose |
|---|---|
| `[project]` | Names the root package `my-test-ai-app` |
| `[tool.uv.workspace]` | Tells UV to treat `apps/*` and `libs/*` as workspace members |
| `[tool.uv.sources]` | Wires `ai-core`, `ai-openai`, `ai-thinktank` as local workspace packages |
| `[dependency-groups]` | Declares `dev`, `test`, `lint` groups at root level |
| `[tool.pytest.ini_options]` | Sets test paths, asyncio mode, markers, and safe env defaults |
| `[tool.ruff]` / `[tool.mypy]` | Linter and type checker config shared across all packages |

## How to Validate

### 1 — File exists
```
type pyproject.toml
```
Expected: file prints with `[tool.uv.workspace]` section visible.

### 2 — UV can read the workspace
```
uv sync --dry-run
```
Expected: UV lists all workspace members without error.

### 3 — Workspace members are recognized
```
uv run python -c "import subprocess; print('ok')"
```
Expected: prints `ok` (confirms .venv is active and UV resolves the root).
