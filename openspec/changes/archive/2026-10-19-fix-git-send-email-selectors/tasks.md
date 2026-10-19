## Implementation Tasks

- [x] Add the fixed send-email grammar and prelaunch dispatcher without changing other Git/family rules (verification: unit - tests/test_command_validator.py; verification-id: send-email-selector-regression)
- [x] Add RED/GREEN rejection and permitted-neighbor tests for every design inventory class, plus executor/pipeline no-process/no-marker tests (verification: integration - tests/test_shell_executor.py; verification-id: send-email-selector-regression)
- [x] Synchronize README/SECURITY/changelog with the finite selector rule and conservative path/prefix choices, preserve existing canonical rules at archive (verification: unit - tests/test_command_validator.py; verification-id: send-email-selector-regression)

## Final Validation

Run the declared focus, full pytest, lint/typecheck, diff check and archive gate. Preserve active and archived automation paths.

Results (2026-10-19, apply):
- RED on base: 83 validator and 20 executor send-email rejection cases failed before the code change, including the four basic smtp-server/sendmail-cmd forms.
- Focus gate `uv run pytest tests/test_command_validator.py tests/test_shell_executor.py -q`: 1307 passed, 4 skipped.
- `uv run pytest -q`: 1506 passed, 4 skipped.
- `uv run make lint typecheck`: black/isort/ruff clean, mypy exit 0.
- `git diff --check`: clean. `cflx openspec validate fix-git-send-email-selectors --archive-gate`: passed.

## Future Work

Parent performs real isolated Git artifact acceptance, final independent review and coordinated release/disclosure. No public writes belong to this implementation.

