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


def test_is_command_allowed_with_patterns(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "allowed_cmd")
    monkeypatch.setenv("ALLOW_PATTERNS", "cmd[0-9]+")

    assert validator.is_command_allowed("allowed_cmd")
    assert validator.is_command_allowed("cmd123")
    assert not validator.is_command_allowed("disallowed_cmd")
    assert not validator.is_command_allowed("cmdabc")
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "allowed_cmd")
    assert validator.is_command_allowed("allowed_cmd")
    assert not validator.is_command_allowed("disallowed_cmd")


def test_allow_patterns_use_fullmatch_not_prefix(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", "ls")

    assert validator.is_command_allowed("ls")
    assert not validator.is_command_allowed("lsof")


def test_allow_patterns_reject_unsafe_command_names(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", ".+")

    assert not validator.is_command_allowed("ls; touch /tmp/pwned")
    assert not validator.is_command_allowed("ls -la")


@pytest.mark.parametrize("unsafe_pattern", ["ls -la", "ls;.*"])
def test_allow_patterns_reject_unsafe_pattern_forms(
    validator, monkeypatch, unsafe_pattern
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", unsafe_pattern)

    with pytest.raises(ValueError, match="ALLOW_PATTERNS entries"):
        validator.is_command_allowed("ls")


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


def test_rejects_find_exec_even_when_allowlisted(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "find")

    with pytest.raises(ValueError, match="find -exec"):
        validator.validate_command(["find", ".", "-exec", "sh", "-c", "id", ";"])


def test_rejects_shells_and_interpreters_even_when_allowlisted(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv(
        "ALLOW_COMMANDS",
            "sh,/bin/bash,zsh,python,python3.12,perl,ruby,node,env,xargs",

    )

    for command in [
        "sh",
        "/bin/bash",
        "zsh",
        "python",
        "python3.12",
        "perl",
        "ruby",
        "node",
        "env",
        "xargs",
    ]:
        with pytest.raises(ValueError, match="default argument policy"):
            validator.validate_command([command, "--version"])


def test_rejects_awk_system_call_but_allows_plain_awk(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "awk")

    validator.validate_command(["awk", "{ print $1 }"])

    with pytest.raises(ValueError, match=r"awk system\(\)"):
        validator.validate_command(["awk", "BEGIN { system(\"id\") }"])


def test_rejects_tar_checkpoint_action_exec(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "tar")

    validator.validate_command(["tar", "-cf", "archive.tar", "file.txt"])

    with pytest.raises(ValueError, match="tar --checkpoint-action=exec"):
        validator.validate_command(
            ["tar", "--checkpoint=1", "--checkpoint-action=exec=sh exploit.sh"]
        )


def test_validate_pipeline_rejects_dangerous_segment(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "cat,xargs")

    with pytest.raises(ValueError, match="default argument policy"):
        validator.validate_pipeline(["cat", "items.txt", "|", "xargs", "sh", "-c"])
