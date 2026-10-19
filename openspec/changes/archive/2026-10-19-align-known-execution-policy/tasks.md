## Implementation Tasks

- [x] Add the five known wrapper/runtime names to categorical denial and find interactive primaries to the existing finite execution rule; preserve aliases and preprocessor behavior (verification: unit - tests/test_command_validator.py; verification-id: finite-policy-regression)
- [x] Test exact/pattern/absolute/pipeline rejection before subprocess creation, find-specific validator reasons, benign controls and delegated make/dd/tee validation (verification: integration - tests/test_shell_executor.py and tests/test_trusted_execution_contract.py; verification-id: finite-policy-regression)
- [x] Explicitly reconcile the broad canonical wrapper promise with finite tested rules and trusted delegation in README/SECURITY/changelog, retaining all other concrete policy requirements (verification: unit - tests/test_trusted_execution_contract.py; verification-id: finite-policy-regression)

## Final Validation
Run focused tests and repository full checks, then archive-gate once. Parent owns independent runtime/artifact/release acceptance.

Results (apply, 2026-10-19): focused suite and full `uv run pytest` passed (527 passed); `make lint` and `make typecheck` exited 0; `cflx openspec validate align-known-execution-policy --strict` and `--archive-gate` passed.
