## Implementation Tasks

- [ ] Replace shell-string subprocess creation with argv-based execution in `src/mcp_shell_server/process_manager.py` for normal single-command and pipeline paths. Completion condition: normal execution code calls `asyncio.create_subprocess_exec()` with argv lists and no longer passes user-controlled command strings to `asyncio.create_subprocess_shell()`. (verification: unit - `tests/test_process_manager.py` asserts/mocks argv lists passed to subprocess creation; run `pytest tests/test_process_manager.py`.)

- [ ] Preserve and validate full pipeline argv segments in `src/mcp_shell_server/shell_executor.py`. Completion condition: `_execute_pipeline()` passes `List[List[str]]` including arguments into the process manager and no longer uses `[command[0] for command in parsed_commands]`. (verification: integration - `tests/test_shell_executor_pipeline.py` covers `['echo', 'hello', '|', 'grep', 'h']` success and `['ls; touch /tmp/pwned', '|', 'cat']` rejection without side effects; run `pytest tests/test_shell_executor_pipeline.py`.)

- [ ] Harden command and argument validation in `src/mcp_shell_server/command_validator.py`. Completion condition: `ALLOW_PATTERNS` uses fullmatch semantics, unsafe pattern/input forms with whitespace or shell metacharacters are rejected, and default dangerous exec-capable vectors are rejected. (verification: unit - `tests/test_command_validator.py` covers `ALLOW_PATTERNS=ls` rejecting `lsof`, metacharacter strings, `find -exec`, shell/interpreter commands, `awk system()`, `tar --checkpoint-action=exec`, `xargs`, and `env`; run `pytest tests/test_command_validator.py`.)

- [ ] Enforce redirection path containment in `src/mcp_shell_server/io_redirection_handler.py` before opening files. Completion condition: redirection targets are relative paths whose resolved realpath remains under the validated `directory`, and absolute paths, `..`, and symlink escapes are rejected before read/truncate/open. (verification: unit - `tests/test_shell_executor_redirections.py` covers absolute input path rejection, parent traversal rejection, symlink escape rejection, and valid in-directory redirection success; run `pytest tests/test_shell_executor_redirections.py`.)

- [ ] Fix runtime file-handle detection after containment is enforced. Completion condition: stdout file handles are recognized using runtime-valid checks such as `io.IOBase` or write/close capabilities rather than `typing.IO`, without reintroducing path escape writes. (verification: integration - `tests/test_shell_executor_redirections.py` proves `>` and `>>` write only inside the working directory and return no captured stdout for redirected output; run `pytest tests/test_shell_executor_redirections.py`.)

- [ ] Isolate child process environments in `src/mcp_shell_server/process_manager.py`. Completion condition: child processes receive a minimal environment plus documented allowlisted variables and do not inherit `os.environ` wholesale. (verification: integration - `tests/test_process_manager.py` or `tests/test_shell_executor.py` sets parent `SECRET_TOKEN` and proves an allowed child command cannot observe it unless explicitly allowlisted; run the updated test file with `pytest`.)

- [ ] Add server-side execution timeout bounds in `src/mcp_shell_server/server.py`, `shell_executor.py`, and `process_manager.py`. Completion condition: timeout omitted by the client still applies a configured safe default, client timeout is clamped to a configured maximum, and the effective timeout reaches process execution. (verification: integration - `tests/test_server_validation.py` and `tests/test_shell_executor.py` cover omitted timeout default behavior and over-limit timeout clamp/rejection; run `pytest tests/test_server_validation.py tests/test_shell_executor.py`.)

- [ ] Add output byte cap enforcement for stdout and stderr. Completion condition: commands producing more than the configured output limit are terminated or truncated deterministically without unbounded `communicate()` buffering. (verification: integration - `tests/test_process_manager.py` or `tests/test_shell_executor.py` uses finite high-output or mocked stream behavior to prove explicit capped/truncated result and process cleanup; run the updated test file with `pytest`.)

- [ ] Add structured audit logging for command invocations. Completion condition: success, rejection, timeout, output-cap, and process-error outcomes emit structured logs with timestamp, command name, redacted argv, resolved directory, redirection metadata, timeout, output byte counts, return code, duration, and result type. (verification: unit - `tests/test_server_validation.py` or a new `tests/test_audit_logging.py` uses `caplog` to assert expected audit fields and redaction; run the updated/new test file with `pytest`.)

- [ ] Update project documentation for the hardened security model. Completion condition: `README.md` no longer contains claims contradicted by implementation, documents default timeout/output/env/redirection behavior, warns that command-name allowlists are not complete sandboxes, and `SECURITY.md` replaces placeholder content with project-specific reporting/support guidance. (verification: manual - inspect `git diff -- README.md SECURITY.md CHANGELOG.md` for consistency with implemented behavior because documentation clarity is reviewer-evaluated.)

- [ ] Run repository verification commands and address failures. Completion condition: configured test, lint, and typecheck commands complete successfully, or any unavailable command is documented with the reason and substitute verification. (verification: manual - run `pytest`, `ruff check .`, and `mypy src` or the repository's configured equivalents.)

## Future Work

Consider a richer per-command argument policy format for users who need to safely allow a constrained subset of otherwise exec-capable tools.

Consider OS-level sandboxing as a separate defense-in-depth proposal.

Coordinate any public GHSA/CVE publication or advisory update outside this implementation proposal.

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate fix-shell-execution-boundary --archive-gate`.
