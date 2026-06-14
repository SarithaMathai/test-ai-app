#!/bin/sh
# Entrypoint for plm-tcin-mapper-client Streamlit UI.
#
# Streamlit: lightweight Python web app framework.
#
# Env vars (all have sensible defaults):
#   APP_PORT           — bind port (default: 8080, TAP standard)
#   API_BASE_URL       — plm-tcin-mapper-api service URL (default: http://localhost:8080)
#   APP_CONFIG_DIR     — config directory (default: /app/config; TAP mounts at /tap/config)

set -eu

# TAP mounts config at /tap/config when the app is deployed — prefer it over baked-in defaults.
if [ -f "/tap/config/base.yaml" ] || [ -f "/tap/config/base.yml" ]; then
    export APP_CONFIG_DIR=/tap/config
else
    export APP_CONFIG_DIR="${APP_CONFIG_DIR:-/app/config}"
fi

: "${APP_PORT:=8080}"
: "${API_BASE_URL:=http://plm-tcin-mapper-api:8080}"

echo "Starting plm-tcin-mapper-client — port=${APP_PORT}, api=${API_BASE_URL}"

exec /app/.venv/bin/python -m streamlit run plm_tcin_mapper_client/streamlit_app.py \
    --server.port "${APP_PORT}" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --logger.level info
