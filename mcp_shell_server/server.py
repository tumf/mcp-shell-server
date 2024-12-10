import asyncio
from mcp.server.stdio import stdio_server
from .shell_executor import ShellExecutor

class ShellServer:
    """
    MCP server that executes shell commands in a secure manner.
    Only commands listed in the ALLOW_COMMANDS environment variable can be executed.
    """
    
    def __init__(self):
        self.executor = ShellExecutor()

    async def handle(self, args: dict) -> dict:
        """
        Handle incoming MCP requests to execute shell commands.
        
        Args:
            args (dict): Arguments containing the command to execute and optional stdin
            
        Returns:
            dict: Execution results including stdout, stderr, status code, and execution time
        """
        command = args.get("command", [])
        stdin = args.get("stdin")
        
        if not command:
            return {
                "error": "No command provided",
                "status": 1
            }
        
        return await self.executor.execute(command, stdin)

def main():
    """Entry point for the MCP shell server"""
    server = ShellServer()
    stdio_server(server.handle)