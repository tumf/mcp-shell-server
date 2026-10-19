"""Test cases for the CommandValidator class."""

import pytest

from mcp_shell_server.command_validator import (
    BSD_TAR_DIALECT,
    GNU_TAR_DIALECT,
    TAR_PROHIBITED_LONG_OPTIONS,
    CommandValidator,
)


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
        ["git", "--attr-source", "HEAD", "config", "alias.pwn", "!sh -c id"],
        ["git", "--attr-source=HEAD", "config", "alias.pwn", "!sh -c id"],
        [
            "git",
            "-C",
            "repo",
            "--attr-source",
            "HEAD",
            "config",
            "alias.pwn",
            "!sh -c id",
        ],
        ["git", "--shallow-file", "x", "config", "alias.pwn", "!sh -c id"],
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
        ["gawk", '@nsinclude "library.awk"'],
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
        ["gawk", "--assign", "name=-f", "{ print name }"],
        ["gawk", "--field-separator", "-f", "{ print $1 }"],
        ["gawk", "--", "-f"],
        ["gawk", '{ print "safe" }', "-f"],
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


# Argv after `git`. P is a helper path without shell operators.
GIT_EXECUTION_REJECTED = [
    # grep pager selection
    ["grep", "-O", "-e", "MATCH"],
    ["grep", "-OP", "-e", "MATCH"],
    ["grep", "-nO", "P"],
    ["grep", "-nOP"],
    ["grep", "-1OP"],
    ["grep", "--open-files-in-pager", "-e", "MATCH"],
    ["grep", "--open-files-in-pager=P"],
    ["grep", "--op=P"],
    ["grep", "--op", "P"],
    ["grep", "(", "-e", "MATCH", ")", "-OP"],
    # rebase exec
    ["rebase", "-x", "P", "HEAD~1"],
    ["rebase", "-xP", "HEAD~1"],
    ["rebase", "-qx", "P"],
    ["rebase", "-qxP"],
    ["rebase", "--exec", "P"],
    ["rebase", "--exec=P"],
    ["rebase", "--ex", "P"],
    ["rebase", "--ex=P"],
    ["rebase", "HEAD~1", "-xP"],
    ["rebase", "-xP", "--no-exec"],
    # filter-branch and bisect run
    ["filter-branch"],
    ["filter-branch", "--tree-filter", "P", "HEAD"],
    ["filter-branch", "--help"],
    ["bisect", "run", "P"],
    ["bisect", "run", "--", "P"],
    # ambiguous target prefixes are conservatively rejected
    ["grep", "--o=P"],
    ["rebase", "--e=P"],
    # a required value of `--` does not end option parsing
    ["grep", "-e", "--", "-OP", "data"],
    ["rebase", "--strategy", "--", "-xP"],
    # global prefixes, repeated and reordered
    ["-C", "repo", "grep", "-OP"],
    ["--git-dir=repo/.git", "--work-tree", "repo", "rebase", "-xP"],
    ["--attr-source", "HEAD", "--namespace", "ns", "-C", "repo", "filter-branch"],
    ["--shallow-file", "x", "bisect", "run", "P"],
    ["-C", "-x", "grep", "-OP"],
    # --exec keeps selecting a helper outside rebase
    ["push", "--exec=sh", "/tmp/repo"],
    ["push", "--exec", "sh", "/tmp/repo"],
    ["archive", "--remote=/tmp/repo", "--exec=sh", "HEAD"],
    ["send-pack", "--exec=sh", "/tmp/repo", "main"],
    ["ls-remote", "--exec=sh", "/tmp/repo"],
    ["push", "--e=sh", "/tmp/repo"],
    ["archive", "--remote=/tmp/repo", "--e", "sh", "HEAD"],
]
GIT_EXEC_PREFIX_REJECTED = [
    [subcommand, *option, *operands]
    for subcommand, operands in [
        ("push", ["/tmp/repo"]),
        ("archive", ["--remote=/tmp/repo", "HEAD"]),
        ("send-pack", ["/tmp/repo", "main"]),
        ("ls-remote", ["/tmp/repo"]),
    ]
    for prefix in ["--e", "--ex", "--exe", "--exec"]
    for option in ([f"{prefix}=sh"], [prefix, "sh"])
]


@pytest.mark.parametrize("command", GIT_EXECUTION_REJECTED + GIT_EXEC_PREFIX_REJECTED)
def test_git_execution_options_are_rejected(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    with pytest.raises(ValueError, match="git external program"):
        validator.validate_command(["git", *command])


@pytest.mark.parametrize(
    "command",
    [
        ["status", "--short"],
        ["log", "--oneline"],
        ["grep", "-n", "-e", "MATCH", "--", "data"],
        ["rebase", "--onto", "main", "topic"],
        ["bisect", "start"],
        ["bisect", "log"],
        ["bisect", "reset"],
        # required values are data, never rescanned
        ["grep", "-e", "-O", "data"],
        ["grep", "-e--open-files-in-pager", "data"],
        ["grep", "-ne", "-O", "data"],
        ["grep", "-f", "-O", "data"],
        ["grep", "--context", "-O", "data"],
        ["grep", "--con", "1", "-e", "MATCH", "data"],
        ["grep", "--color", "-e", "-O", "data"],
        ["rebase", "-Xx"],
        ["rebase", "-s", "-x"],
        ["rebase", "-Sx"],
        ["rebase", "-rx"],
        ["rebase", "--onto", "--exec"],
        ["rebase", "--strategy-option=-x"],
        ["rebase", "--strategy-o", "-x"],
        ["rebase", "--empty", "-x"],
        # end of options
        ["grep", "--", "-O", "data"],
        ["grep", "--end-of-options", "-O", "data"],
        ["rebase", "--", "-xP"],
        ["rebase", "--", "--exec=P"],
        # grep stops at its first operand
        ["grep", "MATCH", "-OP"],
        ["grep", "-e", "MATCH", "--", "--open-files-in-pager=P"],
        # negations unset the option
        ["grep", "--no-open-files-in-pager", "-e", "MATCH"],
        ["grep", "--no-op", "-e", "MATCH"],
        ["rebase", "--no-exec"],
        # only an exact `run` directly after bisect dispatches
        ["bisect", "log", "run"],
        ["bisect", "start", "--", "run"],
        ["bisect", "ru"],
        ["bisect", "--", "run"],
        # global prefix values are not subcommands or helper options
        ["-C", "filter-branch", "status"],
        ["--namespace", "bisect", "status"],
        ["--attr-source", "grep", "status"],
        ["-C", "--exec", "status"],
        ["commit", "-c", "HEAD", "--dry-run"],
    ],
)
def test_git_ordinary_operations_are_allowed(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    validator.validate_command(["git", *command])


GIT_REQUIRED_VALUE_OPTIONS = {
    "grep": (
        [f"-{letter}" for letter in "ABCefm"]
        + [
            f"--{name}"
            for name in [
                "after-context",
                "before-context",
                "context",
                "max-count",
                "max-depth",
                "threads",
            ]
        ],
        ["-O", "-OP", "--open-files-in-pager=P"],
        "-OP",
    ),
    "rebase": (
        [f"-{letter}" for letter in "CsX"]
        + [
            f"--{name}"
            for name in ["onto", "whitespace", "empty", "strategy", "strategy-option"]
        ],
        ["-x", "-xP", "--exec", "--exec=P"],
        "-xP",
    ),
}


@pytest.mark.parametrize(
    "subcommand,option,value,target",
    [
        (subcommand, option, value, target)
        for subcommand, (options, values, target) in GIT_REQUIRED_VALUE_OPTIONS.items()
        for option in options
        for value in values
    ],
)
def test_git_required_values_are_consumed_but_later_targets_rejected(
    validator, monkeypatch, subcommand, option, value, target
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    validator.validate_command(["git", subcommand, option, value])
    with pytest.raises(ValueError, match="git external program"):
        validator.validate_command(["git", subcommand, option, value, target])


@pytest.mark.parametrize(
    "command",
    [
        # optional values are attached only, so the next token stays an option
        ["rebase", "-r", "-xP"],
        ["rebase", "-S", "-xP"],
        ["rebase", "--rebase-merges", "-xP"],
        ["rebase", "--gpg-sign", "-xP"],
        ["grep", "--color", "-OP"],
        # no-value options never consume the next token
        ["grep", "--only-matching", "-OP"],
        ["grep", "--or", "-OP"],
        ["rebase", "--edit-todo", "-xP"],
        # ambiguous or unknown long names do not consume a value
        ["grep", "--max", "-OP"],
        ["rebase", "--str", "-xP"],
        ["rebase", "--unknown-option", "-xP"],
        # unknown short letters are not guessed to take a value
        ["grep", "-Y", "-OP"],
        ["rebase", "-Y", "-xP"],
    ],
)
def test_git_option_walker_does_not_skip_execution_options(
    validator, monkeypatch, command
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    with pytest.raises(ValueError, match="git external program"):
        validator.validate_command(["git", *command])


def test_git_empty_is_an_exact_required_option_not_an_exec_prefix(
    validator, monkeypatch
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "git")

    validator.validate_command(["git", "rebase", "--empty", "--exec=P"])
    with pytest.raises(ValueError, match="git external program"):
        validator.validate_command(["git", "rebase", "--e", "--empty"])


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


KNOWN_WRAPPER_RUNTIME_NAMES = ["setarch", "strace", "valgrind", "deno", "bun"]


@pytest.mark.parametrize("name", KNOWN_WRAPPER_RUNTIME_NAMES)
@pytest.mark.parametrize(
    ("allow_env", "allow_value", "argv0"),
    [
        ("ALLOW_COMMANDS", "{name}", "{name}"),
        ("ALLOW_COMMANDS", "/usr/bin/{name}", "/usr/bin/{name}"),
        ("ALLOW_PATTERNS", "{name}", "{name}"),
        ("ALLOW_PATTERNS", "(?:.*/)?{name}", "/opt/bin/{name}"),
    ],
)
@pytest.mark.parametrize(
    "args",
    [
        ["touch", "/tmp/marker"],
        ["--version"],
        ["-p", "1"],
    ],
)
def test_known_wrapper_and_runtime_names_are_rejected(
    validator, monkeypatch, name, allow_env, allow_value, argv0, args
):
    clear_env(monkeypatch)
    monkeypatch.setenv(allow_env, allow_value.format(name=name))
    argv = [argv0.format(name=name), *args]

    assert validator.is_command_allowed(argv[0])
    with pytest.raises(
        ValueError, match=f"^Command rejected by default security policy: {name}$"
    ):
        validator.validate_command(argv)


@pytest.mark.parametrize("name", KNOWN_WRAPPER_RUNTIME_NAMES)
def test_known_wrapper_and_runtime_names_are_rejected_in_later_pipeline_stage(
    validator, monkeypatch, name
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", f"echo,{name}")

    with pytest.raises(
        ValueError, match=f"^Command rejected by default security policy: {name}$"
    ):
        validator.validate_pipeline(["echo", "x", "|", f"/usr/bin/{name}", "run"])


def test_existing_dangerous_names_remain_rejected_when_allowlisted(
    validator, monkeypatch
):
    from mcp_shell_server.command_validator import DANGEROUS_COMMANDS

    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", ",".join(sorted(DANGEROUS_COMMANDS)))
    monkeypatch.setenv("ALLOW_PATTERNS", ".*")

    for name in sorted(DANGEROUS_COMMANDS):
        with pytest.raises(ValueError, match="default security policy"):
            validator.validate_command([name, "--version"])


@pytest.mark.parametrize("finder", ["find", "gfind", "bfind", "/usr/bin/find"])
@pytest.mark.parametrize("primary", ["-exec", "-execdir", "-ok", "-okdir"])
def test_find_execution_primaries_are_rejected_by_validator(
    validator, monkeypatch, finder, primary
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "find,gfind,bfind,/usr/bin/find")

    # The trailing ";" is deliberately absent: this asserts the find policy
    # itself, independent of the shared semicolon preprocessing rejection.
    with pytest.raises(
        ValueError, match="^Command rejected by default security policy: find -exec$"
    ):
        validator.validate_command([finder, ".", primary, "rm", "{}", "+"])


@pytest.mark.parametrize("finder", ["find", "gfind", "bfind"])
def test_ordinary_find_search_remains_allowed(validator, monkeypatch, finder):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "find,gfind,bfind")

    validator.validate_command([finder, ".", "-name", "*.py", "-print"])
    validator.validate_command([finder, ".", "-name", "-ok.txt", "-print"])


@pytest.mark.parametrize(
    "command",
    [
        ["make", "build"],
        ["make", "-C", "subdir", "test"],
        ["dd", "if=input.bin", "of=output.bin", "bs=1"],
        ["tee", "output.txt"],
        ["tee", "-a", "log.txt"],
    ],
)
def test_delegated_program_owned_behavior_is_not_blocked(
    validator, monkeypatch, command
):
    """make recipes and dd/tee file I/O are delegated authority, not contained."""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "make,dd,tee")

    validator.validate_command(command)


TAR_POLICY_ERROR_PATTERN = (
    "^Command rejected by default security policy: tar command execution option$"
)


def _tar_long_option_spellings():
    """Every abbreviation of every forbidden name, separate and equals form.

    A prefix that is itself an exact benign name (`checkpoint`) resolves to
    that name instead and is covered by the allowed-interval tests.
    """
    known = GNU_TAR_DIALECT.long_options | BSD_TAR_DIALECT.long_options
    for name in sorted(TAR_PROHIBITED_LONG_OPTIONS):
        for length in range(1, len(name) + 1):
            prefix = name[:length]
            if prefix != name and prefix in known:
                continue
            yield ["tar", "-cf", "out.tar", f"--{prefix}", "helper", "dir"]
            yield ["tar", "-cf", "out.tar", f"--{prefix}=helper", "dir"]


@pytest.mark.parametrize("command", list(_tar_long_option_spellings()))
def test_tar_external_program_long_option_spellings_are_rejected(
    validator, monkeypatch, command
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "tar")

    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        # Short -I/-F in clusters, attached, separated and old-style words.
        ["tar", "-I/bin/sh", "-cf", "x.tar", "file"],
        ["tar", "-I", "helper", "-cf", "x.tar", "file"],
        ["tar", "-cI", "helper", "-f", "x.tar", "file"],
        ["tar", "-cvzIhelper", "-f", "x.tar", "file"],
        ["tar", "-cF", "helper", "-f", "x.tar", "file"],
        ["tar", "-Fhelper", "-cf", "x.tar", "file"],
        ["tar", "-cf", "x.tar", "-MF", "helper", "file"],
        ["tar", "cIf", "helper", "x.tar", "file"],
        ["tar", "cfF", "x.tar", "helper", "file"],
        ["tar", "Icf", "helper", "x.tar", "file"],
        # Every checkpoint action is denied, not only exec=.
        ["tar", "--checkpoint=1", "--checkpoint-action=dot", "-cf", "x.tar", "f"],
        ["tar", "--checkpoint-action", "echo", "-cf", "x.tar", "file"],
        # The rmt prefix and ambiguous prefixes containing forbidden names.
        ["tar", "--rm", "helper", "-cf", "host:x.tar", "file"],
        ["tar", "--rm=helper", "-cf", "host:x.tar", "file"],
        ["tar", "--to", "helper", "-xf", "x.tar"],
        ["tar", "--new", "helper", "-cf", "x.tar", "file"],
        # Options after operands are still options (GNU permutation).
        ["tar", "-cf", "x.tar", "file", "--to-command=helper"],
        ["tar", "-cf", "x.tar", "file", "-I", "helper"],
        ["tar", "cf", "x.tar", "file", "--rsh-command=helper"],
        ["tar", "-xf", "x.tar", "member", "-F", "helper"],
        # Exact no-value or optional-value names do not swallow the next option.
        ["tar", "--checkpoint", "--use-compress-program=helper", "-cf", "x", "f"],
        ["tar", "--list", "--to-command=helper", "-f", "x.tar"],
        ["tar", "--sparse", "--info-script=helper", "-cf", "x.tar", "file"],
        ["tar", "--xattrs", "--new-volume-script=helper", "-cf", "x.tar", "f"],
        ["tar", "--totals", "--use-compress-program=helper", "-cf", "x", "f"],
        # A required value of `--` does not end option scanning.
        ["tar", "-c", "-f", "--", "--use-compress-program=helper", "file"],
        ["tar", "-cf", "--", "--to-command=helper", "file"],
        ["tar", "cf", "--", "--use-compress-program=helper", "file"],
        ["tar", "-cC", "--", "-I", "helper", "-f", "x.tar", "file"],
        # GNU -W means verify and does not take the next token.
        ["tar", "-cW", "--to-command=helper", "-f", "x.tar", "file"],
        ["tar", "-W", "--rsh-command=helper", "-cf", "host:x.tar", "file"],
        # Unknown or ambiguous names never manufacture value consumption.
        ["tar", "--no-such-option", "--to-command=helper", "-xf", "x.tar"],
        ["tar", "--ex", "--use-compress-program=helper", "-cf", "x", "f"],
        # bsdtar: H/L take no value, so the following helper option is real.
        ["tar", "-cH", "--use-compress-program=helper", "-f", "x.tar", "file"],
        ["tar", "-cL", "--use-compress-program", "helper", "-f", "x.tar", "f"],
        ["tar", "-cHWuse-compress-program=helper", "-f", "x.tar", "file"],
        ["tar", "-cLWuse-compress-program=helper", "-f", "x.tar", "file"],
        ["tar", "cHf", "x.tar", "--use-compress-program=helper", "file"],
        ["tar", "cLf", "x.tar", "--use-compress-program=helper", "file"],
        # bsdtar: hyphen-style -W dispatches a long option.
        ["tar", "-c", "-Wuse-compress-program=helper", "-f", "x.tar", "file"],
        ["tar", "-c", "-W", "use-compress-program=helper", "-f", "x.tar", "f"],
        ["tar", "-c", "-W", "use-compress-program", "helper", "-f", "x", "f"],
        ["tar", "-c", "-Wuse-comp=helper", "-f", "x.tar", "file"],
        ["tar", "-c", "-W", "u", "helper", "-f", "x.tar", "file"],
        ["tar", "-cWexclude", "--use-compress-program=helper", "-f", "x", "f"],
        # bsdtar: --mo/--mod are no-value modification-time, GNU --mode.
        ["tar", "--mo", "--use-compress-program=helper", "-cf", "x.tar", "f"],
        ["tar", "--mod", "--use-compress-program", "helper", "-cf", "x", "f"],
        # bsdtar: a bare `-` is an empty short group, not an operand.
        ["tar", "-c", "-", "-L", "--use-compress-program", "P", "-f", "-", "x"],
        ["tar", "-c", "-", "-H", "--use-compress-program", "P", "-f", "-", "x"],
    ],
)
def test_tar_external_program_option_forms_are_rejected(
    validator, monkeypatch, command
):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "tar")

    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator.validate_command(command)


@pytest.mark.parametrize(
    "argv0", ["tar", "gtar", "bsdtar", "/usr/bin/tar", "/opt/homebrew/bin/gtar"]
)
@pytest.mark.parametrize(
    "args",
    [
        ["--to-c=helper", "-xf", "x.tar"],
        ["-cIhelper", "-f", "x.tar", "file"],
        ["-cHWuse-compress-program=helper", "-f", "x.tar", "file"],
    ],
)
def test_tar_aliases_share_dual_dialect_policy(validator, monkeypatch, argv0, args):
    clear_env(monkeypatch)
    monkeypatch.setenv(
        "ALLOW_COMMANDS", "tar,gtar,bsdtar,/usr/bin/tar,/opt/homebrew/bin/gtar"
    )

    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator.validate_command([argv0, *args])


def test_tar_policy_applies_to_later_pipeline_stage(validator, monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,tar")

    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator.validate_pipeline(
            ["echo", "x", "|", "tar", "-cf", "-", "--use-comp=helper", "-T", "-"]
        )


@pytest.mark.parametrize(
    "command",
    [
        ["tar", "-cf", "out.tar", "dir"],
        ["tar", "-tvf", "out.tar"],
        ["tar", "-xf", "out.tar", "-C", "dest"],
        ["tar", "cf", "out.tar", "dir"],
        ["tar", "xvf", "out.tar"],
        ["tar", "-czf", "out.tar.gz", "dir"],
        ["tar", "-cjf", "out.tar.bz2", "dir"],
        ["tar", "-cJf", "out.tar.xz", "dir"],
        ["tar", "--create", "--gzip", "--file=out.tar.gz", "dir"],
        ["tar", "--extract", "--file", "out.tar", "--directory", "dest"],
        # Checkpoint intervals stay usable; only actions are denied.
        ["tar", "--checkpoint=10", "-cf", "out.tar", "dir"],
        ["tar", "--checkpoint", "-cf", "out.tar", "dir"],
        # Optional values attach with `=`.
        ["tar", "--totals=USR1", "-cf", "out.tar", "dir"],
        ["tar", "--backup=numbered", "-xf", "out.tar"],
        ["tar", "--atime-preserve=system", "-cf", "out.tar", "dir"],
        ["tar", "--occurrence=2", "-xf", "out.tar", "member"],
        ["tar", "--one-top-level=dest", "-xf", "out.tar"],
        # Option-looking tokens after an unconsumed `--` are operands.
        ["tar", "-cf", "out.tar", "--", "--use-compress-program=x", "-I", "-F"],
        ["tar", "-c", "-f", "-", "-"],
        # Values containing I/F or helper-looking text are data in both walks.
        ["tar", "-cf", "IF.tar", "dir"],
        ["tar", "-cfIF.tar", "dir"],
        ["tar", "-cC", "Idir", "-f", "out.tar", "file"],
        ["tar", "-cf", "out.tar", "--exclude", "--to-command=x", "dir"],
        ["tar", "-cf", "out.tar", "--exclude=-Ihelper", "dir"],
        ["tar", "-cf", "out.tar", "-X", "--use-compress-program=x", "dir"],
        ["tar", "-cf", "out.tar", "--directory", "-I", "file"],
        # Unique abbreviations of benign required options consume values.
        ["tar", "-cf", "out.tar", "--exclude-fr", "--info-script", "dir"],
        ["tar", "-cf", "out.tar", "--strip", "-F", "dir"],
        # bsdtar -W with benign required and no-value long options.
        ["tar", "-cf", "out.tar", "-Wexclude=foo", "dir"],
        ["tar", "-cf", "out.tar", "-W", "exclude", "foo", "dir"],
        ["tar", "-cf", "out.tar", "-W", "totals", "dir"],
        ["tar", "-cWf", "out.tar", "dir"],
        ["tar", "-cvf", "out.tar", "dir", "-W"],
        # Old-style W just takes its argument.
        ["tar", "cWf", "verify-arg", "out.tar", "dir"],
        ["gtar", "-czf", "out.tgz", "dir"],
        ["bsdtar", "-xf", "out.tar"],
    ],
)
def test_ordinary_tar_arguments_remain_allowed(validator, monkeypatch, command):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "tar,gtar,bsdtar")

    validator.validate_command(command)


@pytest.mark.parametrize("letter", sorted("gfLbHVKNCTX"))
def test_tar_gnu_required_short_values_are_data(validator, monkeypatch, letter):
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "tar")

    # Separated: GNU consumes the value; bsdtar either consumes it too or
    # stops at it as the first operand.
    validator.validate_command(["tar", "-c", f"-{letter}", "IF-data", "x.tar"])
    validator._validate_tar_arguments([f"-{letter}", "-I"], GNU_TAR_DIALECT)
    validator._validate_tar_arguments([f"-c{letter}-Ihelper"], GNU_TAR_DIALECT)
    validator._validate_tar_arguments([f"c{letter}", "-I"], GNU_TAR_DIALECT)
    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator._validate_tar_arguments(
            [f"-{letter}", "value", "--to-command=helper"], GNU_TAR_DIALECT
        )
    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator._validate_tar_arguments(
            [f"c{letter}", "value", "-I", "helper"], GNU_TAR_DIALECT
        )


@pytest.mark.parametrize("letter", sorted("bCfsTWX"))
def test_tar_bsd_required_short_values_are_data(validator, letter):
    validator._validate_tar_arguments([f"-{letter}", "-Ihelper"], BSD_TAR_DIALECT)
    if letter != "W":
        validator._validate_tar_arguments([f"-c{letter}-Ihelper"], BSD_TAR_DIALECT)
    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator._validate_tar_arguments(
            [f"-{letter}", "value", "--use-compress-program=helper"], BSD_TAR_DIALECT
        )


@pytest.mark.parametrize(
    ("dialect", "name"),
    [
        (dialect, name)
        for dialect in (GNU_TAR_DIALECT, BSD_TAR_DIALECT)
        for name in sorted(
            dialect.long_options_with_required_value - TAR_PROHIBITED_LONG_OPTIONS
        )
    ],
)
def test_tar_benign_required_long_option_values_are_data(validator, dialect, name):
    validator._validate_tar_arguments(
        [f"--{name}", "--use-compress-program=helper"], dialect
    )
    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator._validate_tar_arguments(
            [f"--{name}", "value", "--use-compress-program=helper"], dialect
        )
    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator._validate_tar_arguments(
            [f"--{name}=value", "--use-compress-program=helper"], dialect
        )


@pytest.mark.parametrize(
    ("dialect", "name"),
    [
        (dialect, name)
        for dialect in (GNU_TAR_DIALECT, BSD_TAR_DIALECT)
        for name in sorted(dialect.long_options_without_separate_value)
    ],
)
def test_tar_no_value_long_options_do_not_swallow_next_option(validator, dialect, name):
    with pytest.raises(ValueError, match=TAR_POLICY_ERROR_PATTERN):
        validator._validate_tar_arguments(
            [f"--{name}", "--use-compress-program=helper"], dialect
        )


def test_tar_dialect_tables_shadow_their_prefix_extensions():
    """Exact names that are prefixes of longer names keep their own arity."""
    for name in ("checkpoint", "list", "sparse", "xattrs", "totals"):
        assert name in GNU_TAR_DIALECT.long_options_without_separate_value
    assert "mode" in GNU_TAR_DIALECT.long_options_with_required_value
    assert "modification-time" in BSD_TAR_DIALECT.long_options_without_separate_value
    assert "totals" in BSD_TAR_DIALECT.long_options_without_separate_value
    for dialect in (GNU_TAR_DIALECT, BSD_TAR_DIALECT):
        assert not (
            dialect.long_options_with_required_value
            & dialect.long_options_without_separate_value
        )
