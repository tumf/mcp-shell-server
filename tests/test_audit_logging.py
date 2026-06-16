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
    timeout_audit = _audit_records(caplog)[-1]
    assert timeout_audit["result_type"] == "timeout"
    assert timeout_audit["error_type"] == "TimeoutError"
    assert timeout_audit["timeout"] == 1

    manager.execute_with_timeout = AsyncMock(
        side_effect=OutputLimitExceeded("stdout", 3, stdout=b"abc")
    )
    result = await executor.execute(["echo", "long"], str(tmp_path), timeout=1)
    assert result["status"] == -1
    output_cap_audit = _audit_records(caplog)[-1]
    assert output_cap_audit["result_type"] == "output_cap"
    assert output_cap_audit["stdout_bytes"] == 3
    assert "abc" not in str(output_cap_audit)
    assert "abc" not in caplog.text

    manager.execute_with_timeout = AsyncMock(side_effect=RuntimeError("boom"))
    result = await executor.execute(["echo", "boom"], str(tmp_path), timeout=1)
    assert result["status"] == 1
    process_audit = _audit_records(caplog)[-1]
    assert process_audit["result_type"] == "process_error"
    assert process_audit["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_audit_logging_create_process_error_and_env_redaction(
    tmp_path, monkeypatch, caplog
):
    """Process creation failures are audited and secret-like env metadata is redacted."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    caplog.set_level(logging.INFO, logger="mcp-shell-server.audit")

    manager = MagicMock()
    manager.create_process = AsyncMock(side_effect=ValueError("spawn failed"))
    manager.execute_with_timeout = AsyncMock()
    manager.cleanup_processes = AsyncMock()
    executor = ShellExecutor(process_manager=manager)

    result = await executor.execute(
        ["echo", "ok"],
        str(tmp_path),
        timeout=2,
        envs={"SECRET_TOKEN": "super-secret-value", "VISIBLE": "short"},
        output_limit=10,
    )

    assert result["status"] == 1
    audit = _audit_records(caplog)[-1]
    assert audit["result_type"] == "process_error"
    assert audit["error_type"] == "ValueError"
    assert audit["output_limit"] == 10
    assert audit["env"] == {"[REDACTED]": "[REDACTED]", "VISIBLE": "short"}
    assert "SECRET_TOKEN" not in str(audit)
    assert "super-secret-value" not in str(audit)
    assert "SECRET_TOKEN" not in caplog.text
    assert "super-secret-value" not in caplog.text
    manager.execute_with_timeout.assert_not_called()
