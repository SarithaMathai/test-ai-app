# Architecture

## Monorepo strategy

This project uses a **UV workspace** — one `uv.lock` at the root, each package
(`apps/*`, `libs/*`) has its own `pyproject.toml` with its own `dependencies`.
The lock file is shared so all packages always resolve to the same versions.

```
Root pyproject.toml
  └── [tool.uv.workspace]  members = ["apps/*", "libs/*"]
  └── [tool.uv.sources]    wire lib names → local paths
```

## Library dependency graph

```
ai-core          ← no internal deps (zero provider coupling)
   ↑
ai-openai        ← depends on: ai-core only
ai-thinktank     ← depends on: ai-core only

apps/spark-think-tank-ai    ← depends on: ai-core, ai-thinktank
apps/tcin-impression-mapping ← depends on: ai-core, ai-openai
```

**Rule**: `ai-openai` and `ai-thinktank` must never import from each other.
An app chooses which provider(s) it needs by declaring them in its `pyproject.toml`.

## Switching LLM providers

Every app calls `build_llm_client(config)` from `ai_core.llm.factory`.
The factory reads `config.llm.provider` and returns the right concrete client.
To switch providers:

```yaml
# config/base.yaml
llm:
  provider: openai   # change to: thinktank
```

No application code changes required.

## Configuration system

Based on `pydantic-settings` with YAML support (`pydantic-settings[yaml]`).

Resolution order (highest wins):
1. Constructor kwargs
2. Process environment variables (`APP__SECTION__KEY=value`)
3. `.env` file (secrets — never checked in)
4. `config/local.yaml` (local overrides — git-ignored)
5. `config/base.yaml` (repo defaults — checked in)
6. Field defaults

**Rule**: YAML files must never contain secrets. Secrets go in `.env` (local)
or are injected as environment variables (CI/CD, production).

## Elasticsearch integration

`ai_core.elastic.client` provides a thin wrapper around the official
`elasticsearch-py` client. Each app configures its own index names via config.
The shared client handles connection, auth, and retry logic so apps don't repeat it.

## Code style

- **Ruff** for linting and formatting (replaces flake8, isort, black)
- **mypy** for type checking (non-strict by default, tighten per package)
- **pytest** with `unit` and `integration` markers
  - `unit`: no external deps, runs in CI on every PR
  - `integration`: needs Elasticsearch/OpenAI/ThinkTank, opt-in only
- **pre-commit** for git hooks (runs ruff on staged files)
