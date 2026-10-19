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

## Current Acceptance Follow-up
- attempt: 1
- [x] [send-email-early-pass-flag-attached-value] (major) Early-pass no-value flags with an attached =value are removed from the residual argv, so the main pass never checks a header-cmd selection that Getopt::Long still makes | evidence: src/mcp_shell_server/command_validator.py _git_send_email_pass (~line 761): only required-arity options with value None are kept in the residual; a no-value flag with an attached value is dropped; Getopt::Long 2.52 FindOption lines 1090-1092: a no-value flag given =value returns (0) under pass_through, and the token is restored to argv for later passes (line 725 onward); git-send-email.perl v2.53.0: help pass declares flag h (line 502); the main pass declares header-cmd=s (line 544), whose unique abbreviation is h; it runs per patch through process_file/pre_process_file/execute_cmd (lines 2170, 1887-1888, 2182) whether or not --dry-run is set; tests/test_command_validator.py SEND_EMAIL_REJECTED has no case for an early-pass flag with an attached value | required_changes: src/mcp_shell_server/command_validator.py — In non-main passes, retain tokens whose resolved option has no-value arity but carries an attached =value, matching Getopt::Long pass_through | verification: tests/test_command_validator.py — Add rejection cases for --h=P, -h=P and +H=P after git send-email, and confirm -h and -h VALUE keep their current outcomes
  finding: {"evidence":["src/mcp_shell_server/command_validator.py _git_send_email_pass (~line 761): only required-arity options with value None are kept in the residual; a no-value flag with an attached value is dropped","Getopt::Long 2.52 FindOption lines 1090-1092: a no-value flag given =value returns (0) under pass_through, and the token is restored to argv for later passes (line 725 onward)","git-send-email.perl v2.53.0: help pass declares flag h (line 502); the main pass declares header-cmd=s (line 544), whose unique abbreviation is h; it runs per patch through process_file/pre_process_file/execute_cmd (lines 2170, 1887-1888, 2182) whether or not --dry-run is set","tests/test_command_validator.py SEND_EMAIL_REJECTED has no case for an early-pass flag with an attached value"],"id":"send-email-early-pass-flag-attached-value","required_changes":[{"description":"In non-main passes, retain tokens whose resolved option has no-value arity but carries an attached =value, matching Getopt::Long pass_through","file":"src/mcp_shell_server/command_validator.py"}],"severity":"major","summary":"Early-pass no-value flags with an attached =value are removed from the residual argv, so the main pass never checks a header-cmd selection that Getopt::Long still makes","verification":[{"description":"Add rejection cases for --h=P, -h=P and +H=P after git send-email, and confirm -h and -h VALUE keep their current outcomes","file":"tests/test_command_validator.py"}]}
  evidence: src/mcp_shell_server/command_validator.py _git_send_email_pass now retains a resolved no-value flag carrying an attached =value in the residual (no value consumed), so later passes reparse it as Getopt::Long pass_through does
  evidence: tests/test_command_validator.py SEND_EMAIL_REJECTED adds --h=P, -h=P, +H=P and --h= PATCH (4 RED on base, now pass); allowed list adds -h VALUE beside -h, and the existing -h VALUE --sendmail-cmd rejection is unchanged
  evidence: uv run pytest tests/test_command_validator.py tests/test_shell_executor.py -q 1312 passed 4 skipped; uv run pytest -q 1511 passed 4 skipped; make lint typecheck exit 0; git diff --check clean; archive gate passed
