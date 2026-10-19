## Implementation Tasks

- [ ] Add the fixed send-email grammar and prelaunch dispatcher without changing other Git/family rules (verification: unit - tests/test_command_validator.py; verification-id: send-email-selector-regression)
- [ ] Add RED/GREEN rejection and permitted-neighbor tests for every design inventory class, plus executor/pipeline no-process/no-marker tests (verification: integration - tests/test_shell_executor.py; verification-id: send-email-selector-regression)
- [ ] Synchronize README/SECURITY/changelog with the finite selector rule and conservative path/prefix choices, preserve existing canonical rules at archive (verification: unit - tests/test_command_validator.py; verification-id: send-email-selector-regression)

## Final Validation

Run the declared focus, full pytest, lint/typecheck, diff check and archive gate. Preserve active and archived automation paths.

## Future Work

Parent performs real isolated Git artifact acceptance, final independent review and coordinated release/disclosure. No public writes belong to this implementation.
