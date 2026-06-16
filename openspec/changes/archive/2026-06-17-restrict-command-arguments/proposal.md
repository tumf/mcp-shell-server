---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2 issue 1
  - src/mcp_shell_server/command_validator.py
  - src/mcp_shell_server/shell_executor.py
  - tests/test_command_validator.py
---

# Restrict command arguments to prevent allowlist bypass

**Change Type**: implementation

## Problem / Context

The command allowlist currently validates only `argv[0]`. If an allowed binary has exec-capable arguments, such as `find -exec`, `awk system()`, `tar --checkpoint-action=exec`, `xargs`, interpreters, shells, or `env`, the allowlist can be bypassed to run non-allowed programs or expose execution context.

## Proposed Solution

Add default command/argument policy checks that reject known exec-capable command vectors before subprocess creation. Keep `ALLOW_COMMANDS` / `ALLOWED_COMMANDS` as command-name allowlists for compatibility, but document and enforce that command-name allowance alone does not make an exec-capable binary safe.

## Acceptance Criteria

- `find -exec` is rejected even when `find` is in `ALLOW_COMMANDS`.
- Shells and interpreters are rejected under default policy.
- `awk` programs containing `system()` are rejected under default policy.
- `tar --checkpoint-action=exec` and `xargs` are rejected under default policy.
- `env` is rejected under default policy unless a future explicit policy says otherwise.
- Rejections happen before subprocess creation.

## Explicit Completion Conditions

- `src/mcp_shell_server/command_validator.py` validates dangerous argument patterns, not only command name.
- `src/mcp_shell_server/shell_executor.py` invokes the enhanced validation before execution.
- Regression tests in `tests/test_command_validator.py` or `tests/test_shell_executor.py` cover all advisory bypass examples.

## Out of Scope

- A full per-command policy language for safe subsets of exec-capable tools.
- OS-level sandboxing.
