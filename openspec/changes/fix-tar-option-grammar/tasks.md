## Implementation Tasks

- [x] Implement finite tar option name/arity parsing, including exact-over-prefix resolution, value consumption, old-style words and seven external-program families, preserving aliases and existing error text (verification: unit - tests/test_command_validator.py; verification-id: tar-policy-regression)
- [x] Add a complete rejection/benign-neighbor grammar matrix plus full ShellExecutor pre-launch marker/archive absence, normal archive success and pipeline checks (verification: integration - tests/test_shell_executor.py and tests/test_command_validator.py; verification-id: tar-policy-regression)
- [x] Update bounded security documentation and changelog and keep the tar command-policy delta ADDED-only so archive promotion appends it without replacing newer git/sort contracts (verification: unit - tests/test_command_validator.py; verification-id: tar-policy-regression)

## Final Validation
Run declared focused tests,  repository checks and cflx openspec validate fix-tar-option-grammar --archive-gate once.

## Notes
- evidence: `uv run pytest tests/test_command_validator.py tests/test_shell_executor.py` passed (928 passed, 4 skipped: GNU tar smoke cases skip because GNU tar is not installed locally; bsdtar 3.7.4 smoke cases ran and proved each BSD-only payload launches the helper directly).
- evidence: full `uv run pytest` passed (1127 passed, 4 skipped); `make lint` and `make typecheck` passed.
- The canonical `openspec/specs/command-policy/spec.md` is not edited during apply: a scratch-worktree archive dry run showed `cflx openspec archive` appends the ADDED requirement itself, so pre-promoting would duplicate it. The same dry run confirmed the existing git/sort requirement text is kept unchanged.
- `tests/test_trusted_execution_contract.py` requires the literal `--checkpoint-action=exec` in README and SECURITY; the docs keep that example while stating that every checkpoint action is denied.

## Future Work
Parent owns isolated GNU tar runtime replay, independent exact release-diff review, artifact and public-PyPI acceptance, release and coordinated disclosure/credit.
