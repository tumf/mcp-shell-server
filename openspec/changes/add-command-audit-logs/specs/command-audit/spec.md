## ADDED Requirements

### Requirement: Command invocations MUST emit structured audit records

The server MUST emit structured audit records for command invocation outcomes without exposing raw command output or unredacted secrets.

#### Scenario: Successful invocation is audited

**Given**: a command passes validation and completes successfully
**When**: the invocation finishes
**Then**: an audit record includes timestamp, command name, redacted argv, resolved directory, output byte counts, return code, duration, and success result

#### Scenario: Rejected invocation is audited

**Given**: a command fails validation before subprocess creation
**When**: the server rejects the command
**Then**: an audit record includes rejection result and redacted metadata sufficient for incident review

#### Scenario: Timeout or output cap is audited

**Given**: a command times out or exceeds output limits
**When**: the server terminates or truncates the command
**Then**: an audit record includes the timeout or output-cap result and relevant limit metadata

#### Scenario: Raw secrets and output are redacted

**Given**: command metadata includes secret-like names or command output includes sensitive text
**When**: the server writes an audit record
**Then**: the audit record excludes raw stdout/stderr and replaces secret-like metadata with redacted placeholders
