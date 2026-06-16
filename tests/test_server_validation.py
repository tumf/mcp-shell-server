import logging
from unittest.mock import AsyncMock

import pytest

from mcp_shell_server.server import ExecuteToolHandler


@pytest.mark.asyncio
async def test_server_input_validation():
    """Test input validation in execute tool."""
    handler = ExecuteToolHandler()

    with pytest.raises(ValueError, match="'command' must be an array"):
        await handler.run_tool({"command": "not an array", "directory": "/"})

    with pytest.raises(ValueError, match="Directory is required"):
        await handler.run_tool({"command": ["echo", "test"], "directory": ""})

    with pytest.raises(ValueError, match="No command provided"):
        await handler.run_tool({"directory": "/"})


@pytest.mark.asyncio
async def test_server_applies_default_timeout_and_output_limit(monkeypatch):
    monkeypatch.setenv("MCP_SHELL_DEFAULT_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("MCP_SHELL_MAX_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("MCP_SHELL_OUTPUT_LIMIT_BYTES", "1234")
    handler = ExecuteToolHandler()
    handler.executor.execute = AsyncMock(
        return_value={"error": None, "stdout": "ok", "stderr": "", "status": 0}
    )

    result = await handler.run_tool({"command": ["echo", "ok"], "directory": "/tmp"})

    assert result[0].text == "ok"
    handler.executor.execute.assert_awaited_once_with(
        ["echo", "ok"],
        "/tmp",
        None,
        7,
        output_limit=1234,
    )


@pytest.mark.asyncio
async def test_server_clamps_requested_timeout(monkeypatch):
    monkeypatch.setenv("MCP_SHELL_DEFAULT_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("MCP_SHELL_MAX_TIMEOUT_SECONDS", "9")
    handler = ExecuteToolHandler()
    handler.executor.execute = AsyncMock(
        return_value={"error": None, "stdout": "ok", "stderr": "", "status": 0}
    )

    await handler.run_tool(
        {"command": ["echo", "ok"], "directory": "/tmp", "timeout": 999}
    )

    assert handler.executor.execute.await_args.args[3] == 9


@pytest.mark.asyncio
async def test_server_applies_default_timeout(monkeypatch, tmp_path):
    """Omitted client timeout is replaced with the configured default."""
    handler = ExecuteToolHandler()
    handler.default_timeout = 7
    handler.max_timeout = 30
    captured = {}

    async def fake_execute(command, directory, stdin, timeout, **kwargs):
        captured["timeout"] = timeout
        captured["output_limit"] = kwargs["output_limit"]
        return {"error": None, "stdout": "ok", "stderr": "", "status": 0}

    monkeypatch.setattr(handler.executor, "execute", fake_execute)

    await handler.run_tool({"command": ["echo", "ok"], "directory": str(tmp_path)})

    assert captured["timeout"] == 7
    assert captured["output_limit"] == handler.output_limit


@pytest.mark.asyncio
async def test_server_clamps_over_limit_timeout(monkeypatch, tmp_path):
    """Client timeout above server maximum is clamped before execution."""
    handler = ExecuteToolHandler()
    handler.default_timeout = 7
    handler.max_timeout = 11
    captured = {}

    async def fake_execute(command, directory, stdin, timeout, **kwargs):
        captured["timeout"] = timeout
        return {"error": None, "stdout": "ok", "stderr": "", "status": 0}

    monkeypatch.setattr(handler.executor, "execute", fake_execute)

    await handler.run_tool(
        {"command": ["echo", "ok"], "directory": str(tmp_path), "timeout": 99}
    )

    assert captured["timeout"] == 11


@pytest.mark.asyncio
async def test_audit_logging_success_and_redaction(tmp_path, monkeypatch, caplog):
    """Successful command emits structured audit fields and redacts secrets."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    handler = ExecuteToolHandler()
    caplog.set_level(logging.INFO, logger="mcp-shell-server.audit")

    await handler.run_tool(
        {
            "command": ["echo", "SECRET_TOKEN=super-secret-value"],
            "directory": str(tmp_path),
            "timeout": 5,
        }
    )

    audit_records = [
        record for record in caplog.records if record.name == "mcp-shell-server.audit"
    ]
    assert audit_records
    audit = audit_records[-1].audit
    assert audit["result_type"] == "success"
    assert audit["command"] == "echo"
    assert audit["argv"][1] == "[REDACTED]=[REDACTED]"
    assert audit["directory"] == str(tmp_path)
    assert audit["timeout"] == 5
    assert audit["return_code"] == 0
    assert "super-secret-value" not in str(audit)


@pytest.mark.asyncio
async def test_audit_logging_rejection(tmp_path, monkeypatch, caplog):
    """Rejected invocations emit a structured audit record."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")
    handler = ExecuteToolHandler()
    caplog.set_level(logging.INFO, logger="mcp-shell-server.audit")

    with pytest.raises(ValueError, match="Unexpected shell operator"):
        await handler.run_tool(
            {"command": ["echo;touch"], "directory": str(tmp_path), "timeout": 5}
        )

    audit = [record.audit for record in caplog.records if hasattr(record, "audit")][-1]
    assert audit["result_type"] == "rejected"
    assert audit["stderr_bytes"] > 0
