import os
import tempfile

import pytest
from mcp.types import TextContent, Tool

from mcp_shell_server.server import call_tool, list_tools


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Return the real path to handle macOS /private/tmp symlink
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_list_tools():
    """Test listing of available tools"""
    tools = await list_tools()
    assert len(tools) == 1
    tool = tools[0]
    assert isinstance(tool, Tool)
    assert tool.name == "execute"
    assert tool.description
    assert tool.inputSchema["type"] == "object"
    assert "command" in tool.inputSchema["properties"]
    assert "stdin" in tool.inputSchema["properties"]
    assert "directory" in tool.inputSchema["properties"]  # New assertion
    assert tool.inputSchema["required"] == ["command"]


@pytest.mark.asyncio
async def test_call_tool_valid_command(monkeypatch):
    """Test execution of a valid command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    result = await call_tool("execute", {"command": ["echo", "hello world"]})
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert result[0].text.strip() == "hello world"


@pytest.mark.asyncio
async def test_call_tool_with_stdin(monkeypatch):
    """Test command execution with stdin"""
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    result = await call_tool("execute", {"command": ["cat"], "stdin": "test input"})
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert result[0].text.strip() == "test input"


@pytest.mark.asyncio
async def test_call_tool_invalid_command(monkeypatch):
    """Test execution of an invalid command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("execute", {"command": ["invalid_command"]})
    assert "Command not allowed: invalid_command" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_unknown_tool():
    """Test calling an unknown tool"""
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("unknown_tool", {})
    assert "Unknown tool: unknown_tool" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_invalid_arguments():
    """Test calling a tool with invalid arguments"""
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("execute", "not a dict")
    assert "Arguments must be a dictionary" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_empty_command():
    """Test execution with empty command"""
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("execute", {"command": []})
    assert "No command provided" in str(excinfo.value)


# New tests for directory functionality
@pytest.mark.asyncio
async def test_call_tool_with_directory(temp_test_dir, monkeypatch):
    """Test command execution in a specific directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd")
    result = await call_tool("execute", {
        "command": ["pwd"],
        "directory": temp_test_dir
    })
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert result[0].text.strip() == temp_test_dir


@pytest.mark.asyncio
async def test_call_tool_with_file_operations(temp_test_dir, monkeypatch):
    """Test file operations in a specific directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls,cat")

    # Create a test file
    test_file = os.path.join(temp_test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    # Test ls command
    result = await call_tool("execute", {
        "command": ["ls"],
        "directory": temp_test_dir
    })
    assert "test.txt" in result[0].text

    # Test cat command
    result = await call_tool("execute", {
        "command": ["cat", "test.txt"],
        "directory": temp_test_dir
    })
    assert result[0].text.strip() == "test content"


@pytest.mark.asyncio
async def test_call_tool_with_nonexistent_directory(monkeypatch):
    """Test command execution with a non-existent directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("execute", {
            "command": ["ls"],
            "directory": "/nonexistent/directory"
        })
    assert "Directory does not exist: /nonexistent/directory" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_with_file_as_directory(temp_test_dir, monkeypatch):
    """Test command execution with a file specified as directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")

    # Create a test file
    test_file = os.path.join(temp_test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("execute", {
            "command": ["ls"],
            "directory": test_file
        })
    assert f"Not a directory: {test_file}" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_with_nested_directory(temp_test_dir, monkeypatch):
    """Test command execution in a nested directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd,mkdir")

    # Create a nested directory
    nested_dir = os.path.join(temp_test_dir, "nested")
    os.mkdir(nested_dir)
    nested_real_path = os.path.realpath(nested_dir)

    result = await call_tool("execute", {
        "command": ["pwd"],
        "directory": nested_dir
    })
    assert result[0].text.strip() == nested_real_path
