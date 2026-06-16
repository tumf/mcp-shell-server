"""Tests for the ProcessManager class."""

import asyncio
import os
import shlex
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_shell_server.process_manager import OutputLimitExceeded, ProcessManager


def create_mock_process():
    """Create a mock process with all required attributes."""
    process = MagicMock()
    process.returncode = 0
    process.communicate = AsyncMock(return_value=(b"output", b"error"))
    process.wait = AsyncMock(return_value=0)
    process.terminate = MagicMock()
    process.kill = MagicMock()
    process.stdout = None
    process.stderr = None
    process.stdin = None
    return process


@pytest.fixture
def process_manager():
    """Fixture for ProcessManager instance."""
    return ProcessManager()


@pytest.mark.asyncio
async def test_create_process(process_manager):
    """Test creating a process with argv-based parameters."""
    mock_proc = create_mock_process()
    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ) as mock_create:
        process = await process_manager.create_process(
            ["echo", "test"],
            directory="/tmp",
            stdin="input",
        )

        assert process == mock_proc
        mock_create.assert_called_once()
        assert mock_create.call_args.args == ("echo", "test")


@pytest.mark.asyncio
async def test_create_process_string_adapter_still_uses_exec(process_manager):
    """Backward-compatible string adapter must still avoid shell execution."""
    mock_proc = create_mock_process()
    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ) as mock_create:
        process = await process_manager.create_process("echo test", directory="/tmp")

    assert process == mock_proc
    assert mock_create.call_args.args == ("echo", "test")


@pytest.mark.asyncio
async def test_create_process_uses_minimal_child_environment(
    process_manager, monkeypatch
):
    """Child processes do not inherit unrelated parent environment variables."""
    monkeypatch.setenv("SECRET_TOKEN", "parent-secret")
    monkeypatch.setenv("UNRELATED_PARENT_VAR", "parent-value")
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)
    mock_proc = create_mock_process()

    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ) as mock_create:
        await process_manager.create_process("echo 'test'", directory="/tmp")

    child_env = mock_create.call_args.kwargs["env"]
    assert child_env["PATH"] == os.environ.get("PATH", os.defpath)
    assert "SECRET_TOKEN" not in child_env
    assert "UNRELATED_PARENT_VAR" not in child_env


@pytest.mark.asyncio
async def test_create_process_filters_envs_by_allowlist(process_manager, monkeypatch):
    """Only allowlisted keys can be inherited from parent or injected via envs."""
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "TEST_VAR, PARENT_ALLOWED")
    monkeypatch.setenv("PARENT_ALLOWED", "parent-allowed-value")
    monkeypatch.setenv("PARENT_DISALLOWED", "parent-disallowed-value")
    mock_proc = create_mock_process()

    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_shell",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ) as mock_create:
        await process_manager.create_process(
            "echo 'test'",
            directory="/tmp",
            envs={"TEST_VAR": "injected-value", "PARENT_DISALLOWED": "blocked"},
        )

    child_env = mock_create.call_args.kwargs["env"]
    assert child_env["TEST_VAR"] == "injected-value"
    assert child_env["PARENT_ALLOWED"] == "parent-allowed-value"
    assert "PARENT_DISALLOWED" not in child_env


@pytest.mark.asyncio
async def test_child_process_cannot_observe_parent_secret_by_default(
    process_manager, monkeypatch
):
    """Integration coverage: parent secret variables are absent by default."""
    monkeypatch.setenv("SECRET_TOKEN", "parent-secret")
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)

    python = shlex.quote(sys.executable)
    script = "import os; print(os.getenv('SECRET_TOKEN', ''))"
    process = await process_manager.create_process(
        f"{python} -c {shlex.quote(script)}", directory=None
    )
    stdout, stderr = await process_manager.execute_with_timeout(process, timeout=1)

    assert stderr == b""
    assert stdout == b"\n"
    assert process.returncode == 0


@pytest.mark.asyncio
async def test_execute_with_timeout_success(process_manager):
    """Test executing a process with successful completion."""
    mock_proc = create_mock_process()
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
    mock_proc.communicate.side_effect = asyncio.TimeoutError("Process timed out")
    mock_proc.returncode = None

    async def set_returncode():
        mock_proc.returncode = -15

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

    mock_proc2 = create_mock_process()
    mock_proc2.communicate.return_value = (b"final output", b"")

    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        side_effect=[mock_proc1, mock_proc2],
    ) as mock_create:
        stdout, stderr, return_code = await process_manager.execute_pipeline(
            [["echo", "test"], ["grep", "test"]],
            directory="/tmp",
            timeout=10,
        )

        assert stdout == b"final output"
        assert stderr == b""
        assert return_code == 0
        assert mock_create.call_count == 2
        assert mock_create.call_args_list[0].args == ("echo", "test")
        assert mock_create.call_args_list[1].args == ("grep", "test")


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
                [["invalid_command"]],
                directory="/tmp",
            )


@pytest.mark.asyncio
async def test_cleanup_processes(process_manager):
    """Test cleaning up processes."""
    running_proc = create_mock_process()
    running_proc.returncode = None
    running_proc.wait.side_effect = [asyncio.TimeoutError(), None]

    completed_proc = create_mock_process()
    completed_proc.returncode = 0

    await process_manager.cleanup_processes([running_proc, completed_proc])

    running_proc.terminate.assert_called_once()
    assert running_proc.wait.await_count == 2
    completed_proc.kill.assert_not_called()
    completed_proc.wait.assert_not_called()


@pytest.mark.asyncio
async def test_create_process_with_error(process_manager):
    """Test creating a process that fails to start."""
    with patch(
        "asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        side_effect=OSError("Failed to create process"),
    ):
        with pytest.raises(ValueError, match="Failed to create process"):
            await process_manager.create_process(["invalid"], directory="/tmp")


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
                [["sleep", "10"]],
                directory="/tmp",
                timeout=1,
            )


@pytest.mark.asyncio
async def test_output_limit_is_enforced_with_mocked_communicate(process_manager):
    """Output exceeding the byte cap raises and preserves truncated bytes."""
    mock_proc = create_mock_process()
    mock_proc.communicate.return_value = (b"abcdef", b"")

    with pytest.raises(OutputLimitExceeded) as exc_info:
        await process_manager.execute_with_timeout(mock_proc, timeout=5, output_limit=3)

    assert exc_info.value.stream_name == "stdout"
    assert exc_info.value.stdout == b"abc"


def test_child_environment_does_not_inherit_secrets(process_manager, monkeypatch):
    """Parent secrets are not copied unless explicitly allowlisted."""
    monkeypatch.setenv("SECRET_TOKEN", "do-not-leak")
    monkeypatch.delenv("MCP_SHELL_ENV_ALLOWLIST", raising=False)

    env = process_manager.build_child_environment()

    assert "SECRET_TOKEN" not in env
    assert env["PATH"]


def test_child_environment_allows_documented_allowlist(process_manager, monkeypatch):
    """Configured allowlisted variables are copied into the child env."""
    monkeypatch.setenv("MCP_SHELL_ENV_ALLOWLIST", "SAFE_VAR")
    monkeypatch.setenv("SAFE_VAR", "visible")

    env = process_manager.build_child_environment()

    assert env["SAFE_VAR"] == "visible"
