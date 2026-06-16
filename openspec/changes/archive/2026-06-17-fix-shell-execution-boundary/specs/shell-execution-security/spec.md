## ADDED Requirements

### Requirement: Shell execution MUST avoid shell interpretation for normal command paths

The shell execution server MUST execute user-provided commands as argv arrays rather than shell-interpreted strings for normal single-command and pipeline execution.

#### Scenario: Single command executes through argv

**Given**: `ALLOW_COMMANDS` allows `echo`
**When**: a client executes `['echo', 'hello']` in a valid directory
**Then**: the server executes the command without passing a user-controlled shell string to a shell interpreter

#### Scenario: Pipeline preserves segment arguments

**Given**: `ALLOW_COMMANDS` allows `echo` and `grep`
**When**: a client executes `['echo', 'hello', '|', 'grep', 'h']`
**Then**: the server validates and executes both argv segments with their arguments preserved

#### Scenario: Pipeline metacharacter injection is rejected

**Given**: a command segment contains shell metacharacters such as `;`
**When**: a client attempts to execute that segment in a pipeline
**Then**: the server rejects the invocation before creating a subprocess

### Requirement: Command policy MUST reject advisory bypass vectors by default

The command policy MUST validate command identity with exact or full-pattern matching and MUST reject known exec-capable bypass vectors by default.

#### Scenario: Pattern allowlist uses full matching

**Given**: `ALLOW_PATTERNS` is set to `ls`
**When**: a client attempts to execute `lsof`
**Then**: the server rejects the command as not allowed

#### Scenario: Exec-capable arguments are rejected

**Given**: `ALLOW_COMMANDS` includes `find`
**When**: a client attempts to execute `['find', '.', '-exec', 'sh', '-c', 'id', '{}', '+']`
**Then**: the server rejects the command before creating a subprocess

#### Scenario: Direct environment dump is rejected by default

**Given**: `ALLOW_COMMANDS` includes `env`
**When**: a client attempts to execute `['env']` under the default hardened policy
**Then**: the server rejects the command before exposing child environment data

### Requirement: Redirection paths MUST remain contained under the working directory

Input and output redirection targets MUST resolve to paths contained under the validated working directory before any file is opened, read, truncated, or appended.

#### Scenario: Absolute redirection path is rejected

**Given**: the working directory is `/tmp/work`
**When**: a client executes `['cat', '<', '/etc/passwd']`
**Then**: the server rejects the invocation before opening `/etc/passwd`

#### Scenario: Parent traversal is rejected

**Given**: the working directory is `/tmp/work`
**When**: a client executes `['cat', '<', '../secret']`
**Then**: the server rejects the invocation before resolving outside `/tmp/work`

#### Scenario: Symlink escape is rejected

**Given**: a symlink inside the working directory points outside the working directory
**When**: a client redirects input or output through that symlink
**Then**: the server rejects the invocation before opening the symlink target

#### Scenario: In-directory redirection is allowed

**Given**: a regular file path resolves inside the working directory
**When**: a client uses that path for `<`, `>`, or `>>`
**Then**: the server allows the redirection subject to command policy and file permissions

### Requirement: Child process environment MUST be isolated from server secrets

Child processes MUST receive only a minimal explicit environment and MUST NOT inherit the server process environment wholesale.

#### Scenario: Parent secret is not visible to child

**Given**: the server process has `SECRET_TOKEN=secret-value` in its environment
**When**: an allowed command is executed
**Then**: the child process environment does not contain `SECRET_TOKEN` unless that variable was explicitly allowlisted by documented configuration

#### Scenario: Audit logs redact secret-like values

**Given**: command arguments or environment metadata contain secret-like names or values
**When**: the server writes audit logs
**Then**: the audit log records redacted placeholders instead of raw secret material

### Requirement: Command execution MUST be bounded by timeout and output limits

Every command invocation MUST have an effective timeout and output byte limit even when the client omits optional timeout input.

#### Scenario: Default timeout applies when client omits timeout

**Given**: a client omits the `timeout` argument
**When**: the command runs longer than the configured default timeout
**Then**: the server terminates the command and returns a timeout outcome

#### Scenario: Output cap prevents unbounded buffering

**Given**: a command produces more output than the configured output byte limit
**When**: the output limit is reached
**Then**: the server terminates or truncates the command deterministically and reports an explicit capped or truncated outcome

### Requirement: Command invocations MUST emit structured audit logs

The server MUST emit structured audit records for successful, rejected, timed-out, output-capped, and process-error command invocations.

#### Scenario: Successful command is audited

**Given**: a command passes validation and completes successfully
**When**: the invocation finishes
**Then**: the audit log includes timestamp, command name, redacted argv, resolved directory, timeout, output byte counts, return code, duration, and success result

#### Scenario: Rejected command is audited

**Given**: a command fails validation before subprocess creation
**When**: the server rejects the invocation
**Then**: the audit log includes the rejection result and enough redacted metadata to support incident review without exposing secrets
