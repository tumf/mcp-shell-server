## Implementation Tasks

- [x] Replace wholesale environment inheritance in `src/mcp_shell_server/process_manager.py` with a minimal child environment builder. Completion condition: process creation no longer uses `{**os.environ, **(envs or {})}`. (verification: unit - `tests/test_process_manager.py` asserts child env excludes unrelated parent variables; run `pytest tests/test_process_manager.py`.)

- [x] Add explicit environment allowlist handling if child env customization is retained. Completion condition: only documented allowlisted keys can be inherited or injected into child env. (verification: unit - `tests/test_process_manager.py` covers allowed and disallowed env keys; run `pytest tests/test_process_manager.py`.)

- [x] Add integration coverage for secret non-exposure. Completion condition: with parent `SECRET_TOKEN` set, a child command cannot observe it by default. (verification: integration - `tests/test_shell_executor.py` or `tests/test_process_manager.py` executes/mocks an env-printing command and asserts `SECRET_TOKEN` is absent; run the updated test file.)

- [x] Document child environment isolation. Completion condition: `README.md` describes default minimal env and allowlist behavior. (verification: manual - inspect `git diff -- README.md`.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate isolate-child-environment --archive-gate`.
