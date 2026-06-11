.PHONY: help init sync \
        lint format type-check quality-gate \
        test test-unit test-functional test-int test-cov \
        test-app test-ai-core test-ai-thinktank test-ai-toss-utils test-ai-mongo test-tcin-mapper \
        run-plm run-thinktank run-tcin-mapper run-tcin-ui \
        docker-build docker-build-tcin-mapper tap \
        build build-libs build-app \
        clean clean-lock

.DEFAULT_GOAL := help

# ── Help ───────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "plm-ai-apps monorepo — available targets"
	@echo "============================================================"
	@echo "  [Setup]"
	@echo "    init                Install all packages + groups + pre-commit hooks"
	@echo "    sync                Sync all packages (no hooks)"
	@echo ""
	@echo "  [Code quality]"
	@echo "    lint                ruff check + ruff format --check (read-only)"
	@echo "    format              ruff format + ruff check --fix (writes files)"
	@echo "    type-check          mypy on libs/ and apps/"
	@echo "    quality-gate        lint + type-check + test-cov (CI entry point)"
	@echo ""
	@echo "  [Tests]"
	@echo "    test                Unit + integration (safe to run anywhere, no credentials)"
	@echo "    test-unit           Unit only  (-m unit)"
	@echo "    test-int            Integration: mocked-external, multi-component  (-m integration)"
	@echo "    test-functional     Functional: calls real ThinkTank API  (-m functional)"
	@echo "                        Requires: THINKTANK_API_KEY in .env"
	@echo "    test-cov            test + test-int + HTML coverage report"
	@echo "    test-app            Unit + functional tests for apps/plm-think-tank-ai"
	@echo "    test-ai-core        Unit + functional tests for libs/ai-core"
	@echo "    test-ai-thinktank   Unit tests for libs/ai-thinktank (live tests: test-int)"
	@echo "    test-ai-toss-utils  Unit + functional tests for libs/ai-toss-utils"
	@echo ""
	@echo "  [Run locally]"
	@echo "    run-plm             Start ALL apps (each on its own port, kills port if in use)"
	@echo "    run-thinktank       Start plm-think-tank-ai only  (:8000)"
	@echo "    run-tcin-mapper     Start plm-tcin-mapper API only (:8001)"
	@echo "    run-tcin-ui         Start plm-tcin-mapper Streamlit operator UI (:8501)"
	@echo ""
	@echo "  [Tests]"
	@echo "    test-tcin-mapper    Unit + integration for apps/plm-tcin-mapper"
	@echo "    test-ai-mongo       Unit tests for libs/ai-mongo"
	@echo ""
	@echo "  [Docker / TAP]"
	@echo "    docker-build              Build plm-think-tank-ai image"
	@echo "    docker-build-tcin-mapper  Build plm-tcin-mapper image"
	@echo "    tap                       Build + start under TAP simulator"
	@echo ""
	@echo "  [Build]"
	@echo "    build               Build wheels for all workspace packages"
	@echo "    build-libs          Build wheels for libs/* (includes ai-mongo)"
	@echo "    build-app           Build wheels for all apps"
	@echo ""
	@echo "  [Clean]"
	@echo "    clean               Remove .venv, dist/, build/, caches (keeps uv.lock)"
	@echo "    clean-lock          clean + remove uv.lock (forces full re-resolve)"
	@echo "============================================================"
	@echo ""

# ── Setup ──────────────────────────────────────────────────────────────────────
init:
	uv sync --all-packages --all-groups
	uv run pre-commit install --install-hooks || true

sync:
	uv sync --all-packages --all-groups

# ── Code quality ───────────────────────────────────────────────────────────────
lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

type-check:
	uv run mypy libs/ai-core/ai_core
	uv run mypy libs/ai-toss-utils/ai_toss_utils
	uv run mypy libs/ai-thinktank/ai_thinktank
	uv run mypy libs/ai-mongo/ai_mongo
	uv run mypy apps/plm-think-tank-ai/plm_think_tank_ai
	uv run mypy apps/plm-tcin-mapper/plm_tcin_mapper

quality-gate: lint type-check test-cov

# ── Tests ──────────────────────────────────────────────────────────────────────
test:
	uv run pytest -m "unit or integration" -v

test-unit:
	uv run pytest -m unit -v

test-int:
	uv run pytest -m integration -v

test-functional:
	uv run pytest -m functional -v

test-cov:
	uv run pytest -m "unit or integration" --cov --cov-report=term-missing --cov-report=html
	@echo "Coverage report → htmlcov/index.html"

# Per-package test targets
test-app:
	uv run pytest apps/plm-think-tank-ai/tests/unit apps/plm-think-tank-ai/tests/integration -v

test-tcin-mapper:
	uv run pytest apps/plm-tcin-mapper/tests/unit apps/plm-tcin-mapper/tests/integration -v

test-ai-core:
	uv run pytest libs/ai-core/tests -v

test-ai-thinktank:
	uv run pytest libs/ai-thinktank/tests -v

test-ai-toss-utils:
	uv run pytest libs/ai-toss-utils/tests -v

test-ai-mongo:
	uv run pytest libs/ai-mongo/tests -v

# ── Run locally ────────────────────────────────────────────────────────────────
# Helper: kill whatever is bound to a port (no-op if port is free).
define kill_port
	@PID=$$(lsof -ti tcp:$(1) 2>/dev/null); \
	if [ -n "$$PID" ]; then \
		echo "Stopping process on port $(1) (PID $$PID)..."; \
		kill $$PID && sleep 1; \
	fi
endef

# Start ALL apps — each kills its own port if already in use.
# Each app gets its own .env override on top of the shared root .env.
run-plm:
	$(call kill_port,8000)
	$(call kill_port,8001)
	APP_CONFIG_DIR=config uv run \
		--env-file .env \
		$(if $(wildcard apps/plm-think-tank-ai/.env),--env-file apps/plm-think-tank-ai/.env,) \
		uvicorn plm_think_tank_ai.main:app --host 0.0.0.0 --port 8000 &
	APP_CONFIG_DIR=config uv run \
		--env-file .env \
		$(if $(wildcard apps/plm-tcin-mapper/.env),--env-file apps/plm-tcin-mapper/.env,) \
		uvicorn plm_tcin_mapper.main:app --reload --host 0.0.0.0 --port 8001

# ── Individual app targets ────────────────────────────────────────────────────
# Add one block per app as new apps are introduced.
# Pattern: --env-file .env (shared) then --env-file apps/<name>/.env (app-specific override).

# plm-think-tank-ai  →  :8000
run-thinktank:
	$(call kill_port,8000)
	APP_CONFIG_DIR=config uv run \
		--env-file .env \
		$(if $(wildcard apps/plm-think-tank-ai/.env),--env-file apps/plm-think-tank-ai/.env,) \
		uvicorn plm_think_tank_ai.main:app --reload --host 0.0.0.0 --port 8000

# plm-tcin-mapper  →  :8001
run-tcin-mapper:
	$(call kill_port,8001)
	APP_CONFIG_DIR=config uv run \
		--env-file .env \
		$(if $(wildcard apps/plm-tcin-mapper/.env),--env-file apps/plm-tcin-mapper/.env,) \
		uvicorn plm_tcin_mapper.main:app --reload --host 0.0.0.0 --port 8001

# plm-tcin-mapper Streamlit operator UI  →  :8501
# Optional internal review tool — needs the `ui` dependency group (streamlit).
# Reads directly from MongoDB; run alongside (or instead of) the API.
run-tcin-ui:
	$(call kill_port,8501)
	APP_CONFIG_DIR=config uv run --group ui \
		--env-file .env \
		$(if $(wildcard apps/plm-tcin-mapper/.env),--env-file apps/plm-tcin-mapper/.env,) \
		streamlit run apps/plm-tcin-mapper/plm_tcin_mapper/ui/streamlit_app.py \
		--server.port=8501 --server.address=0.0.0.0

# ── Docker / TAP ───────────────────────────────────────────────────────────────
docker-build:
	DOCKER_BUILDKIT=0 docker build \
		--build-arg APP_PACKAGE=plm-think-tank-ai \
		-t plm-ai-apps:local .

docker-build-tcin-mapper:
	DOCKER_BUILDKIT=0 docker build \
		--build-arg APP_PACKAGE=plm-tcin-mapper \
		-t plm-tcin-mapper:local .

tap:
	./tap-docker.sh

# ── Build ──────────────────────────────────────────────────────────────────────
build: build-libs build-app

build-libs:
	uv build --package ai-core       --out-dir dist/
	uv build --package ai-toss-utils --out-dir dist/
	uv build --package ai-thinktank  --out-dir dist/
	uv build --package ai-mongo      --out-dir dist/

build-app:
	uv build --package plm-think-tank-ai --out-dir dist/
	uv build --package plm-tcin-mapper   --out-dir dist/

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	rm -rf .venv dist/ build/ htmlcov/ .coverage .mypy_cache .ruff_cache
	# Note: uv.lock is committed — 'make clean' keeps it. Use 'make clean-lock' to also reset the lockfile.

clean-lock: clean
	rm -f uv.lock
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
