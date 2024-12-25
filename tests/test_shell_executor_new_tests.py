import os
import tempfile

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_redirection_validation():
    """Test validation of input/output redirection"""
    executor = ShellExecutor()

    # Missing path for output redirection
    with pytest.raises(ValueError, match="Missing path for output redirection"):
        executor.io_handler.process_redirections(["echo", "test", ">"])

    # Invalid redirection target (operator)
    with pytest.raises(
        ValueError, match="Invalid redirection syntax: consecutive operators"
    ):
        executor.io_handler.process_redirections(["echo", "test", ">", ">"])

    # Missing path for input redirection
    with pytest.raises(ValueError, match="Missing path for input redirection"):
        executor.io_handler.process_redirections(["cat", "<"])

    # Missing path for output redirection after input redirection
    with pytest.raises(ValueError, match="Missing path for output redirection"):
        executor.io_handler.process_redirections(["cat", "<", "input.txt", ">"])


@pytest.mark.asyncio
async def test_directory_validation(monkeypatch):
    """Test directory validation"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    executor = ShellExecutor()

    # Directory validation is performed in the _validate_directory method
    with pytest.raises(ValueError, match="Directory is required"):
        executor.directory_manager.validate_directory(None)

    # Directory is not absolute path
    with pytest.raises(ValueError, match="Directory must be an absolute path"):
        executor.directory_manager.validate_directory("relative/path")

    # Directory does not exist
    with pytest.raises(ValueError, match="Directory does not exist"):
        executor.directory_manager.validate_directory("/path/does/not/exist")


@pytest.mark.asyncio
async def test_process_timeout(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Test process timeout handling"""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    # Mock timeout behavior
    mock_process_manager.execute_with_timeout.side_effect = TimeoutError(
        "Command timed out after 1 seconds"
    )

    # Process timeout test
    result = await shell_executor_with_mock.execute(
        command=["sleep", "5"], directory=temp_test_dir, timeout=1
    )
    assert result["error"] == "Command timed out after 1 seconds"
    assert result["status"] == -1
