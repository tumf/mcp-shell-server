import pytest
from mcp_shell_server.server import ShellServer

@pytest.fixture
def server():
    return ShellServer()

@pytest.mark.asyncio
async def test_server_handle_empty_request(server):
    response = await server.handle({})
    assert response["error"] == "No command provided"
    assert response["status"] == 1

@pytest.mark.asyncio
async def test_server_handle_valid_command(server, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    response = await server.handle({
        "command": ["echo", "hello world"]
    })
    assert response["stdout"].strip() == "hello world"
    assert response["status"] == 0
    assert "execution_time" in response

@pytest.mark.asyncio
async def test_server_handle_stdin(server, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    response = await server.handle({
        "command": ["cat"],
        "stdin": "test input"
    })
    assert response["stdout"].strip() == "test input"
    assert response["status"] == 0

@pytest.mark.asyncio
async def test_server_handle_invalid_command(server, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    response = await server.handle({
        "command": ["invalid_command"]
    })
    assert response["error"] == "Command not allowed: invalid_command"
    assert response["status"] == 1