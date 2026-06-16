import asyncio
import logging
import os
import signal
import traceback
from collections.abc import Sequence
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .process_manager import DEFAULT_OUTPUT_LIMIT_BYTES, DEFAULT_TIMEOUT_SECONDS
from .shell_executor import ShellExecutor
from .version import __version__

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-shell-server")

app: Server = Server("mcp-shell-server")
DEFAULT_MAX_TIMEOUT_SECONDS = 300
DEFAULT_SERVER_OUTPUT_LIMIT_BYTES = DEFAULT_OUTPUT_LIMIT_BYTES


def _positive_int_from_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid integer environment configuration", extra={"name": name})
        return default
    return value if value > 0 else default


class ExecuteToolHandler:
    """Handler for shell command execution."""

    name = "shell_execute"
    description = "Execute a shell command"

    def __init__(self):
        self.executor = ShellExecutor()
        self.default_timeout = _positive_int_from_env(
            "MCP_SHELL_DEFAULT_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS
        )
        self.max_timeout = _positive_int_from_env(
            "MCP_SHELL_MAX_TIMEOUT_SECONDS", DEFAULT_MAX_TIMEOUT_SECONDS
        )
        if self.default_timeout > self.max_timeout:
            self.default_timeout = self.max_timeout
        self.output_limit = _positive_int_from_env(
            "MCP_SHELL_OUTPUT_LIMIT_BYTES", DEFAULT_SERVER_OUTPUT_LIMIT_BYTES
        )

    def get_allowed_commands(self) -> list[str]:
        """Get the allowed commands."""
        return self.executor.validator.get_allowed_commands()

    def get_allowed_patterns(self) -> list[str]:
        """Get the allowed regex patterns."""
        return [
            pattern.pattern for pattern in self.executor.validator._get_allowed_patterns()
        ]

    def _effective_timeout(self, timeout: Any) -> int:
        if timeout is None:
            return self.default_timeout
        if not isinstance(timeout, int):
            raise ValueError("'timeout' must be an integer")
        if timeout <= 0:
            raise ValueError("'timeout' must be greater than 0")
        return min(timeout, self.max_timeout)

    def get_tool_description(self) -> Tool:
        """Get the tool description for the execute command."""
        allowed_commands = ", ".join(self.get_allowed_commands())
        allowed_patterns = ", ".join(self.get_allowed_patterns())
        return Tool(
            name=self.name,
            description=(
                f"{self.description}\nAllowed commands: {allowed_commands}\n"
                f"Allowed patterns: {allowed_patterns}\n"
                f"Default timeout: {self.default_timeout}s; maximum timeout: {self.max_timeout}s; "
                f"output cap: {self.output_limit} bytes"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command and its arguments as array",
                    },
                    "stdin": {
                        "type": "string",
                        "description": "Input to be passed to the command via stdin",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Absolute path to a working directory where the command will be executed",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds; clamped to server maximum",
                        "minimum": 1,
                    },
                },
                "required": ["command", "directory"],
            },
        )

    async def run_tool(self, arguments: dict) -> Sequence[TextContent]:
        """Execute the shell command with the given arguments."""
        command = arguments.get("command", [])
        stdin = arguments.get("stdin")
        directory = arguments.get("directory", "/tmp")
        requested_timeout = arguments.get("timeout")

        if not command:
            raise ValueError("No command provided")

        if not isinstance(command, list):
            raise ValueError("'command' must be an array")

        if not directory:
            raise ValueError("Directory is required")

        effective_timeout = self._effective_timeout(requested_timeout)
        content: list[TextContent] = []
        try:
            result = await self.executor.execute(
                command,
                directory,
                stdin,
                effective_timeout,
                output_limit=self.output_limit,
            )

            if result.get("error"):
                raise ValueError(result["error"])

            if result.get("stdout"):
                content.append(TextContent(type="text", text=result["stdout"]))

            stderr = result.get("stderr")
            if stderr and "cannot set terminal process group" not in stderr:
                content.append(TextContent(type="text", text=stderr))

        except asyncio.TimeoutError as e:
            raise ValueError(
                f"Command timed out after {effective_timeout} seconds"
            ) from e

        return content


# Initialize tool handlers
tool_handler = ExecuteToolHandler()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [tool_handler.get_tool_description()]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls."""
    try:
        if name != tool_handler.name:
            raise ValueError(f"Unknown tool: {name}")

        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a dictionary")

        return await tool_handler.run_tool(arguments)

    except Exception as e:
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Error executing command: {str(e)}") from e


async def main() -> None:
    """Main entry point for the MCP shell server."""
    logger.info(f"Starting MCP shell server v{__version__}")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        if not stop_event.is_set():
            logger.info("Received shutdown signal, starting cleanup...")
            stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    try:
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            server_task = asyncio.create_task(
                app.run(read_stream, write_stream, app.create_initialization_options())
            )
            stop_task = asyncio.create_task(stop_event.wait())
            done, pending = await asyncio.wait(
                [server_task, stop_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                try:
                    await task
                except Exception:
                    raise

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)

        if hasattr(tool_handler, "executor") and hasattr(
            tool_handler.executor, "process_manager"
        ):
            await tool_handler.executor.process_manager.cleanup_processes()

        logger.info("Server shutdown complete")
