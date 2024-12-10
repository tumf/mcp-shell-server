import logging
import traceback
from collections.abc import Sequence
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from .shell_executor import ShellExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-shell-server")

app = Server("mcp-shell-server")


class ExecuteToolHandler:
    """Handler for shell command execution"""

    name = "execute"
    description = "Execute a shell command"

    def __init__(self):
        self.executor = ShellExecutor()

    def get_tool_description(self) -> Tool:
        """Get the tool description for the execute command"""
        return Tool(
            name=self.name,
            description=self.description,
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
                },
                "required": ["command"],
            },
        )

    async def run_tool(self, arguments: dict) -> Sequence[TextContent]:
        """Execute the shell command with the given arguments"""
        command = arguments.get("command", [])
        stdin = arguments.get("stdin")

        if not command:
            raise ValueError("No command provided")

        result = await self.executor.execute(command, stdin)

        # Raise error if command execution failed
        if result.get("error"):
            raise RuntimeError(result["error"])

        # Convert executor result to TextContent sequence
        content: list[TextContent] = []

        if result.get("stdout"):
            content.append(TextContent(type="text", text=result["stdout"]))
        if result.get("stderr"):
            content.append(TextContent(type="text", text=result["stderr"]))

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
        logger.error(f"Error during call_tool: {str(e)}")
        raise RuntimeError(f"Error executing command: {str(e)}") from e


async def main() -> None:
    """Main entry point for the MCP shell server"""
    try:
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream, write_stream, app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise
