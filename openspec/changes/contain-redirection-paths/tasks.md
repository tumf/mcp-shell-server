## Implementation Tasks

- [x] Add redirection target resolution and containment checks in `src/mcp_shell_server/io_redirection_handler.py`. Completion condition: absolute paths, `..` segments, and realpath/commonpath escapes are rejected before file open. (verification: unit - `tests/test_shell_executor_redirections.py` covers absolute path rejection, traversal rejection, symlink escape rejection, and valid in-directory input; run `pytest tests/test_shell_executor_redirections.py`.)

- [x] Ensure output redirection cannot truncate or append outside the validated directory. Completion condition: `>` and `>>` open only contained paths and fail closed for escaping paths. (verification: integration - `tests/test_shell_executor_redirections.py` verifies escaped output targets do not create/modify outside files; run `pytest tests/test_shell_executor_redirections.py`.)

- [x] Fix redirected stdout file-handle handling after containment is enforced. Completion condition: runtime file handles are detected with `io.IOBase` or equivalent runtime-valid checks instead of `typing.IO`. (verification: integration - `tests/test_shell_executor_redirections.py` proves valid `>` and `>>` write inside the working directory and produce expected command result metadata.)

## Final Validation

Archive validation itself is the authoritative final OpenSpec validation gate. Expected archive gate: `cflx openspec validate contain-redirection-paths --archive-gate`.
