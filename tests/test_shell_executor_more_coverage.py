import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_private_validate_command_and_pipeline_ok(monkeypatch):
    """Test private _validate_command and _validate_pipeline methods with allowed commands to cover lines 48,72."""
    # Set environment to allow echo and cat commands
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")

    executor = ShellExecutor()

    # Test _validate_command with valid command (covers line 48)
    try:
        executor._validate_command(["echo"])  # Should not raise
    except ValueError:
        pytest.fail("_validate_command should not raise with allowed command")

    # Test _validate_pipeline with valid pipeline (covers line 72)
    result = executor._validate_pipeline(["echo", "|", "cat"])
    # Should return empty dict for success
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_timeout_with_stdout_handle_closed(monkeypatch, temp_test_dir):
    """Test execute method with timeout that closes stdout handle (covers lines 294, 300)."""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")

    # Create a ShellExecutor with mock process manager
    mock_process_manager = MagicMock()
    executor = ShellExecutor(process_manager=mock_process_manager)

    # Create a proper IO mock that will pass isinstance(stdout_handle, IO) check
    from typing import IO

    mock_stdout = MagicMock(spec=IO)
    mock_stdout.close = MagicMock()

    with patch.object(
        executor.io_handler,
        "setup_redirects",
        return_value={"stdout": mock_stdout, "stdin_data": None},
    ):
        # Mock process creation
        mock_process = AsyncMock()
        mock_process.returncode = None

        # Mock kill to raise ProcessLookupError to cover line 294
        async def kill_side_effect():
            raise ProcessLookupError("Process not found")

        mock_process.kill = AsyncMock(side_effect=kill_side_effect)
        mock_process.wait = AsyncMock()
        mock_process_manager.create_process = AsyncMock(return_value=mock_process)

        # Mock execute_with_timeout to raise TimeoutError
        mock_process_manager.execute_with_timeout = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        # Mock process_redirections to return simple command
        with patch.object(
            executor.io_handler,
            "process_redirections",
            return_value=(["sleep", "1"], {}),
        ):
            result = await executor.execute(["sleep", "1"], temp_test_dir, timeout=1)

        # Should return timeout error
        assert "timed out" in result["error"]
        assert result["status"] == -1

        # Verify stdout handle close was called (covers line 300)
        mock_stdout.close.assert_called_once()


@pytest.mark.asyncio
async def test_execute_generic_exception_closes_stdout_handle(
    monkeypatch, temp_test_dir
):
    """Test execute method with generic exception that closes stdout handle (covers line 312)."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")

    # Create a ShellExecutor with mock process manager
    mock_process_manager = MagicMock()
    executor = ShellExecutor(process_manager=mock_process_manager)

    # Create a proper IO mock that will pass isinstance(stdout_handle, IO) check
    from typing import IO

    mock_stdout = MagicMock(spec=IO)
    mock_stdout.close = MagicMock()

    with patch.object(
        executor.io_handler,
        "setup_redirects",
        return_value={"stdout": mock_stdout, "stdin_data": None},
    ):
        # Mock process creation
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process_manager.create_process = AsyncMock(return_value=mock_process)

        # Mock execute_with_timeout to raise RuntimeError
        mock_process_manager.execute_with_timeout = AsyncMock(
            side_effect=RuntimeError("Test error")
        )

        # Mock process_redirections to return simple command
        with patch.object(
            executor.io_handler,
            "process_redirections",
            return_value=(["echo", "test"], {}),
        ):
            result = await executor.execute(["echo", "test"], temp_test_dir)

        # Should return error result
        assert "Test error" in result["error"]
        assert result["status"] == 1

        # Verify stdout handle close was called (covers line 312)
        mock_stdout.close.assert_called_once()


@pytest.mark.asyncio
async def test_execute_directory_nonexist_and_notdir_paths(monkeypatch, temp_test_dir):
    """Test execute method with nonexistent directory and file path as directory (covers lines 188, 196)."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    executor = ShellExecutor()

    # Test nonexistent directory (covers line 188)
    nonexistent_dir = "/nonexistent/directory/path"
    result = await executor.execute(["echo", "test"], nonexistent_dir)
    assert "Directory does not exist" in result["error"]
    assert result["status"] == 1

    # Test file path instead of directory (covers line 196)
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name

    try:
        result = await executor.execute(["echo", "test"], temp_file_path)
        assert "Not a directory" in result["error"]
        assert result["status"] == 1
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


@pytest.mark.asyncio
async def test_pipeline_outer_except_in__execute_pipeline(monkeypatch, temp_test_dir):
    """Test _execute_pipeline method with outer exception handling (covers lines 415-416)."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,cat")

    # Create a ShellExecutor with mock process manager
    mock_process_manager = MagicMock()
    executor = ShellExecutor(process_manager=mock_process_manager)

    # Mock execute_pipeline to raise RuntimeError to hit outer except
    mock_process_manager.execute_pipeline = AsyncMock(
        side_effect=RuntimeError("Pipeline error")
    )

    # Mock cleanup_processes
    mock_process_manager.cleanup_processes = AsyncMock()

    # Mock io_handler cleanup_handles
    with patch.object(executor.io_handler, "cleanup_handles", AsyncMock()):
        result = await executor._execute_pipeline(
            [["echo", "test"], ["cat"]], temp_test_dir
        )

    # Should return error result from outer except block
    assert "Pipeline error" in result["error"]
    assert result["status"] == 1
    assert "execution_time" in result
