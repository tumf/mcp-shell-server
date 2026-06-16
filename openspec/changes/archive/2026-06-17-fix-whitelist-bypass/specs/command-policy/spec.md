## MODIFIED Requirements

### Requirement: Command policy MUST reject exec-capable allowlist bypass vectors

The server MUST validate command arguments and reject known exec-capable bypass vectors before process creation, even when the command name itself is allowed.

#### Scenario: git alias exec bypass is rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client executes `['git', '-c', 'alias.pwn=!sh -c "touch <marker>"', 'pwn']`
**Then**: the server rejects the command before creating a subprocess and the marker file is not created
