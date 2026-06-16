---
change_type: implementation
priority: medium
dependencies: []
references:
  - GHSA-6rrx-pj43-m9p2 issue 6
  - src/mcp_shell_server/server.py
  - src/mcp_shell_server/shell_executor.py
  - tests/test_server_validation.py
---

# Add structured command audit logs

**Change Type**: implementation

## Problem / Context

The server currently logs startup, shutdown, and errors, but successful and rejected command invocations do not produce structured audit records. If command execution is abused, there is no reliable forensic trail for command, directory, redirection, timeout, output size, exit status, or rejection reason.

## Proposed Solution

Emit structured audit logs for all command invocation outcomes: success, validation rejection, timeout, output cap, and process error. Audit records must include useful metadata while redacting secret-like values and avoiding raw stdout/stderr content.

## Acceptance Criteria

- Successful command execution emits a structured audit record.
- Validation rejection emits a structured audit record before subprocess creation.
- Timeout, output cap, and process errors emit structured audit records.
- Audit records include timestamp, command name, redacted argv, resolved directory, redirection metadata, timeout, output byte counts, return code, duration, and result type where applicable.
- Audit records do not contain raw stdout/stderr or unredacted secret-like values.

## Explicit Completion Conditions

- Audit logging is wired into the command invocation path in `server.py` and/or `shell_executor.py`.
- Tests using `caplog` or logger mocks verify fields and redaction.
- Documentation states what audit data is logged and what is redacted.

## Out of Scope

- External SIEM integration.
- Append-only tamper-resistant log storage.
