## ADDED Requirements

### Requirement: Redirection paths MUST be contained under the working directory

The server MUST reject input and output redirection targets that resolve outside the validated working directory before opening, reading, truncating, or appending to files.

#### Scenario: Absolute input redirection is rejected

**Given**: the working directory is `/tmp/work`
**When**: a client executes `['cat', '<', '/etc/passwd']`
**Then**: the server rejects the invocation before opening `/etc/passwd`

#### Scenario: Parent traversal is rejected

**Given**: the working directory is `/tmp/work`
**When**: a client redirects input or output to `../secret`
**Then**: the server rejects the invocation before accessing the target path

#### Scenario: Symlink escape is rejected

**Given**: a symlink inside the working directory points outside the working directory
**When**: a client redirects input or output through that symlink
**Then**: the server rejects the invocation before opening the symlink target

#### Scenario: Contained redirection succeeds

**Given**: a redirection target resolves to a regular path inside the working directory
**When**: a client uses `<`, `>`, or `>>` with that target
**Then**: the server permits the redirection subject to command policy and file permissions
