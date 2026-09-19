## Implementation Tasks

- [ ] Add repository tests that bind README and SECURITY.md to the trusted-execution contract and reject an unqualified complete-sandbox claim. (verification: `uv run pytest -q`; verification-id: trusted-execution-contract)
- [ ] Rewrite the README introduction and security guidance to define direct command-name admission, retained non-exhaustive hardening, and concrete external isolation boundaries. (verification: `uv run pytest -q`; verification-id: trusted-execution-contract)
- [ ] Align SECURITY.md guarantees, non-guarantees, deployment guidance, and vulnerability-reporting scope with the same threat model. (verification: `uv run pytest -q`; verification-id: trusted-execution-contract)
- [ ] Emit one operator warning through the existing logger during server startup and verify that MCP stdout framing is unchanged. (verification: `uv run pytest -q`; verification-id: runtime-trust-warning)
- [ ] Clarify the MCP tool description without changing tool names, schemas, environment variables, or execution behavior. (verification: `uv run pytest -q`; verification-id: trusted-execution-contract)
- [ ] Record the startup warning and clarified trusted-execution contract under Unreleased in CHANGELOG.md. (verification: `uv run pytest -q`; verification-id: trusted-execution-contract)
- [ ] Run the complete repository quality gates and retain every existing command-specific security regression. (verification: `uv run pytest -q && uv run black --check . && uv run isort --check . && uv run ruff check . && uv run mypy src/mcp_shell_server tests`; verification-id: compatibility-preserved)

## Final Validation

- `uv run pytest -q`
- `uv run black --check .`
- `uv run isort --check .`
- `uv run ruff check .`
- `uv run mypy src/mcp_shell_server tests`
- `cflx openspec validate define-trusted-execution --archive-gate`
- Inspect server startup stderr and verify no warning text appears on MCP stdout.
