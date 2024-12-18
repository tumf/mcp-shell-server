import os


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest-asyncio defaults"""
    config.option.asyncio_mode = "strict"
    # Enable command execution for tests
    os.environ["ALLOW_COMMANDS"] = "1"
    # Add allowed commands for tests
    os.environ["ALLOWED_COMMANDS"] = (
        "echo,sleep,cat,ls,pwd,touch,mkdir,rm,mv,cp,grep,awk,sed"
    )
