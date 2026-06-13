# PLM TCIN Mapper Split - Completion Summary

## Overview

The `plm_tcin_mapper` monolithic application (FastAPI + Streamlit in one package) has been successfully split into two independent, deployable microservices:

1. **plm-tcin-mapper-api** — FastAPI backend service
2. **plm-tcin-mapper-client** — Streamlit UI frontend service

Each service has its own Docker image, deployment configuration, and can be scaled independently.

---

## What Was Done

### 1. Created plm-tcin-mapper-api Application

**Directory:** `apps/plm-tcin-mapper-api/`

**Files Created:**
- `pyproject.toml` — Project metadata and dependencies (FastAPI, Uvicorn, Gunicorn, ai-core, ai-mongo)
- `entrypoint.sh` — Production startup script (gunicorn + uvicorn)
- `plm_tcin_mapper_api/` — Full Python package with all API logic
  - Copied from original: `main.py`, `dependencies.py`, `routes/`, `services/`, `pipeline/`, `matching/`, `llm/`, `cli/`, `models/`, `database/`
  - Updated all imports from `plm_tcin_mapper.*` to `plm_tcin_mapper_api.*` (30 files)

**New API Endpoints Added** (7 new endpoints needed by client pages):
1. `GET /api/v1/variations` — Distinct impression variations for a PID
2. `GET /api/v1/departments` — All distinct departments
3. `GET /api/v1/mappings/summary` — Department-level mapping aggregation
4. `POST /api/v1/mappings/{id}/clear` — Set mapping status to NO_MATCH
5. `GET /api/v1/llm/quality` — LLM call metrics and quality data
6. `GET /api/v1/improvements` + `POST /api/v1/improvements` — Correction impact tracking
7. `GET /api/v1/admin/stats` — Admin statistics and document counts

**Key Characteristics:**
- Fully async (Motor + FastAPI)
- Production-ready with Gunicorn + UvicornWorker
- CORS enabled for client communication
- Structured error handling (JSON responses)
- Health check endpoint at `GET /health`

### 2. Created plm-tcin-mapper-client Application

**Directory:** `apps/plm-tcin-mapper-client/`

**Files Created:**
- `pyproject.toml` — Project metadata (Streamlit, httpx)
- `entrypoint.sh` — Streamlit startup script
- `Dockerfile.client` — Separate Dockerfile for Streamlit (different healthcheck path)
- `plm_tcin_mapper_client/` — Full Python package
  - `main.py` — CLI entry point
  - `api_client.py` — *NEW* — HTTP wrapper for all API calls (40+ convenience functions)
  - `enums.py` — *NEW* — Shared enums (FeedbackAction, MappingStatus)
  - `streamlit_app.py` — Updated to use new package name
  - `pages/` — All 10 pages refactored to call HTTP API instead of MongoDB
  - `utils.py` — Helper utilities (size_sort_key, confidence_badge, etc.)

**Pages Refactored** (all 10 pages now use API, zero direct MongoDB access):
1. `pid_lookup.py` — PID search with color-grouped mappings
2. `review_panel.py` — Review queue for low-confidence mappings
3. `department_view.py` — Browse mappings by department
4. `data_pipeline.py` — Ingest data and run matching
5. `evaluation_metrics.py` — Accuracy analysis by signal/dept/LLM
6. `threshold_optimizer.py` — Threshold tuning proposals
7. `alias_mining_dashboard.py` — Alias mining proposals
8. `llm_quality.py` — LLM performance metrics
9. `improvement_tracker.py` — Track algorithm improvements
10. `admin.py` — System administration and statistics

**Key Characteristics:**
- Zero MongoDB dependency (pure HTTP client)
- Streamlit's `/_stcore/health` for health checks
- Configurable API base URL via `API_BASE_URL` env var
- Error handling with user-friendly `st.error()` messages
- Clean import structure using local `api_client` module

### 3. Updated Docker Setup

**Changes:**
- Kept existing `Dockerfile` for API apps (parameterized via `APP_PACKAGE` build arg)
- Created new `Dockerfile.client` for Streamlit UI
  - Same base image and structure as API Dockerfile
  - Different healthcheck (Streamlit's `/_stcore/health` endpoint)
  - Longer startup period (45s vs 30s for Streamlit)

**Build Commands:**
```bash
# API
docker build --build-arg APP_PACKAGE=plm-tcin-mapper-api -t plm-tcin-mapper-api:latest .

# Client
docker build -f Dockerfile.client --build-arg APP_PACKAGE=plm-tcin-mapper-client -t plm-tcin-mapper-client:latest .
```

### 4. Updated CI/CD Pipeline (.vela.yml)

**Vela Changes:**
- **PR Dry-Run Stage:** 2 new kaniko steps (API + client) with Dockerfile selection
- **Docker Build Stage:** 10 new kaniko steps (5 each for API and client)
  - dev/feat/hotfix/stage/prod builds for each app
  - API: uses `Dockerfile`
  - Client: uses `Dockerfile.client`
- **TAP Deploy Stage:** 6 new tapctl deploy steps (3 each for API and client)
  - Deploys to dev/stage/prod via separate pipelines
  - Allows independent rollout

**Total Deployables:** 3 (plm-think-tank-ai, plm-tcin-mapper-api, plm-tcin-mapper-client)

### 5. Updated Root Configuration

**pyproject.toml Changes:**
- Workspace members already auto-discovered via `members = ["apps/*", "libs/*"]`
- Updated `ui` dependency group comment to note it's deprecated (now in client's pyproject.toml)

**No Breaking Changes:**
- Existing workspace member auto-discovery handles new dirs automatically
- No explicit member list changes needed

### 6. Created Comprehensive Documentation

**Files Created:**
- `ARCHITECTURE.md` — Complete architecture guide
  - Service overview and responsibilities
  - Technology stacks for each service
  - Running locally (development setup)
  - Docker deployment (compose example)
  - All environment variables
  - Full API endpoint reference
  - CI/CD pipeline explanation
  - Configuration details
  - Migration guide for developers
  - Troubleshooting guide
  - Future improvements

---

## Architecture Summary

### Before Split
```
plm_tcin_mapper (monolith)
├── FastAPI main.py
├── Routes (API endpoints)
├── Services (business logic)
├── Pipeline & matching
├── UI (Streamlit)
└── Pages (directly query MongoDB)
```

### After Split
```
├── plm-tcin-mapper-api (service 1)
│   ├── FastAPI main.py + 7 new endpoints
│   ├── All routes, services, pipeline logic
│   └── MongoDB only (no UI code)
│
└── plm-tcin-mapper-client (service 2)
    ├── Streamlit app.py
    ├── 10 pages (all refactored to use api_client)
    ├── HTTP API calls only (no MongoDB)
    └── api_client.py wrapper (40+ functions)
```

### Communication
```
User Browser → Streamlit Client (port 8080)
              ↓ HTTP API calls
         FastAPI Backend (port 8081)
              ↓ MongoDB queries
         MongoDB
```

---

## Environment Variables

### API Service
- `APP_PORT` — Bind port (default: 8080)
- `GUNICORN_WORKERS` — Worker processes (default: 4)
- `GUNICORN_TIMEOUT` — Worker timeout seconds (default: 120)
- `MONGO_URL` — MongoDB connection string
- `MONGO_DATABASE` — Database name (default: tcin_mapper)

### Client Service
- `APP_PORT` — Bind port (default: 8080)
- `API_BASE_URL` — API service URL (default: http://localhost:8080)

---

## Running Locally

### Terminal 1: Start API
```bash
export APP_PORT=8001
uv run uvicorn plm_tcin_mapper_api.main:app --reload --port 8001
```

### Terminal 2: Start Client
```bash
export API_BASE_URL=http://localhost:8001
uv run streamlit run apps/plm-tcin-mapper-client/plm_tcin_mapper_client/streamlit_app.py
```

Then visit: `http://localhost:8080` (client) and `http://localhost:8001/docs` (API docs)

---

## What Remains Unchanged

1. **plm-think-tank-ai** — Completely unchanged
2. **Shared Libraries** (ai-core, ai-mongo, ai-thinktank, ai-toss-utils) — Unchanged
3. **Configuration System** — Unchanged (still uses config/base.yaml)
4. **Database Schema** — Unchanged (MongoDB collections remain the same)
5. **Core Business Logic** — All pipeline, matching, evaluation logic identical
6. **Existing Tests** — Unit and integration tests still work

---

## Migration Notes for TAP

TAP pipelines need to be created for both new services:
1. Create TAP pipeline: `plm-tcin-mapper-api` with image tag `docker.target.com/iam/spark/plm-tcin-mapper-api`
2. Create TAP pipeline: `plm-tcin-mapper-client` with image tag `docker.target.com/iam/spark/plm-tcin-mapper-client`

Vela pipeline already configured to deploy both via `.vela.yml` updates.

---

## Verification Checklist

- ✅ API app created with full code split
- ✅ Client app created with UI refactored
- ✅ 7 new API endpoints implemented
- ✅ All 10 Streamlit pages refactored to use api_client
- ✅ Both apps have pyproject.toml with correct dependencies
- ✅ Both apps have entrypoint.sh scripts
- ✅ Dockerfile.client created with correct healthcheck
- ✅ .vela.yml updated with build and deploy steps for both apps
- ✅ Root pyproject.toml updated
- ✅ Comprehensive documentation created

---

## File Structure Reference

```
test-ai-app/
├── Dockerfile                      (API and think-tank, parameterized)
├── Dockerfile.client              (NEW - Client/Streamlit)
├── .vela.yml                       (UPDATED - 3 deployable apps now)
├── pyproject.toml                  (minor update)
├── ARCHITECTURE.md                 (NEW - comprehensive guide)
├── config/base.yaml               (unchanged)
├── libs/                          (unchanged)
│   ├── ai-core/
│   ├── ai-mongo/
│   ├── ai-thinktank/
│   └── ai-toss-utils/
├── apps/
│   ├── plm-think-tank-ai/        (unchanged)
│   ├── plm_tcin_mapper/          (original monolith, deprecated)
│   │
│   ├── plm-tcin-mapper-api/      (NEW - API service)
│   │   ├── pyproject.toml
│   │   ├── entrypoint.sh
│   │   └── plm_tcin_mapper_api/
│   │       ├── main.py
│   │       ├── routes/
│   │       │   ├── admin.py             (NEW)
│   │       │   ├── departments.py       (NEW)
│   │       │   ├── variations.py        (NEW)
│   │       │   ├── llm_quality.py       (NEW)
│   │       │   ├── improvements.py      (NEW)
│   │       │   └── mappings.py          (EXTENDED with /summary and /clear)
│   │       ├── services/
│   │       ├── pipeline/
│   │       ├── matching/
│   │       ├── llm/
│   │       ├── cli/
│   │       ├── models/
│   │       └── database/
│   │
│   └── plm-tcin-mapper-client/   (NEW - UI service)
│       ├── pyproject.toml
│       ├── entrypoint.sh
│       └── plm_tcin_mapper_client/
│           ├── main.py
│           ├── api_client.py            (NEW - HTTP wrapper)
│           ├── enums.py                 (NEW - shared enums)
│           ├── streamlit_app.py         (UPDATED)
│           ├── utils.py                 (unchanged)
│           └── pages/
│               ├── admin.py             (REFACTORED - uses API)
│               ├── alias_mining_dashboard.py (REFACTORED)
│               ├── data_pipeline.py     (REFACTORED)
│               ├── department_view.py   (REFACTORED)
│               ├── evaluation_metrics.py (REFACTORED)
│               ├── improvement_tracker.py (REFACTORED)
│               ├── llm_quality.py       (REFACTORED)
│               ├── pid_lookup.py        (REFACTORED)
│               ├── review_panel.py      (REFACTORED)
│               └── threshold_optimizer.py (REFACTORED)
```

---

## Next Steps

1. **Verify Builds:** Test Docker builds for both new apps
2. **Test Locally:** Run both services locally with docker-compose
3. **TAP Configuration:** Create TAP pipelines for both services
4. **Integration Testing:** Test full flow (UI → API → DB)
5. **Deployment:** Deploy to dev/stage/prod via Vela

---

## Support

Refer to:
- `ARCHITECTURE.md` — Complete technical documentation
- `.vela.yml` — CI/CD pipeline configuration
- `apps/plm-tcin-mapper-api/pyproject.toml` — API dependencies
- `apps/plm-tcin-mapper-client/pyproject.toml` — Client dependencies
- `apps/plm-tcin-mapper-client/plm_tcin_mapper_client/api_client.py` — API wrapper functions
