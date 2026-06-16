## Implementation Tasks

- [x] Add structured audit logging hooks around command invocation outcomes in `src/mcp_shell_server/server.py` and/or `src/mcp_shell_server/shell_executor.py`. Completion condition: success, rejection, timeout, output-cap, and process-error paths each emit an audit event. (verification: unit - `tests/test_server_validation.py` or `tests/test_audit_logging.py` uses `caplog` to assert one event per outcome; run the updated/new test file.)

- [x] Implement audit redaction for secret-like argv/env values. Completion condition: keys or values matching secret-like names are replaced with redacted placeholders. (verification: unit - `tests/test_audit_logging.py` or `tests/test_server_validation.py` asserts `SECRET_TOKEN`-like values do not appear in log text; run the updated/new test file.)

- [x] Avoid logging raw command output. Completion condition: audit records include output byte counts but not raw stdout/stderr bodies. (verification: unit - `tests/test_audit_logging.py` or `tests/test_server_validation.py` asserts known stdout text is not present while byte counts are present.)

- [x] Document audit behavior. Completion condition: `README.md` or `SECURITY.md` describes audit fields and redaction. (verification: manual - inspect `git diff -- README.md SECURITY.md`.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate add-command-audit-logs --archive-gate`.
