### Requirement: Supported MCP SDK major version

The package SHALL constrain dependency resolution to MCP Python SDK versions compatible with the server API used by the implementation.

#### Scenario: Fresh production dependency resolution

**Given**: A clean Python environment installs `mcp-shell-server`
**When**: The package manager resolves production dependencies
**Then**: It selects an MCP SDK version below 2.0.0 and importing `mcp_shell_server` succeeds

#### Scenario: MCP SDK v2 migration remains incomplete

**Given**: The server implementation uses MCP SDK v1-only APIs
**When**: Project dependency metadata is checked
**Then**: The MCP dependency excludes SDK major version 2
