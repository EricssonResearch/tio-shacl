.PHONY: help install test test-fast lint format type-check clean setup-tio java-build coverage

help:
	@echo "Available targets:"
	@echo "  install       Install all deps (api, mcp, dev) via uv"
	@echo "  setup-tio     Apply TIO 3.6.0 patch (ontology/ must exist)"
	@echo "  test          Run fast test suite (skips slow 133-case validations)"
	@echo "  test-fast     Run fast tests in parallel (pytest-xdist)"
	@echo "  test-slow     Run ALL tests incl. full 133-case validations (parallel)"
	@echo "  test-full     Same as test-slow but serial (debugging)"
	@echo "  lint          Run ruff linter"
	@echo "  format        Run ruff formatter + autofix"
	@echo "  type-check    Run mypy"
	@echo "  java-build    Build Jena + TopBraid CLI jars"
	@echo "  coverage      Generate validation coverage report"
	@echo "  clean         Remove caches and build artifacts"

install:
	uv sync --all-extras --all-groups

setup-tio:
	bash scripts/setup_tio.sh

test:
	uv run pytest

test-fast:
	uv run pytest -n auto

test-slow:
	uv run pytest -m "slow or not slow" -n auto

test-full:
	uv run pytest -m "slow or not slow"

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

type-check:
	uv run mypy src/tio_shacl/

java-build:
	cd java_wrappers && ./mvnw package

coverage:
	uv run python scripts/generate_coverage_report.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
