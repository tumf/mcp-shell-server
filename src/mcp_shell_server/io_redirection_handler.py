"""IO redirection handling module for MCP Shell Server."""

import asyncio
import logging
import os
from typing import IO, Any, Dict, List, Optional, Tuple, Union

LOGGER = logging.getLogger(__name__)


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

    def _resolve_redirection_path(self, target: str, directory: Optional[str]) -> str:
        """Resolve a redirection target and ensure it stays under directory."""
        if not directory:
            LOGGER.error("Redirection rejected because working directory is missing")
            raise ValueError("Redirection requires a working directory")

        if os.path.isabs(target):
            LOGGER.warning(
                "Rejected absolute redirection target",
                extra={"target": target, "directory": directory},
            )
            raise ValueError(
                "Redirection target must be relative to the working directory"
            )

        raw_parts = target.split(os.sep)
        if os.path.altsep:
            raw_parts = [
                part for value in raw_parts for part in value.split(os.path.altsep)
            ]
        if ".." in raw_parts:
            LOGGER.warning(
                "Rejected parent-traversal redirection target",
                extra={"target": target, "directory": directory},
            )
            raise ValueError("Redirection target cannot contain parent traversal")

        base_path = os.path.realpath(directory)
        candidate_path = os.path.realpath(os.path.join(base_path, target))
        try:
            common_path = os.path.commonpath([base_path, candidate_path])
        except ValueError as e:
            LOGGER.warning(
                "Rejected redirection target on a different path root",
                extra={"target": target, "directory": directory},
            )
            raise ValueError("Redirection target escapes the working directory") from e

        if common_path != base_path:
            LOGGER.warning(
                "Rejected redirection target escaping working directory",
                extra={
                    "target": target,
                    "directory": directory,
                    "resolved_target": candidate_path,
                    "resolved_directory": base_path,
                },
            )
            raise ValueError("Redirection target escapes the working directory")

        LOGGER.debug(
            "Resolved contained redirection target",
            extra={
                "target": target,
                "directory": directory,
                "resolved_target": candidate_path,
            },
        )
        return candidate_path

    async def setup_redirects(
        self,
        redirects: Dict[str, Union[None, str, bool]],
        directory: Optional[str] = None,
    ) -> Dict[str, Union[IO[Any], int, str, None]]:
        """Set up file handles for contained redirections."""
        handles: Dict[str, Union[IO[Any], int, str, None]] = {}

        if redirects["stdin"]:
            path = self._resolve_redirection_path(str(redirects["stdin"]), directory)
            LOGGER.info(
                "Opening contained input redirection",
                extra={"path": path, "directory": directory},
            )
            try:
                file = open(path, "r")
                try:
                    handles["stdin"] = asyncio.subprocess.PIPE
                    handles["stdin_data"] = file.read()
                finally:
                    file.close()
            except (FileNotFoundError, IOError) as e:
                LOGGER.error(
                    "Failed to open input redirection file",
                    exc_info=True,
                    extra={"path": path, "directory": directory},
                )
                raise ValueError("Failed to open input file") from e

        if redirects["stdout"]:
            path = self._resolve_redirection_path(str(redirects["stdout"]), directory)
            mode = "a" if redirects.get("stdout_append") else "w"
            LOGGER.info(
                "Opening contained output redirection",
                extra={"path": path, "directory": directory, "mode": mode},
            )
            try:
                handles["stdout"] = open(path, mode)
            except (IOError, PermissionError) as e:
                LOGGER.error(
                    "Failed to open output redirection file",
                    exc_info=True,
                    extra={"path": path, "directory": directory, "mode": mode},
                )
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
