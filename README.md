# MCP Shell Server

[![codecov](https://codecov.io/gh/tumf/mcp-shell-server/branch/main/graph/badge.svg)](https://codecov.io/gh/tumf/mcp-shell-server)
[![smithery badge](https://smithery.ai/badge/mcp-shell-server)](https://smithery.ai/server/mcp-shell-server)

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/tumf-mcp-shell-server-badge.png)](https://mseep.ai/app/tumf-mcp-shell-server)

A secure shell command execution server implementing the Model Context Protocol (MCP). This server allows remote execution of whitelisted shell commands with support for stdin input.

<a href="https://glama.ai/mcp/servers/rt2d4pbn22"><img width="380" height="200" src="https://glama.ai/mcp/servers/rt2d4pbn22/badge" alt="mcp-shell-server MCP server" /></a>

<a href="https://glama.ai/mcp/servers/rt2d4pbn22"><img width="380" height="200" src="https://glama.ai/mcp/servers/rt2d4pbn22/badge" alt="mcp-shell-server MCP server" /></a>

## Features

* **Secure Command Execution**: Only whitelisted commands can be executed
* **Standard Input Support**: Pass input to commands via stdin
* **Comprehensive Output**: Returns stdout, stderr, exit status, and execution time
* **Shell Operator Safety**: Validates commands after shell operators (; , &&, ||, |)
* **Timeout Control**: Set maximum execution time for commands

## MCP client setting in your Claude.app

### Published version

```shell
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "shell": {
      "command": "uvx",
      "args": [
        "mcp-shell-server"
      ],
      "env": {
        "ALLOW_COMMANDS": "ls,cat,pwd,grep,wc,touch,find"
      }
    },
  }
}
```

### Local version

#### Configuration

```shell
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "shell": {
      "command": "uv",
      "args": [
        "--directory",
        ".",
        "run",
        "mcp-shell-server"
      ],
      "env": {
        "ALLOW_COMMANDS": "ls,cat,pwd,grep,wc,touch,find"
      }
    },
  }
}
```

#### Installation

### Installing via Smithery

To install Shell Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-shell-server):

```bash
npx -y @smithery/cli install mcp-shell-server --client claude
```

### Manual Installation

### Installing via Smithery

To install Shell Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-shell-server):

```bash
npx -y @smithery/cli install mcp-shell-server --client claude
```

### Manual Installation

```bash
pip install mcp-shell-server
```

### Installing via Smithery

To install Shell Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-shell-server):

```bash
npx -y @smithery/cli install mcp-shell-server --client claude
```

## Usage

### Starting the Server

```bash
ALLOW_COMMANDS="ls,cat,echo" uvx mcp-shell-server
# Or using the alias
ALLOWED_COMMANDS="ls,cat,echo" uvx mcp-shell-server
```

The `ALLOW_COMMANDS` (or its alias `ALLOWED_COMMANDS` ) environment variable specifies which commands are allowed to be executed. Commands can be separated by commas with optional spaces around them.

Valid formats for ALLOW_COMMANDS or ALLOWED_COMMANDS:

```bash
ALLOW_COMMANDS="ls,cat,echo"          # Basic format
ALLOWED_COMMANDS="ls ,echo, cat"      # With spaces (using alias)
ALLOW_COMMANDS="ls,  cat  , echo"     # Multiple spaces
```

`ALLOW_PATTERNS` can be used for comma-separated regular expressions that match command names. Each pattern is applied with full-match semantics, so `ALLOW_PATTERNS="ls"` allows only the command name `ls` and does not allow `lsof` or `ls -la`. Patterns and command names containing whitespace or shell metacharacters are rejected; do not use `ALLOW_PATTERNS` to describe shell command strings or argument-level policies.

```bash
ALLOW_PATTERNS="python[0-9.]*,node"    # Command-name patterns only
```

### Child process environment

Commands run with an isolated child environment. The server does **not** pass the full parent process environment to child commands, so unrelated variables such as API tokens, credentials, and `SECRET_TOKEN` are absent by default.

By default the child environment contains only the minimal launch keys needed for command execution: `PATH` on POSIX systems, plus Windows process-launch keys when applicable (`COMSPEC`, `PATHEXT`, `SYSTEMROOT`, and `WINDIR`).

Use `MCP_SHELL_CHILD_ENV_ALLOWLIST` to explicitly allow additional environment variable names to be inherited from the parent process or accepted from per-command environment overrides. The allowlist is comma-separated and uses exact environment variable names:

```bash
MCP_SHELL_CHILD_ENV_ALLOWLIST="LANG,LC_ALL,MY_TOOL_HOME" \
ALLOW_COMMANDS="printenv,my-tool" \
uvx mcp-shell-server
```

Only keys named in `MCP_SHELL_CHILD_ENV_ALLOWLIST` are forwarded. Secret-like names are treated defensively in logs and should not be allowlisted unless you intentionally want a child command to read that secret.

### Request Format

```python
# Basic command execution
{
    "command": ["ls", "-l", "/tmp"]
}

# Command with stdin input
{
    "command": ["cat"],
    "stdin": "Hello, World!"
}

# Command with timeout
{
    "command": ["long-running-process"],
    "timeout": 30  # Maximum execution time in seconds
}

# Command with working directory and timeout
{
    "command": ["grep", "-r", "pattern"],
    "directory": "/path/to/search",
    "timeout": 60
}
```

### Response Format

Successful response:

```json
{
    "stdout": "command output",
    "stderr": "",
    "status": 0,
    "execution_time": 0.123
}
```

Error response:

```json
{
    "error": "Command not allowed: rm",
    "status": 1,
    "stdout": "",
    "stderr": "Command not allowed: rm",
    "execution_time": 0
}
```

## Security

The server implements several security measures:

1. **Command Whitelisting**: Only explicitly allowed commands can be executed
2. **Dangerous Argument Rejection**: Known execution-bypass vectors such as `find -exec`, `awk` programs containing `system()`, `tar --checkpoint-action=exec`, `xargs`, shells, interpreters, and `env` are rejected before subprocess creation even when the command name appears in `ALLOW_COMMANDS` or `ALLOWED_COMMANDS`
3. **Shell Operator Validation**: Commands after shell operators (;, &&, ||, |) are also validated against the whitelist and argument policy
4. **No Shell Injection**: Commands are executed directly without shell interpretation

`ALLOW_COMMANDS` and `ALLOWED_COMMANDS` are command-name allowlists, not a sandbox. Do not allow exec-capable tools unless there is an explicit argument policy that makes the intended subset safe.

## Development

### Setting up Development Environment

1. Clone the repository

```bash
git clone https://github.com/yourusername/mcp-shell-server.git
cd mcp-shell-server
```

2. Install dependencies including test requirements

```bash
pip install -e ".[test]"
```

### Running Tests

```bash
pytest
```

## API Reference

### Request Arguments

| Field     | Type       | Required | Description                                   |
|-----------|------------|----------|-----------------------------------------------|
| command   | string[]   | Yes      | Command and its arguments as array elements   |
| stdin     | string     | No       | Input to be passed to the command            |
| directory | string     | No       | Working directory for command execution       |
| timeout   | integer    | No       | Maximum execution time in seconds             |

### Response Fields

| Field           | Type    | Description                                |
|----------------|---------|---------------------------------------------|
| stdout         | string  | Standard output from the command           |
| stderr         | string  | Standard error output from the command     |
| status         | integer | Exit status code                           |
| execution_time | float   | Time taken to execute (in seconds)         |
| error          | string  | Error message (only present if failed)     |

## Requirements

* Python 3.11 or higher
* mcp>=1.1.0

## License

MIT License - See LICENSE file for details
