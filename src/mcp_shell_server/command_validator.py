"""Command validation for argv-based shell execution."""

import os
import re
from typing import Dict, List

SHELL_METACHAR_PATTERN = re.compile(r"[\s;&|<>`\n\r]")
DANGEROUS_COMMANDS = {
    "sh",
    "bash",
    "zsh",
    "fish",
    "csh",
    "ksh",
    "python",
    "python3",
    "perl",
    "ruby",
    "node",
    "php",
    "lua",
    "env",
    "chroot",
    "ex",
    "flock",
    "gdb",
    "ionice",
    "less",
    "man",
    "more",
    "mysql",
    "nice",
    "nohup",
    "pg",
    "psql",
    "rsync",
    "script",
    "sed",
    "setsid",
    "sqlite3",
    "ssh",
    "stdbuf",
    "taskset",
    "time",
    "timeout",
    "unshare",
    "vi",
    "view",
    "vim",
    "watch",
    "xargs",
    "zip",
}

COMMAND_POLICY_ALIASES = {
    "bfind": "find",
    "bsdtar": "tar",
    "gawk": "awk",
    "gfind": "find",
    "gsort": "sort",
    "gtar": "tar",
    "mawk": "awk",
    "nawk": "awk",
}

# GNU coreutils `sort` long options mapped to whether they consume a separate
# value argument. The table exists so abbreviated options can be resolved the
# way getopt_long resolves them, and so benign option values are never rescanned
# as options themselves.
SORT_LONG_OPTIONS: Dict[str, bool] = {
    "batch-size": True,
    "buffer-size": True,
    "check": False,  # value is optional and only accepted as `--check=DIAG`
    "compress-program": True,
    "debug": False,
    "dictionary-order": False,
    "field-separator": True,
    "files0-from": True,
    "general-numeric-sort": False,
    "help": False,
    "human-numeric-sort": False,
    "ignore-case": False,
    "ignore-leading-blanks": False,
    "ignore-nonprinting": False,
    "key": True,
    "merge": False,
    "month-sort": False,
    "numeric-sort": False,
    "output": True,
    "parallel": True,
    "random-sort": False,
    "random-source": True,
    "reverse": False,
    "sort": True,
    "stable": False,
    "temporary-directory": True,
    "unique": False,
    "version": False,
    "version-sort": False,
    "zero-terminated": False,
}
# Options that select an external program, an output path, an external input
# file list, or an external temporary directory.
SORT_PROHIBITED_LONG_OPTIONS = {
    "compress-program",
    "files0-from",
    "output",
    "temporary-directory",
}
SORT_SHORT_OPTIONS_WITH_VALUE = {"k", "o", "S", "t", "T"}
SORT_PROHIBITED_SHORT_OPTIONS = {"o", "T"}
SORT_POLICY_ERROR = (
    "Command rejected by default security policy: sort external program or path option"
)

AWK_LONG_OPTIONS = {
    "assign",
    "bignum",
    "characters-as-bytes",
    "copyright",
    "csv",
    "debug",
    "dump-variables",
    "exec",
    "field-separator",
    "file",
    "gen-pot",
    "help",
    "include",
    "lint",
    "load",
    "no-optimize",
    "non-decimal-data",
    "optimize",
    "posix",
    "pretty-print",
    "profile",
    "sandbox",
    "source",
    "trace",
    "traditional",
    "use-lc-numeric",
    "version",
}
AWK_PROHIBITED_LONG_OPTIONS = {"exec", "file", "include", "load", "source"}
AWK_PROHIBITED_SHORT_OPTIONS = {"E", "e", "f", "i", "l"}
AWK_SHORT_OPTIONS_WITH_REQUIRED_VALUE = {"E", "e", "f", "F", "i", "l", "v"}
AWK_SHORT_OPTIONS_WITH_OPTIONAL_ATTACHED_VALUE = {"d", "D", "L", "o", "p"}
AWK_EXTERNAL_DIRECTIVE_PATTERN = re.compile(r"(^|\s)@(include|load)\b")


class CommandValidator:
    """Validates argv commands against allowlists and default deny rules."""

    def __init__(self):
        """Initialize the validator."""
        return None

    def _get_allowed_commands(self) -> set[str]:
        """Get the set of allowed commands from environment variables."""
        allow_commands = os.environ.get("ALLOW_COMMANDS", "")
        allowed_commands = os.environ.get("ALLOWED_COMMANDS", "")
        commands = allow_commands + "," + allowed_commands
        return {cmd.strip() for cmd in commands.split(",") if cmd.strip()}

    def _validate_pattern_source(self, pattern: str) -> None:
        if re.search(r"[\s;&|<>`\n\r]", pattern):
            raise ValueError(f"Unsafe allowed command pattern: {pattern}")

    def _get_allowed_patterns(self) -> List[re.Pattern]:
        """Get the list of allowed regex patterns from environment variables."""
        allow_patterns = os.environ.get("ALLOW_PATTERNS", "")
        patterns = [
            pattern.strip() for pattern in allow_patterns.split(",") if pattern.strip()
        ]
        compiled = []
        for pattern in patterns:
            self._validate_pattern_source(pattern)
            compiled.append(re.compile(pattern))
        return compiled

    def get_allowed_commands(self) -> list[str]:
        """Public API: return list form of allowed commands."""
        return list(self._get_allowed_commands())

    def _validate_command_name_form(self, command: str) -> str:
        cmd = command.strip()
        if not cmd:
            raise ValueError("Empty command")
        if SHELL_METACHAR_PATTERN.search(cmd):
            raise ValueError(f"Unsafe command name: {cmd}")
        return cmd

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is in the allowed list or fully matches a pattern."""
        cmd = self._validate_command_name_form(command)
        if cmd in self._get_allowed_commands():
            return True
        for pattern in self._get_allowed_patterns():
            if pattern.fullmatch(cmd):
                return True
        return False

    def validate_no_shell_operators(self, cmd: str) -> None:
        """Validate that a token is not a shell operator or shell fragment."""
        if cmd in [";", "&&", "||", "|"]:
            raise ValueError(f"Unexpected shell operator: {cmd}")
        if any(operator in cmd for operator in [";", "&&", "||", "`", "\n", "\r"]):
            raise ValueError(f"Unexpected shell operator: {cmd}")

    def _has_option_value(self, args: List[str], option: str, predicate) -> bool:
        for index, arg in enumerate(args):
            if arg == option and index + 1 < len(args) and predicate(args[index + 1]):
                return True
            if arg.startswith(f"{option}=") and predicate(arg.split("=", 1)[1]):
                return True
        return False

    def _has_any_option(self, args: List[str], options: set[str]) -> bool:
        return any(
            arg in options or any(arg.startswith(f"{option}=") for option in options)
            for arg in args
        )

    def _has_short_option_prefix(self, args: List[str], option: str) -> bool:
        return any(arg == option or arg.startswith(option) for arg in args)

    def _git_subcommand_index(self, args: List[str]) -> int | None:
        options_with_value = {
            "-C",
            "--config-env",
            "--git-dir",
            "--namespace",
            "--super-prefix",
            "--work-tree",
        }
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == "--":
                return None
            if arg == "-c" or arg.startswith("-c"):
                raise ValueError(
                    "Command rejected by default security policy: git command-scoped config"
                )
            if not arg.startswith("-"):
                return index
            index += 2 if arg in options_with_value else 1
        return None

    def _sort_long_option_candidates(self, name: str) -> set[str]:
        """Resolve a `sort` long option name the way getopt_long resolves it.

        An exact name wins outright; otherwise every option the token
        abbreviates stays a candidate. GNU sort rejects ambiguous abbreviations,
        so treating each candidate as reachable only makes the policy stricter.
        """
        if name in SORT_LONG_OPTIONS:
            return {name}
        return {option for option in SORT_LONG_OPTIONS if option.startswith(name)}

    def _awk_uses_external_program_source(self, args: List[str]) -> bool:
        def prohibited_long_option(name: str) -> bool:
            candidates = (
                {name}
                if name in AWK_LONG_OPTIONS
                else {option for option in AWK_LONG_OPTIONS if option.startswith(name)}
            )
            return bool(candidates & AWK_PROHIBITED_LONG_OPTIONS)

        index = 0
        while index < len(args):
            arg = args[index]
            index += 1
            if AWK_EXTERNAL_DIRECTIVE_PATTERN.search(arg):
                return True
            if arg.startswith("--"):
                name = arg[2:].partition("=")[0]
                if prohibited_long_option(name):
                    return True
            elif arg == "-W" and index + 1 < len(args):
                name = args[index + 1].partition("=")[0]
                if prohibited_long_option(name):
                    return True
            elif arg.startswith("-W"):
                name = arg[2:].partition("=")[0]
                if prohibited_long_option(name):
                    return True
            elif len(arg) > 1 and arg[0] == "-":
                for position, letter in enumerate(arg[1:], start=1):
                    if letter in AWK_PROHIBITED_SHORT_OPTIONS:
                        return True
                    if letter in AWK_SHORT_OPTIONS_WITH_REQUIRED_VALUE:
                        if position == len(arg) - 1:
                            index += 1
                        break
                    if letter in AWK_SHORT_OPTIONS_WITH_OPTIONAL_ATTACHED_VALUE:
                        break
        return False

    def _validate_sort_arguments(self, args: List[str]) -> None:
        """Reject `sort` options that reach outside the validated argv boundary.

        GNU option permutation allows options after operands, so every argument
        is scanned until a discrete `--`; tokens after it are filename operands
        even when they look like options.
        """
        index = 0
        while index < len(args):
            arg = args[index]
            index += 1
            if arg == "--":
                return
            if arg == "-" or not arg.startswith("-"):
                continue
            if arg.startswith("--"):
                name, separator, _value = arg[2:].partition("=")
                candidates = self._sort_long_option_candidates(name)
                if candidates & SORT_PROHIBITED_LONG_OPTIONS:
                    raise ValueError(SORT_POLICY_ERROR)
                if not separator and len(candidates) == 1:
                    (resolved,) = candidates
                    if SORT_LONG_OPTIONS[resolved]:
                        index += 1
                continue
            for position, letter in enumerate(arg[1:], start=1):
                if letter in SORT_PROHIBITED_SHORT_OPTIONS:
                    raise ValueError(SORT_POLICY_ERROR)
                if letter in SORT_SHORT_OPTIONS_WITH_VALUE:
                    # The value is either the rest of this token or the next
                    # argument. Either way it is data, so it must not be
                    # rescanned as further clustered option letters.
                    if position == len(arg) - 1:
                        index += 1
                    break

    def _policy_command_name(self, command: str) -> str:
        cmd = os.path.basename(self._validate_command_name_form(command))
        if re.fullmatch(r"python\d+(?:\.\d+)*", cmd):
            return "python"
        return COMMAND_POLICY_ALIASES.get(cmd, cmd)

    def _validate_default_argument_policy(self, command: List[str]) -> None:
        cmd = self._policy_command_name(command[0])
        args = command[1:]
        if cmd in DANGEROUS_COMMANDS:
            raise ValueError(f"Command rejected by default security policy: {cmd}")

        if cmd == "find":
            if any(arg in {"-exec", "-execdir"} for arg in args):
                raise ValueError(
                    "Command rejected by default security policy: find -exec"
                )
            if any(arg in {"-fprintf", "-fprint", "-fprint0", "-fls"} for arg in args):
                raise ValueError(
                    "Command rejected by default security policy: find file output"
                )

        if cmd == "awk" and (
            self._awk_uses_external_program_source(args)
            or any(
                "system(" in (compact := re.sub(r"\s+", "", arg))
                or "|" in compact
                or ">" in arg
                or "<" in arg
                for arg in args
            )
        ):
            raise ValueError(
                "Command rejected by default security policy: awk external access"
            )

        if cmd == "tar" and (
            self._has_option_value(
                args, "--checkpoint-action", lambda value: value.startswith("exec=")
            )
            or self._has_any_option(
                args, {"--to-command", "--use-compress-program", "--rsh-command"}
            )
            or self._has_short_option_prefix(args, "-I")
        ):
            raise ValueError(
                "Command rejected by default security policy: tar command execution option"
            )

        if cmd == "sort":
            self._validate_sort_arguments(args)

        if cmd == "git":
            subcommand_index = self._git_subcommand_index(args)
            git_args = args if subcommand_index is None else args[subcommand_index:]
            clone_args = git_args[1:] if git_args and git_args[0] == "clone" else []
            if git_args and git_args[0] == "config":
                raise ValueError(
                    "Command rejected by default security policy: git config"
                )
            if (
                self._has_any_option(
                    args,
                    {
                        "--config-env",
                        "--exec",
                        "--exec-path",
                        "--receive-pack",
                        "--upload-pack",
                    },
                )
                or any(arg.startswith("--upl") for arg in args)
                or any(arg.startswith("--rece") for arg in args)
                or (
                    clone_args
                    and (
                        self._has_short_option_prefix(clone_args, "-c")
                        or self._has_short_option_prefix(clone_args, "-u")
                        or any(arg.startswith("--u") for arg in clone_args)
                        or any(
                            arg == "--co"
                            or arg.startswith("--co=")
                            or arg.startswith("--con")
                            for arg in clone_args
                        )
                    )
                )
                or any(arg.startswith("ext::") for arg in args)
            ):
                raise ValueError(
                    "Command rejected by default security policy: git external program"
                )

    def validate_pipeline(self, commands: List[str]) -> Dict[str, str]:
        """Validate pipeline tokens and ensure all command segments are allowed."""
        current_cmd: List[str] = []

        for token in commands:
            if token == "|":
                if not current_cmd:
                    raise ValueError("Empty command before pipe operator")
                self.validate_command(current_cmd)
                current_cmd = []
            elif token in [";", "&&", "||"]:
                raise ValueError(f"Unexpected shell operator in pipeline: {token}")
            else:
                if not current_cmd:
                    self.validate_no_shell_operators(token)
                current_cmd.append(token)

        if current_cmd:
            self.validate_command(current_cmd)

        return {}

    def validate_command(self, command: List[str]) -> None:
        """Validate if the argv command is allowed to be executed."""
        if not command:
            raise ValueError("Empty command")

        if not self._get_allowed_commands() and not self._get_allowed_patterns():
            raise ValueError(
                "No commands are allowed. Please set ALLOW_COMMANDS environment variable."
            )

        cleaned_cmd = self._validate_command_name_form(command[0])
        self._validate_default_argument_policy([cleaned_cmd, *command[1:]])
        if not self.is_command_allowed(cleaned_cmd):
            raise ValueError(f"Command not allowed: {cleaned_cmd}")
