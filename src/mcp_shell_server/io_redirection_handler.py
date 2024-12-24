"""IO redirection handling module for MCP Shell Server."""

import asyncio
import os
from typing import IO, Any, Dict, List, Optional, Tuple, Union


class IORedirectionHandler:
    """Handles input/output redirection for shell commands."""

    def validate_redirection_syntax(self, command: List[str]) -> None:
        """
        Validate the syntax of redirection operators in the command.

        Args:
            command (List[str]): Command and its arguments including redirections

        Raises:
            ValueError: If the redirection syntax is invalid
        """
        prev_token = None
        for token in command:
            if token in [">", ">>", "<"]:
                if prev_token and prev_token in [">", ">>", "<"]:
                    raise ValueError(
                        "Invalid redirection syntax: consecutive operators"
                    )
            prev_token = token

    def process_redirections(
        self, command: List[str]
    ) -> Tuple[List[str], Dict[str, Union[None, str, bool]]]:
        """
        Process input/output redirections in the command.

        Args:
            command (List[str]): Command and its arguments including redirections

        Returns:
            Tuple[List[str], Dict[str, Any]]: Processed command without redirections and
                                           redirection configuration

        Raises:
            ValueError: If the redirection syntax is invalid
        """
        self.validate_redirection_syntax(command)

        cmd = []
        redirects: Dict[str, Union[None, str, bool]] = {
            "stdin": None,
            "stdout": None,
            "stdout_append": False,
        }

        i = 0
        while i < len(command):
            token = command[i]

            # Output redirection
            if token in [">", ">>"]:
                if i + 1 >= len(command):
                    raise ValueError("Missing path for output redirection")
                if i + 1 < len(command) and command[i + 1] in [">", ">>", "<"]:
                    raise ValueError("Invalid redirection target: operator found")
                path = command[i + 1]
                redirects["stdout"] = path
                redirects["stdout_append"] = token == ">>"
                i += 2
                continue

            # Input redirection
            if token == "<":
                if i + 1 >= len(command):
                    raise ValueError("Missing path for input redirection")
                path = command[i + 1]
                if path in [">", ">>", "<"]:
                    raise ValueError("Invalid redirection target: operator found")
                redirects["stdin"] = path
                i += 2
                continue

            cmd.append(token)
            i += 1

        return cmd, redirects

    async def setup_redirects(
        self,
        redirects: Dict[str, Union[None, str, bool]],
        directory: Optional[str] = None,
    ) -> Dict[str, Union[IO[Any], int, str, None]]:
        """
        Set up file handles for redirections.

        Args:
            redirects (Dict[str, Union[None, str, bool]]): Redirection configuration
            directory (Optional[str]): Working directory for file paths

        Returns:
            Dict[str, Union[IO[Any], int, str, None]]: File handles for subprocess
        """
        handles: Dict[str, Union[IO[Any], int, str, None]] = {}

        # Handle input redirection
        if redirects["stdin"]:
            path = (
                os.path.join(directory or "", str(redirects["stdin"]))
                if directory and redirects["stdin"]
                else str(redirects["stdin"])
            )
            try:
                file = open(path, "r")
                handles["stdin"] = asyncio.subprocess.PIPE
                handles["stdin_data"] = file.read()
                file.close()
            except (FileNotFoundError, IOError) as e:
                raise ValueError("Failed to open input file") from e

        # Handle output redirection
        if redirects["stdout"]:
            path = (
                os.path.join(directory or "", str(redirects["stdout"]))
                if directory and redirects["stdout"]
                else str(redirects["stdout"])
            )
            mode = "a" if redirects["stdout_append"] else "w"
            try:
                handles["stdout"] = open(path, mode)
            except IOError as e:
                raise ValueError(f"Failed to open output file: {e}") from e
        else:
            handles["stdout"] = asyncio.subprocess.PIPE

        handles["stderr"] = asyncio.subprocess.PIPE

        return handles

    async def cleanup_handles(
        self, handles: Dict[str, Union[IO[Any], int, None]]
    ) -> None:
        """
        Clean up file handles after command execution.

        Args:
            handles (Dict[str, Union[IO[Any], int, None]]): File handles to clean up
        """
        for key in ["stdout", "stderr"]:
            handle = handles.get(key)
            if handle and hasattr(handle, "close") and not isinstance(handle, int):
                try:
                    handle.close()
                except (IOError, ValueError):
                    pass
