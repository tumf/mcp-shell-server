---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2 issue 3
  - src/mcp_shell_server/shell_executor.py
  - src/mcp_shell_server/process_manager.py
  - tests/test_shell_executor_pipeline.py
---

# Harden pipeline execution

**Change Type**: implementation

## Problem / Context

Pipeline execution currently passes command segment names to shell execution and drops segment arguments. With permissive `ALLOW_PATTERNS`, a metacharacter-bearing segment can be interpreted by the shell and execute unintended commands.

## Proposed Solution

Represent pipelines as `List[List[str]]`, validate each full argv segment, and execute each segment without shell interpretation. Preserve pipeline arguments, reject shell metacharacters, and ensure injection payloads are rejected or treated as invalid executable names rather than shell syntax.

## Acceptance Criteria

- Pipeline execution no longer passes user-controlled segment strings to `create_subprocess_shell()`.
- Pipeline argv arguments are preserved for every segment.
- `echo hello | grep h` continues to work.
- `ls; touch /tmp/pwned | cat` is rejected or fails safely without creating `/tmp/pwned`.
- Pipeline validation errors occur before subprocess creation when shell operators/metacharacters are detected.

## Explicit Completion Conditions

- `src/mcp_shell_server/shell_executor.py` no longer calls `execute_pipeline([command[0] for command in parsed_commands], ...)`.
- `src/mcp_shell_server/process_manager.py` accepts and executes pipeline argv arrays without shell string interpretation.
- Regression tests cover normal pipeline success, argument preservation, and metacharacter injection rejection.

## Out of Scope

- Replacing the current sequential pipeline model with fully concurrent OS pipe wiring unless needed for correctness.
