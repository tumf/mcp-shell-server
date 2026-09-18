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


@pytest.mark.parametrize("command", ["python2", "python3.11", "/usr/bin/python3.11"])
def test_versioned_python_interpreters_are_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_PATTERNS", r"(?:.*/)?python[0-9.]*")

    with pytest.raises(ValueError, match="default security policy"):
        validator.validate_command([command, "-c", "print(1)"])


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
        ["git", "clone", "--u=sh", "repo"],
        ["git", "push", "--rece=sh", "repo"],
        ["git", "--config-env=alias.pwn=PAYLOAD", "pwn"],
        ["git", "--exec-path=/tmp", "pwn"],
        ["git", "clone", "-u", "sh", "repo"],
        ["git", "clone", "-c", "core.fsmonitor=touch marker", "repo"],
        ["git", "clone", "--config", "core.fsmonitor=touch marker", "repo"],
        ["git", "clone", "--co", "core.fsmonitor=touch marker", "repo"],
        ["git", "clone", "--co=core.fsmonitor=touch marker", "repo"],
        ["git", "clone", "ext::sh -c id"],
    ],
)
def test_git_external_program_vectors_are_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    with pytest.raises(ValueError, match="git external program"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["git", "config", "alias.pwn", "!sh -c id"],
        ["git", "config", "core.fsmonitor", "sh -c id"],
        ["git", "config", "--global", "alias.pwn", "!sh -c id"],
    ],
)
def test_git_persistent_config_is_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    with pytest.raises(ValueError, match="git config"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["gfind", ".", "-exec", "sh", "-c", "id", ";"],
        ["gawk", 'BEGIN { system("id") }'],
        ["gtar", "--checkpoint-action=exec=sh shell.sh"],
        ["bsdtar", "--to-command=sh shell.sh"],
    ],
)
def test_alternate_binary_names_share_default_policy(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "gfind,gawk,gtar,bsdtar")

    with pytest.raises(ValueError, match="default security policy"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["timeout", "5", "touch", "/tmp/marker"],
        ["nice", "touch", "/tmp/marker"],
        ["nohup", "touch", "/tmp/marker"],
        ["setsid", "touch", "/tmp/marker"],
        ["stdbuf", "-o0", "touch", "/tmp/marker"],
        ["flock", "/tmp/lock", "touch", "/tmp/marker"],
    ],
)
def test_command_wrappers_are_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "timeout,nice,nohup,setsid,stdbuf,flock")

    with pytest.raises(ValueError, match="default security policy"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["sed", "1e touch /tmp/marker", "input"],
        ["sed", "-e", "1w /tmp/marker", "input"],
        ["sed", "-e1r /etc/passwd", "input"],
        ["sed", "-f", "script.sed", "input"],
        ["find", ".", "-fprintf", "/tmp/marker", "pwned"],
        ["find", ".", "-fprint", "/tmp/marker"],
        ["find", ".", "-fprint0", "/tmp/marker"],
        ["find", ".", "-fls", "/tmp/marker"],
        ["awk", 'BEGIN { print "pwned" > "/tmp/marker" }'],
        ["awk", 'BEGIN { getline value < "/etc/passwd" }'],
        ["awk", "-f", "script.awk"],
    ],
)
def test_embedded_execution_and_io_vectors_are_rejected(
    validator, monkeypatch, command
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "sed,find,awk")

    with pytest.raises(ValueError, match="default security policy"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["awk", 'BEGIN{print "x" | "id"}'],
        ["awk", 'BEGIN { print "x" | "id" }'],
        ["awk", 'BEGIN { "id" | getline out; print out }'],
        ["gawk", 'BEGIN{print "x" | "id"}'],
    ],
)
def test_awk_embedded_pipe_payload_is_rejected_in_original_argv_form(
    validator, monkeypatch, command
):
    """The awk policy inspects the original argument, pipe characters included."""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "awk,gawk")

    with pytest.raises(ValueError, match="awk external access"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["gawk", "--file=/dev/stdin"],
        ["gawk", "--file", "/dev/stdin"],
        ["gawk", "--exec=/dev/stdin"],
        ["gawk", "-E/dev/stdin"],
        ["gawk", "-Sf/dev/stdin"],
        ["gawk", "--include=/dev/stdin"],
        ["gawk", "-i/dev/stdin"],
        ["gawk", "--load=/tmp/extension.so"],
        ["gawk", "-l/tmp/extension.so"],
        ["gawk", "--source", 'BEGIN { print "safe" }'],
        ["gawk", "-e", 'BEGIN { print "safe" }'],
        ["gawk", "-W", "file=/dev/stdin"],
        ["gawk", "-W", "fi=/dev/stdin"],
        ["gawk", "-Wfile=/dev/stdin"],
        ["gawk", "-Wfi=/dev/stdin"],
        ["gawk", '@include "library.awk"'],
        ["gawk", '@load "extension"'],
    ],
)
def test_awk_external_program_sources_are_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "gawk")

    with pytest.raises(ValueError, match="awk external access"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["awk", 'BEGIN { print "safe" }'],
        ["gawk", "-F,", "{ print $1 }"],
        ["gawk", "-F", "-f", "{ print $1 }"],
        ["gawk", "--assign", "name=value", "{ print name }"],
        ["gawk", "-o/tmp/profile", 'BEGIN { print "safe" }'],
        ["gawk", "-p/tmp/profile", 'BEGIN { print "safe" }'],
        ["gawk", "-d/tmp/variables", 'BEGIN { print "safe" }'],
        ["gawk", "-D/tmp/debug", 'BEGIN { print "safe" }'],
        ["gawk", "-Lfatal", 'BEGIN { print "safe" }'],
    ],
)
def test_awk_safe_program_arguments_remain_allowed(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "awk,gawk")

    validator.validate_command(command)


def test_git_status_is_allowed(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    validator.validate_command(["git", "status"])


def test_git_subcommand_c_option_is_allowed(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    validator.validate_command(["git", "commit", "-c", "HEAD", "--dry-run"])


@pytest.mark.parametrize(
    "command",
    [
        # Full long forms, equals and separated.
        ["sort", "--compress-program=/tmp/program", "input"],
        ["sort", "--compress-program", "/tmp/program", "input"],
        ["sort", "--output=/tmp/outside", "input"],
        ["sort", "--output", "/tmp/outside", "input"],
        ["sort", "--files0-from=/tmp/list"],
        ["sort", "--files0-from", "/tmp/list"],
        ["sort", "--temporary-directory=/tmp/elsewhere", "input"],
        ["sort", "--temporary-directory", "/tmp/elsewhere", "input"],
        # Shortest unique abbreviations.
        ["sort", "--co=/tmp/program", "input"],
        ["sort", "--co", "/tmp/program", "input"],
        ["sort", "--o=/tmp/outside", "input"],
        ["sort", "--o", "/tmp/outside", "input"],
        ["sort", "--fil=/tmp/list"],
        ["sort", "--fil", "/tmp/list"],
        ["sort", "--t=/tmp/elsewhere", "input"],
        ["sort", "--t", "/tmp/elsewhere", "input"],
        # Longer abbreviations.
        ["sort", "--comp=/tmp/program", "input"],
        ["sort", "--outp", "/tmp/outside", "input"],
        ["sort", "--files0", "/tmp/list"],
        ["sort", "--temp=/tmp/elsewhere", "input"],
        # Short forms: separated, attached, and clustered.
        ["sort", "-o", "/tmp/outside", "input"],
        ["sort", "-o/tmp/outside", "input"],
        ["sort", "-ro", "/tmp/outside", "input"],
        ["sort", "-ro/tmp/outside", "input"],
        ["sort", "-T", "/tmp/elsewhere", "input"],
        ["sort", "-T/tmp/elsewhere", "input"],
        ["sort", "-rT", "/tmp/elsewhere", "input"],
        ["sort", "-rT/tmp/elsewhere", "input"],
        # GNU permutation places the option after an operand.
        ["sort", "input", "-o", "/tmp/outside"],
        ["sort", "input", "--compress-program=/tmp/program"],
        # The gsort alias shares the policy.
        ["gsort", "--co=/tmp/program", "input"],
        ["gsort", "--o=/tmp/outside", "input"],
        ["gsort", "-ro", "/tmp/outside", "input"],
        ["gsort", "-rT", "/tmp/elsewhere", "input"],
        # Absolute paths resolve to the same policy command name.
        ["/usr/bin/sort", "-o", "/tmp/outside", "input"],
    ],
)
def test_sort_external_program_and_path_options_are_rejected(
    validator, monkeypatch, command
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "sort,gsort,/usr/bin/sort")

    with pytest.raises(ValueError, match="sort external program or path option"):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        ["sort", "input"],
        ["sort", "-r", "input"],
        ["sort", "-u", "-n", "input"],
        ["sort", "-S", "1M", "input"],
        # `1T` is the value of -S, not a clustered -T option.
        ["sort", "-S1T", "input"],
        # `T` is the field separator, not a clustered -T option.
        ["sort", "-tT", "-k2,2", "input"],
        ["sort", "-rk2,2", "input"],
        ["sort", "--buffer-size=1T", "input"],
        ["sort", "--field-separator", "T", "input"],
        ["sort", "--key", "2,2", "input"],
        ["sort", "--parallel", "4", "input"],
        ["sort", "--random-source=/dev/urandom", "input"],
        # Option-like tokens after `--` are filename operands.
        ["sort", "--", "--output=/tmp/name"],
        ["sort", "--", "-o", "/tmp/name"],
        ["gsort", "-S1T", "input"],
        ["/usr/bin/sort", "-r", "input"],
    ],
)
def test_ordinary_sort_arguments_remain_allowed(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "sort,gsort,/usr/bin/sort")

    validator.validate_command(command)
