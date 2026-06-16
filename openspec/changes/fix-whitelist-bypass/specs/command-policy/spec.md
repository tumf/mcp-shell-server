## ADDED Requirements

### Requirement: Command policy MUST reject git alias exec bypass vectors

The server MUST reject `git -c alias.<name>=!<exec>` style invocations before creating a subprocess, even when `git` itself is allowed.

#### Scenario: git alias exec bypass is rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', '-c', 'alias.pwn=!sh -c "touch <marker>"', 'pwn']`
**Then**: the server rejects the command before creating a subprocess and the marker file is not created

#### Scenario: xargs sh execution is rejected

**Given**: `ALLOW_COMMANDS` includes `xargs`
**When**: a client executes `['xargs', 'sh', '-c', 'id']`
**Then**: the server rejects the command before creating a subprocess

## MODIFIED Requirements

### Requirement: Command policy MUST reject exec-capable allowlist bypass vectors

The server MUST validate command arguments and reject known exec-capable bypass vectors before process creation, even when the command name itself is allowed.

#### Scenario: git alias exec bypass is rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', '-c', 'alias.pwn=!sh -c "touch <marker>"', 'pwn']`
**Then**: the server rejects the command before creating a subprocess

#### Scenario: xargs sh execution is rejected

**Given**: `ALLOW_COMMANDS` includes `xargs`
**When**: a client executes `['xargs', 'sh', '-c', 'id']`
**Then**: the server rejects the command before creating a subprocess
