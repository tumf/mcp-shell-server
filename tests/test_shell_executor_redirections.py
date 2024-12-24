import os
import tempfile
from io import TextIOWrapper

import pytest

from mcp_shell_server.io_redirection_handler import IORedirectionHandler


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield os.path.realpath(tmpdirname)


@pytest.fixture
def handler():
    """Create a new IORedirectionHandler instance for each test"""
    return IORedirectionHandler()


@pytest.mark.asyncio
async def test_file_input_redirection(temp_test_dir, handler):
    """Test input redirection from a file"""
    # Create a test input file
    with open(os.path.join(temp_test_dir, "input.txt"), "w") as f:
        f.write("test content")

    redirects = {
        "stdin": "input.txt",
        "stdout": None,
        "stdout_append": False,
    }
    handles = await handler.setup_redirects(redirects, temp_test_dir)
    assert "stdin" in handles
    assert "stdin_data" in handles
    assert handles["stdin_data"] == "test content"
    assert isinstance(handles["stdout"], int)
    assert isinstance(handles["stderr"], int)


@pytest.mark.asyncio
async def test_file_output_redirection(temp_test_dir, handler):
    """Test output redirection to a file"""
    output_file = os.path.join(temp_test_dir, "output.txt")
    redirects = {
        "stdin": None,
        "stdout": output_file,
        "stdout_append": False,
    }
    handles = await handler.setup_redirects(redirects, temp_test_dir)
    assert isinstance(handles["stdout"], TextIOWrapper)
    assert not handles["stdout"].closed
    await handler.cleanup_handles(handles)
    assert handles["stdout"].closed


@pytest.mark.asyncio
async def test_append_mode(temp_test_dir, handler):
    """Test output redirection in append mode"""
    output_file = os.path.join(temp_test_dir, "output.txt")

    # Test append mode
    redirects = {
        "stdin": None,
        "stdout": output_file,
        "stdout_append": True,
    }
    handles = await handler.setup_redirects(redirects, temp_test_dir)
    assert handles["stdout"].mode == "a"
    await handler.cleanup_handles(handles)

    # Test write mode
    redirects["stdout_append"] = False
    handles = await handler.setup_redirects(redirects, temp_test_dir)
    assert handles["stdout"].mode == "w"
    await handler.cleanup_handles(handles)


def test_validate_redirection_syntax(handler):
    """Test validation of redirection syntax"""
    # Valid cases
    handler.validate_redirection_syntax(["echo", "hello", ">", "output.txt"])
    handler.validate_redirection_syntax(["cat", "<", "input.txt", ">", "output.txt"])
    handler.validate_redirection_syntax(["echo", "hello", ">>", "output.txt"])

    # Invalid cases
    with pytest.raises(ValueError, match="consecutive operators"):
        handler.validate_redirection_syntax(["echo", ">", ">", "output.txt"])

    with pytest.raises(ValueError, match="consecutive operators"):
        handler.validate_redirection_syntax(["cat", "<", ">", "output.txt"])


def test_process_redirections(handler):
    """Test processing of redirection operators"""
    # Input redirection
    cmd, redirects = handler.process_redirections(["cat", "<", "input.txt"])
    assert cmd == ["cat"]
    assert redirects["stdin"] == "input.txt"
    assert redirects["stdout"] is None

    # Output redirection
    cmd, redirects = handler.process_redirections(["echo", "test", ">", "output.txt"])
    assert cmd == ["echo", "test"]
    assert redirects["stdout"] == "output.txt"
    assert not redirects["stdout_append"]

    # Combined redirections
    cmd, redirects = handler.process_redirections(
        ["cat", "<", "in.txt", ">", "out.txt"]
    )
    assert cmd == ["cat"]
    assert redirects["stdin"] == "in.txt"
    assert redirects["stdout"] == "out.txt"


@pytest.mark.asyncio
async def test_setup_errors(temp_test_dir, handler):
    """Test error cases in redirection setup"""
    # Test non-existent input file
    redirects = {
        "stdin": "nonexistent.txt",
        "stdout": None,
        "stdout_append": False,
    }
    with pytest.raises(ValueError, match="Failed to open input file"):
        await handler.setup_redirects(redirects, temp_test_dir)

    # Test error in output file creation
    os.chmod(temp_test_dir, 0o444)  # Make directory read-only
    try:
        redirects = {
            "stdin": None,
            "stdout": "output.txt",
            "stdout_append": False,
        }
        with pytest.raises(ValueError, match="Failed to open output file"):
            await handler.setup_redirects(redirects, temp_test_dir)
    finally:
        os.chmod(temp_test_dir, 0o755)  # Reset permissions
