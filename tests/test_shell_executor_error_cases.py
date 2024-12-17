import asyncio

import pytest

from mcp_shell_server.shell_executor import ShellExecutor


@pytest.mark.asyncio
async def test_empty_command_validation():
    """Test validation of empty commands"""
    executor = ShellExecutor()

    # 空のコマンドのテスト
    with pytest.raises(ValueError, match="Empty command"):
        executor._validate_command([])


@pytest.mark.asyncio
async def test_no_allowed_commands_validation(monkeypatch):
    """Test validation when no commands are allowed"""
    # ALLOW_COMMANDSを削除
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)

    executor = ShellExecutor()
    with pytest.raises(
        ValueError,
        match="No commands are allowed. Please set ALLOW_COMMANDS environment variable.",
    ):
        executor._validate_command(["any_command"])


@pytest.mark.asyncio
async def test_shell_operator_validation():
    """Test validation of shell operators"""
    executor = ShellExecutor()

    operators = [";" "&&", "||", "|"]
    for op in operators:
        # シェル操作子の検証
        with pytest.raises(ValueError, match=f"Unexpected shell operator: {op}"):
            executor._validate_no_shell_operators(op)


@pytest.mark.asyncio
async def test_process_execution_timeout(monkeypatch):
    """Test process execution timeout handling"""
    monkeypatch.setenv("ALLOW_COMMANDS", "sleep")
    executor = ShellExecutor()

    # プロセスのタイムアウトをテスト
    command = ["sleep", "5"]
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(executor.execute(command), timeout=0.1)


@pytest.mark.asyncio
async def test_process_failure(monkeypatch):
    """Test handling of process execution failure"""
    monkeypatch.setenv("ALLOW_COMMANDS", "false")
    executor = ShellExecutor()

    # falseコマンドは常に終了コード1を返す
    result = await executor.execute(["false"])
    assert result["status"] == 1
