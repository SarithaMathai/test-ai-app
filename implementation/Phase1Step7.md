# Phase 1 — Step 7: Create Minimal Entry Points

## What Was Done
Created the bare minimum source files so that `make run-spark` and `make run-tcin` have valid targets to point at. These are placeholder implementations — real logic comes in Phase 5 and Phase 6.

---

### `apps/spark-think-tank-ai/spark_think_tank_ai/main.py`

```python
from fastapi import FastAPI

app = FastAPI(title="Spark Think Tank AI")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

**Why needed:** The Makefile's `run-spark` target calls:
```
uv run uvicorn spark_think_tank_ai.main:app --reload ...
```
Without `main.py` defining `app`, this command fails with `ImportError`.

---

### `apps/tcin-impression-mapping/tcin_impression_mapping/ui/app.py`

```python
import streamlit as st

st.title("TCIN Impression Mapping")
st.write("Application ready.")
```

**Why needed:** The Makefile's `run-tcin` target calls:
```
uv run streamlit run apps/tcin-impression-mapping/tcin_impression_mapping/ui/app.py
```
Without this file, Streamlit errors with `FileNotFoundError`.

---

## How to Validate

### 1 — Files exist
```
type apps\spark-think-tank-ai\spark_think_tank_ai\main.py
type apps\tcin-impression-mapping\tcin_impression_mapping\ui\app.py
```
Expected: each prints the stub content shown above.

### 2 — FastAPI app is importable
```
uv run python -c "from spark_think_tank_ai.main import app; print(app.title)"
```
Expected: prints `Spark Think Tank AI`.

### 3 — Uvicorn can load the app (dry-run)
```
uv run python -c "import uvicorn; uvicorn.run('spark_think_tank_ai.main:app', host='127.0.0.1', port=8000)"
```
Then press Ctrl+C.
Expected: uvicorn starts and prints `Application startup complete` before you stop it.
