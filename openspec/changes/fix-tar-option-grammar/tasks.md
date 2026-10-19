## Implementation Tasks

- [ ] Implement finite tar option name/arity parsing, including exact-over-prefix resolution, value consumption, old-style words and seven external-program families, preserving aliases and existing error text (verification: unit - tests/test_command_validator.py; verification-id: tar-policy-regression)
- [ ] Add a complete rejection/benign-neighbor grammar matrix plus full ShellExecutor pre-launch marker/archive absence, normal archive success and pipeline checks (verification: integration - tests/test_shell_executor.py and tests/test_command_validator.py; verification-id: tar-policy-regression)
- [ ] Update bounded security documentation and changelog and promote the tar command-policy delta without replacing newer git/sort contracts (verification: unit - tests/test_command_validator.py; verification-id: tar-policy-regression)

## Final Validation
Run declared focused tests,  repository checks and cflx openspec validate fix-tar-option-grammar --archive-gate once.

## Future Work
Parent owns isolated GNU tar runtime replay, independent exact release-diff review, artifact and public-PyPI acceptance, release and coordinated disclosure/credit.
