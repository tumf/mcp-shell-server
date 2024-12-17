import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def executor():
    return ShellExecutor()


@pytest.mark.asyncio
async def test_basic_pipe_command(executor, monkeypatch):
    """Test basic pipe functionality with allowed commands"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    result = await executor.execute(["echo", "hello world", "|", "grep", "world"])
    assert result["status"] == 0
    assert result["stdout"].strip() == "hello world"


@pytest.mark.asyncio
async def test_invalid_pipe_command(executor, monkeypatch):
    """Test pipe command with non-allowed command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    result = await executor.execute(["echo", "hello", "|", "grep", "hello"])
    assert result["status"] == 1
    assert "Command not allowed: grep" in result["error"]
