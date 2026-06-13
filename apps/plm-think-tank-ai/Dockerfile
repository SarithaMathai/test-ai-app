# PLM Think Tank AI — FastAPI application.
# Standalone service for AI prompt generation and reasoning.
#
# Base image: https://github.com/target-corp/python-docker-uv
#   Provides Python 3.12, uv, Target CA certs, Artifactory pip config, non-root user.
#
# Build:
#   docker build -f apps/plm-think-tank-ai/Dockerfile -t plm-think-tank-ai:latest .
#
# Run:
#   docker run -p 8080:8080 plm-think-tank-ai:latest
#
# ─────────────────────────────────────────────────────────────────────────────
FROM docker.target.com/iam/python/tgt-uv:3.12-slim-bullseye

USER root

# curl: health checks / liveness probes.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Target Application Platform runtime connector — wraps the entrypoint and
# injects secrets/config/certificates at /tap/* mount points.
COPY --from=docker.target.com/tap/runtime-connector:v2.5.4 /runtime-connector /runtime-connector

WORKDIR /app
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ── Stage 1: dependency install (cached layer) ────────────────────────────────
# Copy lockfile + root manifests first so Docker can cache the install layer.
COPY pyproject.toml uv.lock* .python-version* README.md ./
COPY libs/ ./libs/
COPY apps/plm-think-tank-ai/ ./apps/plm-think-tank-ai/

# Install only this app and its transitive runtime deps.
# --package scopes to one app; dev/test/lint groups are excluded by default.
RUN uv sync --frozen --package plm-think-tank-ai

# ── Stage 2: application source + runtime files ───────────────────────────────
# Per-app entrypoint lives alongside the app source.
COPY apps/plm-think-tank-ai/entrypoint.sh ./entrypoint.sh
# Bake non-secret YAML config defaults into the image.
# TAP mounts /tap/config at deploy time to override (see entrypoint.sh).
COPY config/ /app/config/

RUN mkdir -p /tap/secret /tap/config /tap/certificates /tap/secret/restricted && \
    chmod +x /app/entrypoint.sh && \
    chown -R python:python /app /tap && \
    chmod 750 /tap

USER python

# Default config dir; TAP-mounted /tap/config takes precedence (see entrypoint.sh).
ENV APP_CONFIG_DIR=/app/config

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

ENTRYPOINT ["/runtime-connector", "--", "/bin/sh", "./entrypoint.sh"]
