## Implementation Tasks

- [ ] Extend default argument policy for git alias exec bypass in `src/mcp_shell_server/command_validator.py`; completion condition: `git -c alias.<name>=!... <name>` is rejected before subprocess creation. (verification: unit - add `tests/test_command_validator.py` coverage that fails on current implementation and passes after the policy rejects the git alias PoC.)

- [ ] Add integration coverage proving the git alias PoC has no side effect; completion condition: executing `ShellExecutor().execute(['git', '-c', 'alias.pwn=!sh -c "touch <marker>"', 'pwn'], ...)` returns a rejection/error and does not create `<marker>`. (verification: integration - `uv run pytest tests/test_shell_executor.py -k git` or a new security regression test file under `tests/`).

- [ ] Keep existing advisory regression coverage passing; completion condition: existing `find -exec`, interpreter, `awk system()`, `tar --checkpoint-action=exec`, `env`, and `xargs` rejection tests still pass (xargs is already covered by `DANGEROUS_COMMANDS` and requires no code change). (verification: unit - `uv run pytest tests/test_command_validator.py`.)

- [ ] Update security documentation if policy semantics change; completion condition: `README.md` and/or `SECURITY.md` describe that allowlisting exec-capable binaries is constrained by default argument hardening and name at least the git alias exec case. (verification: manual - inspect `README.md` / `SECURITY.md` diff for the policy note.)

## Future Work

- Design a full user-configurable argv policy language if default hardening proves too restrictive or incomplete.

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate.
Expected archive gate: `cflx openspec validate fix-whitelist-bypass --archive-gate`.
