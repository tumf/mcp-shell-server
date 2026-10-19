"""Tests for the ProcessManager class."""

import asyncio
import os
import shlex
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_shell_server import process_manager as process_manager_module
from mcp_shell_server.process_manager import (
    DEFAULT_SAFE_PATH,
    OutputLimitExceeded,
    ProcessManager,
    build_child_environment,
)


class _OsNameProxy:
    """Module-scoped ``os`` stand-in that only overrides ``os.name``."""

    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        return getattr(os, attr)


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
    monkeypatch.setenv("PATH", "/parent/shadow/bin:/usr/bin")
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)
    monkeypatch.delenv("MCP_SHELL_SAFE_PATH", raising=False)
    mock_proc = create_mock_process()

    with patch(
        "mcp_shell_server.process_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ) as mock_create:
        await process_manager.create_process("echo 'test'", directory="/tmp")

    mock_create.assert_called_once()
    assert mock_create.call_args.args == ("echo", "test")
    child_env = mock_create.call_args.kwargs["env"]
    assert child_env["PATH"] == DEFAULT_SAFE_PATH
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
        "mcp_shell_server.process_manager.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        return_value=mock_proc,
    ) as mock_create:
        await process_manager.create_process(
            "echo 'test'",
            directory="/tmp",
            envs={"TEST_VAR": "injected-value", "PARENT_DISALLOWED": "blocked"},
        )

    mock_create.assert_called_once()
    assert mock_create.call_args.args == ("echo", "test")
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


@pytest.mark.asyncio
async def test_execute_with_timeout_terminates_real_process(process_manager):
    """Timed-out subprocesses are terminated and reaped promptly."""
    process = await process_manager.create_process(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        directory=None,
    )

    with pytest.raises(asyncio.TimeoutError):
        await process_manager.execute_with_timeout(process, timeout=0.05)

    assert process.returncode is not None


@pytest.mark.asyncio
async def test_output_limit_terminates_real_high_output_process(process_manager):
    """High-output subprocesses are capped without buffering full output."""
    process = await process_manager.create_process(
        [sys.executable, "-c", "import sys; sys.stdout.write('x' * 4096)"],
        directory=None,
    )

    with pytest.raises(OutputLimitExceeded) as exc_info:
        await process_manager.execute_with_timeout(process, timeout=1, output_limit=64)

    assert exc_info.value.stream_name == "stdout"
    assert exc_info.value.stdout == b"x" * 64
    assert process.returncode is not None


def test_child_environment_does_not_inherit_secrets(process_manager, monkeypatch):
    """Parent secrets are not copied unless explicitly allowlisted."""
    monkeypatch.setenv("SECRET_TOKEN", "do-not-leak")
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "SAFE_VAR")
    monkeypatch.setenv("SAFE_VAR", "visible")
    monkeypatch.delenv("MCP_SHELL_SAFE_PATH", raising=False)

    env = build_child_environment()

    assert "SECRET_TOKEN" not in env
    assert env == {"PATH": DEFAULT_SAFE_PATH, "SAFE_VAR": "visible"}
    assert process_manager.build_child_environment() == env


def test_child_environment_allows_documented_allowlist(process_manager, monkeypatch):
    """Only MCP_SHELL_CHILD_ENV_ALLOWLIST controls copied variables."""
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "SAFE_VAR")
    monkeypatch.setenv("MCP_SHELL_ENV_ALLOWLIST", "OLD_VAR,PATH")
    monkeypatch.setenv("SAFE_VAR", "visible")
    monkeypatch.setenv("OLD_VAR", "obsolete")
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", "/configured/bin")

    env = build_child_environment()

    assert env["SAFE_VAR"] == "visible"
    assert "OLD_VAR" not in env
    assert env["PATH"] == "/configured/bin"
    assert "LANG" not in env
    assert "LC_ALL" not in env
    assert process_manager.build_child_environment() == env


def test_instance_builder_delegates_to_module_builder(process_manager, monkeypatch):
    """The instance adapter filters envs exactly like the module builder."""
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "SAFE_VAR")
    monkeypatch.delenv("MCP_SHELL_SAFE_PATH", raising=False)
    envs = {"SAFE_VAR": "ok", "SECRET_TOKEN": "blocked", "PATH": "/evil"}

    env = process_manager.build_child_environment(envs)

    assert env == build_child_environment(envs)
    assert env == {"PATH": DEFAULT_SAFE_PATH, "SAFE_VAR": "ok"}


@pytest.mark.parametrize("safe_path", [None, "", "   ", "\t\n"])
@pytest.mark.parametrize("parent_path", ["/parent/shadow/bin", None])
def test_blank_safe_path_uses_default_not_parent(monkeypatch, safe_path, parent_path):
    """Unset or blank SAFE_PATH falls back to the POSIX default, never parent PATH."""
    monkeypatch.setattr(process_manager_module, "os", _OsNameProxy("posix"))
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)
    if safe_path is None:
        monkeypatch.delenv("MCP_SHELL_SAFE_PATH", raising=False)
    else:
        monkeypatch.setenv("MCP_SHELL_SAFE_PATH", safe_path)
    if parent_path is None:
        monkeypatch.delenv("PATH", raising=False)
    else:
        monkeypatch.setenv("PATH", parent_path)

    assert build_child_environment()["PATH"] == DEFAULT_SAFE_PATH


def test_configured_safe_path_is_preserved_byte_for_byte(monkeypatch):
    """A nonblank SAFE_PATH is not trimmed or normalized."""
    configured = " /opt/my tools/bin:/usr/bin "
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", configured)
    monkeypatch.setenv("PATH", "/parent/shadow/bin")
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)

    assert build_child_environment()["PATH"] == configured


def test_nonallowlisted_per_call_path_and_policy_vars_are_ignored(monkeypatch):
    """Per-call envs cannot change PATH or server policy without operator opt-in."""
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", "/configured/bin")
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "SAFE_VAR")
    monkeypatch.setenv("PATH", "/parent/shadow/bin")

    env = build_child_environment(
        {
            "PATH": "/per-call/shadow/bin",
            "MCP_SHELL_SAFE_PATH": "/per-call/safe",
            "MCP_SHELL_CHILD_ENV_ALLOWLIST": "PATH",
            "MCP_SHELL_ENV_ALLOWLIST": "PATH",
        }
    )

    assert env == {"PATH": "/configured/bin"}


def test_delegated_path_prefers_per_call_then_parent(monkeypatch):
    """Exact PATH allowlisting delegates to per-call, then parent PATH."""
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", "/configured/bin")
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "PATH")
    monkeypatch.setenv("PATH", "/parent/bin")

    assert build_child_environment()["PATH"] == "/parent/bin"
    assert build_child_environment({"PATH": "/call/bin"})["PATH"] == "/call/bin"
    assert build_child_environment({"PATH": ""})["PATH"] == ""

    monkeypatch.setenv("PATH", "")
    assert build_child_environment()["PATH"] == ""


def test_delegated_path_missing_values_keep_safe_path(monkeypatch):
    """An allowlisted PATH that is absent everywhere keeps SAFE_PATH/default."""
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "PATH")
    monkeypatch.delenv("PATH", raising=False)
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", "/configured/bin")

    assert build_child_environment({"OTHER": "x"})["PATH"] == "/configured/bin"

    monkeypatch.delenv("MCP_SHELL_SAFE_PATH", raising=False)
    monkeypatch.setattr(process_manager_module, "os", _OsNameProxy("posix"))
    assert build_child_environment()["PATH"] == DEFAULT_SAFE_PATH


def test_path_allowlist_requires_exact_key(monkeypatch):
    """Only the exact PATH key delegates PATH."""
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", "/configured/bin")
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "path,PATH_EXTRA,MYPATH")
    monkeypatch.setenv("PATH", "/parent/bin")

    assert build_child_environment({"PATH": "/call/bin"})["PATH"] == "/configured/bin"


def test_windows_path_keeps_launch_compatibility(monkeypatch):
    """Windows uses SAFE_PATH when set, else parent PATH, else os.defpath."""
    monkeypatch.setattr(process_manager_module, "os", _OsNameProxy("nt"))
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\system32\\cmd.exe")
    monkeypatch.setenv("SYSTEMROOT", "C:\\Windows")
    monkeypatch.setenv("PATH", "C:\\Parent")

    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", "C:\\Safe")
    env = build_child_environment()
    assert env["PATH"] == "C:\\Safe"
    assert env["COMSPEC"] == "C:\\Windows\\system32\\cmd.exe"
    assert env["SYSTEMROOT"] == "C:\\Windows"

    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", " ")
    assert build_child_environment()["PATH"] == "C:\\Parent"

    monkeypatch.delenv("PATH")
    assert build_child_environment()["PATH"] == os.defpath


def _write_probe(directory, name, marker):
    directory.mkdir(parents=True, exist_ok=True)
    executable = directory / name
    executable.write_text(f"#!/bin/sh\n: > '{marker}'\necho {name}\n")
    executable.chmod(0o755)
    return executable


@pytest.mark.skipif(os.name != "posix", reason="POSIX PATH lookup semantics")
@pytest.mark.asyncio
async def test_create_process_ignores_parent_path_shadow(
    process_manager, monkeypatch, tmp_path
):
    """Real process creation resolves bare names via SAFE_PATH, not parent PATH."""
    safe_dir = tmp_path / "safe bin"
    shadow_dir = tmp_path / "shadow"
    safe_marker = tmp_path / "safe-marker"
    shadow_marker = tmp_path / "shadow-marker"
    _write_probe(safe_dir, "pathprobe", safe_marker)
    _write_probe(shadow_dir, "pathprobe", shadow_marker)
    monkeypatch.setenv("PATH", f"{shadow_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", str(safe_dir))
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)

    process = await process_manager.create_process(["pathprobe"], directory=None)
    stdout, _ = await process_manager.execute_with_timeout(process, timeout=5)

    assert process.returncode == 0
    assert stdout == b"pathprobe\n"
    assert safe_marker.exists()
    assert not shadow_marker.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX PATH lookup semantics")
@pytest.mark.asyncio
async def test_create_process_does_not_fall_back_to_parent_path(
    process_manager, monkeypatch, tmp_path
):
    """A command only present in parent PATH fails to launch."""
    safe_dir = tmp_path / "safe"
    safe_dir.mkdir()
    shadow_marker = tmp_path / "shadow-marker"
    _write_probe(tmp_path / "shadow", "parentonly", shadow_marker)
    monkeypatch.setenv("PATH", f"{tmp_path / 'shadow'}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", str(safe_dir))
    monkeypatch.delenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", raising=False)

    with pytest.raises(ValueError, match="Failed to create process"):
        await process_manager.create_process(["parentonly"], directory=None)

    assert not shadow_marker.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX PATH lookup semantics")
@pytest.mark.asyncio
async def test_create_process_uses_parent_path_only_when_delegated(
    process_manager, monkeypatch, tmp_path
):
    """Explicit PATH delegation is the only way the parent PATH is searched."""
    safe_dir = tmp_path / "safe"
    shadow_dir = tmp_path / "shadow"
    safe_marker = tmp_path / "safe-marker"
    shadow_marker = tmp_path / "shadow-marker"
    _write_probe(safe_dir, "pathprobe", safe_marker)
    _write_probe(shadow_dir, "pathprobe", shadow_marker)
    monkeypatch.setenv("PATH", f"{shadow_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("MCP_SHELL_SAFE_PATH", str(safe_dir))
    monkeypatch.setenv("MCP_SHELL_CHILD_ENV_ALLOWLIST", "PATH")

    process = await process_manager.create_process(["pathprobe"], directory=None)
    await process_manager.execute_with_timeout(process, timeout=5)

    assert process.returncode == 0
    assert shadow_marker.exists()
    assert not safe_marker.exists()
