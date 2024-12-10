import os
import asyncio
from typing import Dict, List, Optional, Any
from mcp_core import MCPServer, MCPRequest
from .shell_executor import ShellExecutor

class ShellServer(MCPServer):
    def __init__(self):
        super().__init__()
        self.executor = ShellExecutor()

    async def handle_request(self, request: MCPRequest) -> Dict[str, Any]:
        command: List[str] = request.args.get("command", [])
        stdin: Optional[str] = request.args.get("stdin")
        
        if not command:
            return {
                "error": "No command provided",
                "status": 1
            }
        
        result = await self.executor.execute(command, stdin)
        return result

def main():
    server = ShellServer()
    server.run()