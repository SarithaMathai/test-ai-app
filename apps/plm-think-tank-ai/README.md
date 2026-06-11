# plm-think-tank-ai

FastAPI microservice for PLM UI → ThinkTank AI prompt operations.

Routes PLM product lifecycle management (PLM) editor prompts to Target's ThinkTank LLM gateway. Supports spell-checking and unit-test template generation prompts today; easily extended for additional prompt types.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — returns 200 with service name + version |
| `POST` | `/api/v1/prompt` | Execute an AI prompt operation |

### POST /api/v1/prompt

**Request body:**
```json
{
  "content": "public class Calculator { ... }",
  "operation": "unit_test"
}
```

**Supported `operation` values:**

| Value | Description |
|---|---|
| `spell_check` | Grammar and spell-check the provided content |
| `unit_test` | Generate unit tests for the provided code |

**Response:**
```json
{
  "result": "Here are unit tests for your class...",
  "operation": "unit_test",
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 145,
    "completion_tokens": 312,
    "total_tokens": 457
  }
}
```

## Local development

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for full setup instructions.

**Quick start:**
```bash
# From monorepo root
cp .env.example .env
# Edit .env with your ThinkTank credentials
make init
make run-plm
```

The server starts at http://localhost:8000.

## Configuration

Configured via YAML + environment variables (see `config/base.yaml`). Environment variables override YAML values.

| Variable | Required | Description |
|---|---|---|
| `THINKTANK_API_KEY` | Yes (or OAuth) | ThinkTank API key |
| `THINKTANK_GATEWAY_API_KEY` | No | Gateway-level API key (`x-api-key` header) |
| `THINKTANK_URL` | Yes | ThinkTank base URL |
| `THINKTANK_OAUTH_CLIENT_ID` | No | OAuth client ID (alternative to API key) |
| `THINKTANK_OAUTH_CLIENT_SECRET` | No | OAuth client secret |
| `APP_ENV` | No | `local` / `dev` / `prod` (default: `development`) |
| `LOG_LEVEL` | No | `DEBUG` / `INFO` / `WARNING` (default: `INFO`) |

## Running tests

```bash
# Unit tests only (no credentials required)
uv run pytest apps/plm-think-tank-ai/tests/unit -v

# Integration tests (require live ThinkTank credentials)
uv run pytest apps/plm-think-tank-ai/tests/integration -v

# Via Makefile shortcut
make test-app
```

## Docker

```bash
# Build locally
make docker-build

# Run container
docker run --rm -p 8080:8080 \
  -e THINKTANK_API_KEY=your-key \
  -e THINKTANK_URL=https://api.thinktank.target.com \
  plm-ai-apps:local
```
