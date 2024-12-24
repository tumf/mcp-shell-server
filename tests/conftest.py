"""Test configuration and fixtures."""

import asyncio
import functools
import os
from typing import AsyncGenerator

import pytest_asyncio


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest-asyncio defaults"""
    # Enable command execution for tests
    os.environ["ALLOW_COMMANDS"] = "1"
    # Add allowed commands for tests
    os.environ["ALLOWED_COMMANDS"] = (
        "echo,sleep,cat,ls,pwd,touch,mkdir,rm,mv,cp,grep,awk,sed"
    )


@pytest_asyncio.fixture()
async def cleanup_processes() -> AsyncGenerator[None, None]:
    """Ensure all subprocess are cleaned up after each test."""
    yield
    loop = asyncio.get_running_loop()

    # Patch the close method to avoid errors during cleanup
    def quiet_close(self):
        try:
            self.close()
        except RuntimeError:
            pass

    for transport in getattr(loop, "_transports", set()).copy():
        if hasattr(transport, "_proc"):
            transport.close = functools.partial(quiet_close, transport)

    try:
        # Get all tasks and wait for them to complete
        tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
        if tasks:
            # Cancel all tasks and wait for them to complete
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        # Shutdown async generators
        await loop.shutdown_asyncgens()
    except Exception as e:
        print(f"Error during cleanup: {e}")
