## Implementation Tasks

- [x] Implement fixed Git subcommand-specific grammar and tables for grep pager/rebase exec/filter-branch/bisect run, contextualizing only the existing --exec scan for exact rebase while retaining post-subcommand --exec family rejection on other Git subcommands; all unrelated broad checks remain full-argv (verification: unit - tests/test_command_validator.py; verification-id: git-exec-grammar-regression)
- [x] Add all mandatory rejection/allowed/arity cases and prelaunch executor/pipeline boundary tests with no side effects (verification: integration - tests/test_shell_executor.py and tests/test_command_validator.py; verification-id: git-exec-grammar-regression)
- [x] Synchronize finite docs/changelog and canonical Git requirement without replacing concurrently promoted requirements (verification: unit - tests/test_command_validator.py; verification-id: git-exec-grammar-regression)

## Final Validation
Run declared focus, full suite, lint/typecheck, diff check, archive gate.

## Future Work
Parent independent integration/real Git artifact acceptance, release and coordinated disclosure.
