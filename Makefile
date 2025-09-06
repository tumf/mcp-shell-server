.PHONY: test format lint typecheck check install-pre-commit
.DEFAULT_GOAL := all

install:
	uv pip install --upgrade '.[dev,test]'

test:
	uv run pytest

test-parallel:
	uv run pytest -n auto

test-fast:
	uv run pytest -n auto -m "not slow"

format:
	uv run isort .
	uv run black .
	uv run mypy --install-types --non-interactive src/mcp_shell_server tests
	uv run ruff check --fix .


lint:
	uv run black --check .
	uv run isort --check .
	uv run ruff check .

typecheck:
	uv sync --group dev --extra test
	uv run mypy src/mcp_shell_server tests

coverage:
	uv run pytest --cov=src/mcp_shell_server --cov-report=xml --cov-report=term-missing tests

# Run all checks required before pushing
check:  lint typecheck
fix: check format
all: format check coverage

install-pre-commit:
	@.wkm/bin/install
