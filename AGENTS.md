# plm-ai-apps — Agent Guidelines

## Repo structure

UV monorepo. One `.venv` at the root, one `uv.lock`.

```
apps/plm-think-tank-ai/   # FastAPI service — PLM UI → ThinkTank LLM
libs/ai-core/             # Foundation: config, exceptions, LLM ABC, OAuth token, HTTP client
libs/ai-thinktank/        # ThinkTank LLMClient — depends on ai-core only
libs/ai-toss-utils/       # Target Object Storage — placeholder, no code yet
config/base.yaml          # Non-secret runtime defaults (checked in)
.env.example              # Secret variable template (never commit .env)
```

Dependency rule: `ai-core` has no internal deps. `ai-thinktank` depends on `ai-core` only. Apps depend on libs, never the reverse.

## Build and test

```bash
make init          # first-time setup after clone
make quality-gate  # lint + type-check + test-cov  ← run before every PR
make test-unit     # fast, no credentials
make test-int      # mocked network, no credentials
make run-thinktank # start plm-think-tank-ai on :8000
make run-plm       # start all apps (each kills its port first)
```

Tests use markers: `@pytest.mark.unit` (no network) and `@pytest.mark.integration` (mocked network). Functional tests (`@pytest.mark.functional`) need live credentials.

## Configuration

Non-secret defaults: `config/base.yaml`. Secrets: env vars only, injected via `_inject_secrets()` in `ai_core/config.py`. Never put secrets in YAML.

Override any YAML field: `APP__SECTION__KEY=value` (double underscore). Example: `APP__LLM__MODEL=gpt-4o`.

Key config section is `thinktank:` (maps to `settings.thinktank` / `ThinkTankConfig`). Not `toss`.

## Code conventions

- **Config**: Each integration has its own `*Config` class in `ai_core/config.py` (e.g. `ThinkTankConfig`). Secrets are never in YAML — inject them in `_inject_secrets()` from env vars only.
- **HTTP client**: `ai_core.http.AuthenticatedHttpClient` is a generic transport — it handles Bearer token injection and retry only. Each integration builds and passes its own `headers` dict at construction time. Never put provider-specific headers inside the client itself.
- **Headers per integration**: Each lib that calls an external service owns a `_<provider>_headers(settings)` function that builds its header contract. Keep that function in the lib, not in `ai-core`.
- **Token**: `ai_core.token.get_bearer_token(settings)` provides OAuth-first with API key fallback. Use this for any Target OAuth integration — do not implement auth inline in a lib or app.
- **Exceptions**: All exceptions inherit from `ai_core.exceptions.AIError`. Raise `AuthenticationError`, `ProviderError`, or `LLMError` as appropriate. Never raise bare `Exception`.
- **Lib boundaries**: `ai-core` has zero internal deps. Provider libs (e.g. `ai-thinktank`) depend on `ai-core` only — never on each other. Apps depend on libs, never the reverse.
- **Placeholder libs**: A lib with no current implementation (e.g. `ai-toss-utils`) should remain empty until its feature is built. Do not add unrelated code to it as a convenience.

## CI/CD — Docker tags

| Trigger | Tag |
|---|---|
| `feat/*` branch push | `feat{BUILD_NUMBER}-{sha8}` |
| `hotfix/*` branch push | `b{BUILD_NUMBER}-{sha8}-hot` |
| `main` push | `b{BUILD_NUMBER}-{sha8}` → deploys to **dev** |
| `v0.0.x-rc` tag | `v0.0.x-rc` → deploys to **stage** |
| `v0.0.x` tag | `v0.0.x`, `latest` → deploys to **prod** |

## Adding a new app

1. Create `apps/<name>/` with `pyproject.toml`, `entrypoint.sh`, source package.
2. Add `run-<name>` target to `Makefile` with its own port. Wire into `run-plm`.
3. Add `test-<name>` target to `Makefile`.
4. Add a `docker-build-<name>` step in `.vela.yml` if it needs a separate image.
5. See [apps/plm-think-tank-ai/DEVELOPER_GUIDE.md](apps/plm-think-tank-ai/DEVELOPER_GUIDE.md) for the full setup pattern.

## Adding a new lib

1. Create `libs/<name>/` with `pyproject.toml` and source package.
2. Declare internal deps via `[tool.uv.sources]` in root `pyproject.toml`.
3. Keep `ai-core` as the only lib with no internal deps.
4. Add `test-<name>` target to `Makefile`.
