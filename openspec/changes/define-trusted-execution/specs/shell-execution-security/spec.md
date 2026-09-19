## ADDED Requirements

### Requirement: The server exposes an explicit trusted-execution boundary

mcp-shell-server SHALL describe command admission as delegation of the server process's existing OS authority to an allowed program. Command-name allowlisting and command-specific argument rejection SHALL NOT be represented as comprehensive containment of an allowed program's own behavior.

#### Scenario: Operator reads the execution contract

**Given**: An operator evaluates mcp-shell-server for an MCP deployment
**When**: The operator reads README and SECURITY.md
**Then**: The documents state that allowlists control executable names directly launched by the server
**And**: They state that allowed programs may use child processes, configuration, interpreters, filesystem access, and network access within the server's OS authority
**And**: They identify existing command-specific rejection rules as non-exhaustive defense in depth

#### Scenario: Untrusted content requires external isolation

**Given**: An authenticated client or LLM can submit requests derived from untrusted prompts, files, or repositories
**When**: The operator determines the deployment boundary
**Then**: Documentation requires independently enforced OS isolation for filesystem, network, credentials, descendant processes, and resources
**And**: Client authentication alone is not described as making the processed content trusted

#### Scenario: Server starts with an allowed command policy

**Given**: The MCP server starts normally
**When**: Startup initialization completes
**Then**: The operator receives one warning through logging or stderr that allowed programs run with server privileges
**And**: The warning directs untrusted-input deployments to external isolation
**And**: MCP stdout framing remains unchanged

### Requirement: Defense-in-depth compatibility is preserved

The trusted-execution definition SHALL retain existing command-specific security checks and existing MCP/configuration contracts. Documented limitations SHALL NOT waive security treatment for direct allowlist bypasses, unintended shell interpretation, server-managed redirection escape, secret exposure, execution-limit failures, or violations of an explicitly documented rejection rule.

#### Scenario: Existing deployment upgrades

**Given**: A deployment uses existing command allowlist variables and MCP requests
**When**: It upgrades to the implementation of this change
**Then**: Existing environment variable names, tool names, request schemas, response schemas, and subprocess semantics remain compatible
**And**: Existing command-specific rejection tests continue to pass

#### Scenario: A future implementation violates an explicit contract

**Given**: The documentation states that the server directly enforces a specific boundary
**When**: A report demonstrates that the implementation bypasses that boundary
**Then**: The report remains security-sensitive even though the product is defined as a trusted execution tool
