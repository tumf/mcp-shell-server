import asyncio
import logging
import traceback
from collections.abc import Sequence
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .shell_executor import ShellExecutor
from .version import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-shell-server")

app = Server("mcp-shell-server")


class ExecuteToolHandler:
    """Handler for shell command execution"""

    name = "shell_execute"
    description = "Execute a shell command"

    def __init__(self):
        self.executor = ShellExecutor()

    def get_allowed_commands(self) -> list[str]:
        """Get the allowed commands"""
        return self.executor.validator.get_allowed_commands()

    def get_tool_description(self) -> Tool:
        """Get the tool description for the execute command"""
        return Tool(
            name=self.name,
            description=f"{self.description}\nAllowed commands: {', '.join(self.get_allowed_commands())}",
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
                        "description": "Working directory where the command will be executed",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds",
                        "minimum": 0,
                    },
                },
                "required": ["command", "directory"],
            },
        )

    async def run_tool(self, arguments: dict) -> Sequence[TextContent]:
        """Execute the shell command with the given arguments"""
        command = arguments.get("command", [])
        stdin = arguments.get("stdin")
        directory = arguments.get("directory", "/tmp")  # default to /tmp for safety
        timeout = arguments.get("timeout")

        if not command:
            raise ValueError("No command provided")

        if not isinstance(command, list):
            raise ValueError("'command' must be an array")

        # Make sure directory exists
        if not directory:
            raise ValueError("Directory is required")

        content: list[TextContent] = []
        try:
            # Handle execution with timeout
            try:
                result = await asyncio.wait_for(
                    self.executor.execute(
                        command, directory, stdin, None
                    ),  # Pass None for timeout
                    timeout=timeout,
                )
            except asyncio.TimeoutError as e:
                raise ValueError("Command execution timed out") from e

            if result.get("error"):
                raise ValueError(result["error"])

            # Add stdout if present
            if result.get("stdout"):
                content.append(TextContent(type="text", text=result["stdout"]))

            # Add stderr if present (filter out specific messages)
            stderr = result.get("stderr")
            if stderr and "cannot set terminal process group" not in stderr:
                content.append(TextContent(type="text", text=stderr))

        except asyncio.TimeoutError as e:
            raise ValueError(f"Command timed out after {timeout} seconds") from e

        return content


# Initialize tool handlers
tool_handler = ExecuteToolHandler()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [tool_handler.get_tool_description()]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls"""
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
    """Main entry point for the MCP shell server"""
    logger.info(f"Starting MCP shell server v{__version__}")
    try:
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream, write_stream, app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
