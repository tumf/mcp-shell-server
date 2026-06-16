### Requirement: ALLOW_PATTERNS MUST use full command-name matching

Allowed regex patterns MUST match the full command name and MUST NOT admit command strings through prefix overmatch.

#### Scenario: Exact pattern allows exact command

**Given**: `ALLOW_PATTERNS` is `ls`
**When**: a client executes command name `ls`
**Then**: the command name is allowed subject to other policy checks

#### Scenario: Prefix overmatch is rejected

**Given**: `ALLOW_PATTERNS` is `ls`
**When**: a client executes command name `lsof`
**Then**: the server rejects the command as not allowed

#### Scenario: Metacharacter-bearing command string is rejected

**Given**: `ALLOW_PATTERNS` is configured
**When**: a client attempts to admit a command string containing shell metacharacters through pattern matching
**Then**: the server rejects the command before process creation

### Requirement: Command policy MUST reject exec-capable allowlist bypass vectors

The server MUST validate command arguments and reject known exec-capable bypass vectors before process creation, even when the command name itself is allowed.

#### Scenario: find exec is rejected

**Given**: `ALLOW_COMMANDS` includes `find`
**When**: a client executes `['find', '.', '-exec', 'sh', '-c', 'id', '{}', '+']`
**Then**: the server rejects the command before creating a subprocess

#### Scenario: interpreter execution is rejected

**Given**: `ALLOW_COMMANDS` includes a shell or interpreter command
**When**: a client attempts to execute that command under default policy
**Then**: the server rejects the invocation before creating a subprocess

#### Scenario: awk system is rejected

**Given**: `ALLOW_COMMANDS` includes `awk`
**When**: a client provides an awk program containing `system()`
**Then**: the server rejects the invocation before creating a subprocess

#### Scenario: tar exec action is rejected

**Given**: `ALLOW_COMMANDS` includes `tar`
**When**: a client provides `--checkpoint-action=exec` or equivalent exec action
**Then**: the server rejects the invocation before creating a subprocess

#### Scenario: env dump is rejected by default

**Given**: `ALLOW_COMMANDS` includes `env`
**When**: a client executes `['env']` under default policy
**Then**: the server rejects the invocation before creating a subprocess
