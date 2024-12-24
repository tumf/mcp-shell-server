"""Test cases for the CommandValidator class."""

import pytest

from mcp_shell_server.command_validator import CommandValidator


def clear_env(monkeypatch):
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)


@pytest.fixture
def validator():
    return CommandValidator()


def test_get_allowed_commands(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "cmd1,cmd2")
    monkeypatch.setenv("ALLOWED_COMMANDS", "cmd3,cmd4")
    assert set(validator.get_allowed_commands()) == {"cmd1", "cmd2", "cmd3", "cmd4"}


def test_is_command_allowed(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "allowed_cmd")
    assert validator.is_command_allowed("allowed_cmd")
    assert not validator.is_command_allowed("disallowed_cmd")


def test_validate_no_shell_operators(validator):
    validator.validate_no_shell_operators("echo")  # Should not raise
    with pytest.raises(ValueError, match="Unexpected shell operator"):
        validator.validate_no_shell_operators(";")
    with pytest.raises(ValueError, match="Unexpected shell operator"):
        validator.validate_no_shell_operators("&&")


def test_validate_pipeline(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "ls,grep")

    # Valid pipeline
    validator.validate_pipeline(["ls", "|", "grep", "test"])

    # Empty command before pipe
    with pytest.raises(ValueError, match="Empty command before pipe operator"):
        validator.validate_pipeline(["|", "grep", "test"])

    # Command not allowed
    with pytest.raises(ValueError, match="Command not allowed"):
        validator.validate_pipeline(["invalid_cmd", "|", "grep", "test"])


def test_validate_command(validator, monkeypatch):
    clear_env(monkeypatch)

    # No allowed commands
    with pytest.raises(ValueError, match="No commands are allowed"):
        validator.validate_command(["cmd"])

    monkeypatch.setenv("ALLOW_COMMANDS", "allowed_cmd")

    # Empty command
    with pytest.raises(ValueError, match="Empty command"):
        validator.validate_command([])

    # Command not allowed
    with pytest.raises(ValueError, match="Command not allowed"):
        validator.validate_command(["disallowed_cmd"])

    # Command allowed
    validator.validate_command(["allowed_cmd", "-arg"])  # Should not raise
