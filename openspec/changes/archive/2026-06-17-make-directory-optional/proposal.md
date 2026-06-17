---
change_type: implementation
priority: medium
dependencies: []
references:
  - https://github.com/tumf/mcp-shell-server/issues/11
  - src/mcp_shell_server/server.py
  - src/mcp_shell_server/directory_manager.py
  - src/mcp_shell_server/io_redirection_handler.py
  - tests/test_server.py
  - tests/test_server_validation.py
  - openspec/specs/shell-execution-security/spec.md
---

# Make shell execution directory optional

**Change Type**: implementation

## Problem/Context

Issue #11 proposes making the `directory` argument optional so clients and LLMs do not need to provide long absolute paths for every command invocation. The current implementation is inconsistent: the MCP tool schema requires `directory`, while `ExecuteToolHandler.run_tool()` has a hidden `/tmp` fallback before rejecting empty values. Existing shell execution and redirection security still depend on a validated working directory as the containment boundary.

## Proposed Solution

Make `directory` optional at the MCP tool boundary. When omitted, resolve the effective working directory to the MCP server process current working directory. When provided as a relative path, resolve it relative to the server process current working directory. When provided as an absolute path, preserve the existing behavior. Always validate the resolved effective directory before subprocess creation or redirection handling.

The effective working directory becomes the single containment boundary for redirection paths and audit metadata. Empty or whitespace-only `directory` values remain invalid and are not treated as omission.

## Acceptance Criteria

- The `shell_execute` input schema requires only `command`; `directory` remains available but optional.
- Calling `shell_execute` without `directory` executes in the server process current working directory after validation.
- Calling `shell_execute` with a relative `directory` executes in that path resolved from the server process current working directory after validation.
- Calling `shell_execute` with an absolute `directory` keeps the existing validated behavior.
- Empty or whitespace-only `directory` values are rejected before command execution.
- Redirection containment continues to use the validated effective working directory, including when `directory` is omitted or relative.
- README usage documentation states that the default and relative path base is the server process CWD, not the MCP client CWD.

## Explicit Completion Conditions

- `src/mcp_shell_server/server.py` no longer marks `directory` as required in the tool schema and no longer uses a hidden `/tmp` fallback.
- Directory resolution is centralized or otherwise consistently applied before calling `ShellExecutor.execute()` so downstream execution and redirection receive a non-empty effective directory.
- Existing absolute-directory behavior remains covered by tests.
- New tests cover omitted, relative, empty, and redirection containment behavior.
- Documentation updates describe omitted and relative `directory` semantics clearly enough for MCP clients and LLMs.
- `cflx openspec validate make-directory-optional --strict` passes.

## Out of Scope

- Changing command allowlist or `ALLOW_PATTERNS` behavior.
- Changing redirection containment rules other than using the effective directory as the existing boundary.
- Interpreting omitted `directory` as the MCP client process CWD.
- Adding sandboxing or project-root policy beyond the existing validated working directory model.
