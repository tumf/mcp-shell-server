.PHONY: test format lint typecheck check
.DEFAULT_GOAL := all

test:
	pytest

format:
	black .
	isort .
	ruff check --fix .


lint:
	black --check .
	isort --check .
	ruff check .

typecheck:
	mypy --install-types --non-interactive src/mcp_shell_server

coverage:
	pytest --cov=src/mcp_shell_server --cov-report=xml --cov-report=term-missing tests

# Run all checks required before pushing
check:  lint typecheck
fix: check format
all: format check coverage
