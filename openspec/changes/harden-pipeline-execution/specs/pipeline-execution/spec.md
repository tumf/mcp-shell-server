## ADDED Requirements

### Requirement: Pipeline execution MUST preserve argv and avoid shell interpretation

The server MUST represent each pipeline segment as an argv array and MUST NOT execute user-controlled pipeline segment strings through shell interpretation.

#### Scenario: Pipeline arguments are preserved

**Given**: `ALLOW_COMMANDS` includes `echo` and `grep`
**When**: a client executes `['echo', 'hello', '|', 'grep', 'h']`
**Then**: the `grep` segment receives `h` as an argument and the pipeline succeeds

#### Scenario: Pipeline shell metacharacter injection has no side effect

**Given**: a pipeline segment contains `; touch <sentinel>`
**When**: a client attempts to execute that pipeline
**Then**: the server rejects or safely fails the invocation without creating the sentinel file

#### Scenario: Each pipeline segment is validated before execution

**Given**: a pipeline contains one disallowed segment
**When**: a client executes the pipeline
**Then**: the server rejects the entire pipeline before creating subprocesses for later segments
