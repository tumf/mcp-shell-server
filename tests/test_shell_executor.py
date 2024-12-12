import os
import tempfile

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


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
async def test_basic_command_execution(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    result = await executor.execute(["echo", "hello"])
    assert result["stdout"].strip() == "hello"
    assert result["status"] == 0


@pytest.mark.asyncio
async def test_stdin_input(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    result = await executor.execute(["cat"], stdin="hello world")
    assert result["stdout"].strip() == "hello world"
    assert result["status"] == 0


@pytest.mark.asyncio
async def test_command_with_space_allowed(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    result = await executor.execute(["cat "], stdin="hello world")
    assert result["error"] is None
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
    result = await executor.execute(["echo", "hello", ";"])
    assert result["error"] == "Unexpected shell operator: ;"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_shell_operators_not_allowed(executor, monkeypatch):
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls")
    operators = [";", "&&", "||", "|"]
    for op in operators:
        result = await executor.execute(["echo", "hello", op])
        assert result["error"] == f"Unexpected shell operator: {op}"
        assert result["status"] == 1


# New tests for directory functionality
@pytest.mark.asyncio
async def test_execute_in_directory(executor, temp_test_dir, monkeypatch):
    """Test command execution in a specific directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd")
    result = await executor.execute(["pwd"], directory=temp_test_dir)
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == temp_test_dir


@pytest.mark.asyncio
async def test_execute_with_file_in_directory(executor, temp_test_dir, monkeypatch):
    """Test command execution with a file in the specified directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls,cat")

    # Create a test file in the temporary directory
    test_file = os.path.join(temp_test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    # Test ls command
    result = await executor.execute(["ls"], directory=temp_test_dir)
    assert "test.txt" in result["stdout"]

    # Test cat command
    result = await executor.execute(["cat", "test.txt"], directory=temp_test_dir)
    assert result["stdout"].strip() == "test content"


@pytest.mark.asyncio
async def test_execute_with_nonexistent_directory(executor, monkeypatch):
    """Test command execution with a non-existent directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")
    result = await executor.execute(["ls"], directory="/nonexistent/directory")
    assert result["error"] == "Directory does not exist: /nonexistent/directory"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_execute_with_file_as_directory(executor, temp_test_dir, monkeypatch):
    """Test command execution with a file specified as directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")

    # Create a test file
    test_file = os.path.join(temp_test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    result = await executor.execute(["ls"], directory=test_file)
    assert result["error"] == f"Not a directory: {test_file}"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_execute_with_no_directory_specified(executor, monkeypatch):
    """Test command execution without specifying a directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd")
    result = await executor.execute(["pwd"])
    assert result["error"] is None
    assert result["status"] == 0
    assert os.path.exists(result["stdout"].strip())


@pytest.mark.asyncio
async def test_execute_with_nested_directory(executor, temp_test_dir, monkeypatch):
    """Test command execution in a nested directory"""
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd,mkdir,ls")

    # Create a nested directory
    nested_dir = os.path.join(temp_test_dir, "nested")
    os.mkdir(nested_dir)
    nested_real_path = os.path.realpath(nested_dir)

    result = await executor.execute(["pwd"], directory=nested_dir)
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == nested_real_path


@pytest.mark.asyncio
async def test_command_timeout(executor, monkeypatch):
    """Test command timeout functionality"""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    result = await executor.execute(["sleep", "2"], timeout=1)
    assert result["error"] == "Command timed out after 1 seconds"
    assert result["status"] == -1
    assert result["stdout"] == ""
    assert result["stderr"] == "Command timed out after 1 seconds"


@pytest.mark.asyncio
async def test_command_completes_within_timeout(executor, monkeypatch):
    """Test command that completes within timeout period"""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    result = await executor.execute(["sleep", "1"], timeout=2)
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"] == ""


@pytest.mark.asyncio
async def test_allowed_commands_alias(executor, monkeypatch):
    """Test ALLOWED_COMMANDS alias functionality"""
    monkeypatch.setenv("ALLOWED_COMMANDS", "echo")
    result = await executor.execute(["echo", "hello"])
    assert result["stdout"].strip() == "hello"
    assert result["status"] == 0


@pytest.mark.asyncio
async def test_both_allow_commands_vars(executor, monkeypatch):
    """Test both ALLOW_COMMANDS and ALLOWED_COMMANDS working together"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    monkeypatch.setenv("ALLOWED_COMMANDS", "cat")

    # Test command from ALLOW_COMMANDS
    result1 = await executor.execute(["echo", "hello"])
    assert result1["stdout"].strip() == "hello"
    assert result1["status"] == 0

    # Test command from ALLOWED_COMMANDS
    result2 = await executor.execute(["cat"], stdin="world")
    assert result2["stdout"].strip() == "world"
    assert result2["status"] == 0


@pytest.mark.asyncio
async def test_allow_commands_precedence(executor, monkeypatch):
    """Test that commands are combined from both environment variables"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls")
    monkeypatch.setenv("ALLOWED_COMMANDS", "echo,cat")

    allowed = executor.get_allowed_commands()
    assert set(allowed) == {"echo", "ls", "cat"}
