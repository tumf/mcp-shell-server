import asyncio
import os
import shlex
import time
from typing import Any, Dict, List, Optional


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
        Get the set of allowed commands from environment variables.
        Checks both ALLOW_COMMANDS and ALLOWED_COMMANDS.
        """
        allow_commands = os.environ.get("ALLOW_COMMANDS", "")
        allowed_commands = os.environ.get("ALLOWED_COMMANDS", "")

        # Combine and deduplicate commands from both environment variables
        commands = allow_commands + "," + allowed_commands
        return {cmd.strip() for cmd in commands.split(",") if cmd.strip()}

    def _clean_command(self, command: List[str]) -> List[str]:
        """
        Clean command by trimming whitespace from each part.

        Args:
            command (List[str]): Original command and its arguments

        Returns:
            List[str]: Cleaned command with trimmed whitespace
        """
        return [arg.strip() for arg in command if arg.strip()]

    def _create_shell_command(self, command: List[str]) -> str:
        """
        Create a shell command string from a list of arguments.
        Properly escapes all arguments to prevent shell injection.

        Args:
            command (List[str]): Command and its arguments

        Returns:
            str: Shell-safe command string
        """
        return " ".join(shlex.quote(arg) for arg in command)

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

    def _validate_directory(self, directory: Optional[str]) -> None:
        """
        Validate if the directory exists and is accessible.

        Args:
            directory (Optional[str]): Directory path to validate

        Raises:
            ValueError: If the directory doesn't exist or is not accessible
        """
        if directory is None:
            return

        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")
        if not os.path.isdir(directory):
            raise ValueError(f"Not a directory: {directory}")
        if not os.access(directory, os.R_OK | os.X_OK):
            raise ValueError(f"Directory is not accessible: {directory}")

    def get_allowed_commands(self) -> list[str]:
        """Get the allowed commands"""
        return list(self._get_allowed_commands())

    async def execute(
        self,
        command: List[str],
        stdin: Optional[str] = None,
        directory: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a shell command with optional stdin input and working directory.

        Args:
            command (List[str]): Command and its arguments
            stdin (Optional[str]): Input to be passed to the command via stdin
            directory (Optional[str]): Working directory for command execution
            timeout (Optional[int]): Timeout for command execution in seconds

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
            self._validate_directory(directory)
        except ValueError as e:
            return {
                "error": str(e),
                "status": 1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": time.time() - start_time,
            }

        try:
            # Create shell command and execute it
            shell_command = self._create_shell_command(cleaned_command)
            process = await asyncio.create_subprocess_shell(
                shell_command,
                stdin=asyncio.subprocess.PIPE if stdin else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PATH": os.environ.get("PATH", "")},
                cwd=directory,  # Set working directory if specified
            )

            try:
                stdin_bytes = stdin.encode() if stdin else None
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=stdin_bytes), timeout=timeout
                )

                return {
                    "error": None,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "status": process.returncode,
                    "execution_time": time.time() - start_time,
                    "directory": directory,
                }

            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass

                return {
                    "error": f"Command timed out after {timeout} seconds",
                    "status": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
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
