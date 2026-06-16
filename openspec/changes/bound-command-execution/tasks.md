## Implementation Tasks

- [ ] Add configurable default and maximum timeout handling in `src/mcp_shell_server/server.py`. Completion condition: omitted timeout receives a safe default and excessive client timeout is clamped or rejected according to documented behavior. (verification: integration - `tests/test_server_validation.py` covers omitted timeout and over-limit timeout behavior; run `pytest tests/test_server_validation.py`.)

- [ ] Pass effective timeout through `src/mcp_shell_server/shell_executor.py` into `src/mcp_shell_server/process_manager.py`. Completion condition: executor calls process execution with the effective timeout rather than `None`. (verification: unit - `tests/test_shell_executor.py` mocks `execute_with_timeout` and asserts the effective timeout value; run `pytest tests/test_shell_executor.py`.)

- [ ] Enforce timeout cleanup in `src/mcp_shell_server/process_manager.py`. Completion condition: long-running processes are terminated and reaped on timeout. (verification: unit/integration - `tests/test_process_manager.py` covers timeout kill/cleanup behavior; run `pytest tests/test_process_manager.py`.)

- [ ] Add stdout/stderr output byte cap enforcement. Completion condition: excessive output is truncated or causes deterministic termination without unbounded buffering. (verification: integration - `tests/test_process_manager.py` or `tests/test_shell_executor.py` uses mocked or finite high-output behavior and asserts explicit capped/truncated result; run the updated test file.)

- [ ] Document timeout and output cap configuration. Completion condition: `README.md` describes defaults, maximums, and output cap behavior. (verification: manual - inspect `git diff -- README.md`.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate bound-command-execution --archive-gate`.
