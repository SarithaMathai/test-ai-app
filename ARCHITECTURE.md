# PLM AI Apps Architecture

## Overview

The `test-ai-app` is a multi-module monorepo containing three deployable applications:

1. **plm-think-tank-ai** — Standalone AI service (FastAPI)
2. **plm-tcin-mapper-api** — TCIN Impression Mapper backend (FastAPI) ← *NEW*
3. **plm-tcin-mapper-client** — TCIN Impression Mapper frontend (Streamlit) ← *NEW*

### Shared Libraries

Located in `libs/`:
- **ai-core** — Configuration, LLM factory, logging, exceptions, HTTP utilities
- **ai-mongo** — MongoDB async client management
- **ai-thinktank** — ThinkTank API client
- **ai-toss-utils** — Token utilities

---

## Recent Changes: plm-tcin-mapper Split

### What Changed

The original `plm-tcin-mapper` monolithic app (FastAPI + Streamlit UI in one package) has been split into two independent services:

#### Before
```
apps/plm_tcin_mapper/
  ├── main.py              (FastAPI)
  ├── routes/              (API endpoints)
  ├── services/            (Business logic)
  ├── pipeline/
  ├── matching/
  ├── ui/                  (Streamlit)
  │   ├── streamlit_app.py
  │   └── pages/
  └── ... (shared code)
```

#### After
```
apps/
  ├── plm-tcin-mapper-api/
  │   ├── pyproject.toml
  │   ├── entrypoint.sh
  │   └── plm_tcin_mapper_api/
  │       ├── main.py
  │       ├── routes/
  │       ├── services/
  │       ├── pipeline/
  │       └── ... (API only, no UI)
  │
  └── plm-tcin-mapper-client/
      ├── pyproject.toml
      ├── entrypoint.sh
      └── plm_tcin_mapper_client/
          ├── main.py
          ├── api_client.py       (NEW: HTTP API wrapper)
          ├── enums.py            (NEW: shared enums)
          ├── streamlit_app.py
          └── pages/              (REFACTORED: API calls only)
```

### Key Benefits

1. **Separation of Concerns** — API and UI are independent services with clear contract (HTTP)
2. **Independent Scaling** — Scale API and UI separately based on demand
3. **Technology Freedom** — Can replace Streamlit UI with any other frontend (React, Vue, etc.) without touching API
4. **Cleaner Testing** — Test API endpoints and UI independently
5. **Deployment Flexibility** — Deploy on separate infrastructure

---

## Architecture

### API Service (plm-tcin-mapper-api)

**Purpose:** RESTful API exposing the TCIN mapping pipeline and data access operations.

**Technology Stack:**
- FastAPI (async web framework)
- Gunicorn + UvicornWorker (production ASGI server)
- Motor (async MongoDB driver)
- Pydantic (request/response schemas)

**Key Files:**
- `plm_tcin_mapper_api/main.py` — FastAPI app factory
- `plm_tcin_mapper_api/routes/` — Endpoint definitions
  - `health.py` — `GET /health`
  - `mappings.py` — Mapping query and CRUD operations
  - `eval.py` — Evaluation endpoints
  - `feedback.py` — User feedback submission
  - `ingest.py` — Data ingestion
  - `alias_mining.py` — Alias mining proposals
  - `threshold_tuning.py` — Threshold optimization
  - `variations.py` — *NEW* — Distinct variations per PID
  - `departments.py` — *NEW* — Distinct departments
  - `llm_quality.py` — *NEW* — LLM metrics
  - `improvements.py` — *NEW* — Correction tracking
  - `admin.py` — *NEW* — Admin statistics

**Dependencies:**
- `ai-core` (config, logging, LLM client)
- `ai-mongo` (MongoDB async client)
- FastAPI, Uvicorn, Gunicorn

**Port:** 8080 (configurable via `APP_PORT` env var)

**Health Check:** `GET /health` returns JSON with service status

### Client Service (plm-tcin-mapper-client)

**Purpose:** Streamlit web UI for TCIN mapping review and administration.

**Technology Stack:**
- Streamlit (Python web app framework)
- httpx (async HTTP client)

**Key Files:**
- `plm_tcin_mapper_client/main.py` — Entrypoint for CLI
- `plm_tcin_mapper_client/streamlit_app.py` — App definition with page navigation
- `plm_tcin_mapper_client/api_client.py` — *NEW* — HTTP wrapper around API endpoints
- `plm_tcin_mapper_client/enums.py` — *NEW* — Shared enums (FeedbackAction, MappingStatus)
- `plm_tcin_mapper_client/pages/` — Page definitions
  - `pid_lookup.py` — Search and review by PID
  - `review_panel.py` — Review queue for low-confidence mappings
  - `department_view.py` — Browse mappings by department
  - `data_pipeline.py` — Ingest data and run mapping
  - `evaluation_metrics.py` — Accuracy analysis
  - `threshold_optimizer.py` — Threshold tuning UI
  - `alias_mining_dashboard.py` — Alias mining proposals
  - `llm_quality.py` — LLM performance metrics
  - `improvement_tracker.py` — Track algorithm improvements
  - `admin.py` — System administration

**Dependencies:**
- Streamlit
- httpx (HTTP client library)

**Port:** 8080 (configurable via `APP_PORT` env var)

**Health Check:** Streamlit's internal endpoint `/_stcore/health`

**API Communication:** All database access goes through HTTP calls to the API service. The API base URL is configurable via `API_BASE_URL` env var (default: `http://localhost:8080`).

---

## Running Locally

### Prerequisites

- Python 3.12
- `uv` package manager
- MongoDB running locally on `mongodb://localhost:27017`

### Install Dependencies

```bash
cd test-ai-app

# Install all workspace dependencies
uv sync --all-packages --all-groups

# Or install specific app
uv sync --package plm-tcin-mapper-api
uv sync --package plm-tcin-mapper-client
```

### Run API Locally

```bash
# Development mode (with auto-reload)
uv run uvicorn plm_tcin_mapper_api.main:app --reload --port 8001

# Or via entrypoint (production-like with gunicorn)
export APP_PORT=8001 GUNICORN_WORKERS=1
./.venv/bin/gunicorn plm_tcin_mapper_api.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 1 --bind 0.0.0.0:8001
```

### Run Streamlit Client Locally

```bash
# Make sure API is running on :8001
export API_BASE_URL=http://localhost:8001

# Development mode
uv run streamlit run apps/plm-tcin-mapper-client/plm_tcin_mapper_client/streamlit_app.py --server.port 8080

# Then open http://localhost:8080 in your browser
```

### Run Both Together (Development)

Terminal 1:
```bash
export APP_PORT=8001
uv run uvicorn plm_tcin_mapper_api.main:app --reload --port 8001
```

Terminal 2:
```bash
export API_BASE_URL=http://localhost:8001
uv run streamlit run apps/plm-tcin-mapper-client/plm_tcin_mapper_client/streamlit_app.py --server.port 8080
```

---

## Docker Deployment

### Build Images

API service:
```bash
docker build --build-arg APP_PACKAGE=plm-tcin-mapper-api -t plm-tcin-mapper-api:latest .
```

Client service:
```bash
docker build -f Dockerfile.client --build-arg APP_PACKAGE=plm-tcin-mapper-client -t plm-tcin-mapper-client:latest .
```

### Run with Docker Compose

```yaml
version: '3.8'
services:
  # MongoDB
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: tcin_mapper

  # API service
  api:
    image: plm-tcin-mapper-api:latest
    ports:
      - "8001:8080"
    environment:
      APP_PORT: 8080
      MONGO_URL: mongodb://mongo:27017
    depends_on:
      - mongo

  # Client service
  client:
    image: plm-tcin-mapper-client:latest
    ports:
      - "8080:8080"
    environment:
      APP_PORT: 8080
      API_BASE_URL: http://api:8080
    depends_on:
      - api
```

Then:
```bash
docker-compose up
# API: http://localhost:8001
# Client: http://localhost:8080
```

---

## Environment Variables

### Common

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `8080` | Port to listen on |
| `APP_ENV` | `development` | Environment (development, staging, production) |
| `APP_CONFIG_DIR` | `/app/config` | Configuration directory; `/tap/config` if TAP-mounted |

### API Service

| Variable | Default | Description |
|----------|---------|-------------|
| `GUNICORN_WORKERS` | `4` | Number of Gunicorn worker processes |
| `GUNICORN_TIMEOUT` | `120` | Worker timeout in seconds |
| `MONGO_URL` | `mongodb://localhost:27017` | MongoDB connection URL |
| `MONGO_DATABASE` | `tcin_mapper` | Database name |

### Client Service

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8080` | Base URL for API service |
| `STREAMLIT_LOGGER_LEVEL` | `info` | Logging level |

### LLM/AI Settings (via config/base.yaml)

See [base.yaml](config/base.yaml) for:
- LLM provider and model configuration
- ThinkTank API settings
- Matching thresholds
- MongoDB connection details
- Evaluation metrics configuration

---

## API Endpoints

### Health & Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| GET | `/api/v1/admin/stats` | Admin statistics (document counts) |

### Mappings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/mappings` | List mappings (with filters: pid, status, department) |
| GET | `/api/v1/mappings/summary` | Dept-level mapping summary |
| POST | `/api/v1/mappings/run` | Run matching pipeline |
| POST | `/api/v1/mappings/{id}/clear` | Clear a mapping (set status=NO_MATCH) |

### Variations & Departments

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/variations` | Get distinct variations for a PID |
| GET | `/api/v1/departments` | Get all departments |

### Feedback & Corrections

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/feedback` | Submit feedback on a mapping |
| GET | `/api/v1/improvements` | Get correction impact records |
| POST | `/api/v1/improvements` | Create a correction impact record |

### Evaluation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/eval/run` | Run basic evaluation |
| GET | `/api/v1/eval/latest` | Get latest basic eval |
| POST | `/api/v1/eval/detailed` | Run detailed evaluation |
| GET | `/api/v1/eval/detailed/latest` | Get latest detailed eval |

### Data Ingestion

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ingest` | Ingest CSV data |

### Threshold Tuning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/threshold-tuning/proposals` | List threshold proposals |
| POST | `/api/v1/threshold-tuning/analyze` | Generate threshold proposals |
| POST | `/api/v1/threshold-tuning/proposals/{id}/apply` | Apply a proposal |

### Alias Mining

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/alias-mining/proposals` | List alias proposals |
| POST | `/api/v1/alias-mining/analyze` | Generate alias proposals |
| POST | `/api/v1/alias-mining/proposals/{id}/apply` | Apply a proposal |

### LLM Quality

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/llm/quality` | Get LLM call quality metrics |

### Other

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/shadow/compare` | Compare shadow vs baseline |
| POST | `/api/v1/batch/start` | Start batch job |
| GET | `/api/v1/batch/status/{id}` | Get batch job status |
| GET | `/api/v1/batch/list` | List batch jobs |

---

## CI/CD Pipeline (.vela.yml)

### Stages

1. **install** — Install dependencies
2. **check-lint** — Lint and format checks (ruff)
3. **check-unit-test** — Run unit tests
4. **docker-build-pr** — PR dry-run Docker builds (no push)
5. **docker-build** — Build and push Docker images
6. **tap-deploy** — Deploy via TAP (Target Application Platform)

### Build Environments

- **dev** (main branch push) → image tag `b{build}-{sha8}`
- **feat** (feat/* branch push) → image tag `feat{build}-{sha8}`
- **hotfix** (hotfix/* branch push) → image tag `b{build}-{sha8}-hot`
- **stage** (v*-rc tag) → image tag `{version}`
- **prod** (v* tag) → image tag `{version}` + `latest`

### Deployable Apps

For each push/tag, Docker images are built for:
- `plm-think-tank-ai` (existing)
- `plm-tcin-mapper-api` (NEW)
- `plm-tcin-mapper-client` (NEW)

TAP deployments trigger for each app separately, enabling independent rollout.

---

## Configuration

Configuration is loaded from `config/base.yaml` (baked into image) and can be overridden at deploy time via TAP mounting at `/tap/config`.

Key config sections:
- `app` — App name, environment, log level
- `llm` — LLM provider and model settings
- `mongo` — MongoDB connection
- `spark` — FastAPI host/port settings
- `matching` — Matching algorithm thresholds
- `ingestion` — Data pipeline settings
- `eval` — Evaluation metric thresholds

---

## Migration from Monolith

### For Operators/Users

No changes required. The Streamlit UI at `http://localhost:8080` works the same way, but now calls a separate API service instead of accessing MongoDB directly.

### For Developers

#### Using the API

Instead of direct MongoDB queries in UI code, use `api_client` module:

```python
from plm_tcin_mapper_client import api_client

# Old way (MongoDB)
db = get_db()
mappings = list(db.mappings.find({"pid": "ABC123"}))

# New way (HTTP)
result = api_client.get_mappings(pid="ABC123")
mappings = result.get("mappings", [])
```

#### Calling Other APIs

All 10 Streamlit pages have been refactored to use `api_client`:

```python
# Get variations for a PID
variations = api_client.get_variations(pid="ABC123")

# Submit feedback
api_client.submit_feedback(feedback_dict)

# Run evaluation
eval_result = api_client.run_eval_detailed()

# Get admin stats
stats = api_client.get_admin_stats()
```

#### Adding New Pages

New Streamlit pages should always use `api_client`, never direct MongoDB:

```python
from plm_tcin_mapper_client import api_client

def my_new_page():
    data = api_client.get_mappings(limit=100)
    # render UI...
```

---

## Testing

### Unit Tests

Run unit tests (no external services required):
```bash
uv run pytest -m unit -v
```

### Integration Tests

Run integration tests (MongoDB required):
```bash
uv run pytest -m integration -v
```

---

## Troubleshooting

### Client can't connect to API

Check `API_BASE_URL` environment variable:
```bash
export API_BASE_URL=http://api-service-hostname:8080
```

### API can't connect to MongoDB

Check `MONGO_URL` environment variable:
```bash
export MONGO_URL=mongodb://mongo-host:27017
```

### Streamlit stuck on startup

Increase the healthcheck `start-period` or check logs:
```bash
docker logs plm-tcin-mapper-client
```

### API endpoints return 503 (MongoDB Error)

MongoDB connection failed. Check network and credentials in config.

---

## Future Improvements

1. **Authentication** — Add auth middleware to API and client
2. **WebSocket** — Real-time updates instead of polling
3. **GraphQL** — Alternative query interface for UI
4. **React/Vue UI** — Replace Streamlit with modern SPA
5. **Caching** — Add Redis caching layer for frequently accessed data
6. **Rate Limiting** — Add rate limiting to API
7. **API Documentation** — Auto-generated OpenAPI/Swagger docs
