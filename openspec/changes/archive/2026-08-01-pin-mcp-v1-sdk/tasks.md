## Implementation Tasks

- [x] Add `tests/test_project_metadata.py` to reject dependency declarations permitting MCP SDK 2.x. (verification-id: mcp-v1-sdk-compatibility) (verification: unit - `uv run pytest tests/test_project_metadata.py` exercises repository metadata)
- [x] Constrain the production MCP SDK dependency in `pyproject.toml` to the compatible v1 line and refresh `uv.lock`. (verification-id: mcp-v1-sdk-compatibility) (verification: integration - `uv lock && uv run python -c "import mcp_shell_server"`)
- [x] Record the startup compatibility fix in `CHANGELOG.md`. (verification-id: mcp-v1-sdk-compatibility) (verification: inspection - review the Unreleased section in `CHANGELOG.md`)
- [x] Run the repository quality suite. (verification-id: mcp-v1-sdk-compatibility) (verification: integration - `uv run make all`)

## Future Work

- Migrate the server to the MCP Python SDK v2 API in a separate change.
- Repository owner decides when to merge and release.

## Final Validation

Expected archive gate: `cflx openspec validate pin-mcp-v1-sdk --archive-gate`

- `cflx openspec validate pin-mcp-v1-sdk --strict` passed.
- `uv run make all` passed: format, lint, mypy, and 205 tests (203 pre-existing plus 2 new), 92% coverage. The single `PytestUnraisableExceptionWarning` is pre-existing and also occurs on the unmodified tree (203 passed, 1 warning).
- `uv run pytest tests/test_project_metadata.py` passed (2 tests); the dependency assertion was confirmed red before the fix (`'mcp>=1.1.2' permits MCP SDK 2.x`).
- `uv lock` resolves `mcp==1.27.2` and records the `>=1.1.2,<2` specifier; `uv run python -c "import mcp_shell_server"` succeeds.
- Reproduced the underlying defect: unconstrained `mcp` resolves `2.0.0`, where `Server.list_tools` no longer exists, so importing `mcp_shell_server.server` raises `AttributeError: 'Server' object has no attribute 'list_tools'`.

## Notes

- The metadata regression tests use only the Python standard library and read committed static metadata files.
