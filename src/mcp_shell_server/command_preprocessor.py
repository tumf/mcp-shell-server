import shlex
from typing import Dict, List, Tuple, Union


class CommandPreProcessor:
    """
    Pre-processes and validates shell commands before execution
    """

    def preprocess_command(self, command: List[str]) -> List[str]:
        """
        Preprocess the command to handle cases where '|' is attached to a command.
        """
        preprocessed_command = []
        for token in command:
            if token in ["||", "&&", ";"]:  # Special shell operators
                preprocessed_command.append(token)
            elif "|" in token and token != "|":
                parts = token.split("|")
                preprocessed_command.extend(
                    [part.strip() for part in parts if part.strip()]
                )
                preprocessed_command.append("|")
            else:
                preprocessed_command.append(token)
        return preprocessed_command

    def clean_command(self, command: List[str]) -> List[str]:
        """
        Clean command by trimming whitespace from each part.
        Removes empty strings but preserves arguments that are meant to be spaces.

        Args:
            command (List[str]): Original command and its arguments

        Returns:
            List[str]: Cleaned command
        """
        return [arg for arg in command if arg]  # Remove empty strings

    def create_shell_command(self, command: List[str]) -> str:
        """
        Create a shell command string from a list of arguments.
        Handles wildcards and arguments properly.
        """
        if not command:
            return ""

        escaped_args = []
        for arg in command:
            if arg.isspace():
                # Wrap space-only arguments in single quotes
                escaped_args.append(f"'{arg}'")
            else:
                # Properly escape all arguments including those with wildcards
                escaped_args.append(shlex.quote(arg.strip()))

        return " ".join(escaped_args)

    def split_pipe_commands(self, command: List[str]) -> List[List[str]]:
        """
        Split commands by pipe operator into separate commands.

        Args:
            command (List[str]): Command and its arguments with pipe operators

        Returns:
            List[List[str]]: List of commands split by pipe operator
        """
        commands: List[List[str]] = []
        current_command: List[str] = []

        for arg in command:
            if arg.strip() == "|":
                if current_command:
                    commands.append(current_command)
                    current_command = []
            else:
                current_command.append(arg)

        if current_command:
            commands.append(current_command)

        return commands

    def parse_command(
        self, command: List[str]
    ) -> Tuple[List[str], Dict[str, Union[None, str, bool]]]:
        """
        Parse command and extract redirections.
        """
        cmd = []
        redirects: Dict[str, Union[None, str, bool]] = {
            "stdin": None,
            "stdout": None,
            "stdout_append": False,
        }

        i = 0
        while i < len(command):
            token = command[i]

            # Shell operators check
            if token in ["|", ";", "&&", "||"]:
                raise ValueError(f"Unexpected shell operator: {token}")

            # Output redirection
            if token in [">", ">>"]:
                if i + 1 >= len(command):
                    raise ValueError("Missing path for output redirection")
                if i + 1 < len(command) and command[i + 1] in [">", ">>", "<"]:
                    raise ValueError("Invalid redirection target: operator found")
                path = command[i + 1]
                redirects["stdout"] = path
                redirects["stdout_append"] = token == ">>"
                i += 2
                continue

            # Input redirection
            if token == "<":
                if i + 1 >= len(command):
                    raise ValueError("Missing path for input redirection")
                path = command[i + 1]
                redirects["stdin"] = path
                i += 2
                continue

            cmd.append(token)
            i += 1

        return cmd, redirects
