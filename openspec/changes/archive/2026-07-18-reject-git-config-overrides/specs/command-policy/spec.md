## MODIFIED Requirements

### Requirement: Command policy MUST reject exec-capable allowlist bypass vectors

The server MUST validate command arguments and reject exec-capable allowlist bypass vectors before process creation, even when the command name itself is allowed. For an allowlisted `git`, the server MUST reject every command-scoped configuration override supplied through either `-c <name=value>` or `-c<name=value>` without attempting to classify the configuration key as safe.

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

#### Scenario: Git external execution surfaces remain rejected

**Given**: `ALLOW_COMMANDS` includes `git`
**When**: a client supplies an external-program option or an `ext::` transport
**Then**: the server rejects the command before creating a subprocess
