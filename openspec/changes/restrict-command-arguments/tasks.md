## Implementation Tasks

- [ ] Add default dangerous-command and dangerous-argument rejection rules in `src/mcp_shell_server/command_validator.py`. Completion condition: validation rejects the GHSA bypass vectors before any subprocess is created. (verification: unit - `tests/test_command_validator.py` covers `find -exec`, shell/interpreter names, `awk system()`, `tar --checkpoint-action=exec`, `xargs`, and `env`; run `pytest tests/test_command_validator.py`.)

- [ ] Wire enhanced argument validation into `src/mcp_shell_server/shell_executor.py` for single-command and pipeline segments. Completion condition: both execution paths call the same full-argv policy before process creation. (verification: integration - `tests/test_shell_executor.py` or `tests/test_shell_executor_pipeline.py` proves rejected commands return errors and process-manager mocks are not called; run the updated tests.)

- [ ] Document that `ALLOW_COMMANDS` is not a sandbox for exec-capable binaries. Completion condition: `README.md` security section warns against allowing exec-capable tools without explicit policy. (verification: manual - inspect `git diff -- README.md`.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate restrict-command-arguments --archive-gate`.
