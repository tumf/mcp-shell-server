"""Test cases for the CommandValidator class."""

import pytest

from mcp_shell_server.command_validator import CommandValidator


def clear_env(monkeypatch):
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOW_PATTERNS", raising=False)


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
    monkeypatch.setenv("ALLOW_PATTERNS", "^cmd[0-9]+$")

    assert validator.is_command_allowed("allowed_cmd")
    assert validator.is_command_allowed("cmd123")
    assert not validator.is_command_allowed("disallowed_cmd")
    assert not validator.is_command_allowed("cmdabc")
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


def test_allow_patterns_use_fullmatch_and_reject_unsafe_forms(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", "ls")

    assert validator.is_command_allowed("ls")
    assert not validator.is_command_allowed("lsof")
    with pytest.raises(ValueError, match="Unsafe command name"):
        validator.is_command_allowed("ls;touch")
    with pytest.raises(ValueError, match="Unsafe command name"):
        validator.is_command_allowed("ls -la")

    monkeypatch.setenv("ALLOW_PATTERNS", "ls;.*")
    with pytest.raises(ValueError, match="Unsafe allowed command pattern"):
        validator.is_command_allowed("ls")


def test_default_dangerous_exec_vectors_are_rejected(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv(
        "ALLOW_COMMANDS", "find,sh,bash,python,python3,awk,tar,xargs,env"
    )

    dangerous_commands = [
        ["find", ".", "-exec", "sh", "-c", "id", ";"],
        ["sh", "-c", "id"],
        ["bash", "-c", "id"],
        ["python", "-c", "print(1)"],
        ["python3", "script.py"],
        ["awk", 'BEGIN { system("id") }'],
        ["awk", 'BEGIN { system\t("id") }'],
        ["awk", 'BEGIN { print "id" | "/bin/sh" }'],
        ["tar", "--checkpoint-action=exec=sh shell.sh"],
        ["tar", "-I/bin/sh", "-cf", "x.tar", "file"],
        ["tar", "--rsh-command=/bin/sh -c id", "-cf", "host:/tmp/x", "file"],
        ["xargs", "sh"],
        ["env"],
    ]

    for command in dangerous_commands:
        with pytest.raises(ValueError, match="default security policy"):
            validator.validate_command(command)


def test_allow_patterns_use_fullmatch(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", "ls")

    validator.validate_command(["ls"])
    with pytest.raises(ValueError, match="Command not allowed"):
        validator.validate_command(["lsof"])
    with pytest.raises(ValueError, match="Unsafe command name"):
        validator.validate_command(["ls;touch"])
    with pytest.raises(ValueError, match="Unsafe command name"):
        validator.validate_command(["ls -la"])


def test_dangerous_exec_capable_vectors_are_rejected(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv(
        "ALLOW_COMMANDS",
        "/usr/bin/find,/bin/sh,/bin/bash,/usr/bin/python,/usr/bin/awk,/usr/bin/tar,/usr/bin/xargs,/usr/bin/env,node,perl,ruby",
    )

    dangerous_commands = [
        (["/usr/bin/find", ".", "-exec", "sh", "-c", "id", ";"], "find -exec"),
        (["/bin/sh", "-c", "id"], "sh"),
        (["/bin/bash", "-c", "id"], "bash"),
        (["/usr/bin/python", "-c", "print(1)"], "python"),
        (["/usr/bin/awk", 'BEGIN { system("id") }'], "awk"),
        (["/usr/bin/awk", 'BEGIN { "id" | getline out; print out }'], "awk"),
        (
            ["/usr/bin/tar", "--checkpoint-action=exec=sh shell.sh"],
            "tar command execution",
        ),
        (
            ["/usr/bin/tar", "--checkpoint-action", "exec=sh shell.sh"],
            "tar command execution",
        ),
        (["/usr/bin/tar", "--to-command=sh shell.sh"], "tar command execution"),
        (
            ["/usr/bin/tar", "--use-compress-program=sh shell.sh"],
            "tar command execution",
        ),
        (["/usr/bin/tar", "-I/bin/sh"], "tar command execution"),
        (["/usr/bin/tar", "--rsh-command=/bin/sh -c id"], "tar command execution"),
        (["/usr/bin/xargs", "sh"], "xargs"),
        (["/usr/bin/env"], "env"),
    ]

    for argv, expected in dangerous_commands:
        with pytest.raises(ValueError, match=expected):
            validator.validate_command(argv)


@pytest.mark.parametrize(
    "command",
    [
        ["git", "-c", "core.fsmonitor=touch marker", "status"],
        ["git", "-cdiff.external=touch marker", "diff", "--ext-diff"],
        ["git", "-c", "user.name=Example", "status"],
        ["git", "-cAlias.pwn=!sh -c id", "status"],
        ["git", "-c"],
        ["git", "-cuser.name=Example", "status"],
    ],
)
def test_git_command_scoped_configs_are_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    with pytest.raises(ValueError, match="git command-scoped config"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["git", "--upload-pack=sh", "fetch"],
        ["git", "clone", "ext::sh -c id"],
    ],
)
def test_git_external_program_vectors_are_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    with pytest.raises(ValueError, match="git external program"):
        validator.validate_command(command)


def test_git_status_is_allowed(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    validator.validate_command(["git", "status"])
