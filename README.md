# MCP Shell Server

A secure shell command execution server implementing the Model Context Protocol (MCP). This server allows remote execution of whitelisted shell commands with support for stdin input.

## Features

* **Secure Command Execution**: Only whitelisted commands can be executed
* **Stdin Support**: Pass input to commands via stdin
* **Comprehensive Output**: Returns stdout, stderr, exit status, and execution time
* **Shell Operator Safety**: Validates commands after shell operators (; , &&, ||, |)

## Installation

```bash
pip install mcp-shell-server
```

Or install from source:

```bash
git clone https://github.com/yourusername/mcp-shell-server.git
cd mcp-shell-server
pip install -e .
```

## Usage

### Starting the Server

```bash
ALLOW_COMMANDS="ls,cat,echo" uvx mcp-shell-server
```

The `ALLOW_COMMANDS` environment variable specifies which commands are allowed to be executed.

### Making Requests

Example requests to the server:

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
2. **Shell Operator Validation**: Commands after shell operators are also validated against the whitelist
3. **No Shell Injection**: Commands are executed directly without shell interpretation

## Environment Variables

* `ALLOW_COMMANDS`: Comma-separated list of allowed commands (e.g., "ls, cat, echo")

## API Reference

### Request Format

| Field    | Type       | Description                                   |
|----------|------------|-----------------------------------------------|
| command  | string[]   | Command and its arguments as array elements   |
| stdin    | string     | (Optional) Input to be passed to the command |

### Response Format

| Field           | Type    | Description                                |
|----------------|---------|---------------------------------------------|
| stdout         | string  | Standard output from the command           |
| stderr         | string  | Standard error output from the command     |
| status         | integer | Exit status code                           |
| execution_time | float   | Time taken to execute (in seconds)         |
| error          | string  | (Optional) Error message if failed         |

## Requirements

* Python 3.11 or higher
* uvicorn
* fastapi
* mcp-core
