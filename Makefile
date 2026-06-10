.PHONY: help init sync \
        lint format type-check quality-gate \
        test test-unit test-int test-cov \
        test-spark test-tcin test-core test-elastic test-mongo test-openai test-thinktank test-toss \
        run-spark run-tcin \
        build build-libs build-spark build-tcin \
        clean

# ── Default target ─────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help

# ── Help ───────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "my-test-ai-app -- available targets"
	@echo "------------------------------------------------------------"
	@echo "  [Setup]"
	@echo "    init            Install all packages + groups + pre-commit hooks"
	@echo "    sync            Sync all packages (no hooks)"
	@echo ""
	@echo "  [Code quality]"
	@echo "    lint            ruff check + ruff format --check + mypy (read-only)"
	@echo "    format          ruff format + ruff check --fix (auto-write)"
	@echo "    type-check      mypy on libs/ and apps/"
	@echo "    quality-gate    lint + type-check + test-cov (CI entry point)"
	@echo ""
	@echo "  [Tests]"
	@echo "    test            Run all tests (unit + integration)"
	@echo "    test-unit       Fast unit tests only  (-m unit)"
	@echo "    test-int        Integration tests only (-m integration)"
	@echo "    test-cov        Full run + HTML coverage -- htmlcov/index.html"
	@echo "    test-spark      Tests for apps/spark-think-tank-ai"
	@echo "    test-tcin       Tests for apps/tcin-impression-mapping"
	@echo "    test-core       Tests for libs/ai-core"
	@echo "    test-openai     Tests for libs/ai-openai"
	@echo "    test-elastic    Tests for libs/ai-elastic"
	@echo "    test-mongo      Tests for libs/ai-mongo"
	@echo "    test-thinktank  Tests for libs/ai-thinktank"
	@echo "    test-toss       Tests for libs/ai-toss-utils"
	@echo ""
	@echo "  [Run locally]"
	@echo "    run-spark       Start spark-think-tank-ai (uvicorn --reload)"
	@echo "    run-tcin        Start tcin-impression-mapping (streamlit)"
	@echo ""
	@echo "  [Build]"
	@echo "    build           Build wheels for all workspace packages"
	@echo "    build-libs      Build wheels for libs/* only"
	@echo "    build-spark     Build wheel for spark-think-tank-ai"
	@echo "    build-tcin      Build wheel for tcin-impression-mapping"
	@echo ""
	@echo "  [Clean]"
	@echo "    clean           Remove .venv, dist/, build/, caches"
	@echo "------------------------------------------------------------"
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
	$(MAKE) type-check

format:
	uv run ruff format .
	uv run ruff check --fix .

type-check:
	uv run mypy libs/ai-core/ai_core
	uv run mypy libs/ai-elastic/ai_elastic
	uv run mypy libs/ai-mongo/ai_mongo
	uv run mypy libs/ai-openai/ai_openai
	uv run mypy libs/ai-thinktank/ai_thinktank
	uv run mypy libs/ai-toss-utils/ai_toss_utils
	uv run mypy apps/spark-think-tank-ai/spark_think_tank_ai
	uv run mypy apps/tcin-impression-mapping/tcin_impression_mapping

quality-gate: lint test-cov
	@echo ""
	@echo "  Quality gate PASSED"
	@echo ""

# ── Tests ──────────────────────────────────────────────────────────────────────
test: sync
	uv run pytest -v

test-unit: sync
	uv run pytest -m unit -v

test-int: sync
	uv run pytest -m integration -v

test-cov: sync
	uv run pytest --cov --cov-report=term-missing --cov-report=html
	@echo "Coverage report → htmlcov/index.html"

# Per-package targets: run only the tests inside that package tree.
test-spark:
	uv run pytest apps/spark-think-tank-ai/tests -v

test-tcin:
	uv run pytest apps/tcin-impression-mapping/tests -v

test-core:
	uv run pytest libs/ai-core/tests -v

test-openai:
	uv run pytest libs/ai-openai/tests -v

test-thinktank:
	uv run pytest libs/ai-thinktank/tests -v

test-elastic:
	uv run pytest libs/ai-elastic/tests -v

test-mongo:
	uv run pytest libs/ai-mongo/tests -v

test-toss:
	uv run pytest libs/ai-toss-utils/tests -v

# ── Run locally ────────────────────────────────────────────────────────────────
run-spark:
	uv run uvicorn spark_think_tank_ai.main:app --reload --host 0.0.0.0 --port 8000

run-tcin:
	uv run streamlit run apps/tcin-impression-mapping/tcin_impression_mapping/ui/app.py

# ── Build ──────────────────────────────────────────────────────────────────────
build: build-libs build-spark build-tcin

build-libs:
	uv build --package ai-core       --out-dir dist/
	uv build --package ai-elastic    --out-dir dist/
	uv build --package ai-mongo      --out-dir dist/
	uv build --package ai-openai     --out-dir dist/
	uv build --package ai-thinktank  --out-dir dist/
	uv build --package ai-toss-utils --out-dir dist/

build-spark:
	uv build --package spark-think-tank-ai --out-dir dist/

build-tcin:
	uv build --package tcin-impression-mapping --out-dir dist/

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	rm -rf .venv dist/ build/ .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".venv" -exec rm -rf {} +
