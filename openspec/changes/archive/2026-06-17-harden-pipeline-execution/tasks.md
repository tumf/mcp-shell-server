## Implementation Tasks

- [x] Preserve pipeline argv arrays in `src/mcp_shell_server/shell_executor.py`. Completion condition: parsed pipeline commands retain all arguments and are passed as `List[List[str]]`. (verification: integration - `tests/test_shell_executor_pipeline.py` covers a pipeline whose second command requires an argument, e.g. `grep h`; run `pytest tests/test_shell_executor_pipeline.py`.)

- [x] Execute pipeline segments without shell interpretation in `src/mcp_shell_server/process_manager.py`. Completion condition: pipeline creation uses argv-based subprocess execution for each segment. (verification: unit - `tests/test_process_manager.py` mocks subprocess creation and asserts argv calls for pipeline segments; run `pytest tests/test_process_manager.py`.)

- [x] Reject or safely fail pipeline metacharacter injection. Completion condition: payloads such as `['ls; touch /tmp/pwned', '|', 'cat']` do not produce side effects. (verification: integration - `tests/test_shell_executor_pipeline.py` asserts `/tmp/pwned` or a temp sentinel file is not created; run `pytest tests/test_shell_executor_pipeline.py`.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate harden-pipeline-execution --archive-gate`.

## Acceptance #1 Failure Follow-up
- [x] Regression: tests/test_shell_executor.py::test_pipe_operator fails — validate_no_shell_operators at command_validator.py:120 applied to all pipeline tokens rejects legitimate newline-containing arguments (hello\nworld). Fixed by scoping pipeline shell-operator fragment validation to command-name tokens before appending arguments. (verification: integration - `uv run pytest tests/test_shell_executor.py::test_pipe_operator tests/test_shell_executor_pipeline.py::test_pipeline_allows_newline_argument_after_safe_command_name tests/test_shell_executor_pipeline.py::test_pipeline_rejects_metacharacter_injected_command tests/test_shell_executor_pipeline.py::test_pipeline_metacharacter_injection_rejected_without_side_effect -q`.)
