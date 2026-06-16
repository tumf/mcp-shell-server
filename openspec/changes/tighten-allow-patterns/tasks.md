## Implementation Tasks

- [x] Replace prefix matching with fullmatch in `src/mcp_shell_server/command_validator.py`. Completion condition: `ALLOW_PATTERNS=ls` permits `ls` and rejects `lsof`. (verification: unit - `tests/test_command_validator.py` covers exact pattern success and prefix-overmatch rejection; run `pytest tests/test_command_validator.py`.)

- [x] Reject unsafe command names or patterns containing whitespace or shell metacharacters in pattern validation. Completion condition: metacharacter-bearing command names cannot be admitted through `ALLOW_PATTERNS`. (verification: unit - `tests/test_command_validator.py` covers `ls; touch /tmp/pwned` and whitespace-bearing strings; run `pytest tests/test_command_validator.py`.)

- [x] Document `ALLOW_PATTERNS` fullmatch semantics in `README.md`. Completion condition: docs state patterns apply to command names and are not shell command patterns. (verification: manual - inspect `git diff -- README.md`.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate tighten-allow-patterns --archive-gate`.
