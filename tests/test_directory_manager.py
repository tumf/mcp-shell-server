"""Tests for directory_manager module."""

import os

import pytest

from mcp_shell_server.directory_manager import DirectoryManager


def test_validate_directory(tmp_path):
    """Test directory validation."""
    manager = DirectoryManager()
    test_dir = str(tmp_path)

    # Valid directory
    manager.validate_directory(test_dir)

    # None directory
    with pytest.raises(ValueError, match="Directory is required"):
        manager.validate_directory(None)

    # Relative path
    with pytest.raises(ValueError, match="Directory must be an absolute path"):
        manager.validate_directory("relative/path")

    # Non-existent directory
    nonexistent = os.path.join(test_dir, "nonexistent")
    with pytest.raises(ValueError, match="Directory does not exist"):
        manager.validate_directory(nonexistent)

    # Not a directory (create a file)
    test_file = os.path.join(test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")
    with pytest.raises(ValueError, match="Not a directory"):
        manager.validate_directory(test_file)


def test_get_absolute_path(tmp_path):
    """Test absolute path resolution."""
    manager = DirectoryManager()
    test_dir = str(tmp_path)

    # Already absolute path
    abs_path = os.path.join(test_dir, "test")
    assert manager.get_absolute_path(abs_path) == abs_path

    # Relative path without base directory
    rel_path = "test/path"
    expected = os.path.abspath(rel_path)
    assert manager.get_absolute_path(rel_path) == expected

    # Relative path with base directory
    rel_path = "test/path"
    expected = os.path.join(test_dir, rel_path)
    assert manager.get_absolute_path(rel_path, test_dir) == expected
