"""Additional tests for the ProcessManager class to improve coverage."""

import asyncio
import logging
import os
import signal
from typing import IO
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from mcp_shell_server.process_manager import ProcessManager


def create_mock_process(returncode=0):
    """Create a mock process with all required attributes."""
    process = MagicMock()
    process.returncode = returncode
    process.communicate = AsyncMock(return_value=(b"output", b"error"))
    process.wait = AsyncMock(return_value=returncode)
    process.terminate = MagicMock()
    process.kill = MagicMock()
    return process


@pytest.fixture
def process_manager():
    """Fixture for ProcessManager instance."""
    return ProcessManager()


@pytest.mark.asyncio
async def test_start_process_sets_is_running(process_manager):
    """Test that start_process sets is_running attribute correctly."""
    mock_proc = create_mock_process()
    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ):
        # Test start_process
        process = await process_manager.start_process(["echo", "test"])

        # Verify is_running attribute is set
        assert hasattr(process, "is_running")

        # Test is_running when returncode is None (running)
        mock_proc.returncode = None
        assert process.is_running() is True

        # Test is_running when returncode is set (finished)
        mock_proc.returncode = 0
        assert process.is_running() is False


@pytest.mark.asyncio
async def test_start_process_async_sets_is_running(process_manager):
    """Test that start_process_async sets is_running attribute correctly."""
    mock_proc = create_mock_process()
    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ):
        # Test start_process_async
        process = await process_manager.start_process_async(["echo", "test"])

        # Verify is_running attribute is set
        assert hasattr(process, "is_running")

        # Test is_running when returncode is None (running)
        mock_proc.returncode = None
        assert process.is_running() is True

        # Test is_running when returncode is set (finished)
        mock_proc.returncode = 0
        assert process.is_running() is False


@pytest.mark.asyncio
async def test_cleanup_all_clears_and_kills(process_manager):
    """Test that cleanup_all kills tracked processes and clears the set."""
    # Create mock processes
    mock_proc1 = create_mock_process()
    mock_proc2 = create_mock_process()
    mock_proc1.returncode = None  # Still running
    mock_proc2.returncode = None  # Still running

    # Add processes to tracked set
    process_manager._processes.add(mock_proc1)
    process_manager._processes.add(mock_proc2)

    # Mock cleanup_processes to simulate killing processes
    with patch.object(
        process_manager, "cleanup_processes", new_callable=AsyncMock
    ) as mock_cleanup:
        await process_manager.cleanup_all()

        # Verify cleanup_processes was called with the tracked processes
        mock_cleanup.assert_called_once()
        called_processes = list(mock_cleanup.call_args[0][0])
        assert len(called_processes) == 2
        assert mock_proc1 in called_processes
        assert mock_proc2 in called_processes

        # Verify _processes set is cleared
        assert len(process_manager._processes) == 0


@pytest.mark.asyncio
async def test_execute_with_timeout_generic_exception(process_manager):
    """Test that generic exceptions in communicate() cause process to be killed and exception re-raised."""
    mock_proc = create_mock_process()

    # Make communicate raise a generic exception
    generic_error = RuntimeError("Communication failed")
    mock_proc.communicate = AsyncMock(side_effect=generic_error)
    mock_proc.returncode = None  # Process is running

    # Execute with timeout should kill process and re-raise exception
    with pytest.raises(RuntimeError, match="Communication failed"):
        await process_manager.execute_with_timeout(mock_proc, timeout=10)

    # Verify process was terminated/killed
    mock_proc.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_create_process_unexpected_exception():
    """Test that unexpected exceptions in create_subprocess_shell are converted to ValueError."""
    process_manager = ProcessManager()

    # Mock asyncio.create_subprocess_shell to raise an unexpected exception
    unexpected_error = RuntimeError("Unexpected system error")
    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        side_effect=unexpected_error,
    ):
        # Should convert to ValueError with specific message
        with pytest.raises(
            ValueError, match="Unexpected error during process creation"
        ):
            await process_manager.create_process("echo test", directory="/tmp")


@pytest.mark.asyncio
async def test_execute_pipeline_last_stdout_handle(process_manager):
    """Test that execute_pipeline writes to IO handle when last_stdout is provided."""
    # Create a mock IO object
    mock_io = MagicMock(spec=IO)

    # Create a mock process that succeeds
    mock_proc = create_mock_process(returncode=0)
    mock_proc.communicate = AsyncMock(return_value=(b"test output", b""))

    with patch.object(
        process_manager,
        "create_process",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ):
        with patch.object(
            process_manager,
            "execute_with_timeout",
            new_callable=AsyncMock,
            return_value=(b"test output", b""),
        ):
            with patch.object(
                process_manager, "cleanup_processes", new_callable=AsyncMock
            ):

                # Execute pipeline with IO handle
                stdout, stderr, returncode = await process_manager.execute_pipeline(
                    ["echo test"], last_stdout=mock_io
                )

                # Verify write was called on the IO handle
                mock_io.write.assert_called_once_with("test output")

                # Verify return values
                assert stderr == b""
                assert returncode == 0


@pytest.mark.asyncio
async def test_execute_pipeline_empty_stderr_nonzero_return(process_manager):
    """Test that execute_pipeline provides default error message when stderr is empty and returncode != 0."""
    # Create a mock process that fails with empty stderr
    mock_proc = create_mock_process(returncode=1)
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))  # Empty stderr

    with patch.object(
        process_manager,
        "create_process",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ):
        with patch.object(
            process_manager,
            "execute_with_timeout",
            new_callable=AsyncMock,
            return_value=(b"", b""),
        ):
            with patch.object(
                process_manager, "cleanup_processes", new_callable=AsyncMock
            ):

                # Should raise ValueError with default message
                with pytest.raises(ValueError, match="Command failed with exit code 1"):
                    await process_manager.execute_pipeline(["failing_command"])


@pytest.mark.asyncio
async def test_signal_handler_termination(process_manager):
    """Test that signal handler terminates tracked processes and calls os.kill."""
    if os.name != "posix":
        pytest.skip("Signal handling only available on POSIX systems")

    # Create mock processes
    mock_proc1 = create_mock_process()
    mock_proc2 = create_mock_process()
    mock_proc1.returncode = None  # Still running
    mock_proc2.returncode = None  # Still running

    # Add processes to tracked set
    process_manager._processes.add(mock_proc1)
    process_manager._processes.add(mock_proc2)

    # Mock os.kill to prevent actual signal sending
    with patch("mcp_shell_server.process_manager.os.kill") as mock_os_kill:
        with patch("mcp_shell_server.process_manager.signal.signal") as mock_signal:
            # Get the signal handler that was registered
            original_handler = MagicMock()
            mock_signal.return_value = original_handler

            # Re-initialize to set up signal handlers
            new_process_manager = ProcessManager()

            # Get the registered signal handler
            signal_handler_calls = mock_signal.call_args_list
            sigint_handler = None
            for call in signal_handler_calls:
                if call[0][0] == signal.SIGINT:
                    sigint_handler = call[0][1]
                    break

            assert sigint_handler is not None, "SIGINT handler should be registered"

            # Add processes to the new manager
            new_process_manager._processes.add(mock_proc1)
            new_process_manager._processes.add(mock_proc2)
            new_process_manager._original_sigint_handler = original_handler

            # Trigger the signal handler
            sigint_handler(signal.SIGINT, None)

            # Verify processes were terminated
            mock_proc1.terminate.assert_called_once()
            mock_proc2.terminate.assert_called_once()

            # Verify os.kill was called to re-raise the signal
            mock_os_kill.assert_called_once()
            call_args = mock_os_kill.call_args
            assert call_args[0][0] == os.getpid()  # Current process PID
            assert call_args[0][1] == signal.SIGINT  # SIGINT signal
