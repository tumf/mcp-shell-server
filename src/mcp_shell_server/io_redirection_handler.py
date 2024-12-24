"""IO redirection handling module for MCP Shell Server."""

import asyncio
import logging
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
    ) -> Tuple[List[str], Dict[str, Union[Optional[str], bool]]]:
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
        redirects: Dict[str, Union[Optional[str], bool]] = {
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
                path = command[i + 1]
                if path in [">", ">>", "<"]:
                    raise ValueError("Invalid redirection syntax")
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
                    raise ValueError("Invalid redirection syntax")
                redirects["stdin"] = path
                i += 2
                continue

            cmd.append(token)
            i += 1

        return cmd, redirects

    async def setup_redirects(
        self,
        redirects: Dict[str, Union[Optional[str], bool]],
        directory: Optional[str] = None,
    ) -> Dict[str, Union[IO[Any], int, str, None]]:
        """
        Set up file handles for redirections.

        Args:
            redirects (Dict[str, Union[Optional[str], bool]]): Redirection configuration
            directory (Optional[str]): Working directory for file paths

        Returns:
            Dict[str, Union[IO[Any], int, str, None]]: File handles for subprocess

        Raises:
            ValueError: If there are issues opening the files
        """
        handles: Dict[str, Union[IO[Any], int, str, None]] = {}

        # Initialize default handles
        handles["stdout"] = asyncio.subprocess.PIPE
        handles["stderr"] = asyncio.subprocess.PIPE

        # Handle input redirection
        stdin_path = redirects["stdin"]
        if isinstance(stdin_path, str):
            path = self._resolve_path(directory, stdin_path)
            try:
                with open(path, "r") as file:
                    handles["stdin"] = asyncio.subprocess.PIPE
                    handles["stdin_data"] = file.read()
            except (FileNotFoundError, IOError) as e:
                raise ValueError("Failed to open input file") from e

        # Handle output redirection
        stdout_path = redirects.get("stdout")
        if isinstance(stdout_path, str):
            path = self._resolve_path(directory, stdout_path)
            mode = "a" if redirects["stdout_append"] else "w"
            try:
                handles["stdout"] = open(path, mode)
            except (FileNotFoundError, IOError) as e:
                raise ValueError("Failed to open output file") from e

        return handles

    def _resolve_path(self, directory: Optional[str], path: str) -> str:
        """Resolves a file path, considering the working directory."""
        return os.path.join(directory or "", str(path)) if directory else str(path)

    async def cleanup_handles(
        self, handles: Dict[str, Union[IO[Any], int, None]]
    ) -> None:
        """
        Clean up file handles after command execution.

        Args:
            handles (Dict[str, Union[IO[Any], int, None]]): File handles to clean up

        Note:
            This method suppresses IOError and ValueError that might occur during cleanup,
            as they are not critical at this point.
        """
        errors = []
        for key in ["stdout", "stderr"]:
            handle = handles.get(key)
            if handle and hasattr(handle, "close") and not isinstance(handle, int):
                try:
                    handle.close()
                except (IOError, ValueError) as e:
                    # Log the error but continue with cleanup
                    errors.append(f"Error closing {key}: {str(e)}")
                    logging.warning(f"Error closing {key}: {str(e)}")
