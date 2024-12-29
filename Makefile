.PHONY: test format lint typecheck check
.DEFAULT_GOAL := all

test:
	uv run pytest

format:
	uv run isort .
	uv run black .
	uv run ruff check --fix .


lint:
	uv run isort --check .
	uv run black --check .
	uv run ruff check .

typecheck:
	uv run mypy src/mcp_shell_server tests

coverage:
	uv run pytest --cov=src/mcp_shell_server tests

# Run all checks required before pushing
check:  lint typecheck
fix: check format
all: format check coverage
