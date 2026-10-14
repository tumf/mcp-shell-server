# command-policy

## Purpose

Allowed regex patterns MUST match the full command name and MUST NOT admit command strings through prefix overmatch.

## Requirements

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

The server MUST validate command arguments and reject exec-capable allowlist bypass vectors before process creation, even when the command name itself is allowed. For an allowlisted `git`, the server MUST reject every command-scoped configuration override supplied through either `-c <name=value>` or `-c<name=value>` without attempting to classify the configuration key as safe. The server MUST also reject persistent `git config` invocations, known alternate binary names for hardened command families, and command-wrapper or shell-escape tools that would execute a non-allowlisted command through their arguments. For an allowlisted GNU `sort` or its `gsort` alias, the server MUST reject options that select an external compression program, direct output to a program-selected path, read an external file list, or select an external temporary directory. Rejection MUST cover full and uniquely abbreviated long options and separated, attached, or clustered short-option forms accepted by GNU option parsing. Option parsing MUST stop at a discrete `--` so later option-like filename operands remain data.

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

#### Scenario: Sort external compression program is rejected

**Given**: `ALLOW_COMMANDS` includes `sort`
**When**: a client executes `['sort', '--compress-program=/tmp/program', 'input']`
**Then**: the server rejects the command before creating a subprocess and the external program is not executed

#### Scenario: Sort direct output is rejected

**Given**: `ALLOW_COMMANDS` includes `sort` and the working directory is `/tmp/work`
**When**: a client executes `['sort', '-o', '/tmp/outside', 'input']`
**Then**: the server rejects the command before creating a subprocess and `/tmp/outside` is not created or modified

#### Scenario: Sort external file-list and temporary-directory options are rejected

**Given**: `ALLOW_COMMANDS` includes `sort`
**When**: a client supplies `--files0-from`, `-T`, or `--temporary-directory` with an attacker-selected path
**Then**: the server rejects the command before creating a subprocess

#### Scenario: GNU alias and abbreviated options use the same policy

**Given**: `ALLOW_COMMANDS` includes `gsort`
**When**: a client supplies a shortest unique abbreviation or clustered form such as `--co=/tmp/program`, `--o=/tmp/outside`, `--fil=/tmp/list`, `--t=/tmp/elsewhere`, `-ro /tmp/outside`, or `-rT /tmp/elsewhere`
**Then**: the server rejects the command before creating a subprocess

#### Scenario: Dangerous option after operand remains rejected

**Given**: `ALLOW_COMMANDS` includes `sort`
**When**: a client executes `['sort', 'input', '-o', '/tmp/outside']`
**Then**: GNU option permutation does not bypass validation and the server rejects the command before creating a subprocess

#### Scenario: Ordinary sort remains allowed

**Given**: `ALLOW_COMMANDS` includes `sort`
**When**: a client executes ordinary sorting arguments, `['sort', '-S1T', 'input']`, or `['sort', '-tT', '-k2,2', 'input']`
**Then**: the command is allowed subject to other policy checks

#### Scenario: Option parsing ends at the operand delimiter

**Given**: `ALLOW_COMMANDS` includes `sort`
**When**: a client executes `['sort', '--', '--output=/tmp/name']`
**Then**: the option-like token after `--` is treated as a filename operand and is allowed subject to other policy checks
