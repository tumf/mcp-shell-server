# process-environment

## Purpose

The server MUST construct an explicit minimal child environment and MUST NOT forward the parent process environment wholesale.

## Requirements

### Requirement: Child processes MUST NOT inherit server secrets by default

The server MUST construct an explicit minimal child environment and MUST NOT forward the parent process environment wholesale.

#### Scenario: Parent secret is excluded

**Given**: the server process has `SECRET_TOKEN=secret-value` in its environment
**When**: a child command is executed under default configuration
**Then**: the child environment does not contain `SECRET_TOKEN`

#### Scenario: Allowlisted variable is included

**Given**: a documented configuration explicitly allowlists a non-secret variable
**When**: a child command is executed
**Then**: that allowlisted variable may be present in the child environment

#### Scenario: Non-allowlisted env injection is rejected or ignored

**Given**: a caller or internal path provides environment values not in the allowlist
**When**: a child command is created
**Then**: the server excludes those values from the child environment

### Requirement: Child command PATH MUST follow explicit server configuration

On POSIX, the authoritative environment builder MUST initialize PATH from a nonblank MCP_SHELL_SAFE_PATH or DEFAULT_SAFE_PATH and MUST NOT inherit the parent PATH by default. Empty or whitespace-only SAFE_PATH MUST fall back to default. A nonblank value MUST be preserved without trimming. Explicit exact PATH membership in MCP_SHELL_CHILD_ENV_ALLOWLIST MUST permit parent and per-call PATH values, with per-call greater precedence than parent and both greater than SAFE_PATH/default. Missing explicitly delegated values MUST retain the initial PATH. Nonallowlisted overrides MUST NOT change PATH or server configuration. All process creation paths and any retained instance adapter MUST use the same builder. Windows MUST preserve launch-key compatibility, use nonblank configured SAFE_PATH, and otherwise preserve parent PATH with os.defpath only as a fallback when parent PATH is absent, without claiming that child environment PATH controls native executable search. Explicitly delegated PATH values, including empty strings, MUST be passed unchanged.

#### Scenario: Parent executable shadow is not selected

**Given**: an allowlisted harmless command exists in configured safe PATH and a shadow executable is earlier in parent PATH, with PATH not delegated
**When**: normal or pipeline execution launches the command
**Then**: only the configured safe executable runs and shadow markers remain absent

#### Scenario: Safe PATH has no executable

**Given**: a command exists only in parent PATH and PATH is not delegated
**When**: execution uses configured SAFE_PATH without that command
**Then**: ShellExecutor returns a process-creation error and the parent fixture marker remains absent

#### Scenario: Explicit PATH delegation is preserved

**Given**: the operator explicitly allowlists PATH
**When**: parent and per-call PATH are supplied
**Then**: the per-call value wins, parent value is the fallback, and absent values retain SAFE_PATH/default

#### Scenario: Blank safe PATH uses default

**Given**: on POSIX MCP_SHELL_SAFE_PATH is unset, empty, or whitespace only, with parent PATH either set or absent
**When**: the server constructs a child environment without PATH delegation
**Then**: documented platform default is used rather than parent PATH
