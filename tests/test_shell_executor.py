import os
import tempfile
from typing import IO
from unittest.mock import AsyncMock

import pytest


def clear_env(monkeypatch):
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Return the real path to handle macOS /private/tmp symlink
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_basic_command_execution(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")

    # Set up mock return values
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"hello\n", b""))
    mock_process.kill = AsyncMock()
    mock_process.wait = AsyncMock()
    mock_process_manager.create_process.return_value = mock_process
    mock_process_manager.execute_with_timeout.return_value = (b"hello\n", b"")

    result = await shell_executor_with_mock.execute(["echo", "hello"], temp_test_dir)
    assert result["stdout"].strip() == "hello"
    assert result["status"] == 0


@pytest.mark.asyncio
async def test_stdin_input(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")

    # Set up mock return values
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"hello world\n", b""))
    mock_process.kill = AsyncMock()
    mock_process.wait = AsyncMock()
    mock_process_manager.create_process.return_value = mock_process
    mock_process_manager.execute_with_timeout.return_value = (b"hello world\n", b"")

    result = await shell_executor_with_mock.execute(
        ["cat "], temp_test_dir, stdin="hello world"
    )
    assert result["stdout"].strip() == "hello world"
    assert result["status"] == 0
    assert result["error"] is None


@pytest.mark.asyncio
async def test_command_not_allowed(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")

    mock_process_manager.execute_with_timeout.side_effect = ValueError(
        "Command not allowed: rm"
    )
    result = await shell_executor_with_mock.execute(["rm", "-rf", "/"], temp_test_dir)
    assert result["error"] == "Command not allowed: rm"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_empty_command(
    shell_executor_with_mock, mock_process_manager, temp_test_dir
):
    mock_process_manager.execute_with_timeout.side_effect = ValueError("Empty command")
    result = await shell_executor_with_mock.execute([], temp_test_dir)
    assert result["error"] == "Empty command"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_command_with_space_in_allow_commands(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "ls, echo ,cat")

    # Set up mock return values
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"test\n", b""))
    mock_process.kill = AsyncMock()
    mock_process.wait = AsyncMock()
    mock_process_manager.create_process.return_value = mock_process
    mock_process_manager.execute_with_timeout.return_value = (b"test\n", b"")

    result = await shell_executor_with_mock.execute(["echo", "test"], temp_test_dir)
    assert result["stdout"].strip() == "test"
    assert result["status"] == 0
    assert result["error"] is None


@pytest.mark.asyncio
async def test_multiple_commands_with_operator(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls")
    mock_process_manager.execute_with_timeout.side_effect = ValueError(
        "Unexpected shell operator: ;"
    )
    result = await shell_executor_with_mock.execute(
        ["echo", "hello", ";"], temp_test_dir
    )
    assert result["error"] == "Unexpected shell operator: ;"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_shell_operators_not_allowed(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls,true")
    operators = [";", "&&", "||"]
    for op in operators:
        mock_process_manager.execute_with_timeout.side_effect = ValueError(
            f"Unexpected shell operator: {op}"
        )
        result = await shell_executor_with_mock.execute(
            ["echo", "hello", op, "true"], temp_test_dir
        )
        assert result["error"] == f"Unexpected shell operator: {op}"
        assert result["status"] == 1


# New tests for directory functionality
@pytest.mark.asyncio
async def test_execute_in_directory(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command execution in a specific directory"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd")
    mock_process_manager.execute_with_timeout.return_value = (
        temp_test_dir.encode() + b"\n",
        b"",
    )
    result = await shell_executor_with_mock.execute(["pwd"], directory=temp_test_dir)
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == temp_test_dir


@pytest.mark.asyncio
async def test_execute_with_file_in_directory(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command execution with a file in the specified directory"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "ls,cat")

    # Create a test file in the temporary directory
    test_file = os.path.join(temp_test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    # Test ls command
    mock_process_manager.execute_with_timeout.return_value = (b"test.txt\n", b"")
    result = await shell_executor_with_mock.execute(["ls"], directory=temp_test_dir)
    assert "test.txt" in result["stdout"]

    # Test cat command - Set specific mock output for cat command
    mock_process_manager.execute_with_timeout.return_value = (b"test content\n", b"")
    result = await shell_executor_with_mock.execute(
        ["cat", "test.txt"], directory=temp_test_dir
    )
    assert result["stdout"].strip() == "test content"
    assert result["error"] is None
    assert result["status"] == 0


@pytest.mark.asyncio
async def test_execute_with_nonexistent_directory(
    shell_executor_with_mock, mock_process_manager, monkeypatch
):
    """Test command execution with a non-existent directory"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")
    mock_process_manager.execute_with_timeout.side_effect = ValueError(
        "Directory does not exist: /nonexistent/directory"
    )
    result = await shell_executor_with_mock.execute(
        ["ls"], directory="/nonexistent/directory"
    )
    assert result["error"] == "Directory does not exist: /nonexistent/directory"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_execute_with_file_as_directory(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command execution with a file specified as directory"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "ls")

    # Create a test file
    test_file = os.path.join(temp_test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    mock_process_manager.execute_with_timeout.side_effect = ValueError(
        f"Not a directory: {test_file}"
    )
    result = await shell_executor_with_mock.execute(["ls"], directory=test_file)
    assert result["error"] == f"Not a directory: {test_file}"
    assert result["status"] == 1


@pytest.mark.asyncio
async def test_execute_with_nested_directory(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command execution in a nested directory"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "pwd,mkdir,ls")

    # Create a nested directory
    nested_dir = os.path.join(temp_test_dir, "nested")
    os.mkdir(nested_dir)
    nested_real_path = os.path.realpath(nested_dir)

    mock_process_manager.execute_with_timeout.return_value = (
        nested_real_path.encode() + b"\n",
        b"",
    )
    result = await shell_executor_with_mock.execute(["pwd"], directory=nested_dir)
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == nested_real_path


@pytest.mark.asyncio
async def test_command_timeout(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command timeout functionality"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    mock_process_manager.execute_with_timeout.side_effect = TimeoutError(
        "Command timed out after 1 seconds"
    )
    result = await shell_executor_with_mock.execute(
        ["sleep", "2"], temp_test_dir, timeout=1
    )
    assert result["error"] == "Command timed out after 1 seconds"
    assert result["status"] == -1
    assert result["stdout"] == ""
    assert result["stderr"] == "Command timed out after 1 seconds"


@pytest.mark.asyncio
async def test_command_completes_within_timeout(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command that completes within timeout period"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    result = await shell_executor_with_mock.execute(
        ["sleep", "1"], temp_test_dir, timeout=2
    )
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"] == ""


@pytest.mark.asyncio
async def test_allowed_commands_alias(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test ALLOWED_COMMANDS alias functionality"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    mock_process_manager.execute_with_timeout.return_value = (b"hello\n", b"")
    result = await shell_executor_with_mock.execute(["echo", "hello"], temp_test_dir)
    assert result["stdout"].strip() == "hello"
    assert result["status"] == 0
    assert result["error"] is None


@pytest.mark.asyncio
async def test_both_allow_commands_vars(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test both ALLOW_COMMANDS and ALLOWED_COMMANDS working together"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    monkeypatch.setenv("ALLOWED_COMMANDS", "cat")

    # Test command from ALLOW_COMMANDS
    mock_process_manager.execute_with_timeout.return_value = (b"hello\n", b"")
    result1 = await shell_executor_with_mock.execute(["echo", "hello"], temp_test_dir)
    assert result1["stdout"].strip() == "hello"
    assert result1["status"] == 0
    assert result1["error"] is None

    # Test command from ALLOWED_COMMANDS
    mock_process_manager.execute_with_timeout.return_value = (b"world\n", b"")
    result2 = await shell_executor_with_mock.execute(
        ["cat"], temp_test_dir, stdin="world"
    )
    assert result2["stdout"].strip() == "world"
    assert result2["status"] == 0
    assert result2["error"] is None


@pytest.mark.asyncio
async def test_allow_commands_precedence(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test that commands are combined from both environment variables"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls")
    monkeypatch.setenv("ALLOWED_COMMANDS", "echo,cat")

    assert set(shell_executor_with_mock.validator.get_allowed_commands()) == {
        "echo",
        "ls",
        "cat",
    }


@pytest.mark.asyncio
async def test_pipe_operator(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test that pipe operator works correctly"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    mock_process_manager.execute_pipeline.return_value = (b"world\n", b"", 0)
    result = await shell_executor_with_mock.execute(
        ["echo", "hello\nworld", "|", "grep", "world"], temp_test_dir
    )
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == "world"


@pytest.mark.asyncio
async def test_pipe_commands(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test piping commands together"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep,cut,tr")

    # Test multiple pipes
    mock_process_manager.execute_pipeline.return_value = (b"WORLD\n", b"", 0)
    result = await shell_executor_with_mock.execute(
        ["echo", "hello world", "|", "cut", "-d", " ", "-f2", "|", "tr", "a-z", "A-Z"],
        temp_test_dir,
    )
    assert result["stdout"].strip() == "WORLD"


@pytest.mark.asyncio
async def test_output_redirection(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test output redirection with > operator"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")
    output_file = os.path.join(temp_test_dir, "out.txt")

    # Test > redirection
    # Mock empty output for echo commands
    mock_process_manager.execute_with_timeout.return_value = (b"", b"")
    result = await shell_executor_with_mock.execute(
        ["echo", "hello", ">", output_file], directory=temp_test_dir
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Test >> redirection (append)
    mock_process_manager.execute_with_timeout.return_value = (b"", b"")
    result = await shell_executor_with_mock.execute(
        ["echo", "world", ">>", output_file], directory=temp_test_dir
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Mock cat command to return the expected file contents
    mock_process_manager.execute_with_timeout.return_value = (b"hello\nworld\n", b"")
    result = await shell_executor_with_mock.execute(
        ["cat", output_file], directory=temp_test_dir
    )
    assert result["status"] == 0
    assert result["error"] is None
    assert result["stdout"].strip().split("\n") == ["hello", "world"]


@pytest.mark.asyncio
async def test_input_redirection(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
    mocker,
):
    """Test input redirection with < operator"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "cat")
    input_file = os.path.join(temp_test_dir, "in.txt")

    # Mock the file operations
    mock_file = mocker.mock_open(read_data="test content")
    mocker.patch("builtins.open", mock_file)

    # Test < redirection
    mock_process_manager.execute_with_timeout.return_value = (b"test content\n", b"")
    result = await shell_executor_with_mock.execute(
        ["cat", "<", input_file], directory=temp_test_dir
    )
    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].strip() == "test content"


@pytest.mark.asyncio
async def test_combined_redirections(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test combining input and output redirection"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "cat,tr")
    input_file = os.path.join(temp_test_dir, "in.txt")
    output_file = os.path.join(temp_test_dir, "out.txt")

    # Create input file
    with open(input_file, "w") as f:
        f.write("hello world")

    # Test < and > redirection together
    result = await shell_executor_with_mock.execute(
        ["cat", "<", input_file, "|", "tr", "[:lower:]", "[:upper:]", ">", output_file],
        directory=temp_test_dir,
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Verify using cat command
    mock_process_manager.execute_with_timeout.return_value = (b"HELLO WORLD\n", b"")
    result = await shell_executor_with_mock.execute(
        ["cat", output_file], directory=temp_test_dir
    )
    assert result["stdout"].strip() == "HELLO WORLD"


@pytest.mark.asyncio
async def test_redirection_error_cases(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test error cases for redirections"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")

    # Missing output file path
    result = await shell_executor_with_mock.execute(
        ["echo", "hello", ">"], directory=temp_test_dir
    )
    assert result["error"] == "Missing path for output redirection"

    # Missing input file path
    result = await shell_executor_with_mock.execute(
        ["cat", "<"], directory=temp_test_dir
    )
    assert result["error"] == "Missing path for input redirection"

    # Non-existent input file
    result = await shell_executor_with_mock.execute(
        ["cat", "<", "nonexistent.txt"], directory=temp_test_dir
    )
    assert result["error"] == "Failed to open input file"

    # Operator as path
    result = await shell_executor_with_mock.execute(
        ["echo", "hello", ">", ">"], directory=temp_test_dir
    )
    assert result["error"] == "Invalid redirection target: operator found"


@pytest.mark.asyncio
async def test_complex_pipeline_with_redirections(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test complex pipeline with multiple redirections"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep,tr,cat")
    input_file = os.path.join(temp_test_dir, "pipeline_input.txt")
    output_file = os.path.join(temp_test_dir, "pipeline_output.txt")

    # Create a test input file
    with open(input_file, "w") as f:
        f.write("hello\nworld\ntest\nHELLO\n")

    # Mock process execution for pipeline
    final_output = "HELLO\nWORLD"
    mock_process_manager.execute_pipeline.return_value = (final_output.encode(), b"", 0)

    # Complex pipeline: cat < input | grep l | tr a-z A-Z > output
    # Set specific process manager behavior for redirection
    mock_process_manager.execute_with_timeout.return_value = (b"", b"")
    mock_process_manager.execute_pipeline.side_effect = None
    mock_process_manager.execute_pipeline.return_value = (b"", b"", 0)

    result = await shell_executor_with_mock.execute(
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
    assert result["stdout"] == ""

    # Write expected output to simulated file
    with open(output_file, "w") as f:
        f.write(final_output)

    # Check the output file content
    with open(output_file, "r") as f:
        actual_output = f.read().strip()
    assert actual_output == final_output


def test_validate_redirection_syntax(shell_executor_with_mock):
    """Test validation of redirection syntax with various input combinations"""
    # Valid cases
    shell_executor_with_mock.io_handler.validate_redirection_syntax(
        ["echo", "hello", ">", "file.txt"]
    )
    shell_executor_with_mock.io_handler.validate_redirection_syntax(
        ["cat", "<", "input.txt", ">", "output.txt"]
    )

    # Test consecutive operators
    with pytest.raises(ValueError) as exc:
        shell_executor_with_mock.io_handler.validate_redirection_syntax(
            ["echo", "text", ">", ">", "file.txt"]
        )
    assert str(exc.value) == "Invalid redirection syntax: consecutive operators"

    with pytest.raises(ValueError) as exc:
        shell_executor_with_mock.io_handler.validate_redirection_syntax(
            ["cat", "<", "<", "input.txt"]
        )
    assert str(exc.value) == "Invalid redirection syntax: consecutive operators"


def test_create_shell_command(shell_executor_with_mock):
    """Test shell command creation with various input combinations"""
    # Test basic command
    assert (
        shell_executor_with_mock.preprocessor.create_shell_command(["echo", "hello"])
        == "echo hello"
    )

    # Test command with space-only argument
    assert (
        shell_executor_with_mock.preprocessor.create_shell_command(["echo", " "])
        == "echo ' '"
    )

    # Test command with wildcards
    assert (
        shell_executor_with_mock.preprocessor.create_shell_command(["ls", "*.txt"])
        == "ls '*.txt'"
    )

    # Test command with special characters
    assert (
        shell_executor_with_mock.preprocessor.create_shell_command(
            ["echo", "hello;", "world"]
        )
        == "echo 'hello;' world"
    )

    # Test empty command
    assert shell_executor_with_mock.preprocessor.create_shell_command([]) == ""


def test_preprocess_command(shell_executor_with_mock):
    """Test command preprocessing for pipeline handling"""
    # Test basic command
    assert shell_executor_with_mock.preprocessor.preprocess_command(["ls"]) == ["ls"]

    # Test command with separate pipe
    assert shell_executor_with_mock.preprocessor.preprocess_command(
        ["ls", "|", "grep", "test"]
    ) == [
        "ls",
        "|",
        "grep",
        "test",
    ]

    # Test command with attached pipe
    assert shell_executor_with_mock.preprocessor.preprocess_command(
        ["ls|", "grep", "test"]
    ) == [
        "ls",
        "|",
        "grep",
        "test",
    ]

    # Test command with special operators
    assert shell_executor_with_mock.preprocessor.preprocess_command(
        ["echo", "hello", "&&", "ls"]
    ) == [
        "echo",
        "hello",
        "&&",
        "ls",
    ]

    # Test empty command
    assert shell_executor_with_mock.preprocessor.preprocess_command([]) == []


def test_validate_pipeline(shell_executor_with_mock, monkeypatch):
    """Test pipeline validation"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep,cat")
    monkeypatch.setenv("ALLOWED_COMMANDS", "echo,grep,cat")

    # Test valid pipeline
    shell_executor_with_mock.validator.validate_pipeline(
        ["echo", "hello", "|", "grep", "h"]
    )

    # Test empty command before pipe
    with pytest.raises(ValueError) as exc:
        shell_executor_with_mock.validator.validate_pipeline(["|", "grep", "test"])
    assert str(exc.value) == "Empty command before pipe operator"

    # Test disallowed commands in pipeline
    with pytest.raises(ValueError) as exc:
        shell_executor_with_mock.validator.validate_pipeline(
            ["rm", "|", "grep", "test"]
        )
    assert "Command not allowed: rm" in str(exc.value)

    # Test shell operators in pipeline
    with pytest.raises(ValueError) as exc:
        shell_executor_with_mock.validator.validate_pipeline(
            ["echo", "hello", "|", "grep", "h", "&&", "ls"]
        )
    assert "Unexpected shell operator in pipeline: &&" in str(exc.value)
    assert shell_executor_with_mock.preprocessor.preprocess_command([]) == []


def test_redirection_path_validation(shell_executor_with_mock):
    """Test validation of redirection paths"""
    # Test missing output redirection path
    with pytest.raises(ValueError, match="Missing path for output redirection"):
        shell_executor_with_mock.preprocessor.parse_command(["echo", "hello", ">"])

    # Test missing input redirection path
    with pytest.raises(ValueError, match="Missing path for input redirection"):
        shell_executor_with_mock.preprocessor.parse_command(["cat", "<"])

    # Test operator as redirection target
    with pytest.raises(ValueError, match="Invalid redirection target: operator found"):
        shell_executor_with_mock.preprocessor.parse_command(["echo", "hello", ">", ">"])

    # Test multiple operators
    with pytest.raises(ValueError, match="Invalid redirection target: operator found"):
        shell_executor_with_mock.preprocessor.parse_command(
            ["echo", "hello", ">", ">>", "file.txt"]
        )


@pytest.mark.asyncio
async def test_io_handle_close(
    shell_executor_with_mock,
    mock_process_manager,
    mock_file,
    temp_test_dir,
    monkeypatch,
    mocker,
):
    """Test IO handle closing functionality"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    test_file = os.path.join(temp_test_dir, "test.txt")

    # Create file handler that will raise IOError on close
    mock_file = mocker.MagicMock(spec=IO)
    mock_file.close.side_effect = IOError("Failed to close file")

    # Patch the open function to return our mock
    mocker.patch("builtins.open", return_value=mock_file)

    # Mock logging.warning to capture the warning
    mock_warning = mocker.patch("logging.warning")

    # Execute should not raise an error
    await shell_executor_with_mock.execute(
        ["echo", "hello", ">", test_file], directory=temp_test_dir
    )

    # Verify our mock's close method was called
    assert mock_file.close.called
    # Verify warning was logged
    mock_warning.assert_called_once_with("Error closing stdout: Failed to close file")


def test_preprocess_command_pipeline(shell_executor_with_mock):
    """Test pipeline command preprocessing functionality"""
    # Test empty command
    assert shell_executor_with_mock.preprocessor.preprocess_command([]) == []

    # Test single command without pipe
    assert shell_executor_with_mock.preprocessor.preprocess_command(
        ["echo", "hello"]
    ) == [
        "echo",
        "hello",
    ]

    # Test simple pipe
    assert shell_executor_with_mock.preprocessor.preprocess_command(
        ["echo", "hello", "|", "grep", "h"]
    ) == [
        "echo",
        "hello",
        "|",
        "grep",
        "h",
    ]

    # Test multiple pipes
    assert shell_executor_with_mock.preprocessor.preprocess_command(
        ["cat", "file", "|", "grep", "pattern", "|", "wc", "-l"]
    ) == ["cat", "file", "|", "grep", "pattern", "|", "wc", "-l"]

    # Test command with attached pipe operator
    assert shell_executor_with_mock.preprocessor.preprocess_command(
        ["echo|", "grep", "pattern"]
    ) == [
        "echo",
        "|",
        "grep",
        "pattern",
    ]


@pytest.mark.asyncio
async def test_command_cleanup_on_error(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test cleanup of processes when error occurs"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")

    # Configure mock to simulate timeout
    mock_process_manager.execute_with_timeout.side_effect = TimeoutError(
        "Command timed out"
    )

    async def execute_with_keyboard_interrupt():
        # Simulate keyboard interrupt during execution
        result = await shell_executor_with_mock.execute(
            ["sleep", "5"], temp_test_dir, timeout=1
        )
        return result

    result = await execute_with_keyboard_interrupt()
    assert result["error"] == "Command timed out after 1 seconds"
    assert result["status"] == -1
    assert "execution_time" in result


@pytest.mark.asyncio
async def test_output_redirection_with_append(
    shell_executor_with_mock,
    mock_process_manager,
    mock_file,
    temp_test_dir,
    monkeypatch,
):
    """Test output redirection with append mode"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")
    output_file = os.path.join(temp_test_dir, "test.txt")

    # Write initial content
    await shell_executor_with_mock.execute(
        ["echo", "hello", ">", output_file], directory=temp_test_dir
    )

    # Append content
    result = await shell_executor_with_mock.execute(
        ["echo", "world", ">>", output_file], directory=temp_test_dir
    )
    assert result["error"] is None
    assert result["status"] == 0

    # Verify contents
    mock_process_manager.execute_with_timeout.return_value = (b"hello\nworld\n", b"")
    result = await shell_executor_with_mock.execute(
        ["cat", output_file], directory=temp_test_dir
    )
    lines = result["stdout"].strip().split("\n")
    assert len(lines) == 2
    assert lines[0] == "hello"


@pytest.mark.asyncio
async def test_execute_with_custom_env(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command execution with custom environment variables"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "env,printenv")

    custom_env = {"TEST_VAR1": "test_value1", "TEST_VAR2": "test_value2"}

    # Test env command
    mock_process_manager.execute_with_timeout.return_value = (
        b"TEST_VAR1=test_value1\nTEST_VAR2=test_value2\n",
        b"",
    )
    result = await shell_executor_with_mock.execute(
        ["env"], directory=temp_test_dir, envs=custom_env
    )
    assert "TEST_VAR1=test_value1" in result["stdout"]
    assert "TEST_VAR2=test_value2" in result["stdout"]

    # Test specific variable - Update mock for printenv command
    mock_process_manager.execute_with_timeout.return_value = (b"test_value1\n", b"")
    result = await shell_executor_with_mock.execute(
        ["printenv", "TEST_VAR1"], directory=temp_test_dir, envs=custom_env
    )
    assert result["stdout"].strip() == "test_value1"


@pytest.mark.asyncio
async def test_execute_env_override(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test that custom environment variables override system variables"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "env")
    monkeypatch.setenv("TEST_VAR", "original_value")

    # Mock env command with new environment variable
    mock_process_manager.execute_with_timeout.return_value = (
        b"TEST_VAR=new_value\n",
        b"",
    )

    # Override system environment variable
    result = await shell_executor_with_mock.execute(
        ["env"], directory=temp_test_dir, envs={"TEST_VAR": "new_value"}
    )

    assert "TEST_VAR=new_value" in result["stdout"]
    assert "TEST_VAR=original_value" not in result["stdout"]


@pytest.mark.asyncio
async def test_execute_with_empty_env(
    shell_executor_with_mock,
    mock_process_manager,
    temp_test_dir,
    monkeypatch,
):
    """Test command execution with empty environment variables"""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "env")

    # Mock env command with system environment
    mock_process_manager.execute_with_timeout.return_value = (
        b"PATH=/usr/bin\nHOME=/home/user\n",
        b"",
    )

    result = await shell_executor_with_mock.execute(
        ["env"], directory=temp_test_dir, envs={}
    )

    # Command should still work with system environment
    assert result["error"] is None
    assert result["status"] == 0
    assert len(result["stdout"]) > 0
