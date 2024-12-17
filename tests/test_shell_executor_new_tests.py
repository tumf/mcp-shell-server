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
