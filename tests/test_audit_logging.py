"""Structured audit logging tests for shell execution outcomes."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_shell_server.process_manager import OutputLimitExceeded
from mcp_shell_server.shell_executor import ShellExecutor


def _audit_records(caplog):
    return [record.audit for record in caplog.records if hasattr(record, "audit")]


@pytest.mark.asyncio
async def test_audit_logging_timeout_output_cap_and_process_error(
    tmp_path, monkeypatch, caplog
):
    """Timeout, output-cap, and process-error outcomes emit structured audit logs."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    caplog.set_level(logging.INFO, logger="mcp-shell-server.audit")

    process = MagicMock()
    process.returncode = 0
    process.kill = MagicMock()
    process.wait = AsyncMock(return_value=0)

    manager = MagicMock()
    manager.create_process = AsyncMock(return_value=process)
    manager.cleanup_processes = AsyncMock()
    manager.execute_pipeline = AsyncMock(return_value=(b"", b"", 0))
    manager.execute_with_timeout = AsyncMock(side_effect=TimeoutError("slow"))
    executor = ShellExecutor(process_manager=manager)

    result = await executor.execute(["echo", "slow"], str(tmp_path), timeout=1)
    assert result["status"] == -1
    assert _audit_records(caplog)[-1]["result_type"] == "timeout"

    manager.execute_with_timeout = AsyncMock(
        side_effect=OutputLimitExceeded("stdout", 3, stdout=b"abc")
    )
    result = await executor.execute(["echo", "long"], str(tmp_path), timeout=1)
    assert result["status"] == -1
    assert _audit_records(caplog)[-1]["result_type"] == "output_cap"
    assert _audit_records(caplog)[-1]["stdout_bytes"] == 3

    manager.execute_with_timeout = AsyncMock(side_effect=RuntimeError("boom"))
    result = await executor.execute(["echo", "boom"], str(tmp_path), timeout=1)
    assert result["status"] == 1
    assert _audit_records(caplog)[-1]["result_type"] == "process_error"
