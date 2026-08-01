## Implementation Tasks

- [ ] Add `tests/test_project_metadata.py` to reject dependency declarations permitting MCP SDK 2.x. (verification-id: mcp-v1-sdk-compatibility) (verification: unit - `uv run pytest tests/test_project_metadata.py` exercises repository metadata)
- [ ] Constrain the production MCP SDK dependency in `pyproject.toml` to the compatible v1 line and refresh `uv.lock`. (verification-id: mcp-v1-sdk-compatibility) (verification: integration - `uv lock && uv run python -c "import mcp_shell_server"`)
- [ ] Record the startup compatibility fix in `CHANGELOG.md`. (verification-id: mcp-v1-sdk-compatibility) (verification: unit - `uv run pytest tests/test_project_metadata.py::test_changelog_records_mcp_v2_compatibility_fix`)
- [ ] Run the repository quality suite. (verification-id: mcp-v1-sdk-compatibility) (verification: integration - `uv run make all`)

## Future Work

- Migrate the server to the MCP Python SDK v2 API in a separate change.
- Repository owner decides when to merge and release.

## Final Validation

Expected archive gate: `cflx openspec validate pin-mcp-v1-sdk --archive-gate`
