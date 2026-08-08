## Implementation Tasks

- [ ] Add regression tests proving embedded, leading, and trailing `|` characters remain literal argv data and cannot create an unintended pipeline stage. (verification-id: literal-pipe-argument-security) (verification: unit - `uv run pytest tests/test_shell_executor_pipeline.py` fails on the vulnerable preprocessor behavior and passes after the fix)
- [ ] Update `tests/test_shell_executor.py::test_preprocess_command` and `::test_preprocess_command_pipeline` so attached-pipe cases such as `["ls|", ...]` and `["echo|", ...]` assert that each token remains unsplit literal data; document that implicit attached-pipe conversion is intentionally removed. (verification-id: literal-pipe-argument-security) (verification: unit - `uv run pytest tests/test_shell_executor.py -k 'preprocess_command'` passes only when the legacy vulnerable expectations are removed)
- [ ] Add regression coverage proving the reported `awk` policy payload is validated in its original argv form and rejected before subprocess creation or file side effects; assert that `create_process` and `execute_pipeline` are not awaited and that a sentinel file is not created. (verification-id: literal-pipe-argument-security) (verification: integration - `uv run pytest tests/test_command_validator.py tests/test_shell_executor_pipeline.py` asserts rejection and mocked process/file boundaries remain untouched)
- [ ] Change `CommandPreProcessor.preprocess_command()` so only a discrete `|` argv token represents pipeline syntax, without changing explicit pipeline execution. (verification-id: literal-pipe-argument-security) (verification: unit - `uv run pytest tests/test_shell_executor_pipeline.py` covers preserved literals plus explicit pipeline compatibility)
- [ ] Add the affected range and patched-release upgrade instruction to `CHANGELOG.md` under `## [Unreleased]` → `### Security`, without creating the dated `1.1.8` release heading or publishing it. (verification-id: literal-pipe-argument-security) (verification: integration - `uv run python -c "from pathlib import Path; s=Path('CHANGELOG.md').read_text(); u=s.index('## [Unreleased]'); n=s.find('\n## [', u + 1); section=s[u:n if n >= 0 else len(s)]; assert '### Security' in section and 'GHSA-q8pm-q3r2-q7cg' in section and 'GHSA-7wg7-jj87-qp4c' in section and '1.1.7' in section"`)

## Future Work

- Repository owner authorizes and performs the patched package and GitHub Release publication.
- Repository owner selects the primary Advisory, reconciles severity and duplicate handling, preserves reporter credit, and authorizes publication after the patched artifact is verified.

## Final Validation

Expected archive gate: `cflx openspec validate preserve-literal-pipe-arguments --archive-gate`
