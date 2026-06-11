# plm-think-tank-ai — Developer Guide

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12 | Managed by uv automatically |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | any | Pre-installed on most systems |
| Target Artifactory access | — | Required for `tgt-pypi` and `tgt-python` indexes |

> **On a Target machine:** uv resolves packages from `binrepo.target.com`. Ensure you are on the Target network (or VPN) before running `make init`.

## Local setup — from clone to running

### 1. Clone the repo

```bash
git clone git@github.target.com:PLM/plm-ai-apps.git
cd plm-ai-apps
```

### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart your shell, or:
source ~/.local/bin/env
```

Verify:
```bash
uv --version
```

### 3. Set up credentials

```bash
cp .env.example .env
```

Open `.env` and fill in at least one of the following auth strategies:

**Option A — Static API key (simplest for local dev):**
```bash
THINKTANK_API_KEY=your-key-here
```

**Option B — OAuth (Target internal environments only):**
```bash
THINKTANK_OAUTH_CLIENT_ID=your-client-id
THINKTANK_OAUTH_CLIENT_SECRET=your-client-secret
# Optional — only if your OAuth flow requires NUID:
THINKTANK_OAUTH_NUID_USERNAME=your-nuid
THINKTANK_OAUTH_NUID_PASSWORD=your-password
```

For OAuth, also install the Target-internal auth packages:
```bash
uv add tgt-certs pyOauthTarget --index tgt-python
```

> **No credentials yet?** Set `APP__LLM__PROVIDER=none` in `.env` — the service starts and responds to `/health` without contacting ThinkTank.

### 4. Install all packages

```bash
make init
```

This runs `uv sync --all-packages --all-groups` and installs pre-commit hooks. A single `.venv` is created at the monorepo root covering all libs and apps.

### 5. Run the service

**Start just this app:**
```bash
make run-thinktank
```

**Start all apps at once** (when running the full stack locally):
```bash
make run-plm
```

Both targets kill any existing process on the port before starting, so it's always safe to re-run. Each app has a dedicated port:

| App | Target | Port |
|---|---|---|
| `plm-think-tank-ai` | `make run-thinktank` | `8000` |

When a new app is added to the monorepo, a `run-<appname>` target with its own port is added to the Makefile, and `run-plm` is updated to start it too.

Verify it is up:
```bash
curl http://localhost:8000/health
# → {"status":"ok","provider":"thinktank","model":"gemini-1.5-pro"}
```

Send a test prompt:
```bash
curl -s -X POST http://localhost:8000/api/v1/prompt \
  -H "Content-Type: application/json" \
  -d '{"content": "Ths is a smple sentense.", "operation": "spell_check"}' | jq .
```

### 6. Run tests

```bash
# Unit tests — no credentials needed, fast
make test-unit

# Integration tests — mocked network, no live credentials needed
make test-int

# Full test suite with coverage report
make test-cov
open htmlcov/index.html
```

### 7. Before pushing — run the quality gate

```bash
make quality-gate
# Runs: lint + type-check + test-cov
```

This is the same check that runs in CI.

---

## Environment variables

All variables listed in `.env.example`. Non-secret defaults live in `config/base.yaml`.

### Resolution order (highest wins)
1. Environment variables (TAP secrets, `.env` file)
2. `config/local.yaml` (git-ignored, local overrides)
3. `config/base.yaml` (checked-in defaults)
4. Pydantic field defaults in code

### Required for the service to contact ThinkTank

Choose **one** auth strategy:

| Variable | Auth strategy | Required | Description |
|---|---|---|---|
| `THINKTANK_API_KEY` | API key | Yes (if no OAuth) | Static key — sent as Bearer token |
| `THINKTANK_OAUTH_CLIENT_ID` | OAuth | Yes (if using OAuth) | OAuth2 client ID |
| `THINKTANK_OAUTH_CLIENT_SECRET` | OAuth | Yes (if using OAuth) | OAuth2 client secret |
| `THINKTANK_OAUTH_NUID_USERNAME` | OAuth | No | NUID username for user-based OAuth flow |
| `THINKTANK_OAUTH_NUID_PASSWORD` | OAuth | No | NUID password for user-based OAuth flow |
| `THINKTANK_GATEWAY_API_KEY` | Both | No | Subscription key sent as `x-api-key` header (required in some API gateway setups) |

> **Local dev without OAuth packages:** Set `THINKTANK_API_KEY` only — `get_bearer_token()` automatically falls back to the API key when `pyOauthTarget` is absent or OAuth credentials are blank.

### Runtime configuration (YAML field overrides)

Override nested `config/base.yaml` fields using `APP__SECTION__KEY=value` (double underscore):

| Env var | base.yaml path | Default | Description |
|---|---|---|---|
| `APP__APP__ENV` | `app.env` | `development` | Environment name; `local`/`dev` → colorized logs; `prod` → JSON logs |
| `APP__APP__LOG_LEVEL` | `app.log_level` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP__LLM__PROVIDER` | `llm.provider` | `thinktank` | LLM backend: `thinktank`, `openai`, `none` |
| `APP__LLM__MODEL` | `llm.model` | `gemini-1.5-pro` | Model name passed to the provider |
| `APP__LLM__MAX_TOKENS` | `llm.max_tokens` | `2048` | Maximum tokens in LLM response |
| `APP__LLM__TEMPERATURE` | `llm.temperature` | `1.0` | Sampling temperature |
| `APP__LLM__REQUEST_TIMEOUT` | `llm.request_timeout` | `120` | HTTP timeout in seconds |
| `APP__THINKTANK__BASE_URL` | `thinktank.base_url` | `https://api-internal.target.com` | ThinkTank base URL |
| `APP__THINKTANK__CHAT_ENDPOINT` | `thinktank.chat_endpoint` | `/gen_ai_model_requests/v1/chat/completions` | Chat completions path |
| `APP__THINKTANK__APP_NAME` | `thinktank.app_name` | `plm-think-tank-ai` | Sent as `x-tgt-application` header |
| `APP__THINKTANK__TENANT_ID` | `thinktank.tenant_id` | `""` | Sent as `tenant-id` header |
| `APP__THINKTANK__IS_PROD` | `thinktank.is_prod` | `true` | `false` uses dev/stage OAuth endpoint |
| `APP__SPARK__PORT` | `spark.port` | `8080` | HTTP listen port (uvicorn/gunicorn) |

### Server process variables (entrypoint.sh only)

These apply when running under gunicorn (Docker/TAP) — **not** used by `make run-plm`:

| Env var | Default | Description |
|---|---|---|
| `APP_PORT` | `8080` | Gunicorn bind port |
| `APP_CONFIG_DIR` | `/app/config` | Config directory (TAP auto-sets to `/tap/config`) |
| `GUNICORN_WORKERS` | `4` | Number of UvicornWorker processes |
| `GUNICORN_TIMEOUT` | `120` | Worker timeout in seconds |

## Project layout

```
apps/plm-think-tank-ai/
├── plm_think_tank_ai/
│   ├── main.py              # FastAPI app factory + lifespan, error handlers
│   ├── dependencies.py      # DI providers: get_app_settings, get_llm_client, get_prompt_service
│   ├── models/
│   │   └── schemas.py       # Pydantic v2: PromptRequest, PromptResponse, HealthResponse
│   ├── routes/
│   │   ├── health.py        # GET /health
│   │   └── prompts.py       # POST /api/v1/prompt
│   ├── services/
│   │   └── prompt_service.py  # Maps operation name → system+user prompt → LLM call
│   └── prompts/
│       └── prompt_consts.py   # System prompt templates for each operation
├── tests/
│   ├── conftest.py          # Settings cache clear + mock_prompt_service fixture
│   ├── unit/
│   │   ├── services/
│   │   │   └── test_prompt_service.py   # 4 unit tests
│   │   └── test_application.py          # 1 smoke test
│   └── integration/
│       └── test_routes.py               # 6 route-level tests via TestClient
├── pyproject.toml
├── README.md
└── DEVELOPER_GUIDE.md        ← you are here
```

> **Why are tests inside the app?** In this monorepo, apps contain meaningful business logic (route handling, service layer, prompt engineering). Unlike `obi-workflow-services` apps (thin Temporal workers with no logic of their own), `plm-think-tank-ai` owns its prompt service and route handling and it makes sense to test them co-located. Shared library logic (auth, HTTP, LLM client) is tested in `libs/`.

## Adding a new prompt operation

1. Add the template in `plm_think_tank_ai/prompts/prompt_consts.py`:
```python
MY_OP_SYSTEM_PROMPT = "You are an expert at..."
MY_OP_USER_TEMPLATE = "Process this: {content}"
```

2. Register in `plm_think_tank_ai/services/prompt_service.py`:
```python
OPERATION_PROMPTS = {
    ...
    "my_op": (prompt_consts.MY_OP_SYSTEM_PROMPT, prompt_consts.MY_OP_USER_TEMPLATE),
}
```

3. Update the `operation` literal type in `models/schemas.py`.

4. Write a unit test in `tests/unit/services/test_prompt_service.py`.

5. Update the README operation table.

## Testing

```bash
# Fast unit tests — no credentials needed, runs in CI on every PR
make test-app
# or: uv run pytest apps/plm-think-tank-ai/tests/unit -v

# Integration tests — hit real endpoints (need THINKTANK_API_KEY)
uv run pytest apps/plm-think-tank-ai/tests/integration -v -m integration

# All tests with coverage
uv run pytest apps/plm-think-tank-ai/tests --cov=plm_think_tank_ai --cov-report=html
open htmlcov/index.html
```

Unit tests use `TestClient` (no network) with `dependency_overrides`:

```python
app.dependency_overrides[get_llm_client] = lambda: MockLLMClient()
```

## Docker (local)

```bash
make docker-build

docker run --rm -p 8080:8080 \
  -e THINKTANK_API_KEY=your-key \
  plm-ai-apps:local

curl http://localhost:8080/health
```

## TAP deployment

```bash
tapctl login --env dev
tapctl apply -f tap/workload-dev.yaml --env dev
```

Secrets are injected from TAP's vault at `/tap/secret/`. The config loader reads those mounted files when the corresponding env vars are not already set.

## Troubleshooting

| Problem | Fix |
|---|---|
| `uv sync` fails "conflicting URLs" | `rm -rf .venv && uv sync --all-packages --all-groups` |
| `ModuleNotFoundError: ai_core` | Run from monorepo root, not from app subdirectory |
| 401 from ThinkTank | Check `THINKTANK_API_KEY` in `.env`; run `cat .env` to verify it's set |
| Config not loading | Check `APP_CONFIG_DIR` — defaults to `config/` relative to cwd |
| `pyOauthTarget` import error | Requires `tgt-python` Artifactory index access; or just set `THINKTANK_API_KEY` as fallback |
| Tests fail with `SettingsError` | `clear_settings_cache` fixture auto-runs; check `conftest.py` in tests/ |
