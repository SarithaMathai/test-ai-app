# PLM AI Apps — Complete Setup & API Testing Guide

This guide walks you through everything needed to clone, configure, and test both **plm-think-tank-ai** and **plm-tcin-mapper** services.

---

## 🚀 Quick Start (5 minutes)

```bash
# 1. Clone and enter the repo
git clone git@github.target.com:PLM/plm-ai-apps.git
cd plm-ai-apps

# 2. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Set up ThinkTank credentials (shared by both apps)
cp .env.example .env
# Edit .env and set THINKTANK_API_KEY (or OAuth credentials)

# 4. Run both services at once
make init          # Installs all dependencies
make run-plm       # Starts both APIs: :8000 and :8001
```

---

## 📋 Prerequisites

| Tool | Requirement | Why |
|------|-------------|-----|
| **Python** | 3.12 (auto-managed by uv) | Required by the monorepo |
| **uv** | Latest | Fast package installer; manages Python versions |
| **git** | Any | Clone the repo |
| **MongoDB** | 6.x+ (for tcin-mapper only) | Data persistence for design→color mappings |
| **curl** or Insomnia | Optional | Testing API endpoints |
| **Target network access** | If on Target machines | Some Artifactory dependencies require it |

---

## 🔧 Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone git@github.target.com:PLM/plm-ai-apps.git
cd plm-ai-apps
```

### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env  # Restart shell, or source this
uv --version            # Verify installation
```

### 3. Configure Shared Credentials (Root .env)

This `.env` file is shared by both services. **Only MongoDB is app-specific; other secrets are shared.**

```bash
cp .env.example .env
```

Edit `.env` and choose ONE authentication method for ThinkTank:

**Option A — Static API Key (simplest for local dev):**
```bash
THINKTANK_API_KEY=your-api-key-here
```

**Option B — OAuth (Target internal environments):**
```bash
THINKTANK_OAUTH_CLIENT_ID=your-client-id
THINKTANK_OAUTH_CLIENT_SECRET=your-client-secret
# Optional — only if your OAuth flow requires NUID:
THINKTANK_OAUTH_NUID_USERNAME=your-nuid
THINKTANK_OAUTH_NUID_PASSWORD=your-password
```

**Option C — Test without LLM (no credentials needed):**
```bash
APP__LLM__PROVIDER=none
```

### 4. Start MongoDB (tcin-mapper only)

MongoDB is **only** required if you plan to run **plm-tcin-mapper**. The **plm-think-tank-ai** service does not use MongoDB.

**Option A — Docker (recommended):**
```bash
docker run -d --name tcin-mongo -p 27017:27017 mongo:7
```

**Option B — Local MongoDB:**
If you already have MongoDB installed:
```bash
mongod --dbpath /path/to/data
```

**Option C — Remote MongoDB:**
Update the MongoDB URL in `apps/plm-tcin-mapper/.env` (step 5b below).

### 5a. Install All Packages

```bash
make init
# This runs: uv sync --all-packages --all-groups
# Creates a single .venv at the monorepo root covering all libs + apps
```

### 5b. (Optional) Configure plm-tcin-mapper App-Specific Settings

If you're running **plm-tcin-mapper**, it needs its own `.env` on top of the root `.env`:

```bash
cp apps/plm-tcin-mapper/.env.secrets apps/plm-tcin-mapper/.env
```

Edit `apps/plm-tcin-mapper/.env` and set MongoDB URL:

```bash
APP__MONGO__URL=mongodb://localhost:27017
APP__MONGO__DATABASE=tcin_mapper
APP__SPARK__PORT=8001
```

> **Note:** All ThinkTank credentials are inherited from the root `.env`. You only need MongoDB here.

---

## ▶️ Running the Services

### Option 1: Run Both Services (Think Tank + TCIN Mapper)

```bash
make run-plm
```

This starts:
- **plm-think-tank-ai** on `http://localhost:8000`
- **plm-tcin-mapper** on `http://localhost:8001`

### Option 2: Run Individual Services

```bash
# Think Tank only
make run-thinktank

# TCIN Mapper only
make run-tcin-mapper

# TCIN Mapper UI (Streamlit operator tool)
make run-tcin-ui  # http://localhost:8501
```

### Verify Services Are Running

```bash
# Think Tank health
curl http://localhost:8000/health

# TCIN Mapper health
curl http://localhost:8001/health
```

---

## 🧪 Testing the APIs

### Option 1: Using Insomnia (Recommended)

1. Import `insomnia-collection.json` into Insomnia:
   - File → Import → Select the `.json` file
   - Select the "Local Development" environment
   - Update variables if needed (base URLs, PIDs, etc.)

2. Click any request and hit **Send**

### Option 2: Using curl (Command Line)

#### PLM Think Tank AI

```bash
# Health check
curl http://localhost:8000/health | jq .

# Spell check
curl -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Ths is a smple sentense.",
    "operation": "spell_check"
  }' | jq .

# Generate unit tests
curl -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "content": "public class Calculator { public int add(int a, int b) { return a + b; } }",
    "operation": "unit_test"
  }' | jq .
```

#### PLM TCIN Mapper

```bash
# Health check
curl http://localhost:8001/health | jq .

# Ingest a data chunk
curl -X POST http://localhost:8001/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"chunk": "chunk_01"}'

# Run mapping for a single PID
curl -X POST http://localhost:8001/api/v1/mappings/run \
  -H "Content-Type: application/json" \
  -d '{
    "pid": "PID-0L20P5",
    "use_llm": false,
    "dry_run": false
  }' | jq .

# Query all mappings
curl "http://localhost:8001/api/v1/mappings?page=1&page_size=50" | jq .

# Get evaluation metrics
curl http://localhost:8001/api/v1/eval/latest | jq .
```

---

## 📊 Understanding the Data Flow

### PLM Think Tank AI

```
User Input (spell check / unit test)
         ↓
FastAPI Route (/api/v1/prompt)
         ↓
Prompt Service (maps operation → system+user prompt)
         ↓
LLM Client (ai-core)
         ↓
ThinkTank Gateway
         ↓
Claude / Gemini Model
         ↓
Response with tokens, model info
```

**MongoDB:** Not used. No data persistence.

### PLM TCIN Mapper

```
CSV Data Files
         ↓
Ingestion Route (/api/v1/ingest)
         ↓
Parse CSVs & upsert to MongoDB
         ↓
Query Mappings (/api/v1/mappings)
         ↓
Run Pipeline (/api/v1/mappings/run)
         ↓
1. Score colors (fuzzy matching)
2. Assign via deterministic algorithm (3 rounds)
3. Fallback to LLM for low-confidence pairs
         ↓
Persist results to MongoDB mappings collection
         ↓
Evaluation (/api/v1/eval/run) — compute metrics
         ↓
Human feedback (/api/v1/feedback) — CONFIRM/REJECT/CORRECT
         ↓
Streamlit UI (optional) — review & correct in browser
```

**MongoDB:** Required. Stores:
- `tcin_color_records` — guest-facing TCIN colors
- `variation_records` — design impression names (from CSV)
- `mappings` — results of color→impression matching
- `feedback` — human corrections & validation
- `eval_snapshots` — accuracy metrics over time

---

## 🧪 Running Tests

```bash
# All tests
make test

# Fast unit tests only
make test-unit

# Integration tests (need credentials)
make test-int

# Full suite with coverage
make test-cov
open htmlcov/index.html  # View coverage report
```

---

## 🐳 Docker

### Build Images

```bash
# Both apps
make docker-build

# TCIN Mapper only
make docker-build-tcin-mapper
```

### Run in Docker

```bash
# Think Tank
docker run --rm -p 8080:8080 \
  -e THINKTANK_API_KEY=your-key \
  plm-ai-apps:local

# TCIN Mapper (requires MongoDB URL reachable from container)
docker run --rm -p 8080:8080 \
  -e APP__MONGO__URL=mongodb://host.docker.internal:27017 \
  -e APP__MONGO__DATABASE=tcin_mapper \
  -e APP__LLM__PROVIDER=none \
  plm-tcin-mapper:local

curl http://localhost:8080/health
```

---

## 📚 API Endpoint Reference

### PLM Think Tank AI (Port 8000)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check |
| `POST` | `/api/v1/prompt` | Execute an AI prompt (spell_check, unit_test) |

**Response format:**
```json
{
  "result": "Corrected text...",
  "operation": "spell_check",
  "model": "gemini-1.5-pro",
  "usage": {
    "prompt_tokens": 145,
    "completion_tokens": 312,
    "total_tokens": 457
  }
}
```

### PLM TCIN Mapper (Port 8001)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health + MongoDB + LLM provider status |
| `POST` | `/api/v1/ingest` | Load CSV chunks into MongoDB |
| `POST` | `/api/v1/mappings/run` | Run matching pipeline |
| `GET` | `/api/v1/mappings` | Query results (paginated) |
| `POST` | `/api/v1/feedback` | Submit human corrections |
| `POST` | `/api/v1/eval/run` | Compute accuracy metrics |
| `GET` | `/api/v1/eval/latest` | Fetch latest evaluation snapshot |

---

## ⚙️ Configuration Reference

### Root .env (Shared by both apps)

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP__APP__ENV` | `development` | Environment: `local` / `dev` / `prod` |
| `APP__APP__LOG_LEVEL` | `INFO` | Log level: `DEBUG` / `INFO` / `WARNING` |
| `APP__LLM__PROVIDER` | `thinktank` | LLM backend: `thinktank` / `openai` / `none` |
| `APP__LLM__MODEL` | `gemini-1.5-pro` | Model name |
| `THINKTANK_API_KEY` | — | Static API key (leave blank if using OAuth) |
| `THINKTANK_OAUTH_CLIENT_ID` | — | OAuth client ID (Target internal) |
| `THINKTANK_OAUTH_CLIENT_SECRET` | — | OAuth client secret |

### TCIN Mapper .env (App-specific, `apps/plm-tcin-mapper/.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP__MONGO__URL` | `mongodb://localhost:27017` | MongoDB connection URL |
| `APP__MONGO__DATABASE` | `tcin_mapper` | Database name |
| `APP__SPARK__PORT` | `8001` | HTTP server port |
| `APP__MATCHING__AUTO_CONFIRM_THRESHOLD` | `0.85` | Score ≥ this → AUTO_CONFIRM |
| `APP__MATCHING__NO_MATCH_THRESHOLD` | `0.75` | Score < this → NO_MATCH |
| `APP__MATCHING__LLM_FALLBACK_THRESHOLD` | `0.60` | Score < this → ask LLM |

> **MongoDB is required ONLY for tcin-mapper.** Think Tank does not need MongoDB.

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| `uv sync` fails with "conflicting URLs" | `rm -rf .venv && uv sync --all-packages --all-groups` |
| `/health` returns `"mongo_ok": false` | Start MongoDB or update `APP__MONGO__URL` |
| `ModuleNotFoundError: ai_core` | Run from repo root, not from app subdirectory |
| 401 error from ThinkTank | Check `THINKTANK_API_KEY` in `.env` is set correctly |
| Tests fail in CI but pass locally | Clear cache: `make clean && make init` |
| Streamlit UI not found | Install UI dependencies: `uv sync --group ui` |

---

## 📖 Full Documentation

- **Root README:** `README.md` — monorepo overview & commands
- **Think Tank Developer Guide:** `apps/plm-think-tank-ai/DEVELOPER_GUIDE.md`
- **TCIN Mapper Developer Guide:** `apps/plm-tcin-mapper/DEVELOPER_GUIDE.md`
- **TCIN Mapper Architecture:** `apps/plm-tcin-mapper/docs/ARCHITECTURE.md`
- **Insomnia Collection:** `insomnia-collection.json` — ready-to-import API requests

---

## 🎯 Next Steps

1. **Clone & setup:** Follow "Quick Start" above
2. **Run services:** `make run-plm`
3. **Test APIs:** Import `insomnia-collection.json` or use curl examples
4. **For TCIN Mapper:** Load data via `/api/v1/ingest`, run pipeline via `/api/v1/mappings/run`
5. **Review results:** Query via `/api/v1/mappings`, check metrics via `/api/v1/eval/latest`
6. **Push to CI:** Run `make quality-gate` before opening a PR

---

## ✅ Checklist for First-Time Setup

- [ ] Clone repo: `git clone ...`
- [ ] Install uv: `curl ... | sh`
- [ ] Copy root `.env.example` → `.env` and fill in ThinkTank credentials
- [ ] (If running TCIN) Start MongoDB: `docker run -d --name tcin-mongo -p 27017:27017 mongo:7`
- [ ] (If running TCIN) Copy app `.env.example` → `.env` and set MongoDB URL
- [ ] Install dependencies: `make init`
- [ ] Start services: `make run-plm`
- [ ] Verify: `curl http://localhost:8000/health` and `curl http://localhost:8001/health`
- [ ] Test APIs: Import `insomnia-collection.json` and send requests
- [ ] Run tests: `make test-unit` or `make test-cov`

Enjoy! 🚀
