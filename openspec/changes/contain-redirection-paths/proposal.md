---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2 issue 2
  - src/mcp_shell_server/io_redirection_handler.py
  - src/mcp_shell_server/shell_executor.py
  - tests/test_shell_executor_redirections.py
---

# Contain redirection paths under working directory

**Change Type**: implementation

## Problem / Context

Input and output redirection targets are currently joined with the requested working directory without containment checks. Absolute paths and `..` traversal can escape the working directory, allowing arbitrary file read or truncation where process permissions allow. The current runtime file-handle checks are also fragile and must not be fixed before containment is enforced.

## Proposed Solution

Resolve every redirection target relative to the validated working directory, reject absolute paths and parent traversal, and require the resolved real path to stay within the working directory via `os.path.commonpath`. Apply this check before opening files. After containment is in place, fix runtime file-handle detection for redirected output.

## Acceptance Criteria

- `< /absolute/path` is rejected before opening the file.
- `< ../path` and `> ../path` are rejected before opening or truncating files.
- Symlink escapes outside the working directory are rejected.
- Valid in-directory input and output redirections continue to work.
- Output redirection file handles are recognized with runtime-valid checks and cannot write outside containment.

## Explicit Completion Conditions

- `src/mcp_shell_server/io_redirection_handler.py` performs realpath/commonpath containment checks before file open.
- `src/mcp_shell_server/shell_executor.py` handles redirected output file handles without `typing.IO` runtime misuse.
- Regression tests cover absolute path, traversal, symlink escape, valid in-directory redirection, and redirected write behavior.

## Out of Scope

- General filesystem sandboxing beyond redirection target containment.
