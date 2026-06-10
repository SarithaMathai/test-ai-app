# my-test-ai-app

A UV-managed Python monorepo with multiple AI-powered applications and shared libraries.

## Quick start

```bash
# 1. Install uv (if not already)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and bootstrap
git clone <repo-url> my-test-ai-app
cd my-test-ai-app
make init

# 3. Copy secrets template and fill in values
cp .env.example .env

# 4. Run an app
make run-spark       # FastAPI on http://localhost:8000
make run-tcin        # Streamlit on http://localhost:8501
```

## Workspace layout

```
my-test-ai-app/
├── apps/
│   ├── spark-think-tank-ai/      # FastAPI — user query → ThinkTank chat completions
│   └── tcin-impression-mapping/  # Streamlit — TCIN → impression mapping (OpenAI)
├── libs/
│   ├── ai-core/                  # LLM ABC, config loader, Elasticsearch client
│   ├── ai-openai/                # OpenAI concrete LLM client
│   └── ai-thinktank/             # ThinkTank API concrete LLM client
└── config/
    ├── base.yaml                 # Non-secret defaults (checked in)
    └── local.yaml.example        # Local override template (not checked in)
```

## Common commands

| Command | What it does |
|---|---|
| `make init` | First-time setup: sync all packages + install pre-commit |
| `make sync` | Re-sync after adding a dependency |
| `make lint` | Check code style and types (read-only) |
| `make format` | Auto-fix code style |
| `make test` | Run all tests |
| `make test-unit` | Fast tests only (no network/ES) |
| `make test-cov` | Tests + HTML coverage report |
| `make run-spark` | Start spark-think-tank-ai locally |
| `make run-tcin` | Start tcin-impression-mapping locally |
| `make build` | Build wheels for all packages |
| `make clean` | Remove all build artifacts and `.venv` |

## Configuration

Non-secret configuration lives in `config/base.yaml` and can be overridden by:

1. `config/local.yaml` — local developer overrides (git-ignored)
2. Environment variables — `APP__SECTION__KEY=value` (double underscore separator)
3. `.env` file — secrets only (git-ignored)

See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions.
