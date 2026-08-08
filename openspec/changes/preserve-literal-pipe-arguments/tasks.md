## Implementation Tasks

- [ ] Add regression tests proving embedded, leading, and trailing `|` characters remain literal argv data and cannot create an unintended pipeline stage. (verification-id: literal-pipe-argument-security) (verification: unit - `uv run pytest tests/test_shell_executor_pipeline.py` fails on the vulnerable preprocessor behavior and passes after the fix)
- [ ] Add regression coverage proving reported command-specific policy payloads are validated in their original argv form and rejected before subprocess creation or file side effects. (verification-id: literal-pipe-argument-security) (verification: integration - `uv run pytest tests/test_command_validator.py tests/test_shell_executor_pipeline.py` asserts rejection and mocked process/file boundaries remain untouched)
- [ ] Change `CommandPreProcessor.preprocess_command()` so only a discrete `|` argv token represents pipeline syntax, without changing explicit pipeline execution. (verification-id: literal-pipe-argument-security) (verification: unit - `uv run pytest tests/test_shell_executor_pipeline.py` covers preserved literals plus explicit pipeline compatibility)
- [ ] Update `CHANGELOG.md` with the affected range and upgrade instruction for the next patched release, without publishing it. (verification-id: literal-pipe-argument-security) (verification: integration - `uv run python -c "from pathlib import Path; s=Path('CHANGELOG.md').read_text(); assert 'GHSA-q8pm-q3r2-q7cg' in s and 'GHSA-7wg7-jj87-qp4c' in s and '1.1.7' in s"`)

## Future Work

- Repository owner authorizes and performs the patched package and GitHub Release publication.
- Repository owner selects the primary Advisory, reconciles severity and duplicate handling, preserves reporter credit, and authorizes publication after the patched artifact is verified.

## Final Validation

Expected archive gate: `cflx openspec validate preserve-literal-pipe-arguments --archive-gate`
