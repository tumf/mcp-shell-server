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


@pytest.mark.asyncio
async def test_tool_execution_timeout():
    """Test tool execution with timeout"""
    with pytest.raises(RuntimeError, match="Command execution timed out"):
        await call_tool(
            "shell_execute",
            {
                "command": ["sleep", "2"],
                "directory": "/tmp",
                "timeout": 1,
            },
        )
    tools = await list_tools()
    assert len(tools) == 1
    tool = tools[0]
    assert isinstance(tool, Tool)
    assert tool.name == "shell_execute"
    assert tool.description
    assert tool.inputSchema["type"] == "object"
    assert "command" in tool.inputSchema["properties"]
    assert "stdin" in tool.inputSchema["properties"]
    assert "directory" in tool.inputSchema["properties"]
    assert tool.inputSchema["required"] == ["command", "directory"]


@pytest.mark.asyncio
async def test_call_tool_valid_command(monkeypatch, temp_test_dir):
    """Test execution of a valid command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    result = await call_tool(
        "shell_execute",
        {"command": ["echo", "hello world"], "directory": temp_test_dir},
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert result[0].text.strip() == "hello world"


@pytest.mark.asyncio
async def test_call_tool_with_stdin(monkeypatch, temp_test_dir):
    """Test command execution with stdin"""
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    result = await call_tool(
        "shell_execute",
        {"command": ["cat"], "stdin": "test input", "directory": temp_test_dir},
    )
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert result[0].text.strip() == "test input"


@pytest.mark.asyncio
async def test_call_tool_invalid_command(monkeypatch, temp_test_dir):
    """Test execution of an invalid command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool(
            "shell_execute",
            {"command": ["invalid_command"], "directory": temp_test_dir},
        )
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
        await call_tool("shell_execute", "not a dict")
    assert "Arguments must be a dictionary" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_empty_command():
    """Test execution with empty command"""
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("shell_execute", {"command": []})
    assert "No command provided" in str(excinfo.value)


# New tests for directory functionality
@pytest.mark.asyncio
async def test_call_tool_with_directory(temp_test_dir, monkeypatch):
    """Test command execution in a specific directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd")
    result = await call_tool(
        "shell_execute", {"command": ["pwd"], "directory": temp_test_dir}
    )
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
    result = await call_tool(
        "shell_execute", {"command": ["ls"], "directory": temp_test_dir}
    )
    assert isinstance(result[0], TextContent)
    assert "test.txt" in result[0].text

    # Test cat command
    result = await call_tool(
        "shell_execute", {"command": ["cat", "test.txt"], "directory": temp_test_dir}
    )
    assert isinstance(result[0], TextContent)
    assert result[0].text.strip() == "test content"


@pytest.mark.asyncio
async def test_call_tool_with_nonexistent_directory(monkeypatch):
    """Test command execution with a non-existent directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool(
            "shell_execute", {"command": ["ls"], "directory": "/nonexistent/directory"}
        )
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
        await call_tool("shell_execute", {"command": ["ls"], "directory": test_file})
    assert f"Not a directory: {test_file}" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_with_nested_directory(temp_test_dir, monkeypatch):
    """Test command execution in a nested directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd,mkdir")

    # Create a nested directory
    nested_dir = os.path.join(temp_test_dir, "nested")
    os.mkdir(nested_dir)
    nested_real_path = os.path.realpath(nested_dir)

    result = await call_tool(
        "shell_execute", {"command": ["pwd"], "directory": nested_dir}
    )
    assert isinstance(result[0], TextContent)
    assert result[0].text.strip() == nested_real_path


@pytest.mark.asyncio
async def test_call_tool_with_timeout(monkeypatch):
    """Test command execution with timeout"""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    with pytest.raises(RuntimeError) as excinfo:
        await call_tool("shell_execute", {"command": ["sleep", "2"], "timeout": 1})
    assert "Command execution timed out" in str(excinfo.value)


@pytest.mark.asyncio
async def test_call_tool_completes_within_timeout(monkeypatch):
    """Test command that completes within timeout period"""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    result = await call_tool("shell_execute", {"command": ["sleep", "1"], "timeout": 2})
    assert len(result) == 0  # sleep command produces no output


@pytest.mark.asyncio
async def test_invalid_command_parameter():
    """Test error handling for invalid command parameter"""
    with pytest.raises(RuntimeError) as exc:  # Changed from ValueError to RuntimeError
        await call_tool(
            "shell_execute",
            {"command": "not_an_array", "directory": "/tmp"},  # Should be an array
        )
    assert "'command' must be an array" in str(exc.value)


@pytest.mark.asyncio
async def test_disallowed_command(monkeypatch):
    """Test error handling for disallowed command"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")  # Add allowed command
    with pytest.raises(RuntimeError) as exc:
        await call_tool(
            "shell_execute",
            {
                "command": ["sudo", "reboot"],  # Not in allowed commands
                "directory": "/tmp",
            },
        )
    assert "Command not allowed: sudo" in str(exc.value)


@pytest.mark.asyncio
async def test_call_tool_with_stderr(monkeypatch):
    """Test command execution with stderr output"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")
    result = await call_tool(
        "shell_execute",
        {"command": ["ls", "/nonexistent/directory"]},
    )
    assert len(result) >= 1
    stderr_content = next(
        (c for c in result if isinstance(c, TextContent) and "No such file" in c.text),
        None,
    )
    assert stderr_content is not None
    assert stderr_content.type == "text"


@pytest.mark.asyncio
async def test_main_server(mocker):
    """Test the main server function"""
    # Mock the stdio_server
    mock_read_stream = mocker.AsyncMock()
    mock_write_stream = mocker.AsyncMock()

    # Create an async context manager mock
    context_manager = mocker.AsyncMock()
    context_manager.__aenter__ = mocker.AsyncMock(
        return_value=(mock_read_stream, mock_write_stream)
    )
    context_manager.__aexit__ = mocker.AsyncMock(return_value=None)

    # Set up stdio_server mock to return a regular function that returns the context manager
    def stdio_server_impl():
        return context_manager

    mock_stdio_server = mocker.Mock(side_effect=stdio_server_impl)

    # Mock app.run and create_initialization_options
    mock_server_run = mocker.patch("mcp_shell_server.server.app.run")
    mock_create_init_options = mocker.patch(
        "mcp_shell_server.server.app.create_initialization_options"
    )

    # Import main after setting up mocks
    from mcp_shell_server.server import main

    # Execute main function
    mocker.patch("mcp.server.stdio.stdio_server", mock_stdio_server)
    await main()

    # Verify interactions
    mock_stdio_server.assert_called_once()
    context_manager.__aenter__.assert_awaited_once()
    context_manager.__aexit__.assert_awaited_once()
    mock_server_run.assert_called_once_with(
        mock_read_stream, mock_write_stream, mock_create_init_options.return_value
    )


@pytest.mark.asyncio
async def test_main_server_error_handling(mocker):
    """Test error handling in the main server function"""
    # Mock app.run to raise an exception
    mocker.patch(
        "mcp_shell_server.server.app.run", side_effect=RuntimeError("Test error")
    )

    # Mock the stdio_server
    context_manager = mocker.AsyncMock()
    context_manager.__aenter__ = mocker.AsyncMock(
        return_value=(mocker.AsyncMock(), mocker.AsyncMock())
    )
    context_manager.__aexit__ = mocker.AsyncMock(return_value=None)

    def stdio_server_impl():
        return context_manager

    mock_stdio_server = mocker.Mock(side_effect=stdio_server_impl)

    # Import main after setting up mocks
    from mcp_shell_server.server import main

    # Execute main function and expect it to raise the error
    mocker.patch("mcp.server.stdio.stdio_server", mock_stdio_server)
    with pytest.raises(RuntimeError) as exc:
        await main()

    assert str(exc.value) == "Test error"
