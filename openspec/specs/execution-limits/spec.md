### Requirement: Command execution MUST have timeout and output bounds

The server MUST enforce effective timeout and output byte limits for every command invocation, including when clients omit optional timeout input.

#### Scenario: Default timeout applies

**Given**: a client omits the `timeout` argument
**When**: the command runs longer than the configured default timeout
**Then**: the server terminates the command and returns a timeout outcome

#### Scenario: Excessive client timeout is bounded

**Given**: a client supplies a timeout greater than the configured maximum
**When**: the command is invoked
**Then**: the server clamps or rejects the timeout according to documented behavior

#### Scenario: Effective timeout reaches process execution

**Given**: the server computes an effective timeout
**When**: command execution begins
**Then**: the process execution layer enforces that effective timeout

#### Scenario: Output cap is enforced

**Given**: a command produces more stdout or stderr than the configured byte limit
**When**: the output limit is reached
**Then**: the server truncates or terminates the command deterministically and reports an explicit capped/truncated outcome

#### Scenario: Process cleanup follows limits

**Given**: a command times out or exceeds output limits
**When**: the server stops the command
**Then**: the child process is terminated and reaped without leaving a running process behind
