import pytest
import asyncio

# Configure pytest-asyncio to use function scope
def pytest_configure(config):
    config.option.asyncio_mode = "strict"

@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test case"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()