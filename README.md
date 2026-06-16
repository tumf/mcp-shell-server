# MCP Shell Server

[![codecov](https://codecov.io/gh/tumf/mcp-shell-server/branch/main/graph/badge.svg)](https://codecov.io/gh/tumf/mcp-shell-server)
[![smithery badge](https://smithery.ai/badge/mcp-shell-server)](https://smithery.ai/server/mcp-shell-server)

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/tumf-mcp-shell-server-badge.png)](https://mseep.ai/app/tumf-mcp-shell-server)

A secure shell command execution server implementing the Model Context Protocol (MCP). This server allows remote execution of whitelisted shell commands with support for stdin input.

<a href="https://glama.ai/mcp/servers/rt2d4pbn22"><img width="380" height="200" src="https://glama.ai/mcp/servers/rt2d4pbn22/badge" alt="mcp-shell-server MCP server" /></a>

## Features

* **Argv-based Command Execution**: Allowed commands run via subprocess argv without shell-string interpretation
* **Standard Input Support**: Pass input to commands via stdin
* **Comprehensive Output**: Returns stdout, stderr, exit status, and execution time
* **Safe Pipeline Support**: Pipelines preserve and validate argv segments instead of invoking a shell
* **Execution Limits**: Server-side default timeout, maximum timeout, and output byte caps are enforced
* **Contained Redirection**: `<`, `>`, and `>>` targets must stay inside the requested working directory
* **Minimal Child Environment**: Child processes receive a small allowlisted environment instead of inheriting all server secrets
* **Structured Audit Logging**: Success, rejection, timeout, output-cap, and process-error outcomes are logged with redaction

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

## Installation

### Installing via Smithery

To install Shell Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mcp-shell-server):

```bash
npx -y @smithery/cli install mcp-shell-server --client claude
```

### Manual Installation

```bash
pip install mcp-shell-server
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

Allowlisting a command name is not a sandbox for that program's own argument-level execution features. The server applies default argument hardening even when the binary is allowed: known exec-capable vectors such as `find -exec`, shell/interpreter launchers, `awk system()`, `tar --checkpoint-action=exec`, `env`, `xargs`, and git alias external commands are rejected before subprocess creation. For example, `ALLOW_COMMANDS="git"` does not permit `git -c alias.pwn=!sh -c "touch marker" pwn`; the git `alias.<name>=!<cmd>` exec form is rejected by default.

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

### Structured audit logs

Each command invocation emits one `mcp-shell-server.audit` log event named `shell_execution_audit`. Audit records cover successful execution, validation rejection before subprocess creation, timeout, output-cap termination, and process errors including subprocess creation failures.

Audit metadata includes:

* `timestamp`, `duration`, and `result_type`
* command name and redacted `argv`
* resolved working `directory`
* redirection flags for stdin/stdout/stdout append
* redacted per-call environment override metadata, when supplied
* effective `timeout` and `output_limit`
* `stdout_bytes` and `stderr_bytes`
* `return_code` when available
* `rejection_reason` or `error_type` where applicable

Audit logs intentionally do **not** include raw stdout or stderr bodies. Secret-like argv and environment names or values containing markers such as `SECRET`, `TOKEN`, `PASSWORD`, `PASSWD`, `API_KEY`, `ACCESS_KEY`, `PRIVATE_KEY`, `KEY`, `CREDENTIAL`, or `AUTH` are replaced with `[REDACTED]`. Long non-numeric values are represented by a short SHA-256 digest instead of the raw value.

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

The server implements several security measures, but it is not an OS sandbox. A command-name allowlist reduces accidental exposure, but allowed binaries may still read accessible files, consume CPU, or perform behavior allowed by the operating system. For hostile workloads, run the server inside an external sandbox such as a container, VM, or OS policy boundary.

1. **Command Whitelisting**: Only explicitly allowed command names or full-matching `ALLOW_PATTERNS` entries can be executed.
2. **Default Argument Hardening**: Known exec-capable vectors such as shells/interpreters, `env`, `xargs`, `find -exec`, `awk system()`, `tar --checkpoint-action=exec`, and git external aliases are rejected by default even when the command name is allowlisted.
3. **No Shell-String Execution**: Normal commands and pipelines are executed with `asyncio.create_subprocess_exec(*argv)`; user-controlled strings are not passed to a shell.
4. **Contained Redirection**: Redirection paths must be relative to `directory`; absolute paths, `..` traversal, and symlink escapes are rejected before files are opened.
5. **Environment Isolation**: Children receive a minimal environment plus names listed in `MCP_SHELL_CHILD_ENV_ALLOWLIST`. Parent secrets such as tokens are not inherited by default. Per-call `envs` values are only accepted for explicitly allowlisted names.
6. **Execution Limits**: `MCP_SHELL_DEFAULT_TIMEOUT_SECONDS` defaults to 30 seconds, `MCP_SHELL_MAX_TIMEOUT_SECONDS` defaults to 300 seconds, and `MCP_SHELL_OUTPUT_LIMIT_BYTES` defaults to 1 MiB per captured stdout/stderr stream. Client timeouts are clamped to the server maximum; omitted timeouts receive the default. Processes that time out or exceed the output cap are terminated and reaped before an explicit timeout/output-cap error is returned.
7. **Audit Logging**: Each invocation emits structured audit metadata for success, rejection, timeout, output cap, and process error outcomes. Secret-like argv values are redacted; stdout/stderr content is not logged.

### Security-related environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOW_COMMANDS` / `ALLOWED_COMMANDS` | empty | Comma-separated command names to allow |
| `ALLOW_PATTERNS` | empty | Comma-separated regex patterns matched with `fullmatch()` against command names |
| `MCP_SHELL_DEFAULT_TIMEOUT_SECONDS` | `30` | Timeout used when the client omits `timeout` |
| `MCP_SHELL_MAX_TIMEOUT_SECONDS` | `300` | Maximum effective timeout accepted from clients |
| `MCP_SHELL_OUTPUT_LIMIT_BYTES` | `1048576` | Maximum captured stdout/stderr bytes per process |
| `MCP_SHELL_CHILD_ENV_ALLOWLIST` | empty | Comma-separated parent or per-call environment variables allowed in children |
| `MCP_SHELL_SAFE_PATH` | `/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin` | PATH supplied to children |

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
