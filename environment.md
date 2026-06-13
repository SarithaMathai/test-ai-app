# Environment Variables Reference

Complete reference for all environment variables and configuration properties across all three applications.

---

## Table of Contents

1. [plm-think-tank-ai](#plm-think-tank-ai)
2. [plm-tcin-mapper-api](#plm-tcin-mapper-api)
3. [plm-tcin-mapper-client](#plm-tcin-mapper-client)
4. [Configuration Files](#configuration-files)
5. [Setting Environment Variables](#setting-environment-variables)

---

# plm-think-tank-ai

**Service:** FastAPI backend for AI prompt generation and reasoning
**Default Port:** 8080 (in container), 8001 (on host)
**Entry Point:** `plm_think_tank_ai.main:start`

## Core Application Variables

### APP_PORT
- **Type:** Integer
- **Default:** `8080`
- **Required:** No
- **Description:** Port the application listens on inside the container
- **Example:** `8080`
- **Set In:** entrypoint.sh, docker-compose env, TAP config
```bash
export APP_PORT=8080
```

### APP_ENV
- **Type:** String
- **Default:** `development`
- **Required:** No
- **Options:** `development`, `staging`, `production`
- **Description:** Application environment
- **Set In:** config/base.yaml
```yaml
app:
  env: "development"
```

### LOG_LEVEL
- **Type:** String
- **Default:** `INFO`
- **Required:** No
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description:** Logging level for the application
- **Set In:** config/base.yaml
```yaml
app:
  log_level: "INFO"
```

### APP_NAME
- **Type:** String
- **Default:** `plm-think-tank-ai`
- **Required:** No
- **Description:** Application name (for logging and identification)
- **Set In:** config/base.yaml
```yaml
app:
  name: "plm-think-tank-ai"
```

## Gunicorn/ASGI Server Variables

### GUNICORN_WORKERS
- **Type:** Integer
- **Default:** `4`
- **Required:** No
- **Description:** Number of Gunicorn worker processes
- **Recommended:** CPU cores × 2 + 1
- **Set In:** entrypoint.sh, TAP config
```bash
export GUNICORN_WORKERS=4
```

### GUNICORN_TIMEOUT
- **Type:** Integer (seconds)
- **Default:** `120`
- **Required:** No
- **Description:** Worker timeout in seconds
- **Set In:** entrypoint.sh, TAP config
```bash
export GUNICORN_TIMEOUT=120
```

## Configuration Directory

### APP_CONFIG_DIR
- **Type:** String (file path)
- **Default:** `/app/config`
- **Required:** No
- **TAP Override:** `/tap/config` (if mounted)
- **Description:** Directory containing base.yaml and other config files
- **Set In:** entrypoint.sh
```bash
export APP_CONFIG_DIR=/app/config
# TAP overrides with: /tap/config
```

## LLM Configuration

### LLM Provider Settings
These are set in `config/base.yaml`, not as environment variables:

```yaml
llm:
  provider: "thinktank"              # LLM provider name
  model: "gemini-1.5-pro"            # Model identifier
  temperature: 1.0                   # Temperature (0-2)
  max_tokens: 2048                   # Max tokens in response
  request_timeout: 120               # Request timeout in seconds
  max_retries: 3                     # Max retry attempts
```

**Related Environment Variables:**
- `THINKTANK_API_KEY` — API key for ThinkTank (read from secrets)
- `THINKTANK_GATEWAY_API_KEY` — Gateway API key
- `THINKTANK_OAUTH_CLIENT_ID` — OAuth client ID

### THINKTANK_API_KEY
- **Type:** String (secret)
- **Default:** None
- **Required:** Yes (in production)
- **Description:** API key for ThinkTank service
- **Set In:** TAP secrets, environment secrets
```bash
export THINKTANK_API_KEY=<secret-key>
```

### THINKTANK_GATEWAY_API_KEY
- **Type:** String (secret)
- **Default:** None
- **Required:** No (unless using gateway)
- **Description:** Gateway API key for ThinkTank
- **Set In:** TAP secrets
```bash
export THINKTANK_GATEWAY_API_KEY=<secret-key>
```

### THINKTANK_OAUTH_CLIENT_ID
- **Type:** String (secret)
- **Default:** None
- **Required:** No
- **Description:** OAuth client ID for ThinkTank authentication
- **Set In:** TAP secrets
```bash
export THINKTANK_OAUTH_CLIENT_ID=<client-id>
```

## MongoDB Configuration

### MONGO_URL
- **Type:** String (connection string)
- **Default:** `mongodb://localhost:27017`
- **Required:** Yes
- **Description:** MongoDB connection string
- **Format:** `mongodb://[user:password@]host[:port][/database]`
- **Set In:** config/base.yaml, environment
```yaml
mongo:
  url: "mongodb://localhost:27017"
```

### MONGO_DATABASE
- **Type:** String
- **Default:** `plm_think_tank` (may vary)
- **Required:** No
- **Description:** MongoDB database name
- **Set In:** config/base.yaml
```yaml
mongo:
  database: "plm_think_tank"
```

## ThinkTank API Configuration

```yaml
thinktank:
  base_url: "https://api-internal.target.com"
  chat_endpoint: "/gen_ai_model_requests/v1/chat/completions"
  app_name: "plm-think-tank-ai"
  tenant_id: ""
  is_prod: true
```

---

# plm-tcin-mapper-api

**Service:** FastAPI backend for TCIN impression mapping
**Default Port:** 8080 (in container), 8001 (on host)
**Entry Point:** `plm_tcin_mapper_api.main:start`

## Core Application Variables

### APP_PORT
- **Type:** Integer
- **Default:** `8080`
- **Required:** No
- **Description:** Port the API listens on inside the container
- **Example:** `8080`
- **Set In:** entrypoint.sh, docker-compose env, TAP config
```bash
export APP_PORT=8080
```

### APP_ENV
- **Type:** String
- **Default:** `development`
- **Required:** No
- **Options:** `development`, `staging`, `production`
- **Description:** Application environment
- **Set In:** config/base.yaml
```yaml
app:
  env: "development"
```

### LOG_LEVEL
- **Type:** String
- **Default:** `INFO`
- **Required:** No
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description:** Logging level for the application
- **Set In:** config/base.yaml
```yaml
app:
  log_level: "INFO"
```

### APP_NAME
- **Type:** String
- **Default:** `plm-tcin-mapper-api`
- **Required:** No
- **Description:** Application name (for logging and identification)
- **Set In:** config/base.yaml
```yaml
app:
  name: "plm-tcin-mapper-api"
```

## Gunicorn/ASGI Server Variables

### GUNICORN_WORKERS
- **Type:** Integer
- **Default:** `4`
- **Required:** No
- **Description:** Number of Gunicorn worker processes
- **Recommended:** CPU cores × 2 + 1
- **Set In:** entrypoint.sh, TAP config
```bash
export GUNICORN_WORKERS=4
```

### GUNICORN_TIMEOUT
- **Type:** Integer (seconds)
- **Default:** `120`
- **Required:** No
- **Description:** Worker timeout in seconds
- **Set In:** entrypoint.sh, TAP config
```bash
export GUNICORN_TIMEOUT=120
```

## Configuration Directory

### APP_CONFIG_DIR
- **Type:** String (file path)
- **Default:** `/app/config`
- **Required:** No
- **TAP Override:** `/tap/config` (if mounted)
- **Description:** Directory containing base.yaml and other config files
- **Set In:** entrypoint.sh
```bash
export APP_CONFIG_DIR=/app/config
# TAP overrides with: /tap/config
```

## MongoDB Configuration

### MONGO_URL
- **Type:** String (connection string)
- **Default:** `mongodb://localhost:27017`
- **Required:** Yes
- **Description:** MongoDB connection string
- **Format:** `mongodb://[user:password@]host[:port][/database]`
- **Set In:** config/base.yaml, environment
```yaml
mongo:
  url: "mongodb://localhost:27017"
```

### MONGO_DATABASE
- **Type:** String
- **Default:** `tcin_mapper`
- **Required:** No
- **Description:** MongoDB database name
- **Set In:** config/base.yaml
```yaml
mongo:
  database: "tcin_mapper"
```

## LLM Configuration

```yaml
llm:
  provider: "thinktank"
  model: "gemini-1.5-pro"
  temperature: 1.0
  max_tokens: 2048
  request_timeout: 120
  max_retries: 3
```

### THINKTANK_API_KEY
- **Type:** String (secret)
- **Default:** None
- **Required:** Yes (in production)
- **Description:** API key for ThinkTank service
- **Set In:** TAP secrets, environment secrets
```bash
export THINKTANK_API_KEY=<secret-key>
```

### THINKTANK_GATEWAY_API_KEY
- **Type:** String (secret)
- **Default:** None
- **Required:** No
- **Description:** Gateway API key for ThinkTank
- **Set In:** TAP secrets
```bash
export THINKTANK_GATEWAY_API_KEY=<secret-key>
```

### THINKTANK_OAUTH_CLIENT_ID
- **Type:** String (secret)
- **Default:** None
- **Required:** No
- **Description:** OAuth client ID for ThinkTank authentication
- **Set In:** TAP secrets
```bash
export THINKTANK_OAUTH_CLIENT_ID=<client-id>
```

## Matching Algorithm Configuration

```yaml
matching:
  auto_confirm_threshold: 0.85       # Confidence threshold for auto-confirm
  no_match_threshold: 0.75           # Threshold for no-match determination
  llm_fallback_threshold: 0.60       # Threshold to use LLM fallback
  low_confidence_threshold: 0.50     # Threshold for low-confidence flag
  llm_ambiguity_band: 0.15           # Band around confidence for LLM check
```

## Ingestion Configuration

```yaml
ingestion:
  data_dir: "apps/plm-tcin-mapper/data/normalized"  # Data directory
  batch_size: 500                    # Batch size for processing
  skip_existing: true                # Skip already-ingested records
```

## Evaluation Configuration

```yaml
eval:
  min_high_confidence_pct: 0.40      # Min % of high-confidence mappings
  max_low_confidence_pct: 0.20       # Max % of low-confidence mappings
  review_queue_backlog_limit: 1000   # Max items in review queue
  min_avg_confidence: 0.60           # Min average confidence score
```

## ThinkTank API Configuration

```yaml
thinktank:
  base_url: "https://api-internal.target.com"
  chat_endpoint: "/gen_ai_model_requests/v1/chat/completions"
  app_name: "plm-tcin-mapper-api"
  tenant_id: ""
  is_prod: true
```

---

# plm-tcin-mapper-client

**Service:** Streamlit web UI for TCIN mapping review
**Default Port:** 8080 (in container and host)
**Entry Point:** `plm_tcin_mapper_client.main:start`

## Core Application Variables

### APP_PORT
- **Type:** Integer
- **Default:** `8080`
- **Required:** No
- **Description:** Port the Streamlit app listens on
- **Example:** `8080`
- **Set In:** entrypoint.sh, docker-compose env, TAP config
```bash
export APP_PORT=8080
```

## API Communication

### API_BASE_URL
- **Type:** String (URL)
- **Default:** `http://localhost:8080`
- **Required:** Yes (important!)
- **Description:** Base URL of the API service
- **Format:** `http://[host]:[port]`
- **Set In:** Environment variables, docker-compose, TAP config
```bash
# Local development
export API_BASE_URL=http://localhost:8001

# Docker Compose (service-to-service)
export API_BASE_URL=http://api:8080

# Production (via TAP)
export API_BASE_URL=http://plm-tcin-mapper-api:8080
```

**Critical Note:** This determines which API the UI calls. Must be set correctly or UI will fail.

## Configuration Directory

### APP_CONFIG_DIR
- **Type:** String (file path)
- **Default:** `/app/config`
- **Required:** No
- **TAP Override:** `/tap/config` (if mounted)
- **Description:** Directory containing configuration files
- **Set In:** entrypoint.sh
```bash
export APP_CONFIG_DIR=/app/config
# TAP overrides with: /tap/config
```

## Streamlit Configuration

These can be set via environment or passed as Streamlit CLI args:

### Server Configuration
```bash
# Port
streamlit run app.py --server.port 8080

# Address binding
--server.address 0.0.0.0

# Headless mode (no browser)
--server.headless true
```

### Logger Level

```bash
# Via environment
export STREAMLIT_LOGGER_LEVEL=info

# Options: debug, info, warning, error
```

### Session State (Internal)

Streamlit manages session state internally. No env vars needed.

## API Endpoint Configuration (in api_client.py)

The `api_client.py` module uses `API_BASE_URL` to construct all endpoints:

```python
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")

# Constructs URLs like:
# {API_BASE_URL}/api/v1/mappings
# {API_BASE_URL}/api/v1/admin/stats
# {API_BASE_URL}/health
```

---

# Configuration Files

## config/base.yaml

Master configuration file (baked into Docker images, overridable by TAP):

```yaml
# Application identity
app:
  name: "plm-tcin-mapper-api"        # or other app name
  env: "development"                 # development, staging, production
  log_level: "INFO"

# LLM Configuration
llm:
  provider: "thinktank"
  model: "gemini-1.5-pro"
  temperature: 1.0
  max_tokens: 2048
  request_timeout: 120
  max_retries: 3

# ThinkTank API
thinktank:
  base_url: "https://api-internal.target.com"
  chat_endpoint: "/gen_ai_model_requests/v1/chat/completions"
  app_name: "plm-tcin-mapper-ai"
  tenant_id: ""
  token_env_var: "THINKTANK_API_KEY"
  is_prod: true

# Spark/ASGI Server (for development)
spark:
  host: "0.0.0.0"
  port: 8080

# MongoDB
mongo:
  url: "mongodb://localhost:27017"
  database: "tcin_mapper"

# Matching algorithm (API only)
matching:
  auto_confirm_threshold: 0.85
  no_match_threshold: 0.75
  llm_fallback_threshold: 0.60
  low_confidence_threshold: 0.50
  llm_ambiguity_band: 0.15

# Data ingestion (API only)
ingestion:
  data_dir: "apps/plm-tcin-mapper/data/normalized"
  batch_size: 500
  skip_existing: true

# Evaluation metrics (API only)
eval:
  min_high_confidence_pct: 0.40
  max_low_confidence_pct: 0.20
  review_queue_backlog_limit: 1000
  min_avg_confidence: 0.60
```

---

# Setting Environment Variables

## Development (Local with uvicorn/streamlit)

### Option 1: Export in terminal
```bash
export APP_PORT=8001
export API_BASE_URL=http://localhost:8001
export MONGO_URL=mongodb://localhost:27017
export GUNICORN_WORKERS=1

# Then run
uv run uvicorn plm_tcin_mapper_api.main:app --port 8001
```

### Option 2: .env file (if supported)
Create `.env` in project root:
```
APP_PORT=8001
API_BASE_URL=http://localhost:8001
MONGO_URL=mongodb://localhost:27017
GUNICORN_WORKERS=1
```

Then load before running.

## Docker / Docker Compose

### Option 1: Command line
```bash
docker run \
  -e APP_PORT=8080 \
  -e MONGO_URL=mongodb://mongo:27017 \
  -e GUNICORN_WORKERS=4 \
  -p 8001:8080 \
  plm-tcin-mapper-api:latest
```

### Option 2: docker-compose.yml
```yaml
services:
  api:
    image: plm-tcin-mapper-api:latest
    environment:
      APP_PORT: 8080
      MONGO_URL: mongodb://mongo:27017
      GUNICORN_WORKERS: 4
      GUNICORN_TIMEOUT: 120
    ports:
      - "8001:8080"
    depends_on:
      - mongo

  client:
    image: plm-tcin-mapper-client:latest
    environment:
      APP_PORT: 8080
      API_BASE_URL: http://api:8080
    ports:
      - "8080:8080"
    depends_on:
      - api
```

## Kubernetes / TAP Deployment

### TAP ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: plm-tcin-mapper-api-config
data:
  GUNICORN_WORKERS: "8"
  GUNICORN_TIMEOUT: "120"
  MONGO_URL: "mongodb://mongo-cluster:27017"
---
apiVersion: v1
kind: Secret
metadata:
  name: plm-tcin-mapper-secrets
type: Opaque
data:
  THINKTANK_API_KEY: <base64-encoded-key>
  THINKTANK_OAUTH_CLIENT_ID: <base64-encoded-id>
```

### TAP Deployment
TAP mounts config at `/tap/config` which overrides default `/app/config`.

---

# Environment Variable Summary Table

## plm-think-tank-ai

| Variable | Default | Required | Type | Purpose |
|----------|---------|----------|------|---------|
| APP_PORT | 8080 | No | int | Listen port |
| APP_ENV | development | No | str | Environment |
| LOG_LEVEL | INFO | No | str | Log level |
| GUNICORN_WORKERS | 4 | No | int | Worker processes |
| GUNICORN_TIMEOUT | 120 | No | int | Timeout (sec) |
| MONGO_URL | localhost:27017 | Yes | str | DB connection |
| THINKTANK_API_KEY | None | Yes | str | API key (secret) |

## plm-tcin-mapper-api

| Variable | Default | Required | Type | Purpose |
|----------|---------|----------|------|---------|
| APP_PORT | 8080 | No | int | Listen port |
| APP_ENV | development | No | str | Environment |
| LOG_LEVEL | INFO | No | str | Log level |
| GUNICORN_WORKERS | 4 | No | int | Worker processes |
| GUNICORN_TIMEOUT | 120 | No | int | Timeout (sec) |
| MONGO_URL | localhost:27017 | Yes | str | DB connection |
| THINKTANK_API_KEY | None | Yes | str | API key (secret) |

## plm-tcin-mapper-client

| Variable | Default | Required | Type | Purpose |
|----------|---------|----------|------|---------|
| APP_PORT | 8080 | No | int | Listen port |
| API_BASE_URL | localhost:8080 | Yes | str | API URL |
| APP_CONFIG_DIR | /app/config | No | str | Config directory |

---

# Quick Reference

## Development (Local)

```bash
# API
export APP_PORT=8001
export MONGO_URL=mongodb://localhost:27017
export GUNICORN_WORKERS=1

# Client
export API_BASE_URL=http://localhost:8001
export APP_PORT=8080

# Run tests
python test_integration.py
```

## Production (Docker)

```bash
# API
docker run -e APP_PORT=8080 -e MONGO_URL=mongodb://mongo:27017 \
  -e GUNICORN_WORKERS=8 -p 8001:8080 plm-tcin-mapper-api:latest

# Client
docker run -e APP_PORT=8080 -e API_BASE_URL=http://api:8080 \
  -p 8080:8080 plm-tcin-mapper-client:latest
```

## Production (TAP)

TAP injects:
- Secrets from vault
- Config from `/tap/config/base.yaml`
- Certificates from `/tap/certificates`

No need to manually set environment variables in TAP deployments.

---

# Common Issues & Solutions

## "Cannot connect to API"
- Check `API_BASE_URL` is set correctly
- Verify API is running on the specified port
- Test: `curl http://<API_BASE_URL>/health`

## "MongoDB connection failed"
- Check `MONGO_URL` is correct
- Verify MongoDB is running: `mongosh --eval "db.adminCommand('ping')"`
- Check credentials if using auth

## "Workers not scaling"
- Set `GUNICORN_WORKERS` based on CPU cores
- Formula: CPU cores × 2 + 1
- Example: 4 cores → 9 workers

## "Timeout errors"
- Increase `GUNICORN_TIMEOUT` for long-running operations
- Default 120s may be insufficient for batch jobs

---

**Last Updated:** 2026-06-12
**Status:** ✅ Complete Reference
