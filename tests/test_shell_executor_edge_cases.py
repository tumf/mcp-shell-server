"""Edge case tests for the ShellExecutor class to improve coverage."""

import os
import pwd
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.fixture
def shell_executor():
    """Create ShellExecutor with default dependencies."""
    mock_process_manager = MagicMock()
    return ShellExecutor(process_manager=mock_process_manager)


def test_get_default_shell_fallback_env(shell_executor):
    """Test _get_default_shell falls back to SHELL environment variable when pwd.getpwuid raises exception."""
    # Mock pwd.getpwuid to raise KeyError
    with patch(
        "mcp_shell_server.shell_executor.pwd.getpwuid",
        side_effect=KeyError("User not found"),
    ):
        with patch.dict(os.environ, {"SHELL": "/bin/custom_shell"}):
            result = shell_executor._get_default_shell()
            assert result == "/bin/custom_shell"

    # Test ImportError fallback
    with patch(
        "mcp_shell_server.shell_executor.pwd.getpwuid",
        side_effect=ImportError("pwd module not available"),
    ):
        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            result = shell_executor._get_default_shell()
            assert result == "/bin/zsh"

    # Test fallback to /bin/sh when SHELL env var not set
    with patch(
        "mcp_shell_server.shell_executor.pwd.getpwuid",
        side_effect=KeyError("User not found"),
    ):
        with patch.dict(os.environ, {}, clear=True):
            result = shell_executor._get_default_shell()
            assert result == "/bin/sh"


@pytest.mark.asyncio
async def test_pipeline_validation_error_empty_before_pipe(shell_executor):
    """Test pipeline validation error when preprocess returns empty command before pipe."""
    with patch.dict(
        os.environ, {"ALLOW_COMMANDS": "true"}
    ):  # Set environment to allow commands
        with patch.object(
            shell_executor, "_validate_directory", return_value=None
        ):  # Mock directory validation
            with patch.object(
                shell_executor.preprocessor,
                "preprocess_command",
                return_value=["echo", "test", "|", "cat"],
            ):
                with patch.object(
                    shell_executor.preprocessor,
                    "clean_command",
                    return_value=["echo", "test", "|", "cat"],
                ):
                    with patch.object(
                        shell_executor.preprocessor,
                        "split_pipe_commands",
                        return_value=[],
                    ):  # Empty commands list
                        with patch.object(
                            shell_executor.validator,
                            "validate_pipeline",
                            return_value=None,
                        ):
                            with patch.object(
                                shell_executor.validator,
                                "validate_command",
                                return_value=None,
                            ):

                                # Execute command with pipe
                                result = await shell_executor.execute(
                                    command=["echo", "test", "|", "cat"],
                                    directory="/tmp",
                                )

                                # Verify error response for empty command before pipe
                                assert (
                                    result["error"]
                                    == "Empty command before pipe operator"
                                )
                                assert result["status"] == 1
                                assert (
                                    result["stderr"]
                                    == "Empty command before pipe operator"
                                )


@pytest.mark.asyncio
async def test_invalid_shell_operator_token(shell_executor):
    """Test error when cleaned_command contains invalid shell operators like '&&'."""
    with patch.dict(os.environ, {"ALLOW_COMMANDS": "true"}):
        with patch.object(
            shell_executor.preprocessor,
            "preprocess_command",
            return_value=["echo", "test", "&&", "echo", "more"],
        ):
            with patch.object(
                shell_executor.preprocessor,
                "clean_command",
                return_value=["echo", "test", "&&", "echo", "more"],
            ):
                with patch.object(
                    shell_executor.validator,
                    "validate_no_shell_operators",
                    side_effect=ValueError("Shell operator '&&' not allowed"),
                ):

                    # Execute command
                    result = await shell_executor.execute(
                        command=["echo", "test", "&&", "echo", "more"], directory="/tmp"
                    )

                    # Verify error response
                    assert result["error"] == "Shell operator '&&' not allowed"
                    assert result["status"] == 1
                    assert result["stderr"] == "Shell operator '&&' not allowed"


@pytest.mark.asyncio
async def test_parse_command_error_propagation(shell_executor):
    """Test that exceptions from parse_command are properly handled and return error dict."""
    with patch.dict(os.environ, {"ALLOW_COMMANDS": "true"}):
        with patch.object(
            shell_executor.preprocessor,
            "preprocess_command",
            return_value=["invalid", "command"],
        ):
            with patch.object(
                shell_executor.preprocessor,
                "clean_command",
                return_value=["invalid", "command"],
            ):
                with patch.object(
                    shell_executor.validator,
                    "validate_no_shell_operators",
                    return_value=None,
                ):
                    with patch.object(
                        shell_executor.preprocessor,
                        "parse_command",
                        side_effect=ValueError("Invalid command syntax"),
                    ):

                        # Execute command
                        result = await shell_executor.execute(
                            command=["invalid", "command"], directory="/tmp"
                        )

                        # Verify error dict is returned
                        assert result["error"] == "Invalid command syntax"
                        assert result["status"] == 1
                        assert result["stderr"] == "Invalid command syntax"
                        assert "execution_time" in result


@pytest.mark.asyncio
async def test_io_redirection_processing_error(shell_executor):
    """Test that exceptions from io_handler.process_redirections are handled and return error dict."""
    with patch.dict(os.environ, {"ALLOW_COMMANDS": "true"}):
        with patch.object(
            shell_executor.preprocessor,
            "preprocess_command",
            return_value=["echo", "test"],
        ):
            with patch.object(
                shell_executor.preprocessor,
                "clean_command",
                return_value=["echo", "test"],
            ):
                with patch.object(
                    shell_executor.validator,
                    "validate_no_shell_operators",
                    return_value=None,
                ):
                    with patch.object(
                        shell_executor.preprocessor,
                        "parse_command",
                        return_value=(["echo", "test"], {}),
                    ):
                        with patch.object(
                            shell_executor.validator,
                            "validate_command",
                            return_value=None,
                        ):
                            with patch.object(
                                shell_executor.io_handler,
                                "process_redirections",
                                side_effect=ValueError("Invalid redirection syntax"),
                            ):

                                # Execute command
                                result = await shell_executor.execute(
                                    command=["echo", "test", ">", "invalid"],
                                    directory="/tmp",
                                )

                                # Verify error dict is returned
                                assert result["error"] == "Invalid redirection syntax"
                                assert result["status"] == 1
                                assert result["stderr"] == "Invalid redirection syntax"
                                assert "execution_time" in result


@pytest.mark.asyncio
async def test_setup_redirects_stdout_as_int(shell_executor):
    """Test that setup_redirects returns stdout as int and it's properly handled in create_process."""
    import asyncio
    from typing import IO
    from unittest.mock import AsyncMock

    # Create a mock process
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"test output", b""))

    with patch.dict(os.environ, {"ALLOW_COMMANDS": "true"}):
        with patch.object(
            shell_executor.preprocessor,
            "preprocess_command",
            return_value=["echo", "test"],
        ):
            with patch.object(
                shell_executor.preprocessor,
                "clean_command",
                return_value=["echo", "test"],
            ):
                with patch.object(
                    shell_executor.validator,
                    "validate_no_shell_operators",
                    return_value=None,
                ):
                    with patch.object(
                        shell_executor.preprocessor,
                        "parse_command",
                        return_value=(["echo", "test"], {"stdout": ">"}),
                    ):
                        with patch.object(
                            shell_executor.validator,
                            "validate_command",
                            return_value=None,
                        ):
                            with patch.object(
                                shell_executor.io_handler,
                                "process_redirections",
                                return_value=(["echo", "test"], {"stdout": ">"}),
                            ):
                                with patch.object(
                                    shell_executor.io_handler,
                                    "setup_redirects",
                                    return_value={"stdout": 1, "stdin_data": None},
                                ):
                                    with patch.object(
                                        shell_executor.process_manager,
                                        "create_process",
                                        new_callable=AsyncMock,
                                        return_value=mock_process,
                                    ):
                                        with patch.object(
                                            shell_executor.process_manager,
                                            "execute_with_timeout",
                                            new_callable=AsyncMock,
                                            return_value=(b"test output", b""),
                                        ):
                                            with patch.object(
                                                shell_executor.preprocessor,
                                                "create_shell_command",
                                                return_value="echo test",
                                            ):

                                                # Execute command
                                                result = await shell_executor.execute(
                                                    command=[
                                                        "echo",
                                                        "test",
                                                        ">",
                                                        "output.txt",
                                                    ],
                                                    directory="/tmp",
                                                )

                                                # Verify successful execution
                                                assert result["error"] is None
                                                assert result["returncode"] == 0
                                                assert result["stdout"] == "test output"

                                                # Verify create_process was called with stdout handle as int
                                                create_process_call = (
                                                    shell_executor.process_manager.create_process.call_args
                                                )
                                                assert create_process_call is not None
                                                # Check that stdout_handle parameter was passed as int
                                                stdout_handle = create_process_call[
                                                    1
                                                ].get("stdout_handle")
                                                assert stdout_handle == 1
