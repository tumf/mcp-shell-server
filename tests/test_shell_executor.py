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
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls,true")
    operators = [";", "&&", "||"]
    for op in operators:
        result = await executor.execute(["echo", "hello", op, "true"])
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


@pytest.mark.asyncio
async def test_pipe_operator(executor, monkeypatch):
    """Test that pipe operator works correctly"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    result = await executor.execute(["echo", "hello\nworld", "|", "grep", "world"])
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == "world"


@pytest.mark.asyncio
async def test_pipe_commands(executor, temp_test_dir, monkeypatch):
    """Test piping commands together"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep,cut,tr")
    result = await executor.execute(["echo", "hello world", "|", "grep", "world"])
    assert result["stdout"].strip() == "hello world"

    # Test multiple pipes
    result = await executor.execute(
        ["echo", "hello world", "|", "cut", "-d", " ", "-f2", "|", "tr", "a-z", "A-Z"]
    )
    assert result["stdout"].strip() == "WORLD"


@pytest.mark.asyncio
async def test_output_redirection(executor, temp_test_dir, monkeypatch):
    """Test output redirection with > operator"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")
    output_file = os.path.join(temp_test_dir, "out.txt")

    # Test > redirection
    result = await executor.execute(
        ["echo", "hello", ">", output_file], directory=temp_test_dir
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Verify file contents
    with open(output_file) as f:
        assert f.read().strip() == "hello"

    # Test >> redirection (append)
    result = await executor.execute(
        ["echo", "world", ">>", output_file], directory=temp_test_dir
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Verify appended contents
    with open(output_file) as f:
        lines = f.readlines()
        assert lines[0].strip() == "hello"
        assert lines[1].strip() == "world"


@pytest.mark.asyncio
async def test_input_redirection(executor, temp_test_dir, monkeypatch):
    """Test input redirection with < operator"""
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    input_file = os.path.join(temp_test_dir, "in.txt")

    # Create input file
    with open(input_file, "w") as f:
        f.write("test content")

    # Test < redirection
    result = await executor.execute(["cat", "<", input_file], directory=temp_test_dir)
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == "test content"


@pytest.mark.asyncio
async def test_combined_redirections(executor, temp_test_dir, monkeypatch):
    """Test combining input and output redirection"""
    monkeypatch.setenv("ALLOW_COMMANDS", "cat,tr")
    input_file = os.path.join(temp_test_dir, "in.txt")
    output_file = os.path.join(temp_test_dir, "out.txt")

    # Create input file
    with open(input_file, "w") as f:
        f.write("hello world")

    # Test < and > redirection together
    result = await executor.execute(
        ["cat", "<", input_file, "|", "tr", "[:lower:]", "[:upper:]", ">", output_file],
        directory=temp_test_dir,
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Verify output file
    with open(output_file) as f:
        assert f.read().strip() == "HELLO WORLD"


@pytest.mark.asyncio
async def test_redirection_error_cases(executor, temp_test_dir, monkeypatch):
    """Test error cases for redirections"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")

    # Missing output file path
    result = await executor.execute(["echo", "hello", ">"], directory=temp_test_dir)
    assert result["error"] == "Missing path for output redirection"

    # Missing input file path
    result = await executor.execute(["cat", "<"], directory=temp_test_dir)
    assert result["error"] == "Missing path for input redirection"

    # Non-existent input file
    result = await executor.execute(
        ["cat", "<", "nonexistent.txt"], directory=temp_test_dir
    )
    assert "No such file or directory" in result["error"]

    # Invalid redirection operator
    result = await executor.execute(
        ["echo", "hello", ">", ">", "test.txt"], directory=temp_test_dir
    )
    assert result["error"] == "Invalid redirection target: operator found"

    # Operator as path
    result = await executor.execute(
        ["echo", "hello", ">", ">"], directory=temp_test_dir
    )
    assert result["error"] == "Invalid redirection target: operator found"


@pytest.mark.asyncio
async def test_complex_pipeline_with_redirections(executor, temp_test_dir, monkeypatch):
    """Test complex pipeline with multiple redirections"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep,tr,cat")
    input_file = os.path.join(temp_test_dir, "pipeline_input.txt")
    output_file = os.path.join(temp_test_dir, "pipeline_output.txt")

    # Create input file
    with open(input_file, "w") as f:
        f.write("hello\nworld\ntest\nHELLO\n")

    # Complex pipeline: cat < input | grep l | tr a-z A-Z > output
    result = await executor.execute(
        [
            "cat",
            "<",
            input_file,
            "|",
            "grep",
            "l",
            "|",
            "tr",
            "a-z",
            "A-Z",
            ">",
            output_file,
        ],
        directory=temp_test_dir,
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Verify output file
    with open(output_file) as f:
        lines = f.readlines()
        assert len(lines) == 2
        assert lines[0].strip() == "HELLO"
        assert lines[1].strip() == "WORLD"


@pytest.mark.asyncio
async def test_directory_permissions(executor, temp_test_dir, monkeypatch):
    """Test command execution with directory permission issues"""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")

    # Create a directory with no execute permission
    no_exec_dir = os.path.join(temp_test_dir, "no_exec_dir")
    os.mkdir(no_exec_dir)
    os.chmod(no_exec_dir, 0o600)  # Remove execute permission

    try:
        result = await executor.execute(["ls"], directory=no_exec_dir)
        assert result["error"] == f"Directory is not accessible: {no_exec_dir}"
        assert result["status"] == 1
    finally:
        # Restore permissions for cleanup
        os.chmod(no_exec_dir, 0o700)


def test_validate_redirection_syntax(executor):
    """Test validation of redirection syntax with various input combinations"""
    # Valid cases
    executor._validate_redirection_syntax(["echo", "hello", ">", "file.txt"])
    executor._validate_redirection_syntax(["cat", "<", "input.txt", ">", "output.txt"])

    # Test consecutive operators
    with pytest.raises(ValueError) as exc:
        executor._validate_redirection_syntax(["echo", "text", ">", ">", "file.txt"])
    assert str(exc.value) == "Invalid redirection syntax: consecutive operators"

    with pytest.raises(ValueError) as exc:
        executor._validate_redirection_syntax(["cat", "<", "<", "input.txt"])
    assert str(exc.value) == "Invalid redirection syntax: consecutive operators"


def test_create_shell_command(executor):
    """Test shell command creation with various input combinations"""
    # Test basic command
    assert executor._create_shell_command(["echo", "hello"]) == "echo hello"
    
    # Test command with space-only argument
    assert executor._create_shell_command(["echo", " "]) == "echo ' '"
    
    # Test command with wildcards
    assert executor._create_shell_command(["ls", "*.txt"]) == "ls '*.txt'"
    
    # Test command with special characters
    assert executor._create_shell_command(["echo", "hello;", "world"]) == "echo 'hello;' world"
    
    # Test empty command
    assert executor._create_shell_command([]) == ""


def test_preprocess_command(executor):
    """Test command preprocessing for pipeline handling"""
    # Test basic command
    assert executor._preprocess_command(["ls"]) == ["ls"]
    
    # Test command with separate pipe
    assert executor._preprocess_command(["ls", "|", "grep", "test"]) == [
        "ls",
        "|",
        "grep",
        "test",
    ]
    
    # Test command with attached pipe
    assert executor._preprocess_command(["ls|", "grep", "test"]) == [
        "ls",
        "|",
        "grep",
        "test",
    ]
    
    # Test command with special operators
    assert executor._preprocess_command(["echo", "hello", "&&", "ls"]) == [
        "echo",
        "hello",
        "&&",
        "ls",
    ]
    
    # Test empty command
    assert executor._preprocess_command([]) == []


def test_validate_pipeline(executor, monkeypatch):
    """Test pipeline validation"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep,cat")

    # Test valid pipeline
    executor._validate_pipeline(["echo", "hello", "|", "grep", "h"])

    # Test empty command before pipe
    with pytest.raises(ValueError) as exc:
        executor._validate_pipeline(["|", "grep", "test"])
    assert str(exc.value) == "Empty command before pipe operator"

    # Test disallowed commands in pipeline
    with pytest.raises(ValueError) as exc:
        executor._validate_pipeline(["rm", "|", "grep", "test"])
    assert "Command not allowed: rm" in str(exc.value)

    # Test shell operators in pipeline
    with pytest.raises(ValueError) as exc:
        executor._validate_pipeline(["echo", "hello", "|", "grep", "h", "&&", "ls"])
    assert "Unexpected shell operator in pipeline: &&" in str(exc.value)
    assert executor._preprocess_command([]) == []
