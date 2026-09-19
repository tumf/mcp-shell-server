# MCP Shell Server

[![codecov](https://codecov.io/gh/tumf/mcp-shell-server/branch/main/graph/badge.svg)](https://codecov.io/gh/tumf/mcp-shell-server)
[![smithery badge](https://smithery.ai/badge/mcp-shell-server)](https://smithery.ai/server/mcp-shell-server)

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/tumf-mcp-shell-server-badge.png)](https://mseep.ai/app/tumf-mcp-shell-server)

A trusted execution server implementing the Model Context Protocol (MCP). It runs allowlisted commands as argv arrays, with stdin input, contained redirection, a minimal child environment, execution limits, and structured audit logging.

**This package is not a sandbox.** Allowing a command delegates that program the server process's existing OS authority. Read [Trusted execution contract](#trusted-execution-contract) before configuring it.

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

## Trusted execution contract

Read this before the configuration examples below. The server emits the same warning once at startup through its logger (stderr); MCP stdout framing is unchanged.

### What the server controls

`mcp-shell-server` enforces a boundary around its *own* behavior:

* which executable names it launches directly (`ALLOW_COMMANDS`, `ALLOW_PATTERNS`),
* argv-based process creation without shell-string interpretation,
* server-managed `<`, `>`, and `>>` redirection contained under the requested working directory,
* the child environment it builds,
* timeout and output-byte limits,
* structured audit records.

### What the server does not control

Allowing a command is authority delegation: the allowed program runs with the server process's existing OS identity, filesystem access, network access, and credentials. `ALLOW_COMMANDS` and `ALLOW_PATTERNS` restrict only the command names the server launches directly. They do **not** guarantee containment of:

* child processes an allowed program spawns,
* program-specific interpreters, expression languages, or plugins,
* configuration files, dotfiles, or environment-driven behavior the program reads on its own,
* filesystem reads and writes the program performs itself, outside server-managed redirection,
* network access the program performs itself.

The command-specific rejection rules described under [Security](#security) are best-effort defense in depth against known dangerous argument forms. They are non-exhaustive, and they are not a proof that an allowed program is safe.

### Untrusted input requires external isolation

A trusted, authenticated MCP client does not make the *content* it processes trusted. Model-provided text, fetched web pages, issue text, and repository contents are untrusted input even when the client itself is trusted, and an LLM can be induced to construct a request from that content.

If any request or any file the server can reach may derive from untrusted input, run the server inside an independently enforced OS boundary (container, VM, jail, or OS policy) that provides:

* **Least-privilege identity** — a dedicated non-root user with no administrative rights on the host.
* **Filesystem scope** — only the directories the workload needs, mounted read-only where possible, with host configuration, SSH keys, and cloud credential files out of reach.
* **Network restrictions** — egress denied by default, allowing only the destinations the workload requires.
* **Credential exclusion** — no ambient tokens, cloud instance-metadata access, or agent sockets reachable from the server process.
* **Descendant-process containment** — a process/cgroup namespace so processes spawned by an allowed program are bounded and reaped with the sandbox.
* **Resource limits** — CPU, memory, disk, process-count, and wall-clock caps enforced outside this package.

Keep the allowlist as narrow as the workload allows; a narrow allowlist reduces exposure but never substitutes for the boundary above.

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

Allowlisting a command name is not a sandbox for that program's own argument-level execution features. The server applies default argument hardening even when the binary is allowed: known exec-capable vectors such as `find -exec`, shell/interpreter launchers, `awk system()`, `tar --checkpoint-action=exec`, `env`, `xargs`, command-wrapper tools such as `timeout`/`nice`/`nohup`, shell-escape tools such as `sed`/`less`/`vim`/`ssh`, common alternate names such as `gfind`/`gawk`/`gtar`/`gsort`, GNU `sort` options that select an external program, output path, external file list, or external temporary directory (`--compress-program`, `-o`/`--output`, `--files0-from`, and `-T`/`--temporary-directory`, including abbreviated and clustered forms such as `--co`, `--o`, `-ro FILE`, and `-rT DIR`), all Git command-scoped configuration overrides, and persistent `git config` writes are rejected before subprocess creation. For example, `ALLOW_COMMANDS="git"` does not permit `git -c user.name=Example status`, `git -c alias.pwn=!sh -c "touch marker" pwn`, or `git config alias.pwn '!sh -c "touch marker"'`; every global `git -c <name=value>` and `git -c<name=value>` override is rejected regardless of its key or value.

Write sorted output with the server's contained redirection instead of `sort -o`: `["sort", "input", ">", "output"]` keeps the target inside the requested working directory, while `sort -o` would write directly to any process-accessible path. Option-like filenames stay usable after the `--` delimiter, for example `["sort", "--", "--output=data"]`.

This hardening is best-effort defense in depth against known dangerous argument forms. It is non-exhaustive and is not a complete sandbox for arbitrary untrusted command execution. See [Trusted execution contract](#trusted-execution-contract) for the external isolation required when requests or file contents may derive from untrusted input.

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

The `directory` argument is optional. If omitted, commands run in the MCP server process current working directory (server process CWD). Relative `directory` values are resolved from that same server process CWD. This base is **not** the MCP client CWD; it is the working directory of the process that launched `mcp-shell-server`.

```python
# Basic command execution in the server process CWD
{
    "command": ["ls", "-l"]
}

# Command with a relative working directory resolved from the server process CWD
{
    "command": ["pwd"],
    "directory": "subproject"
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

The measures below are the server's own enforceable boundary; they are not an OS sandbox. A command-name allowlist controls which executables the server launches directly, but an allowed program still runs with the server process's OS authority and may read accessible files, consume CPU, spawn child processes, or reach the network. See [Trusted execution contract](#trusted-execution-contract) for what this does and does not contain, and for the external isolation required with untrusted input.

1. **Command Whitelisting**: Only explicitly allowed command names or full-matching `ALLOW_PATTERNS` entries can be executed. This admits executable names; it does not confine an allowed program's own behavior.
2. **Default Argument Hardening** (non-exhaustive defense in depth): Known exec-capable vectors such as shells/interpreters, `env`, `xargs`, `find -exec`, `awk system()`, `tar --checkpoint-action=exec`, GNU `sort --compress-program`/`-o`/`--files0-from`/`-T`, Git external-program options, and every global `git -c <name=value>` or `git -c<name=value>` configuration override are rejected by default even when the command name is allowlisted.
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
| directory | string     | No       | Working directory; omitted uses the server process CWD, and relative paths resolve from that server process CWD |
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
