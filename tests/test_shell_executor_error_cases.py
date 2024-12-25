import asyncio
import os
import tempfile

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


def clear_env(monkeypatch):
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Return the real path to handle macOS /private/tmp symlink
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_empty_command_validation():
    """Test validation of empty commands"""
    executor = ShellExecutor()

    # Test empty command
    with pytest.raises(ValueError, match="Empty command"):
        executor._validate_command([])


@pytest.mark.asyncio
async def test_no_allowed_commands_validation(monkeypatch):
    """Test validation when no commands are allowed"""
    # Remove ALLOW_COMMANDS
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)

    executor = ShellExecutor()
    with pytest.raises(
        ValueError,
        match="No commands are allowed. Please set ALLOW_COMMANDS environment variable.",
    ):
        executor.validator.validate_command(["any_command"])


@pytest.mark.asyncio
async def test_shell_operator_validation():
    """Test validation of shell operators"""
    executor = ShellExecutor()

    operators = [";", "&&", "||", "|"]
    for op in operators:
        # Test shell operator validation
        with pytest.raises(ValueError, match=f"Unexpected shell operator: {op}"):
            executor._validate_no_shell_operators(op)


@pytest.mark.asyncio
async def test_process_execution_timeout(monkeypatch, temp_test_dir):
    """Test process execution timeout handling"""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    executor = ShellExecutor()

    # Test process timeout
    command = ["sleep", "5"]
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(executor.execute(command, temp_test_dir), timeout=0.1)


@pytest.mark.asyncio
async def test_process_failure(monkeypatch, temp_test_dir):
    """Test handling of process execution failure"""
    monkeypatch.setenv("ALLOW_COMMANDS", "false")
    executor = ShellExecutor()

    # false command always returns exit code 1
    result = await executor.execute(["false"], temp_test_dir)
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_directory_validation():
    """Test directory validation"""
    executor = ShellExecutor()

    # Test missing directory
    with pytest.raises(ValueError, match="Directory is required"):
        executor._validate_directory(None)

    # Test relative path
    with pytest.raises(ValueError, match="Directory must be an absolute path"):
        executor._validate_directory("relative/path")

    # Test non-existent directory
    with pytest.raises(ValueError, match="Directory does not exist"):
        executor._validate_directory("/nonexistent/directory")
