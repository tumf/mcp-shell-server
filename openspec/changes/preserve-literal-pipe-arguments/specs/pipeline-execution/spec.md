## MODIFIED Requirements

### Requirement: Pipeline execution MUST preserve argv and avoid shell interpretation

The server MUST represent each pipeline segment as an argv array, MUST recognize pipeline syntax only from a discrete `|` argv element, MUST preserve pipe characters embedded in all other argv elements as literal argument data, and MUST NOT execute user-controlled pipeline segment strings through shell interpretation.

#### Scenario: Pipeline arguments are preserved

**Given**: `ALLOW_COMMANDS` includes `echo` and `grep`
**When**: a client executes `['echo', 'hello', '|', 'grep', 'h']`
**Then**: the `grep` segment receives `h` as an argument and the pipeline succeeds

#### Scenario: Literal pipe in an argument remains data

**Given**: `ALLOW_COMMANDS` includes `grep`
**When**: a client executes `['grep', '-E', 'error|warning', 'file.txt']`
**Then**: the server preserves `error|warning` as one argument and does not create another pipeline segment

#### Scenario: Trailing literal pipe cannot smuggle a command stage

**Given**: `ALLOW_COMMANDS` includes `echo` and `id`
**When**: a client executes `['echo', 'text|', 'id']`
**Then**: the server preserves `text|` as argument data and does not execute `id` as an independent subprocess

#### Scenario: Command policy sees original embedded-pipe content

**Given**: an allowed command has a policy that rejects an exec-capable argument containing `|`
**When**: a client supplies the prohibited content inside one argv element
**Then**: the policy evaluates the unchanged argument and rejects the invocation before subprocess creation or file side effects

#### Scenario: Pipeline shell metacharacter injection has no side effect

**Given**: a pipeline segment contains `; touch <sentinel>`
**When**: a client attempts to execute that pipeline
**Then**: the server rejects or safely fails the invocation without creating the sentinel file

#### Scenario: Each pipeline segment is validated before execution

**Given**: a pipeline contains one disallowed segment
**When**: a client executes the pipeline
**Then**: the server rejects the entire pipeline before creating subprocesses for later segments
