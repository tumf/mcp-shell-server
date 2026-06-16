---
change_type: implementation
priority: high
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2 issue 7
  - src/mcp_shell_server/server.py
  - src/mcp_shell_server/process_manager.py
  - tests/test_shell_executor.py
---

# Bound command execution time and output

**Change Type**: implementation

## Problem / Context

When clients omit `timeout`, command execution can run indefinitely. Process output is captured without a server-side byte cap, so high-output commands can consume unbounded memory. `server.py` also computes an outer timeout but passes `None` to the executor, producing inconsistent timeout ownership.

## Proposed Solution

Introduce server-side default timeout, maximum timeout, and stdout/stderr output byte caps. Compute an effective timeout in `server.py`, pass it through `ShellExecutor` to `ProcessManager`, and enforce output limits close to process execution. Commands that exceed limits should be terminated or truncated deterministically with an explicit result.

## Acceptance Criteria

- Commands have an effective timeout even when the client omits `timeout`.
- Client-supplied timeout is clamped or rejected when above a configured maximum.
- Effective timeout reaches process execution.
- stdout/stderr output is capped to a configured byte limit.
- Long-running and excessive-output commands are cleaned up without hanging the server or buffering unbounded memory.

## Explicit Completion Conditions

- `src/mcp_shell_server/server.py` computes and passes an effective timeout into the executor.
- `src/mcp_shell_server/process_manager.py` enforces timeout and output caps for direct and pipeline execution.
- Regression tests cover omitted timeout, over-limit timeout, timeout cleanup, output cap, and process cleanup.

## Out of Scope

- Throughput benchmarking beyond correctness of timeout/output bound enforcement.
