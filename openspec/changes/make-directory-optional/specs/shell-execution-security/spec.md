## MODIFIED Requirements

### Requirement: Redirection paths MUST remain contained under the working directory

Input and output redirection targets MUST resolve to paths contained under the validated effective working directory before any file is opened, read, truncated, or appended. The effective working directory is the supplied absolute directory, the supplied relative directory resolved from the server process current working directory, or the server process current working directory when the client omits `directory`.

#### Scenario: Absolute redirection path is rejected

**Given**: the effective working directory is `/tmp/work`
**When**: a client executes `['cat', '<', '/etc/passwd']`
**Then**: the server rejects the invocation before opening `/etc/passwd`

#### Scenario: Parent traversal is rejected

**Given**: the effective working directory is `/tmp/work`
**When**: a client executes `['cat', '<', '../secret']`
**Then**: the server rejects the invocation before resolving outside `/tmp/work`

#### Scenario: Symlink escape is rejected

**Given**: a symlink inside the effective working directory points outside the effective working directory
**When**: a client redirects input or output through that symlink
**Then**: the server rejects the invocation before opening the symlink target

#### Scenario: In-directory redirection is allowed

**Given**: a regular file path resolves inside the effective working directory
**When**: a client uses that path for `<`, `>`, or `>>`
**Then**: the server allows the redirection subject to command policy and file permissions

## ADDED Requirements

### Requirement: Shell execution directory MUST be optional with server CWD default

The shell execution tool MUST allow clients to omit `directory`. When omitted, the server MUST execute the command in the MCP server process current working directory after validating that directory. When a client supplies a relative `directory`, the server MUST resolve it relative to the MCP server process current working directory before validation and execution.

#### Scenario: Directory omitted uses server process CWD

**Given**: the server process current working directory is `/tmp/work`
**When**: a client executes `['pwd']` without a `directory` argument
**Then**: the server validates `/tmp/work` and executes the command with `/tmp/work` as the working directory

#### Scenario: Relative directory is resolved from server process CWD

**Given**: the server process current working directory is `/tmp/work`
**And**: `/tmp/work/subdir` exists and is accessible
**When**: a client executes `['pwd']` with `directory` set to `subdir`
**Then**: the server validates `/tmp/work/subdir` and executes the command with `/tmp/work/subdir` as the working directory

#### Scenario: Absolute directory keeps existing behavior

**Given**: `/tmp/work` exists and is accessible
**When**: a client executes `['pwd']` with `directory` set to `/tmp/work`
**Then**: the server validates `/tmp/work` and executes the command with `/tmp/work` as the working directory

#### Scenario: Empty directory is rejected

**Given**: a client supplies `directory` as an empty or whitespace-only string
**When**: the client executes any command
**Then**: the server rejects the invocation before command execution
