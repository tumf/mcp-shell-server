import os
from typing import Optional


class DirectoryManager:
    """
    Manages directory validation and path operations for shell command execution.
    """

    def validate_directory(self, directory: Optional[str]) -> None:
        """
        Validate if the directory exists and is accessible.

        Args:
            directory (Optional[str]): Directory path to validate

        Raises:
            ValueError: If the directory doesn't exist, not absolute or is not accessible
        """
        # make directory required
        if directory is None:
            raise ValueError("Directory is required")

        # verify directory is absolute path
        if not os.path.isabs(directory):
            raise ValueError(f"Directory must be an absolute path: {directory}")

        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")

        if not os.path.isdir(directory):
            raise ValueError(f"Not a directory: {directory}")

        if not os.access(directory, os.R_OK | os.X_OK):
            raise ValueError(f"Directory is not accessible: {directory}")

    def get_absolute_path(self, path: str, base_directory: Optional[str] = None) -> str:
        """
        Get absolute path by joining base directory with path if path is relative.

        Args:
            path (str): The path to make absolute
            base_directory (Optional[str]): Base directory to join with relative paths

        Returns:
            str: Absolute path
        """
        if os.path.isabs(path):
            return path
        if not base_directory:
            return os.path.abspath(path)
        return os.path.join(base_directory, path)
