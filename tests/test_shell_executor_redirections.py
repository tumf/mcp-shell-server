"""Tests for contained IO redirection handling."""

import os

import pytest

from mcp_shell_server.io_redirection_handler import IORedirectionHandler
from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def handler():
    """Create a new IORedirectionHandler instance for each test."""
    return IORedirectionHandler()


@pytest.mark.asyncio
async def test_file_input_redirection(handler, tmp_path):
    """Test input redirection from a contained relative file."""
    (tmp_path / "input.txt").write_text("test content")
    redirects = {
        "stdin": "input.txt",
        "stdout": None,
        "stdout_append": False,
    }
    handles = await handler.setup_redirects(redirects, str(tmp_path))

    assert "stdin" in handles
    assert handles["stdin_data"] == "test content"
    assert isinstance(handles["stdout"], int)
    assert isinstance(handles["stderr"], int)


@pytest.mark.asyncio
async def test_file_output_redirection(handler, tmp_path):
    """Test output redirection to a contained relative file."""
    redirects = {
        "stdin": None,
        "stdout": "output.txt",
        "stdout_append": False,
    }
    handles = await handler.setup_redirects(redirects, str(tmp_path))

    assert "stdout" in handles
    assert not handles["stdout"].closed
    await handler.cleanup_handles(handles)
    assert (tmp_path / "output.txt").exists()


@pytest.mark.asyncio
async def test_append_mode(handler, tmp_path):
    """Test output redirection in append mode."""
    redirects = {
        "stdin": None,
        "stdout": "output.txt",
        "stdout_append": True,
    }
    handles = await handler.setup_redirects(redirects, str(tmp_path))
    assert handles["stdout"].mode == "a"
    await handler.cleanup_handles(handles)

    redirects["stdout_append"] = False
    handles = await handler.setup_redirects(redirects, str(tmp_path))
    assert handles["stdout"].mode == "w"
    await handler.cleanup_handles(handles)


def test_validate_redirection_syntax(handler):
    """Test validation of redirection syntax."""
    handler.validate_redirection_syntax(["echo", "hello", ">", "output.txt"])
    handler.validate_redirection_syntax(["cat", "<", "input.txt", ">", "output.txt"])
    handler.validate_redirection_syntax(["echo", "hello", ">>", "output.txt"])

    with pytest.raises(ValueError, match="consecutive operators"):
        handler.validate_redirection_syntax(["echo", ">", ">", "output.txt"])

    with pytest.raises(ValueError, match="consecutive operators"):
        handler.validate_redirection_syntax(["cat", "<", ">", "output.txt"])


def test_process_redirections(handler):
    """Test processing of redirection operators."""
    cmd, redirects = handler.process_redirections(["cat", "<", "input.txt"])
    assert cmd == ["cat"]
    assert redirects["stdin"] == "input.txt"
    assert redirects["stdout"] is None

    cmd, redirects = handler.process_redirections(["echo", "test", ">", "output.txt"])
    assert cmd == ["echo", "test"]
    assert redirects["stdout"] == "output.txt"
    assert not redirects["stdout_append"]

    cmd, redirects = handler.process_redirections(
        ["cat", "<", "in.txt", ">", "out.txt"]
    )
    assert cmd == ["cat"]
    assert redirects["stdin"] == "in.txt"
    assert redirects["stdout"] == "out.txt"


@pytest.mark.asyncio
async def test_setup_errors(handler, tmp_path):
    """Test error cases in redirection setup."""
    redirects = {
        "stdin": "nonexistent.txt",
        "stdout": None,
        "stdout_append": False,
    }
    with pytest.raises(ValueError, match="Failed to open input file"):
        await handler.setup_redirects(redirects, str(tmp_path))

    redirects = {
        "stdin": None,
        "stdout": "/tmp/output.txt",
        "stdout_append": False,
    }
    with pytest.raises(ValueError, match="Redirection path must be relative"):
        await handler.setup_redirects(redirects, str(tmp_path))


@pytest.mark.asyncio
async def test_absolute_input_path_rejected(handler, tmp_path):
    """Absolute input redirection is rejected before file open."""
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret")
    redirects = {"stdin": str(outside), "stdout": None, "stdout_append": False}

    with pytest.raises(ValueError, match="relative"):
        await handler.setup_redirects(redirects, str(tmp_path))


@pytest.mark.asyncio
async def test_parent_traversal_rejected(handler, tmp_path):
    """Parent traversal redirection is rejected before file open."""
    redirects = {"stdin": "../outside.txt", "stdout": None, "stdout_append": False}

    with pytest.raises(ValueError, match="parent traversal"):
        await handler.setup_redirects(redirects, str(tmp_path))


@pytest.mark.asyncio
async def test_symlink_escape_rejected(handler, tmp_path):
    """Symlink escapes are rejected by realpath/commonpath containment."""
    outside_dir = tmp_path.parent / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret")
    link = tmp_path / "link.txt"
    os.symlink(outside_file, link)
    redirects = {"stdin": "link.txt", "stdout": None, "stdout_append": False}

    with pytest.raises(ValueError, match="escapes working directory"):
        await handler.setup_redirects(redirects, str(tmp_path))


@pytest.mark.asyncio
async def test_shell_executor_redirect_writes_stay_inside_directory(tmp_path, monkeypatch):
    """Real executor writes only to relative paths in the working directory."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")
    executor = ShellExecutor()

    result = await executor.execute(["echo", "hello", ">", "out.txt"], str(tmp_path))
    assert result["error"] is None
    assert result["stdout"] == ""
    assert (tmp_path / "out.txt").read_text() == "hello\n"

    result = await executor.execute(["echo", "world", ">>", "out.txt"], str(tmp_path))
    assert result["error"] is None
    assert result["stdout"] == ""
    assert (tmp_path / "out.txt").read_text() == "hello\nworld\n"
