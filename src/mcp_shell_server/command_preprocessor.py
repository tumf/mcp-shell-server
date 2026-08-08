import shlex
from typing import Dict, List, Tuple, Union


class CommandPreProcessor:
    """
    Pre-processes and validates shell commands before execution
    """

    def preprocess_command(self, command: List[str]) -> List[str]:
        """
        Return argv unchanged; only a discrete '|' element is pipeline syntax.

        A pipe character embedded in any other argv element is literal argument
        data (regular expressions, URLs, JSON, awk programs, ...), so it is
        never split into a synthetic pipeline boundary. The historical implicit
        conversion of an attached pipe such as "ls|" into a pipeline is
        intentionally removed: it corrupted argument data and let a trailing
        pipe smuggle an extra allowlisted pipeline stage past command-specific
        argument policies (GHSA-q8pm-q3r2-q7cg, GHSA-7wg7-jj87-qp4c). Clients
        MUST express pipelines with a discrete "|" element.
        """
        return list(command)

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
            if arg == "|":
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
