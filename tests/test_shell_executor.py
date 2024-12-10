import os
import pytest
from mcp_shell_server.shell_executor import ShellExecutor

@pytest.fixture
def executor():
    return ShellExecutor()

@pytest.mark.asyncio
async def test_basic_command_execution(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls")
    result = await executor.execute(["echo", "hello"])
    assert result["stdout"].strip() == "hello"
    assert result["status"] == 0
    assert result["stderr"] == ""
    assert "execution_time" in result

@pytest.mark.asyncio
async def test_stdin_input(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    result = await executor.execute(["cat"], stdin="hello world")
    assert result["stdout"].strip() == "hello world"
    assert result["status"] == 0

@pytest.mark.asyncio
async def test_command_not_allowed(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")
    result = await executor.execute(["rm", "-rf", "/"])
    assert result["error"] == "Command not allowed: rm"
    assert result["status"] == 1

@pytest.mark.asyncio
async def test_empty_command(executor):
    result = await executor.execute([])
    assert result["error"] == "Empty command"
    assert result["status"] == 1

@pytest.mark.asyncio
async def test_command_with_space_in_allow_commands(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "ls, echo ,cat")
    result = await executor.execute(["echo", "test"])
    assert result["stdout"].strip() == "test"
    assert result["status"] == 0

@pytest.mark.asyncio
async def test_multiple_commands_with_operator(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls")
    result = await executor.execute(["echo", "hello", ";", "ls", "-l"])
    assert "Command not allowed: ls" in result["error"]
    assert result["status"] == 1

@pytest.mark.asyncio
async def test_command_with_error_output(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")
    result = await executor.execute(["ls", "/nonexistent"])
    assert result["stderr"] != ""
    assert result["status"] != 0