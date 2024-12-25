"""
Test configuration and fixtures.
"""

import asyncio
import os

import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def cleanup_loop():
    """Run after each test to ensure proper event loop cleanup."""
    yield
    if hasattr(asyncio, "current_task") and asyncio.current_task() is not None:
        try:
            await asyncio.sleep(0)  # Allow pending callbacks to complete
        except Exception:
            pass


def pytest_configure(config):
    """Configure pytest-asyncio defaults"""
    # Enable command execution for tests
    os.environ["ALLOW_COMMANDS"] = "1"
    # Add allowed commands for tests
    os.environ["ALLOWED_COMMANDS"] = (
        "echo,sleep,cat,ls,pwd,touch,mkdir,rm,mv,cp,grep,awk,sed"
    )
