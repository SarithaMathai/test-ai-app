# AI monorepo — single parameterized image for all HTTP service apps.
# Selects the app at build time via APP_PACKAGE build arg.
#
# Base image: https://github.com/target-corp/python-docker-uv
#   Provides Python 3.12, uv, Target CA certs, Artifactory pip config, non-root user.
FROM docker.target.com/iam/python/tgt-uv:3.12-slim-bullseye

USER root

# curl: health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Target Application Platform runtime connector — wraps entrypoint and injects
# secrets/config/certificates at /tap/* mount points.
COPY --from=docker.target.com/tap/runtime-connector:v2.5.4 /runtime-connector /runtime-connector

WORKDIR /app
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build arg selects which workspace app to install.
# Example: --build-arg APP_PACKAGE=spark-think-tank-ai
ARG APP_PACKAGE="spark-think-tank-ai"

# Stage 1: copy lockfile and manifests (cached layer for dependency install).
COPY pyproject.toml uv.lock* .python-version* ./
COPY libs/ ./libs/
COPY apps/ ./apps/

# Install only the selected app and its transitive deps (no dev/test/lint).
RUN uv sync --frozen --package "${APP_PACKAGE}" \
        --no-group dev --no-group test --no-group lint

# Stage 2: runtime files.
# Per-app entrypoint lives alongside the app source.
COPY apps/${APP_PACKAGE}/entrypoint.sh ./entrypoint.sh
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
