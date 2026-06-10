# Implementation Roadmap

## Overview
This project is a UV monorepo with shared libraries and two AI-powered applications.

---

## Phase 1 — Workspace Scaffolding  ✅ DONE
Create the UV workspace structure: root config, all library packages, all app packages, sync and verify build.

**Deliverables:**
- `libs/ai-core`, `libs/ai-openai`, `libs/ai-thinktank` scaffolded
- `apps/spark-think-tank-ai`, `apps/tcin-impression-mapping` scaffolded
- All packages registered in UV workspace and `uv sync` passes
- `make build-libs` produces wheels without error

---

## Phase 2 — Core Library (`ai-core`)  ✅ DONE
Build the shared foundation all other packages depend on.

**Deliverables:**
- Config loader (reads env vars / `.env`)
- Logging setup (structured JSON logger)
- Base exception types
- Unit tests for all of the above (`make test-core` passes)

---

## Phase 3 — OpenAI Library (`ai-openai`)  ⬜ TODO
Wrap the OpenAI SDK into a clean internal interface.

**Deliverables:**
- `OpenAIClient` class with async chat completion
- Retry / error handling using `ai-core` exceptions
- Unit tests with mocked responses (`make test-openai` passes)

---

## Phase 4 — ThinkTank Library (`ai-thinktank`)  ⬜ TODO
Integrate the ThinkTank AI provider.

**Deliverables:**
- `ThinkTankClient` class with async completion
- Shared interface compatible with `ai-openai` pattern
- Unit tests with mocked responses (`make test-thinktank` passes)

---

## Phase 5 — Spark Think Tank AI App (`apps/spark-think-tank-ai`)  ⬜ TODO
FastAPI application that exposes ThinkTank AI over HTTP.

**Deliverables:**
- `GET /health` endpoint
- `POST /chat` endpoint using `ai-thinktank`
- Request/response Pydantic models
- App-level unit + integration tests (`make test-spark` passes)
- `make run-spark` starts cleanly

---

## Phase 6 — TCIN Impression Mapping App (`apps/tcin-impression-mapping`)  ⬜ TODO
Streamlit UI that uses OpenAI to map TCIN impressions.

**Deliverables:**
- Streamlit page with input and result display
- Backend logic calling `ai-openai`
- App-level unit tests (`make test-tcin` passes)
- `make run-tcin` starts cleanly

---

## Phase 7 — Quality Gates  ⬜ TODO
Wire up all code-quality tooling end to end.

**Deliverables:**
- `make lint` passes (ruff + mypy) across all packages
- `make test-cov` produces coverage report
- `make format` cleans all files
- Pre-commit hooks installed and passing

---

## Phase 8 — Full Integration Test  ⬜ TODO
Confirm the entire workspace builds and tests green together.

**Deliverables:**
- `make init` from a clean clone works
- `make build` produces all 5 wheels
- `make test` passes all unit tests
- `make lint` passes with no errors
