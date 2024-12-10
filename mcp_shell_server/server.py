from mcp.server.stdio import stdio_server
from .shell_executor import ShellExecutor


class ShellServer:
    def __init__(self):
        self.executor = ShellExecutor()

    async def handle(self, args: dict) -> dict:
        command = args.get("command", [])
        stdin = args.get("stdin")

        if not command:
            return {"error": "No command provided", "status": 1}

        return await self.executor.execute(command, stdin)


def main():
    server = ShellServer()
    stdio_server(server.handle)
