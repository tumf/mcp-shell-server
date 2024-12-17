import asyncio
import os
import tempfile

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def executor():
    return ShellExecutor()


@pytest.mark.asyncio
async def test_process_redirections_empty_command(executor):
    """Test process_redirections with empty command"""
    command, redirects = executor._process_redirections([])
    assert command == []
    assert redirects == {"stdin": None, "stdout": None, "stdout_append": False}


@pytest.mark.asyncio
async def test_process_redirections_invalid_input(executor):
    """Test process_redirections with invalid input redirection"""
    with pytest.raises(ValueError) as exc:
        executor._process_redirections(["cat", "<"])
    assert str(exc.value) == "Missing path for input redirection"


@pytest.mark.asyncio
async def test_process_redirections_invalid_output(executor):
    """Test process_redirections with invalid output redirection"""
    with pytest.raises(ValueError) as exc:
        executor._process_redirections(["echo", "hello", ">"])
    assert str(exc.value) == "Missing path for output redirection"


@pytest.mark.asyncio
async def test_setup_redirects_stdin(executor):
    """Test _setup_redirects method with stdin redirection"""
    # Create a temporary file with test content
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content\n")
        input_file = f.name

    try:
        redirects = {"stdin": input_file, "stdout": None, "stdout_append": False}
        handles = await executor._setup_redirects(redirects)

        assert handles["stdin"] == asyncio.subprocess.PIPE
        assert "stdin_data" in handles
        assert handles["stdin_data"] == "test content\n"
        assert handles["stdout"] == asyncio.subprocess.PIPE
        assert handles["stderr"] == asyncio.subprocess.PIPE

        await executor._cleanup_handles(handles)
    finally:
        os.unlink(input_file)


@pytest.mark.asyncio
async def test_setup_redirects_stdout_error(executor):
    """Test _setup_redirects with output file open error"""
    # Create a read-only directory
    with tempfile.TemporaryDirectory() as tmpdirname:
        output_file = os.path.join(tmpdirname, "out.txt")
        os.chmod(tmpdirname, 0o555)  # Read and execute only

        try:
            redirects = {"stdin": None, "stdout": output_file, "stdout_append": False}
            with pytest.raises(ValueError) as exc:
                await executor._setup_redirects(redirects)
            assert "Failed to open output file" in str(exc.value)
        finally:
            os.chmod(tmpdirname, 0o755)  # Restore permissions


@pytest.mark.asyncio
async def test_process_redirections_consecutive_operators(executor):
    """Test process_redirections with consecutive redirection operators"""
    with pytest.raises(ValueError) as exc:
        executor._validate_redirection_syntax(["echo", "hello", ">", ">", "output.txt"])
    assert str(exc.value) == "Invalid redirection syntax: consecutive operators"


@pytest.mark.asyncio
async def test_process_redirections_input_and_output(executor):
    """Test process_redirections with both input and output redirections"""
    command = ["cat", "<", "input.txt", ">", "output.txt"]
    processed_command, redirections = executor._process_redirections(command)

    assert processed_command == ["cat"]
    assert redirections == {
        "stdin": "input.txt",
        "stdout": "output.txt",
        "stdout_append": False,
    }
