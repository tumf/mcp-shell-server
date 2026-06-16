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
