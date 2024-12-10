import os
import time
import asyncio
from typing import Dict, List, Optional, Any

class ShellExecutor:
    def __init__(self):
        # Allow whitespace in ALLOW_COMMANDS and trim each command
        allow_commands = os.environ.get("ALLOW_COMMANDS", "")
        self.allowed_commands = set(cmd.strip() for cmd in allow_commands.split(",") if cmd.strip())

    def _validate_command(self, command: List[str]) -> None:
        if not command:
            raise ValueError("Empty command")

        # Check first command
        if command[0] not in self.allowed_commands:
            raise ValueError(f"Command not allowed: {command[0]}")

        # Check for shell operators and subsequent commands
        for arg in command[1:]:
            if arg in [";", "&&", "||", "|"]:
                next_cmd_idx = command.index(arg) + 1
                if next_cmd_idx < len(command):
                    next_cmd = command[next_cmd_idx]
                    if next_cmd not in self.allowed_commands:
                        raise ValueError(f"Command not allowed: {next_cmd}")

    async def execute(self, command: List[str], stdin: Optional[str] = None) -> Dict[str, Any]:
        try:
            self._validate_command(command)
        except ValueError as e:
            return {
                "error": str(e),
                "status": 1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": 0
            }

        start_time = time.time()
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE if stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        if stdin:
            stdout, stderr = await process.communicate(stdin.encode())
        else:
            stdout, stderr = await process.communicate()

        execution_time = time.time() - start_time

        return {
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
            "status": process.returncode,
            "execution_time": execution_time
        }