import pytest
from mcp.types import TextContent, Tool
from mcp_shell_server.server import call_tool, list_tools, tool_handler


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
    assert tool.inputSchema["required"] == ["command"]


@pytest.mark.asyncio
async def test_call_tool_valid_command(monkeypatch):
    """Test execution of a valid command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    result = await call_tool("execute", {
        "command": ["echo", "hello world"]
    })
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert result[0].text.strip() == "hello world"


@pytest.mark.asyncio
async def test_call_tool_with_stdin(monkeypatch):
    """Test command execution with stdin"""
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    result = await call_tool("execute", {
        "command": ["cat"],
        "stdin": "test input"
    })
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert result[0].text.strip() == "test input"


@pytest.mark.asyncio
async def test_call_tool_invalid_command(monkeypatch):
    """Test execution of an invalid command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("execute", {
            "command": ["invalid_command"]
        })
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
        await call_tool("execute", {
            "command": []
        })
    assert "No command provided" in str(excinfo.value)