.PHONY: test format lint typecheck check
.DEFAULT_GOAL := all

test:
	uv run pytest

format:
	black .
	isort .
	ruff check --fix .


lint:
	black --check .
	isort --check .
	ruff check .

typecheck:
	mypy src/mcp_shell_server tests

coverage:
	pytest --cov=src/mcp_shell_server tests

# Run all checks required before pushing
check:  lint typecheck test
fix: check format
all: format check test coverage
