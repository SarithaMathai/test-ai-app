# plm-tcin-mapper

FastAPI microservice that maps **design impression names** to **guest-facing TCIN color records** using a deterministic matching engine with optional LLM disambiguation.

Given a Product ID (PID), the service pairs each TCIN color (e.g. `Romantic Red`) with the best design impression (e.g. `Ruby Red`) by running a three-round assignment algorithm over a color-similarity matrix, then falls back to a ThinkTank LLM only for genuinely ambiguous, low-confidence cases. Results, human feedback, and evaluation snapshots are persisted to MongoDB.

This app is part of the `plm-ai-apps` monorepo and follows the same structure, Docker image, Vela CI, and TAP deployment pattern as [`plm-think-tank-ai`](../plm-think-tank-ai/README.md). It additionally depends on the shared [`ai-mongo`](../../libs/ai-mongo/) library; apps that don't need MongoDB do not pull it in.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET`  | `/health` | Liveness check — returns LLM provider/model and MongoDB reachability |
| `POST` | `/api/v1/ingest` | Ingest normalized CSV chunks into MongoDB |
| `POST` | `/api/v1/mappings/run` | Run the matching pipeline for a PID, a department, or all unmatched PIDs |
| `GET`  | `/api/v1/mappings` | Query mappings with filters + pagination |
| `POST` | `/api/v1/feedback` | Submit human feedback (`CONFIRM` / `REJECT` / `CORRECT`) |
| `POST` | `/api/v1/eval/run` | Compute accuracy metrics + guardrail alerts |
| `GET`  | `/api/v1/eval/latest` | Return the most recent evaluation snapshot |

### POST /api/v1/mappings/run

```json
{
  "pid": "PID-0L20P5",
  "use_llm": true,
  "dry_run": false
}
```

Omit `pid` and pass `"department": "214"` to process a whole department, or pass neither to process every unmatched PID. Response:

```json
{
  "status": "ok",
  "batch_id": "batch_9f3a1c20",
  "total_pids": 1,
  "pids_matched": 1,
  "pids_no_data": 0,
  "pids_errored": 0,
  "total_mappings_written": 7,
  "status_counts": { "AUTO_CONFIRM": 5, "NEEDS_SPOT_CHECK": 2 },
  "dry_run": false
}
```

### GET /api/v1/mappings

Query params: `pid`, `status`, `department`, `page` (default 1), `page_size` (default 50, max 500).

```bash
curl "http://localhost:8001/api/v1/mappings?pid=PID-0L20P5&page=1&page_size=50"
```

## Operator UI (optional)

An internal Streamlit review tool ships alongside the service under [`plm_tcin_mapper/ui/`](plm_tcin_mapper/ui/). It reads MongoDB directly (sync PyMongo via `ai-mongo`) and lets reviewers search by PID or department and correct mappings — those corrections flow back into the `feedback` and `mappings` collections.

The UI is **not** part of the deployed image: it lives in the optional `ui` dependency group and is excluded from the Docker build.

```bash
make run-tcin-ui          # http://localhost:8501
```

## Local development

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for full setup. Architecture and data-flow deep dives live in [docs/](docs/).

**Quick start:**
```bash
# From monorepo root
cp .env.example .env                               # shared ThinkTank creds (root)
cp apps/plm-tcin-mapper/.env.example apps/plm-tcin-mapper/.env   # Mongo + port overrides
make init                                          # uv sync --all-packages --all-groups
make run-tcin-mapper                               # API on :8001
```

Both apps can run at once — `plm-think-tank-ai` on `:8000`, `plm-tcin-mapper` on `:8001`:
```bash
make run-plm
```

## Configuration

Configured via YAML (`config/base.yaml`) + environment variables. Env vars override YAML using `APP__SECTION__KEY=value` (double-underscore nesting).

| Variable | Default | Description |
|---|---|---|
| `APP__MONGO__URL` | `mongodb://localhost:27017` | MongoDB connection URL (embed credentials) |
| `APP__MONGO__DATABASE` | `tcin_mapper` | Database name |
| `APP__LLM__PROVIDER` | `thinktank` | `thinktank` / `openai` / `none` (`none` disables LLM disambiguation) |
| `APP__LLM__MODEL` | `gemini-1.5-pro` | Model used for disambiguation |
| `APP__INGESTION__DATA_DIR` | `apps/plm-tcin-mapper/data/normalized` | Root folder of `chunk_*/` CSV directories |
| `APP__MATCHING__AUTO_CONFIRM_THRESHOLD` | `0.85` | Score at/above which a match is auto-confirmed |
| `APP__MATCHING__NO_MATCH_THRESHOLD` | `0.75` | Score below which a match is recorded as `NO_MATCH` |
| `APP__MATCHING__LLM_FALLBACK_THRESHOLD` | `0.60` | Score below which the LLM is consulted |
| `APP__SPARK__PORT` | `8001` (local) / `8080` (container) | HTTP listen port |

ThinkTank credentials (`THINKTANK_OAUTH_*` / `THINKTANK_API_KEY`) are inherited from the root `.env`. See the [think-tank README](../plm-think-tank-ai/README.md#configuration) for the full auth matrix.

## Data ingestion

Normalized CSVs live under [`data/normalized/`](data/normalized/) as `chunk_NN/` folders, each containing `tcin.csv` and `variation.csv`. The ingestion pipeline auto-detects each file's kind by sniffing its header row, so file names don't matter.

```bash
# Dry run (parses + counts, writes nothing)
curl -X POST http://localhost:8001/api/v1/ingest -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# Ingest a single chunk
curl -X POST http://localhost:8001/api/v1/ingest -H "Content-Type: application/json" \
  -d '{"chunk": "chunk_01"}'

# Ingest everything
curl -X POST http://localhost:8001/api/v1/ingest -H "Content-Type: application/json" -d '{}'
```

## Running tests

```bash
make test-tcin-mapper      # unit + integration for this app (mocked Mongo + LLM)
make test-ai-mongo         # unit tests for the shared ai-mongo library
```

## Docker

```bash
make docker-build-tcin-mapper      # builds with --build-arg APP_PACKAGE=plm-tcin-mapper

docker run --rm -p 8080:8080 \
  -e APP__MONGO__URL=mongodb://host.docker.internal:27017 \
  -e APP__MONGO__DATABASE=tcin_mapper \
  -e APP__LLM__PROVIDER=none \
  plm-tcin-mapper:local

curl http://localhost:8080/health
```

## Deployment

Built and deployed by the shared [`.vela.yml`](../../.vela.yml) pipeline: Kaniko builds `docker.target.com/iam/spark/plm-tcin-mapper`, then `tapctl run pipeline plm-tcin-mapper` deploys to dev / stage / prod. See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md#tap-deployment).
