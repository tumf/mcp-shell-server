"""Tests for the ProcessManager class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_shell_server.process_manager import ProcessManager


def create_mock_process():
    """Create a mock process with all required attributes."""
    process = MagicMock()
    process.returncode = 0
    process.communicate = AsyncMock(return_value=(b"output", b"error"))
    process.wait = AsyncMock(return_value=0)
    process.terminate = MagicMock()
    process.kill = MagicMock()
    return process


@pytest.fixture
def process_manager():
    """Fixture for ProcessManager instance."""
    return ProcessManager()


@pytest.mark.asyncio
async def test_create_process(process_manager):
    """Test creating a process with basic parameters."""
    mock_proc = create_mock_process()
    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ) as mock_create:
        process = await process_manager.create_process(
            "echo 'test'",
            directory="/tmp",
            stdin="input",
        )

        assert process == mock_proc
        assert process == mock_proc
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_timeout_success(process_manager):
    """Test executing a process with successful completion."""
    mock_proc = create_mock_process()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"output", b"error")

    stdout, stderr = await process_manager.execute_with_timeout(
        mock_proc,
        stdin="input",
        timeout=10,
    )

    assert stdout == b"output"
    assert stderr == b"error"
    mock_proc.communicate.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_timeout_timeout(process_manager):
    """Test executing a process that times out."""
    mock_proc = create_mock_process()
    exc = asyncio.TimeoutError("Process timed out")
    mock_proc.communicate.side_effect = exc
    mock_proc.returncode = None  # プロセスがまだ実行中の状態をシミュレート

    # プロセスの終了状態をシミュレート
    async def set_returncode():
        mock_proc.returncode = -15  # SIGTERM

    mock_proc.wait.side_effect = set_returncode

    with pytest.raises(TimeoutError):
        await process_manager.execute_with_timeout(
            mock_proc,
            timeout=1,
        )

    mock_proc.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_execute_pipeline_success(process_manager):
    """Test executing a pipeline of commands successfully."""
    mock_proc1 = create_mock_process()
    mock_proc1.communicate.return_value = (b"output1", b"")
    mock_proc1.returncode = 0

    mock_proc2 = create_mock_process()
    mock_proc2.communicate.return_value = (b"final output", b"")
    mock_proc2.returncode = 0

    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        side_effect=[mock_proc1, mock_proc2],
    ) as mock_create:
        stdout, stderr, return_code = await process_manager.execute_pipeline(
            ["echo 'test'", "grep test"],
            directory="/tmp",
            timeout=10,
        )

        assert stdout == b"final output"
        assert stderr == b""
        assert return_code == 0
        assert mock_create.call_count == 2  # Verify subprocess creation calls

        # Verify the command arguments for each subprocess call
        calls = mock_create.call_args_list
        assert "echo" in calls[0].args[0]
        assert "grep" in calls[1].args[0]


@pytest.mark.asyncio
async def test_execute_pipeline_with_error(process_manager):
    """Test executing a pipeline where a command fails."""
    mock_proc = create_mock_process()
    mock_proc.communicate.return_value = (b"", b"error message")
    mock_proc.returncode = 1

    create_process_mock = AsyncMock(return_value=mock_proc)

    with patch.object(process_manager, "create_process", create_process_mock):
        with pytest.raises(ValueError, match="error message"):
            await process_manager.execute_pipeline(
                ["invalid_command"],
                directory="/tmp",
            )


@pytest.mark.asyncio
async def test_cleanup_processes(process_manager):
    """Test cleaning up processes."""
    # Create mock processes with different states
    running_proc = create_mock_process()
    running_proc.returncode = None

    completed_proc = create_mock_process()
    completed_proc.returncode = 0

    # Execute cleanup
    await process_manager.cleanup_processes([running_proc, completed_proc])

    # Verify running process was killed and waited for
    running_proc.kill.assert_called_once()
    running_proc.wait.assert_awaited_once()

    # Verify completed process was not killed or waited for
    completed_proc.kill.assert_not_called()
    completed_proc.wait.assert_not_called()


@pytest.mark.asyncio
async def test_create_process_with_error(process_manager):
    """Test creating a process that fails to start."""
    with patch(
        "asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        side_effect=OSError("Failed to create process"),
    ):
        with pytest.raises(ValueError, match="Failed to create process"):
            await process_manager.create_process("invalid command", directory="/tmp")


@pytest.mark.asyncio
async def test_execute_pipeline_empty_commands(process_manager):
    """Test executing a pipeline with no commands."""
    with pytest.raises(ValueError, match="No commands provided"):
        await process_manager.execute_pipeline([], directory="/tmp")


@pytest.mark.asyncio
async def test_execute_pipeline_timeout(process_manager):
    """Test executing a pipeline that times out."""
    mock_proc = create_mock_process()
    mock_proc.communicate.side_effect = TimeoutError("Process timed out")

    with patch.object(process_manager, "create_process", return_value=mock_proc):
        with pytest.raises(TimeoutError, match="Process timed out"):
            await process_manager.execute_pipeline(
                ["sleep 10"],
                directory="/tmp",
                timeout=1,
            )
            mock_proc.kill.assert_called_once()
