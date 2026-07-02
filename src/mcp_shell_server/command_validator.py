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
    "xargs",
}


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

    def _git_config_values(self, args: List[str]) -> List[str]:
        values: List[str] = []
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == "-c":
                if index + 1 < len(args):
                    values.append(args[index + 1])
                index += 2
                continue
            if arg.startswith("-c") and arg != "-c":
                values.append(arg[2:])
            index += 1
        return values

    def _is_git_dangerous_config(self, config_value: str) -> bool:
        compact = re.sub(r"\s+", "", config_value)
        return bool(
            re.search(r"(?i)(?:^|[.\s])alias\.[^=\s]+\s*=\s*!", config_value)
            or re.search(r"(?i)^core\.(pager|sshcommand)=", compact)
        )

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

    def _validate_default_argument_policy(self, command: List[str]) -> None:
        cmd = os.path.basename(self._validate_command_name_form(command[0]))
        args = command[1:]
        if cmd in DANGEROUS_COMMANDS:
            raise ValueError(f"Command rejected by default security policy: {cmd}")

        if cmd == "find" and any(arg in {"-exec", "-execdir"} for arg in args):
            raise ValueError("Command rejected by default security policy: find -exec")

        if cmd == "awk" and any(
            "system(" in (compact := re.sub(r"\s+", "", arg)) or "|" in compact
            for arg in args
        ):
            raise ValueError(
                "Command rejected by default security policy: awk command execution"
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

        if cmd == "git" and any(
            self._is_git_dangerous_config(config_value)
            for config_value in self._git_config_values(args)
        ):
            raise ValueError(
                "Command rejected by default security policy: git command execution config"
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
