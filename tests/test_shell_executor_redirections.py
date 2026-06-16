"""Tests for contained IO redirection handling."""

import os
from unittest.mock import patch

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
    with pytest.raises(ValueError, match="Redirection target must be relative to the working directory"):
        await handler.setup_redirects(redirects, str(tmp_path))


@pytest.mark.asyncio
async def test_input_redirection_rejects_absolute_path_before_open(handler, tmp_path):
    """Absolute input targets are rejected before file open."""
    redirects = {
        "stdin": os.path.join(str(tmp_path), "secret.txt"),
        "stdout": None,
        "stdout_append": False,
    }

    with patch("builtins.open") as mock_open:
        with pytest.raises(ValueError, match="Redirection target must be relative to the working directory"):
            await handler.setup_redirects(redirects, str(tmp_path))

    mock_open.assert_not_called()


@pytest.mark.asyncio
async def test_input_redirection_rejects_parent_traversal_before_open(handler, tmp_path):
    """Parent traversal input targets are rejected before file open."""
    redirects = {
        "stdin": "../secret.txt",
        "stdout": None,
        "stdout_append": False,
    }

    with patch("builtins.open") as mock_open:
        with pytest.raises(ValueError, match="parent traversal"):
            await handler.setup_redirects(redirects, str(tmp_path))

    mock_open.assert_not_called()


@pytest.mark.asyncio
async def test_output_redirection_rejects_parent_traversal_before_open(handler, tmp_path):
    """Parent traversal output targets are rejected before truncating files."""
    outside_file = tmp_path.parent / "outside.txt"
    outside_file.write_text("keep me", encoding="utf-8")
    redirects = {
        "stdin": None,
        "stdout": "../outside.txt",
        "stdout_append": False,
    }

    with patch("builtins.open") as mock_open:
        with pytest.raises(ValueError, match="parent traversal"):
            await handler.setup_redirects(redirects, str(tmp_path))

    mock_open.assert_not_called()
    assert outside_file.read_text(encoding="utf-8") == "keep me"


@pytest.mark.asyncio
async def test_input_redirection_rejects_symlink_escape_before_open(handler, tmp_path):
    """Symlink input targets that resolve outside directory are rejected."""
    outside_file = tmp_path.parent / "outside-input.txt"
    outside_file.write_text("secret", encoding="utf-8")
    symlink_path = tmp_path / "input-link.txt"
    try:
        os.symlink(outside_file, symlink_path)
    except OSError as e:  # pragma: no cover - platform/filesystem dependent
        pytest.skip(f"symlink creation unavailable: {e}")

    redirects = {
        "stdin": symlink_path.name,
        "stdout": None,
        "stdout_append": False,
    }

    with patch("builtins.open") as mock_open:
        with pytest.raises(ValueError, match="escapes the working directory"):
            await handler.setup_redirects(redirects, str(tmp_path))

    mock_open.assert_not_called()


@pytest.mark.asyncio
async def test_valid_in_directory_input_redirection_reads_file(handler, tmp_path):
    """Contained input redirection continues to read in-directory files."""
    input_file = tmp_path / "input.txt"
    input_file.write_text("contained input", encoding="utf-8")
    redirects = {
        "stdin": input_file.name,
        "stdout": None,
        "stdout_append": False,
    }

    handles = await handler.setup_redirects(redirects, str(tmp_path))

    assert handles["stdin_data"] == "contained input"
    assert isinstance(handles["stdout"], int)
    assert isinstance(handles["stderr"], int)


@pytest.mark.asyncio
async def test_output_redirection_rejects_symlink_escape_before_truncate(handler, tmp_path):
    """Symlink output targets outside directory are rejected before truncation."""
    outside_file = tmp_path.parent / "outside-output.txt"
    outside_file.write_text("keep me", encoding="utf-8")
    symlink_path = tmp_path / "output-link.txt"
    try:
        os.symlink(outside_file, symlink_path)
    except OSError as e:  # pragma: no cover - platform/filesystem dependent
        pytest.skip(f"symlink creation unavailable: {e}")

    redirects = {
        "stdin": None,
        "stdout": symlink_path.name,
        "stdout_append": False,
    }

    with patch("builtins.open") as mock_open:
        with pytest.raises(ValueError, match="escapes the working directory"):
            await handler.setup_redirects(redirects, str(tmp_path))

    mock_open.assert_not_called()
    assert outside_file.read_text(encoding="utf-8") == "keep me"


@pytest.mark.asyncio
async def test_shell_executor_rejects_escaped_output_without_modifying_file(
    tmp_path, monkeypatch
):
    """Executor fails closed for output traversal and leaves outside files intact."""
    monkeypatch.setenv("ALLOW_COMMANDS", "printf")
    outside_file = tmp_path.parent / "executor-outside.txt"
    outside_file.write_text("keep me", encoding="utf-8")

    executor = ShellExecutor()
    result = await executor.execute(
        ["printf", "changed", ">", "../executor-outside.txt"], str(tmp_path)
    )

    assert result["status"] == 1
    assert "parent traversal" in result["error"]
    assert outside_file.read_text(encoding="utf-8") == "keep me"


@pytest.mark.asyncio
async def test_shell_executor_writes_and_appends_inside_directory(tmp_path, monkeypatch):
    """Valid > and >> redirections write contained files and return metadata."""
    monkeypatch.setenv("ALLOW_COMMANDS", "printf")
    output_file = tmp_path / "result.txt"

    executor = ShellExecutor()
    write_result = await executor.execute(
        ["printf", "hello", ">", output_file.name], str(tmp_path)
    )
    append_result = await executor.execute(
        ["printf", "world", ">>", output_file.name], str(tmp_path)
    )

    assert write_result["error"] is None
    assert write_result["status"] == 0
    assert write_result["stdout"] == ""
    assert write_result["directory"] == str(tmp_path)
    assert append_result["error"] is None
    assert append_result["status"] == 0
    assert output_file.read_text(encoding="utf-8") == "helloworld"


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

    with pytest.raises(ValueError, match="Redirection target escapes the working directory"):
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
