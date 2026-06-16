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
