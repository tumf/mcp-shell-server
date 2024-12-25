"""Tests for IO redirection in shell executor with mocked file operations."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_shell_server.io_redirection_handler import IORedirectionHandler


@pytest.fixture
def mock_file():
    """Create a mock file object."""
    file_mock = MagicMock()
    file_mock.closed = False
    file_mock.close = MagicMock()
    file_mock.write = MagicMock()
    file_mock.read = MagicMock(return_value="test content")
    return file_mock


@pytest.fixture
def handler():
    """Create a new IORedirectionHandler instance for each test."""
    return IORedirectionHandler()


@pytest.mark.asyncio
async def test_file_input_redirection(handler, mock_file):
    """Test input redirection from a file using mocks."""
    with (
        patch("builtins.open", return_value=mock_file),
        patch("os.path.exists", return_value=True),
    ):

        redirects = {
            "stdin": "input.txt",
            "stdout": None,
            "stdout_append": False,
        }
        handles = await handler.setup_redirects(redirects, "/mock/dir")

        assert "stdin" in handles
        assert "stdin_data" in handles
        assert handles["stdin_data"] == "test content"
        assert isinstance(handles["stdout"], int)
        assert isinstance(handles["stderr"], int)


@pytest.mark.asyncio
async def test_file_output_redirection(handler, mock_file):
    """Test output redirection to a file using mocks."""
    with patch("builtins.open", return_value=mock_file):
        redirects = {
            "stdin": None,
            "stdout": "output.txt",
            "stdout_append": False,
        }
        handles = await handler.setup_redirects(redirects, "/mock/dir")

        assert "stdout" in handles
        assert not handles["stdout"].closed
        await handler.cleanup_handles(handles)
        mock_file.close.assert_called_once()


@pytest.mark.asyncio
async def test_append_mode(handler, mock_file):
    """Test output redirection in append mode using mocks."""
    with patch("builtins.open", return_value=mock_file):
        # Test append mode
        redirects = {
            "stdin": None,
            "stdout": "output.txt",
            "stdout_append": True,
        }
        mock_file.mode = "a"  # Set the expected mode
        handles = await handler.setup_redirects(redirects, "/mock/dir")
        assert handles["stdout"].mode == "a"
        await handler.cleanup_handles(handles)
        mock_file.close.assert_called_once()

        # Reset mock and test write mode
        mock_file.reset_mock()
        mock_file.mode = "w"  # Set the expected mode for write mode
        redirects["stdout_append"] = False
        handles = await handler.setup_redirects(redirects, "/mock/dir")
        assert handles["stdout"].mode == "w"
        await handler.cleanup_handles(handles)
        mock_file.close.assert_called_once()


def test_validate_redirection_syntax(handler):
    """Test validation of redirection syntax."""
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
    """Test processing of redirection operators."""
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
async def test_setup_errors(handler, mock_file):
    """Test error cases in redirection setup using mocks."""
    # Test non-existent input file
    with patch("os.path.exists", return_value=False):
        redirects = {
            "stdin": "nonexistent.txt",
            "stdout": None,
            "stdout_append": False,
        }
        with pytest.raises(ValueError, match="Failed to open input file"):
            await handler.setup_redirects(redirects, "/mock/dir")

    # Test error in output file creation
    # Mock builtins.open to raise PermissionError
    mock_open = MagicMock(side_effect=PermissionError("Permission denied"))
    with patch("builtins.open", mock_open):
        redirects = {
            "stdin": None,
            "stdout": "output.txt",
            "stdout_append": False,
        }
        with pytest.raises(ValueError, match="Failed to open output file"):
            await handler.setup_redirects(redirects, "/mock/dir")

    mock_file.close.assert_not_called()
