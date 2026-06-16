"""IO redirection handling module for MCP Shell Server."""

import asyncio
import os
from typing import IO, Any, Dict, List, Optional, Tuple, Union


class IORedirectionHandler:
    """Handles contained input/output redirection for argv commands."""

    def validate_redirection_syntax(self, command: List[str]) -> None:
        """Validate the syntax of redirection operators in the command."""
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
        """Remove redirection operators from argv and return redirect metadata."""
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

    def _resolve_contained_path(self, directory: Optional[str], user_path: str) -> str:
        if directory is None:
            raise ValueError("Directory is required for redirection")
        if not user_path:
            raise ValueError("Redirection path must not be empty")
        if os.path.isabs(user_path):
            raise ValueError("Redirection path must be relative")

        path_parts = user_path.split(os.sep)
        if os.altsep:
            path_parts.extend(user_path.split(os.altsep))
        if ".." in path_parts:
            raise ValueError("Redirection path must not contain parent traversal")

        base = os.path.realpath(directory)
        target = os.path.realpath(os.path.join(base, user_path))
        try:
            if os.path.commonpath([base, target]) != base:
                raise ValueError("Redirection path escapes working directory")
        except ValueError as e:
            if "escapes" in str(e):
                raise
            raise ValueError("Redirection path escapes working directory") from e
        return target

    async def setup_redirects(
        self,
        redirects: Dict[str, Union[None, str, bool]],
        directory: Optional[str] = None,
    ) -> Dict[str, Union[IO[Any], int, str, None]]:
        """Set up file handles for contained redirections."""
        handles: Dict[str, Union[IO[Any], int, str, None]] = {}

        if redirects["stdin"]:
            path = self._resolve_contained_path(directory, str(redirects["stdin"]))
            try:
                with open(path, "r") as file:
                    handles["stdin"] = asyncio.subprocess.PIPE
                    handles["stdin_data"] = file.read()
            except (FileNotFoundError, IOError) as e:
                raise ValueError("Failed to open input file") from e

        if redirects["stdout"]:
            path = self._resolve_contained_path(directory, str(redirects["stdout"]))
            mode = "a" if redirects.get("stdout_append") else "w"
            try:
                handles["stdout"] = open(path, mode)
            except (IOError, PermissionError) as e:
                raise ValueError(f"Failed to open output file: {e}") from e
        else:
            handles["stdout"] = asyncio.subprocess.PIPE

        handles["stderr"] = asyncio.subprocess.PIPE

        return handles

    async def cleanup_handles(
        self, handles: Dict[str, Union[IO[Any], int, None]]
    ) -> None:
        """Clean up file handles after command execution."""
        for key in ["stdout", "stderr"]:
            handle = handles.get(key)
            if handle and hasattr(handle, "close") and not isinstance(handle, int):
                try:
                    handle.close()
                except (IOError, ValueError):
                    pass
