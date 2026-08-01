---
change_type: implementation
priority: high
dependencies: []
references:
  - https://github.com/tumf/mcp-shell-server/issues/47
verifications:
  - id: mcp-v1-sdk-compatibility
    requirement: Fresh installs resolve a compatible MCP SDK and the package imports successfully
    phase: pre-integration
    owner: conflux-acceptance
    trigger: pull-request-validation
    automation: pyproject.toml
    evidence: Metadata regression test, lockfile resolution, package import, and repository quality-suite output
    rerun: uv lock && uv run pytest tests/test_project_metadata.py && uv run python -c "import mcp_shell_server" && uv run make all
    prerequisites: []
    execution_class: repository-local
    completion_role: change-blocking
---

# Pin the MCP v1 SDK

Change Type: implementation

## Problem / Context

`mcp-shell-server` uses the MCP Python SDK v1 low-level `Server` API, including `Server.list_tools()`. The project dependency currently has no upper bound, so fresh installs resolve MCP SDK 2.x and crash during import before serving requests.

## Proposed Solution

Constrain the supported SDK dependency to the compatible v1 release line and refresh the lockfile. Add a regression test that reads project metadata and prevents removal of the v2 exclusion while the server still uses the v1 API. Record the compatibility fix in the changelog.

## Acceptance Criteria

- Fresh dependency resolution selects MCP SDK 1.x rather than 2.x.
- Importing `mcp_shell_server` succeeds with the resolved production dependencies.
- The normal test and quality checks pass.
- Project documentation records the MCP SDK 2.x startup-crash fix.

## Explicit Completion Conditions

- `pyproject.toml` declares an MCP dependency with a `<2` upper bound.
- `uv.lock` resolves `mcp` below 2.0.0.
- An automated regression test fails if the upper bound is removed.
- `uv run make all` succeeds.

## Out of Scope

- Migrating the server implementation to MCP SDK 2.x.
- Publishing a release or merging the pull request.
