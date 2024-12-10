# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest-asyncio defaults"""
    config.option.asyncio_mode = "strict"
