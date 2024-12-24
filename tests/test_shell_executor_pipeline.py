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
async def test_pipeline_execution_success(executor, temp_test_dir, monkeypatch):
    """Test successful pipeline execution with proper return value"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOWED_COMMANDS", "echo,grep")

    result = await executor.execute(
        ["echo", "hello world", "|", "grep", "world"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    assert result["status"] == 0
    assert "world" in result["stdout"]
    assert "execution_time" in result


@pytest.mark.asyncio
async def test_pipeline_cleanup_and_timeouts(executor, temp_test_dir, monkeypatch):
    """Test cleanup of processes in pipelines and timeout handling"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "cat,tr,head,sleep")

    # Test pipeline with early termination
    test_file = os.path.join(temp_test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test\n" * 1000)

    result = await executor.execute(
        ["cat", test_file, "|", "tr", "[:lower:]", "[:upper:]", "|", "head", "-n", "1"],
        temp_test_dir,
        timeout=2,
    )
    assert result["status"] == 0
    assert result["stdout"].strip() == "TEST"

    # Test timeout handling in pipeline
    result = await executor.execute(["sleep", "5"], temp_test_dir, timeout=1)
    assert result["status"] == -1
    assert "timed out" in result["error"].lower()  # タイムアウトエラーの確認
