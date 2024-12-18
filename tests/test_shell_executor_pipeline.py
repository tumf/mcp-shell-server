import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.mark.asyncio
async def test_pipeline_split():
    """Test pipeline command splitting functionality"""
    executor = ShellExecutor()

    # Test basic pipe command
    commands = executor._split_pipe_commands(["echo", "hello", "|", "grep", "h"])
    assert len(commands) == 2
    assert commands[0] == ["echo", "hello"]
    assert commands[1] == ["grep", "h"]

    # Test empty pipe sections
    commands = executor._split_pipe_commands(["|", "grep", "pattern"])
    assert len(commands) == 1
    assert commands[0] == ["grep", "pattern"]

    # Test multiple pipes
    commands = executor._split_pipe_commands(
        ["cat", "file.txt", "|", "grep", "pattern", "|", "wc", "-l"]
    )
    assert len(commands) == 3
    assert commands[0] == ["cat", "file.txt"]
    assert commands[1] == ["grep", "pattern"]
    assert commands[2] == ["wc", "-l"]

    # Test trailing pipe
    commands = executor._split_pipe_commands(["echo", "hello", "|"])
    assert len(commands) == 1
    assert commands[0] == ["echo", "hello"]


@pytest.mark.asyncio
async def test_pipeline_execution_success():
    """Test successful pipeline execution with proper return value"""
    executor = ShellExecutor()
    import os

    os.environ["ALLOWED_COMMANDS"] = "echo,grep"

    result = await executor.execute(
        ["echo", "hello world", "|", "grep", "world"], directory="/tmp", timeout=5
    )

    assert result["error"] is None
    assert result["status"] == 0
    assert "world" in result["stdout"]
    assert "execution_time" in result
    assert result["directory"] == "/tmp"
