"""Test pipeline execution and cleanup scenarios."""

import os
import tempfile

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


def clear_env(monkeypatch):
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)


@pytest.fixture
def executor():
    return ShellExecutor()


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Return the real path to handle macOS /private/tmp symlink
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_pipeline_split(executor):
    """Test pipeline command splitting functionality"""
    # Test basic pipe command
    commands = executor.preprocessor.split_pipe_commands(
        ["echo", "hello", "|", "grep", "h"]
    )
    assert len(commands) == 2
    assert commands[0] == ["echo", "hello"]
    assert commands[1] == ["grep", "h"]

    # Test empty pipe sections
    commands = executor.preprocessor.split_pipe_commands(["|", "grep", "pattern"])
    assert len(commands) == 1
    assert commands[0] == ["grep", "pattern"]

    # Test multiple pipes
    commands = executor.preprocessor.split_pipe_commands(
        ["cat", "file.txt", "|", "grep", "pattern", "|", "wc", "-l"]
    )
    assert len(commands) == 3
    assert commands[0] == ["cat", "file.txt"]
    assert commands[1] == ["grep", "pattern"]
    assert commands[2] == ["wc", "-l"]

    # Test trailing pipe
    commands = executor.preprocessor.split_pipe_commands(["echo", "hello", "|"])
    assert len(commands) == 1
    assert commands[0] == ["echo", "hello"]


@pytest.mark.asyncio
async def test_pipeline_execution_success(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Test successful pipeline execution with proper return value"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    # Set up mock for pipeline execution
    expected_output = b"mocked pipeline output\n"
    mock_process_manager.execute_pipeline.return_value = (expected_output, b"", 0)

    result = await shell_executor_with_mock.execute(
        ["echo", "hello world", "|", "grep", "world"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].rstrip() == "mocked pipeline output"
    assert "execution_time" in result


@pytest.mark.asyncio
async def test_pipeline_cleanup_and_timeouts(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Test cleanup of processes in pipelines and timeout handling"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    # Mock timeout behavior for pipeline
    mock_process_manager.execute_pipeline.side_effect = TimeoutError(
        "Command timed out after 1 seconds"
    )

    result = await shell_executor_with_mock.execute(
        ["echo", "test", "|", "grep", "test"],  # Use a pipeline command
        temp_test_dir,
        timeout=1,
    )

    assert result["status"] == -1
    assert "timed out" in result["error"].lower()

    # Verify cleanup was called
    mock_process_manager.cleanup_processes.assert_called_once()
