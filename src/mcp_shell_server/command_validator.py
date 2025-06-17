"""
Provides validation for shell commands and ensures they are allowed to be executed.
"""

import os
from typing import Dict, List


class CommandValidator:
    """
    Validates shell commands against a whitelist and checks for unsafe operators.
    """

    def __init__(self):
        """
        Initialize the validator.
        """
        pass

    def _get_allowed_commands(self) -> set[str]:
        """Get the set of allowed commands from environment variables"""
        allow_commands = os.environ.get("ALLOW_COMMANDS", "")
        allowed_commands = os.environ.get("ALLOWED_COMMANDS", "")
        commands = allow_commands + "," + allowed_commands
        return {cmd.strip() for cmd in commands.split(",") if cmd.strip()}

    def get_allowed_commands(self) -> list[str]:
        """Get the list of allowed commands from environment variables"""
        return list(self._get_allowed_commands())

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is in the allowed list"""
        cmd = command.strip()
        return cmd in self._get_allowed_commands()

    def validate_no_shell_operators(self, cmd: str) -> None:
        """
        Validate that the command does not contain shell operators.

        Args:
            cmd (str): Command to validate

        Raises:
            ValueError: If the command contains shell operators
        """
        if cmd in [";", "&&", "||", "|"]:
            raise ValueError(f"Unexpected shell operator: {cmd}")

    def validate_pipeline(self, commands: List[str]) -> Dict[str, str]:
        """
        Validate pipeline command and ensure all parts are allowed.

        Args:
            commands (List[str]): List of commands to validate

        Returns:
            Dict[str, str]: Error message if validation fails, empty dict if success

        Raises:
            ValueError: If validation fails
        """
        current_cmd: List[str] = []

        for token in commands:
            if token == "|":
                if not current_cmd:
                    raise ValueError("Empty command before pipe operator")
                if not self.is_command_allowed(current_cmd[0]):
                    raise ValueError(f"Command not allowed: {current_cmd[0]}")
                current_cmd = []
            elif token in [";", "&&", "||"]:
                raise ValueError(f"Unexpected shell operator in pipeline: {token}")
            else:
                current_cmd.append(token)

        if current_cmd:
            if not self.is_command_allowed(current_cmd[0]):
                raise ValueError(f"Command not allowed: {current_cmd[0]}")

        return {}

    def validate_command(self, command: List[str]) -> None:
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
        if not self.is_command_allowed(cleaned_cmd):
            raise ValueError(f"Command not allowed: {cleaned_cmd}")
