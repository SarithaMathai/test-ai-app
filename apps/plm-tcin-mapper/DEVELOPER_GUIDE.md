# plm-tcin-mapper — Developer Guide

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12 | Managed by uv automatically |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| MongoDB | 6.x+ | Local Docker container, or a remote URL |
| Target Artifactory access | — | Required for `tgt-pypi` / `tgt-python` indexes (on Target network/VPN) |

> **On a Target machine:** uv resolves packages from `binrepo.target.com`. Ensure you are on the Target network (or VPN) before running `make init`.

## Local setup — from clone to running

### 1. Clone + install uv

```bash
git clone git@github.target.com:PLM/plm-ai-apps.git
cd plm-ai-apps
curl -LsSf https://astral.sh/uv/install.sh | sh   # if not already installed
```

### 2. Set up credentials

This app layers an app-specific `.env` on top of the shared root `.env`:

```bash
cp .env.example .env                                          # root: ThinkTank creds (shared)
cp apps/plm-tcin-mapper/.env.example apps/plm-tcin-mapper/.env  # app: Mongo URL + port
```

Fill in `apps/plm-tcin-mapper/.env`:

```bash
APP__MONGO__URL=mongodb://localhost:27017
APP__MONGO__DATABASE=tcin_mapper
APP__SPARK__PORT=8001
```

> **No ThinkTank credentials?** Set `APP__LLM__PROVIDER=none` — the matching pipeline runs fully deterministically and skips LLM disambiguation. The service still starts and serves all endpoints.

### 3. Start MongoDB

Any reachable MongoDB works. The quickest local option:

```bash
docker run -d --name tcin-mongo -p 27017:27017 mongo:7
```

### 4. Install all packages

```bash
make init
```

Runs `uv sync --all-packages --all-groups` (creates a single root `.venv` covering every lib + app, including the optional `ui` group) and installs pre-commit hooks.

### 5. Run the service

```bash
make run-tcin-mapper          # this app only,  http://localhost:8001
# or
make run-plm                  # both apps: think-tank :8000 + tcin-mapper :8001
```

`run-tcin-mapper` kills any process already on `:8001` first, so it is always safe to re-run.

| App | Target | Port |
|---|---|---|
| `plm-think-tank-ai` | `make run-thinktank` | `8000` |
| `plm-tcin-mapper` (API) | `make run-tcin-mapper` | `8001` |
| `plm-tcin-mapper` (Streamlit UI) | `make run-tcin-ui` | `8501` |

Verify:
```bash
curl http://localhost:8001/health
# → {"status":"ok","llm_provider":"thinktank","llm_model":"gemini-1.5-pro","mongo_ok":true}
```

### 6. Load data and run a mapping

Normalized CSVs are bundled under `apps/plm-tcin-mapper/data/normalized/` (`chunk_NN/` folders).

```bash
# Ingest one chunk
curl -X POST http://localhost:8001/api/v1/ingest \
  -H "Content-Type: application/json" -d '{"chunk": "chunk_01"}'

# Run matching for everything just ingested
curl -X POST http://localhost:8001/api/v1/mappings/run \
  -H "Content-Type: application/json" -d '{"use_llm": false}'

# Inspect results
curl "http://localhost:8001/api/v1/mappings?page=1&page_size=20" | jq .
```

### 7. (Optional) Launch the operator UI

```bash
make run-tcin-ui    # http://localhost:8501
```

Search by PID or department, review color → impression matches, and submit corrections. The UI reads MongoDB directly and writes corrections back to the `feedback` + `mappings` collections.

### 8. Quality gate before pushing

```bash
make quality-gate   # lint + type-check + test-cov (same as CI)
```

---

## Environment variables

Resolution order (highest wins): **env vars → `config/local.yaml` → `config/base.yaml` → Pydantic defaults.**

| Variable | base.yaml path | Default | Description |
|---|---|---|---|
| `APP__APP__ENV` | `app.env` | `development` | `local`/`dev` → colorized logs; `prod` → JSON logs |
| `APP__APP__LOG_LEVEL` | `app.log_level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `APP__MONGO__URL` | `mongo.url` | `mongodb://localhost:27017` | Connection URL — embed credentials |
| `APP__MONGO__DATABASE` | `mongo.database` | `tcin_mapper` | Database name |
| `APP__LLM__PROVIDER` | `llm.provider` | `thinktank` | `thinktank` / `openai` / `none` |
| `APP__LLM__MODEL` | `llm.model` | `gemini-1.5-pro` | Disambiguation model |
| `APP__MATCHING__AUTO_CONFIRM_THRESHOLD` | `matching.auto_confirm_threshold` | `0.85` | Auto-confirm at/above this score |
| `APP__MATCHING__NO_MATCH_THRESHOLD` | `matching.no_match_threshold` | `0.75` | Below this → `NO_MATCH` |
| `APP__MATCHING__LLM_FALLBACK_THRESHOLD` | `matching.llm_fallback_threshold` | `0.60` | Below this → consult LLM |
| `APP__INGESTION__DATA_DIR` | `ingestion.data_dir` | `apps/plm-tcin-mapper/data/normalized` | Root of `chunk_*/` CSV dirs |
| `APP__INGESTION__BATCH_SIZE` | `ingestion.batch_size` | `500` | Bulk-write batch size |
| `APP__EVAL__MIN_AVG_CONFIDENCE` | `eval.min_avg_confidence` | `0.60` | Guardrail: minimum acceptable avg confidence |
| `APP__SPARK__PORT` | `spark.port` | `8080` | HTTP port (Makefile binds `:8001` locally) |

Secrets (ThinkTank OAuth / API key) come from the root `.env` locally, or from TAP-mounted `/tap/secret/*` files in clusters — never from YAML.

## Project layout

```
apps/plm-tcin-mapper/
├── plm_tcin_mapper/
│   ├── main.py                 # FastAPI app factory + lifespan + error handlers
│   ├── dependencies.py         # DI providers (settings, LLM, Mongo, services)
│   ├── models/
│   │   └── schemas.py          # API request/response Pydantic models
│   ├── database/
│   │   └── models.py           # MongoDB document models + enums (StrEnum)
│   ├── routes/                 # health, ingest, mappings, eval, feedback
│   ├── services/               # one service per route group; run sync work in a thread pool
│   ├── matching/               # deterministic engine
│   │   ├── color_keywords.py   #   canonical base-color dictionary + alias overrides
│   │   ├── scorer.py           #   color_score(): token / keyword / fuzzy cascade
│   │   ├── size_normalizer.py  #   size label normalization + similarity
│   │   └── deterministic.py    #   three-round Greedy → Hungarian → Fallback assignment
│   ├── pipeline/               # orchestration over Mongo
│   │   ├── ingestion.py        #   CSV → Mongo (header-sniffing, bulk upserts)
│   │   ├── orchestrator.py     #   run_batch / match_pid
│   │   └── evaluator.py        #   accuracy metrics + guardrail alerts
│   ├── llm/
│   │   └── disambiguator.py    # low-confidence fallback via ai-core LLMClient.chat()
│   └── ui/                     # OPTIONAL Streamlit operator tool (ui dependency group)
│       ├── streamlit_app.py    #   navigation entry point
│       ├── db.py               #   cached sync Mongo handle via ai-mongo
│       ├── utils.py            #   badges / sorting helpers
│       └── pages/              #   pid_lookup, department_view, llm_quality
├── data/normalized/            # bundled chunk_NN/ CSV data for ingestion
├── docs/                       # ARCHITECTURE.md, DATA_FLOW_DESIGN.md
├── tests/                      # unit + integration (mocked Mongo + LLM)
├── entrypoint.sh               # gunicorn + UvicornWorker (Docker/TAP)
├── pyproject.toml
├── README.md
└── DEVELOPER_GUIDE.md          ← you are here
```

## How the matching pipeline works

For each PID the orchestrator loads its TCIN records and variation (impression) records, then:

1. **Score** — `scorer.color_score()` produces a 0–1 similarity for every (TCIN color, impression) pair using a cascade: exact token overlap → canonical base-color keyword match → fuzzy string similarity.
2. **Assign** — `deterministic._three_round_assign()` resolves the color↔impression matrix in three rounds:
   - **Round 1 (Greedy):** lock in high-confidence pairs (≥ `HIGH_CONF_THRESHOLD`).
   - **Round 2 (Hungarian):** optimal assignment (`scipy.optimize.linear_sum_assignment`) over whatever remains.
   - **Round 3 (Fallback):** best-available impression for any still-unassigned color.
3. **Disambiguate (optional)** — pairs below `llm_fallback_threshold` are sent to `llm/disambiguator.py`, which asks the ThinkTank LLM (via `ai-core`'s `LLMClient.chat()`) to pick from the candidate list. Skipped entirely when `use_llm=false` or `provider=none`.
4. **Persist** — each result becomes a `Mapping` document with a status (`AUTO_CONFIRM`, `NEEDS_SPOT_CHECK`, `LLM_ASSISTED`, `NO_MATCH`, …) and confidence tier, upserted into the `mappings` collection.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DATA_FLOW_DESIGN.md](docs/DATA_FLOW_DESIGN.md) for full detail and diagrams.

## Why MongoDB lives in a shared library

MongoDB access is isolated in [`libs/ai-mongo`](../../libs/ai-mongo/) (`MongoClientManager` wrapping Motor + PyMongo). Only apps that need it depend on it — `plm-think-tank-ai` does not, so it has no Mongo dependency and its `.env` requires no Mongo URL. This keeps the apps low-coupled and high-cohesion: shared infrastructure is reusable, but never forced on apps that don't use it.

## Testing

```bash
# This app — unit + integration (mocked Mongo + LLM, no network, no DB needed)
make test-tcin-mapper
# or directly:
uv run pytest apps/plm-tcin-mapper/tests/unit apps/plm-tcin-mapper/tests/integration -v

# Shared Mongo library
make test-ai-mongo
```

Unit tests cover the pure matching logic (`scorer`, `size_normalizer`, `deterministic`). Integration tests exercise the routes via `TestClient` with `dependency_overrides` swapping in a mocked `MongoClientManager` and a `NoOpLLMClient` — so no MongoDB or ThinkTank credentials are required in CI.

## Docker (local)

```bash
make docker-build-tcin-mapper

docker run --rm -p 8080:8080 \
  -e APP__MONGO__URL=mongodb://host.docker.internal:27017 \
  -e APP__MONGO__DATABASE=tcin_mapper \
  -e APP__LLM__PROVIDER=none \
  plm-tcin-mapper:local

curl http://localhost:8080/health
```

The image is the shared monorepo `Dockerfile`, parameterized by `--build-arg APP_PACKAGE=plm-tcin-mapper`. Only this app and its transitive deps are installed; the `ui` group (Streamlit) is excluded.

## TAP deployment

Builds and deploys are driven by the shared [`.vela.yml`](../../.vela.yml):

- **Build:** Kaniko builds `docker.target.com/iam/spark/plm-tcin-mapper` on pushes to `main` / `feat/*` / `hotfix/*` and on release tags.
- **Deploy:** `tapctl run pipeline plm-tcin-mapper -e=<dev|stage|prod>` runs after a successful build.

```bash
tapctl login --env dev
tapctl run pipeline plm-tcin-mapper -e=dev -t="<image-tag>" --force --wait
```

Secrets are injected from TAP's vault at `/tap/secret/`; non-secret config is mounted at `/tap/config/` (the entrypoint prefers it over the baked-in `config/`). Set `APP__MONGO__URL` / `APP__MONGO__DATABASE` and the ThinkTank credentials as TAP secrets for the workload.

## Troubleshooting

| Problem | Fix |
|---|---|
| `health` returns `"mongo_ok": false` | MongoDB unreachable — check `APP__MONGO__URL` and that the DB is up |
| `uv sync` fails "conflicting URLs" | `rm -rf .venv && uv sync --all-packages --all-groups` |
| `ModuleNotFoundError: ai_mongo` | Run from monorepo root, not the app subdirectory; re-run `make init` |
| `make run-tcin-ui` → `streamlit: command not found` | UI deps are in the `ui` group: `uv sync --group ui` (or `make init`) |
| Ingestion writes 0 docs | Confirm `APP__INGESTION__DATA_DIR` points at the `chunk_*/` parent; check CSV headers |
| LLM disambiguation never runs | Set `APP__LLM__PROVIDER=thinktank` + valid creds, and pass `use_llm=true` |
| 502 from `/api/v1/...` | An `AIError` (LLM failure) — check ThinkTank credentials and connectivity |
