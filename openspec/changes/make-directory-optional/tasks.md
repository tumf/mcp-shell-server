## Implementation Tasks

- [x] Update MCP tool schema and request handling so `directory` is optional and `command` remains required. Completion condition: `shell_execute` input schema has `required == ["command"]`, `directory` is still documented as a string property, and `ExecuteToolHandler.run_tool()` accepts omitted `directory` without raising a required-directory error. (verification: unit - update/add tests in `tests/test_server.py` and `tests/test_server_validation.py`)

- [x] Resolve an effective working directory before execution for omitted, relative, and absolute inputs. Completion condition: omitted `directory` resolves to the server process CWD, relative `directory` resolves from the server process CWD, absolute `directory` is accepted unchanged except for existing validation/realpath normalization, and empty or whitespace-only strings are rejected. (verification: unit - add assertions in `tests/test_server_validation.py` or `tests/test_directory_manager.py` using `tmp_path` and `monkeypatch.chdir()`)

- [x] Ensure subprocess execution and redirection receive the validated effective directory. Completion condition: `ShellExecutor.execute()` and redirection handling are invoked with a concrete effective directory for omitted/relative inputs, not `None` and not the old hidden `/tmp` fallback. (verification: integration - update `tests/test_server_validation.py` mocked executor assertions and add/adjust `tests/test_shell_executor_redirections.py` cases)

- [x] Preserve redirection containment under the effective directory. Completion condition: relative redirection paths inside the effective directory are allowed and `../` or symlink escapes outside that effective directory remain rejected when `directory` is omitted or relative. (verification: integration - add `tests/test_shell_executor_redirections.py` cases using `tmp_path` real files/symlinks)

- [x] Update README usage documentation for optional `directory`. Completion condition: `README.md` states omitted `directory` uses the MCP server process CWD, relative `directory` is resolved from that same CWD, and this is not the MCP client CWD. (verification: manual - `README.md`; run `rg "server process.*CWD|MCP client CWD|relative.*directory" README.md`)

- [x] Run the project verification suite for this change. Completion condition: relevant unit/integration tests pass and default quality checks configured by the repository pass. (verification: manual - run `pytest tests/test_server.py tests/test_server_validation.py tests/test_shell_executor_redirections.py` plus discovered lint/typecheck commands)

## Future Work

- Consider a separate proposal for a configurable project-root or sandbox root if users need stronger boundaries than the server process CWD.

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate.
Expected archive gate: `cflx openspec validate make-directory-optional --archive-gate`
