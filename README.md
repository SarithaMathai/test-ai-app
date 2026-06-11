# plm-ai-apps

UV monorepo for PLM AI microservices and shared libraries.

## Structure

```
plm-ai-apps/
├── apps/
│   └── plm-think-tank-ai/     # FastAPI service — PLM UI → ThinkTank LLM
├── libs/
│   ├── ai-core/               # Zero-dependency foundation (config, exceptions, LLM ABC, logging, OAuth + authenticated HTTP client)
│   ├── ai-thinktank/          # ThinkTank LLM client (implements ai-core's LLMClient)
│   └── ai-toss-utils/         # Target Object Storage (TOSS) utilities
├── config/
│   └── base.yaml              # Default config baked into Docker images
├── Dockerfile                 # Parameterized: --build-arg APP_PACKAGE=<name>
├── Makefile
├── pyproject.toml             # UV workspace root
└── uv.lock                    # Single shared lockfile
```

### Dependency graph

```
apps/plm-think-tank-ai
    └── ai-thinktank
            ├── ai-toss-utils
            │       └── ai-core
            └── ai-core
```

## Quick start

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Copy and fill in credentials
cp .env.example .env
# Edit .env — set THINKTANK_API_KEY and THINKTANK_URL at minimum

# 3. Install all packages + pre-commit hooks
make init

# 4. Run the service locally
make run-plm
# → http://localhost:8000
```

## Available commands

```bash
make help          # Full command reference
make sync          # Re-sync dependencies after pyproject.toml changes
make format        # Auto-format + fix lint issues
make lint          # Check only (no writes)
make type-check    # mypy over all libs and app
make quality-gate  # lint + type-check + test-cov (CI gate)

make test          # All tests
make test-unit     # Fast unit tests only
make test-int      # Integration tests (needs credentials)
make test-cov      # Full run with HTML coverage report

make test-app             # Tests for apps/plm-think-tank-ai
make test-ai-core         # Tests for libs/ai-core
make test-ai-thinktank    # Tests for libs/ai-thinktank
make test-ai-toss-utils   # Tests for libs/ai-toss-utils

make docker-build  # Build Docker image (plm-ai-apps:local)
make clean         # Remove .venv, dist/, caches
```

## Apps

### [plm-think-tank-ai](apps/plm-think-tank-ai/README.md)

FastAPI service that receives PLM editor prompts (spell-check, unit-test generation) and routes them to Target's ThinkTank LLM gateway.

- **Endpoints:** `GET /health`, `POST /api/v1/prompt`
- **See:** [README](apps/plm-think-tank-ai/README.md) · [Developer Guide](apps/plm-think-tank-ai/DEVELOPER_GUIDE.md)

## Libraries

### [ai-core](libs/ai-core/README.md)

Zero-dependency foundation — configuration loading (YAML + env), exception hierarchy, `LLMClient` ABC, structured logging, OAuth token management, and authenticated HTTP client with retry/backoff.

- **See:** [README](libs/ai-core/README.md) · [Developer Guide](libs/ai-core/DEVELOPER_GUIDE.md)

### [ai-thinktank](libs/ai-thinktank/README.md)

ThinkTank LLM client. **Single import point for all ThinkTank connectivity.** Implements `LLMClient` from `ai-core`.

- **See:** [README](libs/ai-thinktank/README.md) · [Developer Guide](libs/ai-thinktank/DEVELOPER_GUIDE.md)

### [ai-toss-utils](libs/ai-toss-utils/README.md)

Target Object Storage (TOSS) utilities — integrated when connecting to TOSS for object storage operations across projects.

- **See:** [README](libs/ai-toss-utils/README.md) · [Developer Guide](libs/ai-toss-utils/DEVELOPER_GUIDE.md)

## CI/CD

Vela CI pipeline (`.vela.yml`):

| Trigger | Image tag |
|---|---|
| Push to `main` | `feat-<build>-<sha8>`, `feat-latest` |
| Release tag (e.g. `1.2.3`) | `1.2.3`, `latest` |

Docker registry: `docker.target.com/managed/genai-platform/plm-ai-apps`

## Environment variables

See [`.env.example`](.env.example) for the full list of supported environment variables.

Key variables:

| Variable | Description |
|---|---|
| `THINKTANK_API_KEY` | ThinkTank API key (TAP secret) |
| `THINKTANK_GATEWAY_API_KEY` | Gateway-level API key for `x-api-key` header |
| `THINKTANK_URL` | ThinkTank base URL |
| `THINKTANK_OAUTH_CLIENT_ID` | OAuth client ID (alternative to API key) |
| `APP_ENV` | `local` / `dev` / `prod` — controls log format |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` |

## Contributing

1. Branch from `main`.
2. Run `make quality-gate` before opening a PR.
3. Unit tests must pass in CI (no credentials required). Integration tests are optional in CI.
4. Use `feat-` prefix for feature branches; the tag `feat-latest` is updated on every `main` merge.
