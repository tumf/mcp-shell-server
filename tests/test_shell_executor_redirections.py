import os
import tempfile
from io import TextIOWrapper

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_redirection_setup(temp_test_dir):
    """Test setup of redirections with files"""
    executor = ShellExecutor()

    # Create a test input file
    with open(os.path.join(temp_test_dir, "input.txt"), "w") as f:
        f.write("test content")

    # Test input redirection setup
    redirects = {
        "stdin": "input.txt",
        "stdout": None,
        "stdout_append": False,
    }
    handles = await executor._setup_redirects(redirects, temp_test_dir)
    assert "stdin" in handles
    assert "stdin_data" in handles
    assert handles["stdin_data"] == "test content"
    assert isinstance(handles["stdout"], int)
    assert isinstance(handles["stderr"], int)

    # Test output redirection setup
    output_file = os.path.join(temp_test_dir, "output.txt")
    redirects = {
        "stdin": None,
        "stdout": output_file,
        "stdout_append": False,
    }
    handles = await executor._setup_redirects(redirects, temp_test_dir)
    assert isinstance(handles["stdout"], TextIOWrapper)
    assert not handles["stdout"].closed
    await executor._cleanup_handles(handles)
    try:
        assert handles["stdout"].closed
    except ValueError:
        # Ignore errors from already closed file
        pass


@pytest.mark.asyncio
async def test_redirection_append_mode(temp_test_dir):
    """Test output redirection in append mode"""
    executor = ShellExecutor()

    output_file = os.path.join(temp_test_dir, "output.txt")

    # Test append mode
    redirects = {
        "stdin": None,
        "stdout": output_file,
        "stdout_append": True,
    }
    handles = await executor._setup_redirects(redirects, temp_test_dir)
    assert handles["stdout"].mode == "a"
    await executor._cleanup_handles(handles)

    # Test write mode
    redirects["stdout_append"] = False
    handles = await executor._setup_redirects(redirects, temp_test_dir)
    assert handles["stdout"].mode == "w"
    await executor._cleanup_handles(handles)


@pytest.mark.asyncio
async def test_redirection_setup_errors(temp_test_dir):
    """Test error cases in redirection setup"""
    executor = ShellExecutor()

    # Test non-existent input file
    redirects = {
        "stdin": "nonexistent.txt",
        "stdout": None,
        "stdout_append": False,
    }
    with pytest.raises(ValueError, match="Failed to open input file"):
        await executor._setup_redirects(redirects, temp_test_dir)

    # Test error in output file creation
    os.chmod(temp_test_dir, 0o444)  # Make directory read-only
    try:
        redirects = {
            "stdin": None,
            "stdout": "output.txt",
            "stdout_append": False,
        }
        with pytest.raises(ValueError, match="Failed to open output file"):
            await executor._setup_redirects(redirects, temp_test_dir)
    finally:
        os.chmod(temp_test_dir, 0o755)  # Reset permissions


@pytest.mark.asyncio
async def test_invalid_redirection_paths():
    """Test invalid redirection path scenarios"""
    executor = ShellExecutor()

    # Test missing path for output redirection
    with pytest.raises(ValueError, match="Missing path for output redirection"):
        executor._parse_command(["echo", "test", ">"])

    # Test invalid redirection target (operator found)
    with pytest.raises(ValueError, match="Invalid redirection target: operator found"):
        executor._parse_command(["echo", "test", ">", ">"])

    # Test missing path for input redirection
    with pytest.raises(ValueError, match="Missing path for input redirection"):
        executor._parse_command(["cat", "<"])

    # Test missing path for output redirection
    with pytest.raises(ValueError, match="Missing path for output redirection"):
        executor._parse_command(["echo", "test", ">"])

    # Test invalid redirection target: operator found for output
    with pytest.raises(ValueError, match="Invalid redirection target: operator found"):
        executor._parse_command(["echo", "test", ">", ">"])
