## Implementation Tasks

- [x] Add `tests/test_project_metadata.py` to reject dependency declarations permitting MCP SDK 2.x. (verification-id: mcp-v1-sdk-compatibility) (verification: unit - `uv run pytest tests/test_project_metadata.py` exercises repository metadata)
- [x] Constrain the production MCP SDK dependency in `pyproject.toml` to the compatible v1 line and refresh `uv.lock`. (verification-id: mcp-v1-sdk-compatibility) (verification: integration - `uv lock && uv run python -c "import mcp_shell_server"`)
- [x] Record the startup compatibility fix in `CHANGELOG.md`. (verification-id: mcp-v1-sdk-compatibility) (verification: unit - `uv run pytest tests/test_project_metadata.py::test_changelog_records_mcp_v2_compatibility_fix`)
- [x] Run the repository quality suite. (verification-id: mcp-v1-sdk-compatibility) (verification: integration - `uv run make all`)

## Future Work

- Migrate the server to the MCP Python SDK v2 API in a separate change.
- Repository owner decides when to merge and release.

## Final Validation

Expected archive gate: `cflx openspec validate pin-mcp-v1-sdk --archive-gate`

- `cflx openspec validate pin-mcp-v1-sdk --strict` passed.
- `uv run make all` passed: format, lint, mypy, and 218 tests (203 pre-existing plus 15 new), 92% coverage. The single `PytestUnraisableExceptionWarning` is pre-existing and also occurs on the unmodified tree (203 passed, 1 warning).
- `uv run pytest tests/test_project_metadata.py` passed (15 tests); the two repository-facing assertions were confirmed red before the fix (`'mcp>=1.1.2' permits MCP SDK 2.x`, `CHANGELOG.md must record the MCP SDK 2.x startup-crash fix`).
- `uv lock` resolves `mcp==1.27.2` and records the `>=1.1.2,<2` specifier; `uv run python -c "import mcp_shell_server"` succeeds.
- Reproduced the underlying defect: unconstrained `mcp` resolves `2.0.0`, where `Server.list_tools` no longer exists, so importing `mcp_shell_server.server` raises `AttributeError: 'Server' object has no attribute 'list_tools'`.

## Notes

- Added `packaging>=23.0` to the `test` optional-dependency extra so the regression test's PEP 440 specifier parsing rests on a declared dependency rather than a transitive one.
- Verification-type alignment: the specifier, changelog, and lockfile decision logic is factored into pure helpers verified with in-memory inputs, so the `unit` classification holds. The repository-facing assertions read committed static metadata files, which is inherent to a metadata regression test and is not mutable external boundary state.
