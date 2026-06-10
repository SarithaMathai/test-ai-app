# Phase 1 — Step 5: `pyproject.toml` for Each App

## What Was Done
Created a `pyproject.toml` inside each app package. Apps depend on libs and add their own framework dependencies.

---

### `apps/spark-think-tank-ai/pyproject.toml`

```toml
[project]
name = "spark-think-tank-ai"
dependencies = [
    "ai-core",
    "ai-thinktank",
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn[standard]>=0.32.0,<1.0.0",
]
```

**Key decisions:**
- Uses `ai-thinktank` (not `ai-openai`) — this app is the ThinkTank-powered service
- `uvicorn[standard]` includes websocket and watchfiles support needed for `--reload`

---

### `apps/tcin-impression-mapping/pyproject.toml`

```toml
[project]
name = "tcin-impression-mapping"
dependencies = [
    "ai-core",
    "ai-openai",
    "streamlit>=1.40.0,<2.0.0",
]
```

**Key decisions:**
- Uses `ai-openai` — this app calls OpenAI for impression mapping
- Streamlit pinned to `<2.0.0` to avoid breaking API changes

---

## How to Validate

### 1 — Both files exist
```
type apps\spark-think-tank-ai\pyproject.toml
type apps\tcin-impression-mapping\pyproject.toml
```
Expected: each prints with `[project]` and `[build-system]` sections.

### 2 — UV resolves app dependencies
```
uv sync --dry-run
```
Expected: output lists `spark-think-tank-ai` and `tcin-impression-mapping` as workspace members, plus `fastapi`, `uvicorn`, `streamlit` in the install plan.

### 3 — Dependency graph is correct (no circular deps)
```
uv tree
```
Expected: `spark-think-tank-ai` shows `ai-thinktank` → `ai-core` in its tree.
`tcin-impression-mapping` shows `ai-openai` → `ai-core` in its tree.
