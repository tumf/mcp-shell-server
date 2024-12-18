import pytest

from mcp_shell_server.server import ExecuteToolHandler


@pytest.mark.asyncio
async def test_server_input_validation():
    """Test input validation in execute tool"""
    handler = ExecuteToolHandler()

    # Test command must be an array
    with pytest.raises(ValueError, match="'command' must be an array"):
        await handler.run_tool({"command": "not an array", "directory": "/"})

    # Test directory is required
    with pytest.raises(ValueError, match="Directory is required"):
        await handler.run_tool({"command": ["echo", "test"], "directory": ""})

    # Test command without arguments
    with pytest.raises(ValueError, match="No command provided"):
        await handler.run_tool({"directory": "/"})
