## Implementation Tasks

- [x] Add redirection target resolution and containment checks in `src/mcp_shell_server/io_redirection_handler.py`. Completion condition: absolute paths, `..` segments, and realpath/commonpath escapes are rejected before file open. (verification: unit - `tests/test_shell_executor_redirections.py` covers absolute path rejection, traversal rejection, symlink escape rejection, and valid in-directory input; run `pytest tests/test_shell_executor_redirections.py`.)

- [x] Ensure output redirection cannot truncate or append outside the validated directory. Completion condition: `>` and `>>` open only contained paths and fail closed for escaping paths. (verification: integration - `tests/test_shell_executor_redirections.py` verifies escaped output targets do not create/modify outside files; run `pytest tests/test_shell_executor_redirections.py`.)

- [x] Fix redirected stdout file-handle handling after containment is enforced. Completion condition: runtime file handles are detected with `io.IOBase` or equivalent runtime-valid checks instead of `typing.IO`. (verification: integration - `tests/test_shell_executor_redirections.py` proves valid `>` and `>>` write inside the working directory and produce expected command result metadata.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate contain-redirection-paths --archive-gate`.

## Acceptance #1 Failure Follow-up

- [x] tests/test_process_manager_additional.py::test_execute_pipeline_last_stdout_handle fails: MagicMock(spec=IO) does not pass isinstance(x, io.IOBase) check at process_manager.py:301. Fixed with runtime-valid `io.TextIOBase` mock. (verification: integration - targeted pytest run `ba4315106109015f4a6ef654a68ff3c0`).
- [x] tests/test_shell_executor.py::test_combined_redirections fails: uses absolute paths for both input and output redirection targets. Fixed by using relative redirection filenames while keeping absolute paths only for fixture setup/assertions. (verification: integration - targeted pytest run `ba4315106109015f4a6ef654a68ff3c0`).
- [x] tests/test_shell_executor.py::test_input_redirection fails: uses absolute path os.path.join(temp_test_dir, 'in.txt') as redirection target. Fixed by using relative filename 'in.txt'. (verification: integration - targeted pytest run `ba4315106109015f4a6ef654a68ff3c0`).
- [x] tests/test_shell_executor.py::test_output_redirection fails: uses absolute path os.path.join(temp_test_dir, 'out.txt') as redirection target, now rejected by containment check in io_redirection_handler.py:96. Fixed by using relative filename 'out.txt'. (verification: integration - targeted pytest run `ba4315106109015f4a6ef654a68ff3c0`).
- [x] tests/test_shell_executor.py::test_output_redirection_with_append fails: uses absolute path os.path.join(temp_test_dir, 'test.txt'). Fixed by using relative filename 'test.txt'. (verification: integration - targeted pytest run `ba4315106109015f4a6ef654a68ff3c0`).
