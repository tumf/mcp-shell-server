"""
Test configuration and fixtures.
"""

import asyncio
from typing import IO
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def mock_file(mocker):
    """Provide a mock file object."""
    mock = mocker.MagicMock(spec=IO)
    mock.close = mocker.MagicMock()
    return mock


@pytest_asyncio.fixture
async def mock_process_manager():
    """Provide a mock process manager."""
    manager = MagicMock()

    # Mock process object
    process = AsyncMock()
    process.returncode = 0

    # Mock manager methods
    manager.create_process = AsyncMock()

    async def create_process_side_effect(*args, **kwargs):
        process = AsyncMock()
        process.returncode = 0
        process.communicate = AsyncMock(return_value=(b"", b""))
        process.kill = AsyncMock()
        process.wait = AsyncMock()
        return process

    manager.create_process.side_effect = create_process_side_effect

    manager.execute_with_timeout = AsyncMock()
    manager.execute_pipeline = AsyncMock()
    manager.cleanup_processes = AsyncMock()

    # Set empty default return values - tests should override these as needed
    manager.execute_with_timeout.return_value = (b"", b"")
    manager.execute_pipeline.return_value = (b"", b"", 0)

    return manager


@pytest_asyncio.fixture
async def shell_executor_with_mock(mock_process_manager):
    """Provide a shell executor with mock process manager."""
    executor = ShellExecutor(process_manager=mock_process_manager)
    return executor


@pytest.fixture
def temp_test_dir(tmpdir):
    """Provide a temporary test directory."""
    return str(tmpdir)


@pytest_asyncio.fixture(scope="function")
async def event_loop():
    """Create and provide a new event loop for each module."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # Clean up the event loop
    try:
        # Close all tasks
        tasks = asyncio.all_tasks(loop)
        if tasks:
            # Cancel all tasks and wait for their completion
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

        # Clean up all transports
        if hasattr(loop, "_transports"):
            for transport in list(loop._transports.values()):
                if hasattr(transport, "close"):
                    transport.close()

        # Cleanup
        loop.stop()
        asyncio.set_event_loop(None)
        await loop.shutdown_asyncgens()
        loop.close()
    except Exception as e:
        print(f"Error during loop cleanup: {e}")
