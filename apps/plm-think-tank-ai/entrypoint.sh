#!/bin/sh
# Entrypoint for plm-think-tank-ai FastAPI service.
#
# Gunicorn + UvicornWorker: production-grade process manager with async workers.
#
# Env vars (all have sensible defaults):
#   GUNICORN_WORKERS   — number of worker processes (default: 4)
#   GUNICORN_TIMEOUT   — worker timeout in seconds (default: 120)
#   APP_PORT           — bind port (default: 8080, TAP standard)
#   APP_CONFIG_DIR     — config directory (default: /app/config; TAP mounts at /tap/config)

set -eu

# TAP mounts config at /tap/config when the app is deployed — prefer it over baked-in defaults.
if [ -f "/tap/config/base.yaml" ] || [ -f "/tap/config/base.yml" ]; then
    export APP_CONFIG_DIR=/tap/config
else
    export APP_CONFIG_DIR="${APP_CONFIG_DIR:-/app/config}"
fi

: "${GUNICORN_WORKERS:=4}"
: "${GUNICORN_TIMEOUT:=120}"
: "${APP_PORT:=8080}"

echo "Starting plm-think-tank-ai — workers=${GUNICORN_WORKERS}, port=${APP_PORT}, config_dir=${APP_CONFIG_DIR}"

exec .venv/bin/gunicorn plm_think_tank_ai.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${GUNICORN_WORKERS}" \
    --bind "0.0.0.0:${APP_PORT}" \
    --timeout "${GUNICORN_TIMEOUT}" \
    --access-logfile - \
    --error-logfile - \
    --log-level info
