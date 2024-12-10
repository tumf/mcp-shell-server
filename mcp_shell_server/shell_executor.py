import os
import time
import asyncio
from typing import Dict, List, Optional, Any


class ShellExecutor:
    """
    Executes shell commands in a secure manner by validating against a whitelist.
    """

    def __init__(self):
        """
        Initialize the executor. The allowed commands are read from ALLOW_COMMANDS
        environment variable during command validation, not at initialization.
        """
        pass

    def _get_allowed_commands(self) -> set:
        """
        Get the set of allowed commands from environment variable.

        Returns:
            set: Set of allowed command names
        """
        allow_commands = os.environ.get("ALLOW_COMMANDS", "")
        return {cmd.strip() for cmd in allow_commands.split(",") if cmd.strip()}

    def _clean_command(self, command: List[str]) -> List[str]:
        """
        Clean command by trimming whitespace from each part.

        Args:
            command (List[str]): Original command and its arguments

        Returns:
            List[str]: Cleaned command with trimmed whitespace
        """
        return [arg.strip() for arg in command if arg.strip()]

    def _validate_command(self, command: List[str]) -> None:
        """
        Validate if the command is allowed to be executed.

        Args:
            command (List[str]): Command and its arguments

        Raises:
            ValueError: If the command is empty, not allowed, or contains invalid shell operators
        """
        if not command:
            raise ValueError("Empty command")

        allowed_commands = self._get_allowed_commands()
        if not allowed_commands:
            raise ValueError(
                "No commands are allowed. Please set ALLOW_COMMANDS environment variable."
            )

        # Clean and check the first command
        cleaned_cmd = command[0].strip()
        if cleaned_cmd not in allowed_commands:
            raise ValueError(f"Command not allowed: {cleaned_cmd}")

        # Check for shell operators and validate subsequent commands
        for i, arg in enumerate(command[1:], start=1):
            cleaned_arg = arg.strip()
            if cleaned_arg in [";", "&&", "||", "|"]:
                if i + 1 >= len(command):
                    raise ValueError(f"Unexpected shell operator: {cleaned_arg}")
                next_cmd = command[i + 1].strip()
                if next_cmd not in allowed_commands:
                    raise ValueError(
                        f"Command not allowed after {cleaned_arg}: {next_cmd}"
                    )

    async def execute(
        self, command: List[str], stdin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a shell command with optional stdin input.

        Args:
            command (List[str]): Command and its arguments
            stdin (Optional[str]): Input to be passed to the command via stdin

        Returns:
            Dict[str, Any]: Execution result containing stdout, stderr, status code, and execution time.
                           If error occurs, result contains additional 'error' field.
        """
        start_time = time.time()

        try:
            # Clean command before validation and execution
            cleaned_command = self._clean_command(command)
            if not cleaned_command:
                raise ValueError("Empty command")

            self._validate_command(cleaned_command)
        except ValueError as e:
            return {
                "error": str(e),
                "status": 1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": time.time() - start_time,
            }

        try:
            process = await asyncio.create_subprocess_exec(
                cleaned_command[0],
                *cleaned_command[1:],
                stdin=asyncio.subprocess.PIPE if stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PATH": os.environ.get("PATH", "")},
            )

            stdin_bytes = stdin.encode() if stdin else None
            stdout, stderr = await process.communicate(input=stdin_bytes)

            return {
                "error": None,  # Set error field to None for success case
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "status": process.returncode,
                "execution_time": time.time() - start_time,
            }
        except FileNotFoundError:
            return {
                "error": f"Command not found: {cleaned_command[0]}",
                "status": 1,
                "stdout": "",
                "stderr": f"Command not found: {cleaned_command[0]}",
                "execution_time": time.time() - start_time,
            }
        except Exception as e:
            return {
                "error": str(e),
                "status": 1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": time.time() - start_time,
            }
