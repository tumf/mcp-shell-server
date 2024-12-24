"""Tests for the ProcessManager class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_shell_server.process_manager import ProcessManager


@pytest.fixture
def process_manager():
    """Fixture for ProcessManager instance."""
    return ProcessManager()


@pytest.mark.asyncio
async def test_create_process(process_manager):
    """Test creating a process with basic parameters."""
    mock_process = AsyncMock()
    mock_process.returncode = 0

    with patch(
        "asyncio.create_subprocess_shell", return_value=mock_process
    ) as mock_create:
        process = await process_manager.create_process(
            "echo 'test'",
            directory="/tmp",
            stdin="input",
        )

        assert process == mock_process
        mock_create.assert_called_once()
        args = mock_create.call_args[0]
        kwargs = mock_create.call_args[1]
        assert args[0] == "echo 'test'"
        assert kwargs["stdin"] == asyncio.subprocess.PIPE
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        assert kwargs["stderr"] == asyncio.subprocess.PIPE
        assert kwargs["cwd"] == "/tmp"


@pytest.mark.asyncio
async def test_execute_with_timeout_success(process_manager):
    """Test executing a process with successful completion."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"output", b"error")
    mock_process.returncode = 0

    stdout, stderr = await process_manager.execute_with_timeout(
        mock_process,
        stdin="input",
        timeout=10,
    )

    assert stdout == b"output"
    assert stderr == b"error"
    mock_process.communicate.assert_called_once_with(input=b"input")


@pytest.mark.asyncio
async def test_execute_with_timeout_timeout(process_manager):
    """Test executing a process that times out."""
    mock_process = AsyncMock()
    mock_process.communicate.side_effect = asyncio.TimeoutError()
    mock_process.returncode = None

    with pytest.raises(asyncio.TimeoutError):
        await process_manager.execute_with_timeout(
            mock_process,
            timeout=1,
        )


@pytest.mark.asyncio
async def test_execute_pipeline_success(process_manager):
    """Test executing a pipeline of commands successfully."""
    mock_process1 = AsyncMock()
    mock_process1.communicate.return_value = (b"output1", b"")
    mock_process1.returncode = 0

    mock_process2 = AsyncMock()
    mock_process2.communicate.return_value = (b"final output", b"")
    mock_process2.returncode = 0

    create_process_mock = AsyncMock(side_effect=[mock_process1, mock_process2])

    with patch.object(process_manager, "create_process", create_process_mock):
        stdout, stderr, return_code = await process_manager.execute_pipeline(
            ["echo 'test'", "grep test"],
            directory="/tmp",
            timeout=10,
        )

        assert stdout == b"final output"
        assert stderr == b""
        assert return_code == 0
        assert create_process_mock.call_count == 2


@pytest.mark.asyncio
async def test_execute_pipeline_with_error(process_manager):
    """Test executing a pipeline where a command fails."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"error message")
    mock_process.returncode = 1
    mock_process.kill = MagicMock()  # killはMagicMockに
    mock_process.wait = AsyncMock()  # waitはそのままAsyncMockに

    create_process_mock = AsyncMock(return_value=mock_process)

    with patch.object(process_manager, "create_process", create_process_mock):
        with pytest.raises(ValueError, match="error message"):
            await process_manager.execute_pipeline(
                ["invalid_command"],
                directory="/tmp",
            )

            mock_process.kill.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_processes(process_manager):
    """Test cleaning up processes."""
    mock_process1 = AsyncMock()
    mock_process1.returncode = None
    mock_process1.kill = MagicMock()  # killはMagicMockに
    mock_process1.wait = AsyncMock()  # waitはそのままAsyncMockに

    mock_process2 = AsyncMock()
    mock_process2.returncode = 0
    mock_process2.kill = MagicMock()  # killはMagicMockに
    mock_process2.wait = AsyncMock()  # waitはそのままAsyncMockに

    await process_manager.cleanup_processes([mock_process1, mock_process2])

    mock_process1.kill.assert_called_once()
    assert mock_process1.wait.await_count == 1
    assert not mock_process2.kill.called
    assert mock_process2.wait.await_count == 0  # waitも呼び出されていないことを確認
