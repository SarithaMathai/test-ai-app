#!/usr/bin/env bash
# Build the PLM AI Apps image and start it under the TAP simulator.
#
# Usage:
#   ./tap-docker.sh          # defaults: port 8080
#   ./tap-docker.sh 8081     # custom port
#
# The script vendors the shared libs from test-ai-app before building so
# the Dockerfile COPY libs/ step resolves locally.

set -euo pipefail

APP_PORT="${1:-8080}"
IMAGE="plm-ai-apps:local"

echo "→ Vendoring shared libs..."
make vendor-libs

echo "→ Building Docker image ${IMAGE}..."
DOCKER_BUILDKIT=0 docker build -t "${IMAGE}" .

echo "→ Starting TAP simulator (port ${APP_PORT})..."
tapctl simulator start \
    --cluster plm-ai-apps \
    --image "${IMAGE}" \
    -e dev \
    -p "${APP_PORT}:8080"
