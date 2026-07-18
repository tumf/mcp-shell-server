## Implementation Tasks

- [ ] Replace Git configuration-key denylisting with categorical rejection of separated and attached `git -c` forms in `src/mcp_shell_server/command_validator.py`; preserve existing external-program option and `ext::` transport checks. (verification: unit - `tests/test_command_validator.py` rejects all command-scoped configuration while allowing `git status`)
- [ ] Add validator regressions for `core.fsmonitor`, `diff.external`, benign-looking `user.name`, mixed case where applicable, missing values, and both `-c` token forms. (verification: unit - `pytest tests/test_command_validator.py` exercises each case through `CommandValidator.validate_command`)
- [ ] Add an executor-level regression using an isolated temporary Git repository that submits at least one advisory payload and asserts rejection plus absence of its marker file. (verification: integration - `pytest tests/test_shell_executor.py` must fail if a subprocess executes the injected command)
- [ ] Update `SECURITY.md` to state that all Git command-scoped configuration overrides are rejected and remove wording that implies a maintainable executable-key denylist. (verification: manual - compare `SECURITY.md` with `src/mcp_shell_server/command_validator.py` because this is operator-facing policy text)
- [ ] Reconcile the implementation with any pre-existing uncommitted argument-hardening work without weakening its unrelated protections. (verification: unit - `pytest tests/test_command_validator.py` preserves dangerous-command, Git transport, and ordinary-command coverage)
- [ ] Prepare version and advisory metadata for a patched release greater than `1.1.1`, keeping `<=1.1.1` in the vulnerable range and naming the concrete patched version. (verification: manual - inspect `src/mcp_shell_server/version.py` and private advisory `GHSA-56qh-7rgp-wfgr` before publication; publication requires repository-owner control)
- [ ] Run all repository-provided quality commands and resolve failures attributable to this change. (verification: integration - `pytest`, `ruff check .`, `black --check .`, and `mypy src` exit successfully)

## Future Work

- Repository owner publishes the patched package release.
- Repository owner updates and publishes `GHSA-56qh-7rgp-wfgr` only after confirming the patched artifact is available.

## Final Validation

Archive validation is the authoritative final OpenSpec gate.
Expected archive gate: `cflx openspec validate reject-git-config-overrides --archive-gate`
