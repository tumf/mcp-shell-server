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

The server MUST validate command arguments and reject exec-capable allowlist bypass vectors before process creation, even when the command name itself is allowed. For an allowlisted `git`, the server MUST reject every command-scoped configuration override supplied through either `-c <name=value>` or `-c<name=value>` without attempting to classify the configuration key as safe. The server MUST also reject persistent `git config` invocations, known alternate binary names for hardened command families, and command-wrapper or shell-escape tools that would execute a non-allowlisted command through their arguments.

#### Scenario: Separated git configuration override is rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', '-c', 'core.fsmonitor=touch marker', 'status']`
**Then**: the server rejects the command before creating a subprocess and `marker` is not created

#### Scenario: Attached git configuration override is rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', '-cdiff.external=touch marker', 'diff', '--ext-diff']`
**Then**: the server rejects the command before creating a subprocess and `marker` is not created

#### Scenario: Benign-looking git configuration override is rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', '-c', 'user.name=Example', 'status']`
**Then**: the server rejects the command before creating a subprocess because command-scoped Git configuration is categorically disallowed

#### Scenario: Ordinary git command remains allowed

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', 'status']`
**Then**: the command is allowed subject to other policy checks

#### Scenario: Persistent git configuration write is rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', 'config', 'alias.pwn', '!sh -c id']`
**Then**: the server rejects the command before creating a subprocess

#### Scenario: Alternate binary name uses the same default policy

**Given**: `ALLOW_COMMANDS` includes `gawk`
**When**: a client executes `['gawk', 'BEGIN { system("id") }']`
**Then**: the server rejects the command before creating a subprocess

#### Scenario: Command wrapper is rejected

**Given**: `ALLOW_COMMANDS` includes `timeout`
**When**: a client executes `['timeout', '5', 'touch', '/tmp/marker']`
**Then**: the server rejects the command before creating a subprocess

#### Scenario: Git external execution surfaces remain rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client supplies an external-program option or an `ext::` transport
**Then**: the server rejects the command before creating a subprocess
