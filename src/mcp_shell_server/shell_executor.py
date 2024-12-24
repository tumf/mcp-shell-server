import asyncio
import os
import pwd
import shlex
import time
from typing import IO, Any, Dict, List, Optional, Tuple, Union

from mcp_shell_server.command_validator import CommandValidator
from mcp_shell_server.directory_manager import DirectoryManager


class ShellExecutor:
    """
    Executes shell commands in a secure manner by validating against a whitelist.
    """

    def __init__(self):
        """
        Initialize the executor with a command validator and directory manager.
        """
        self.validator = CommandValidator()
        self.directory_manager = DirectoryManager()

    def _validate_redirection_syntax(self, command: List[str]) -> None:
        """
        Validate the syntax of redirection operators in the command.

        Args:
            command (List[str]): Command and its arguments including redirections

        Raises:
            ValueError: If the redirection syntax is invalid
        """
        prev_token = None
        for token in command:
            if token in [">", ">>", "<"]:
                if prev_token and prev_token in [">", ">>", "<"]:
                    raise ValueError(
                        "Invalid redirection syntax: consecutive operators"
                    )
            prev_token = token

    def _process_redirections(
        self, command: List[str]
    ) -> Tuple[List[str], Dict[str, Union[None, str, bool]]]:
        """
        Process input/output redirections in the command.

        Args:
            command (List[str]): Command and its arguments including redirections

        Returns:
            Tuple[List[str], Dict[str, Any]]: Processed command without redirections and
                                             redirection configuration

        Raises:
            ValueError: If the redirection syntax is invalid
        """
        self._validate_redirection_syntax(command)

        cmd = []
        redirects: Dict[str, Union[None, str, bool]] = {
            "stdin": None,
            "stdout": None,
            "stdout_append": False,
        }

        i = 0
        while i < len(command):
            token = command[i]

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
                if path in [">", ">>", "<"]:
                    raise ValueError("Invalid redirection target: operator found")
                redirects["stdin"] = path
                i += 2
                continue

            cmd.append(token)
            i += 1

        return cmd, redirects

    async def _setup_redirects(
        self,
        redirects: Dict[str, Union[None, str, bool]],
        directory: Optional[str] = None,
    ) -> Dict[str, Union[IO[Any], int, str, None]]:
        """
        Set up file handles for redirections.

        Args:
            redirects (Dict[str, Union[None, str, bool]]): Redirection configuration
            directory (Optional[str]): Working directory for file paths

        Returns:
            Dict[str, Union[IO[Any], int, str, None]]: File handles for subprocess
        """
        handles: Dict[str, Union[IO[Any], int, str, None]] = {}

        # Handle input redirection
        if redirects["stdin"]:
            path = (
                os.path.join(directory or "", str(redirects["stdin"]))
                if directory and redirects["stdin"]
                else str(redirects["stdin"])
            )
            try:
                file = open(path, "r")
                handles["stdin"] = asyncio.subprocess.PIPE
                handles["stdin_data"] = file.read()
                file.close()
            except IOError as e:
                raise ValueError(f"Failed to open input file: {e}") from e

        # Handle output redirection
        if redirects["stdout"]:
            path = (
                os.path.join(directory or "", str(redirects["stdout"]))
                if directory and redirects["stdout"]
                else str(redirects["stdout"])
            )
            mode = "a" if redirects["stdout_append"] else "w"
            try:
                handles["stdout"] = open(path, mode)
            except IOError as e:
                raise ValueError(f"Failed to open output file: {e}") from e
        else:
            handles["stdout"] = asyncio.subprocess.PIPE

        handles["stderr"] = asyncio.subprocess.PIPE

        return handles

    async def _cleanup_handles(
        self, handles: Dict[str, Union[IO[Any], int, None]]
    ) -> None:
        """
        Clean up file handles after command execution.

        Args:
            handles (Dict[str, Union[IO[Any], int, None]]): File handles to clean up
        """
        for key in ["stdout", "stderr"]:
            handle = handles.get(key)
            if handle and hasattr(handle, "close") and not isinstance(handle, int):
                try:
                    handle.close()
                except (IOError, ValueError):
                    pass

    def _clean_command(self, command: List[str]) -> List[str]:
        """
        Clean command by trimming whitespace from each part.
        Removes empty strings but preserves arguments that are meant to be spaces.

        Args:
            command (List[str]): Original command and its arguments

        Returns:
            List[str]: Cleaned command
        """
        return [arg for arg in command if arg]  # 空文字列のみを除外

    def _create_shell_command(self, command: List[str]) -> str:
        """
        Create a shell command string from a list of arguments.
        Handles wildcards and arguments properly.
        """
        if not command:
            return ""

        escaped_args = []
        for arg in command:
            # すべての引数を適切にエスケープする
            if arg.isspace():
                # 空白文字のみの場合はシングルクォートで囲む
                escaped_args.append(f"'{arg}'")
            else:
                # ワイルドカードを含む場合も含めて、すべての引数を適切にエスケープ
                escaped_args.append(shlex.quote(arg.strip()))

        return " ".join(escaped_args)

    def _validate_command(self, command: List[str]) -> None:
        """
        Validate if the command is allowed to be executed.

        Args:
            command (List[str]): Command and its arguments

        Raises:
            ValueError: If the command is empty, not allowed, or contains invalid shell operators
        """
        if not command:
            raise ValueError("Empty command")

        self.validator.validate_command(command)

    def _validate_directory(self, directory: Optional[str]) -> None:
        """
        Validate if the directory exists and is accessible.

        Args:
            directory (Optional[str]): Directory path to validate

        Raises:
            ValueError: If the directory doesn't exist, not absolute or is not accessible
        """
        self.directory_manager.validate_directory(directory)

    def _validate_no_shell_operators(self, cmd: str) -> None:
        """Validate that the command does not contain shell operators"""
        self.validator.validate_no_shell_operators(cmd)

    def _validate_pipeline(self, commands: List[str]) -> Dict[str, str]:
        """Validate pipeline command and ensure all parts are allowed

        Returns:
            Dict[str, str]: Error message if validation fails, empty dict if success
        """
        return self.validator.validate_pipeline(commands)

    def _split_pipe_commands(self, command: List[str]) -> List[List[str]]:
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

    def _parse_command(
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

    def _preprocess_command(self, command: List[str]) -> List[str]:
        """
        Preprocess the command to handle cases where '|' is attached to a command.
        """
        preprocessed_command = []
        for token in command:
            if token in ["||", "&&", ";"]:  # 特別なシェル演算子を保護
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

    def _get_default_shell(self) -> str:
        """Get the login shell of the current user"""
        try:
            return pwd.getpwuid(os.getuid()).pw_shell
        except (ImportError, KeyError):
            return os.environ.get("SHELL", "/bin/sh")

    async def execute(
        self,
        command: List[str],
        directory: str,
        stdin: Optional[str] = None,
        timeout: Optional[int] = None,
        envs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        process = None  # Initialize process variable

        try:
            # Validate directory if specified
            try:
                self._validate_directory(directory)
            except ValueError as e:
                return {
                    "error": str(e),
                    "status": 1,
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time": time.time() - start_time,
                }

            # Process command
            preprocessed_command = self._preprocess_command(command)
            cleaned_command = self._clean_command(preprocessed_command)
            if not cleaned_command:
                return {
                    "error": "Empty command",
                    "status": 1,
                    "stdout": "",
                    "stderr": "Empty command",
                    "execution_time": time.time() - start_time,
                }

            # First check for pipe operators and handle pipeline
            if "|" in cleaned_command:
                try:
                    # Validate pipeline first using the validator
                    try:
                        self.validator.validate_pipeline(cleaned_command)
                    except ValueError as e:
                        return {
                            "error": str(e),
                            "status": 1,
                            "stdout": "",
                            "stderr": str(e),
                            "execution_time": time.time() - start_time,
                        }

                    # Split commands
                    commands: List[List[str]] = []
                    current_cmd: List[str] = []
                    for token in cleaned_command:
                        if token == "|":
                            if current_cmd:
                                commands.append(current_cmd)
                                current_cmd = []
                            else:
                                raise ValueError("Empty command before pipe operator")
                        else:
                            current_cmd.append(token)
                    if current_cmd:
                        commands.append(current_cmd)

                    return await self._execute_pipeline(
                        commands, directory, timeout, envs
                    )
                except ValueError as e:
                    return {
                        "error": str(e),
                        "status": 1,
                        "stdout": "",
                        "stderr": str(e),
                        "execution_time": time.time() - start_time,
                    }

            # Then check for other shell operators
            for token in cleaned_command:
                try:
                    self.validator.validate_no_shell_operators(token)
                except ValueError as e:
                    return {
                        "error": str(e),
                        "status": 1,
                        "stdout": "",
                        "stderr": str(e),
                        "execution_time": time.time() - start_time,
                    }

            # Single command execution
            cmd, redirects = self._parse_command(cleaned_command)
            self.validator.validate_command(cmd)

            # Directory validation
            if directory:
                if not os.path.exists(directory):
                    return {
                        "error": f"Directory does not exist: {directory}",
                        "status": 1,
                        "stdout": "",
                        "stderr": f"Directory does not exist: {directory}",
                        "execution_time": time.time() - start_time,
                    }
                if not os.path.isdir(directory):
                    return {
                        "error": f"Not a directory: {directory}",
                        "status": 1,
                        "stdout": "",
                        "stderr": f"Not a directory: {directory}",
                        "execution_time": time.time() - start_time,
                    }

            # Clean and validate command
            cleaned_command = self._clean_command(command)
            if not cleaned_command:
                raise ValueError("Empty command")

            # Update stdin from redirects if present
            if redirects["stdin"]:
                stdin_path = self.directory_manager.get_absolute_path(
                    str(redirects["stdin"]), directory
                )
                try:
                    with open(stdin_path, "r") as f:
                        stdin = f.read()
                except IOError as e:
                    raise ValueError(f"Failed to read input file: {e}") from e

            # Setup output redirection
            stdout_handle: Union[int, IO[Any]] = asyncio.subprocess.PIPE
            if redirects["stdout"]:
                stdout_path = self.directory_manager.get_absolute_path(
                    str(redirects["stdout"]), directory
                )
                mode = "a" if redirects["stdout_append"] else "w"
                try:
                    stdout_handle = open(stdout_path, mode)
                except IOError as e:
                    raise ValueError(f"Failed to open output file: {e}") from e

            # Execute the command with interactive shell
            shell = self._get_default_shell()
            shell_cmd = self._create_shell_command(cmd)
            shell_cmd = f"{shell} -i -c {shlex.quote(shell_cmd)}"

            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdin=asyncio.subprocess.PIPE if stdin else None,
                stdout=stdout_handle,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(envs or {})},  # Merge environment variables
                cwd=directory,
            )

            try:
                # Send input if provided
                stdin_bytes = stdin.encode() if stdin else None

                async def communicate_with_timeout():
                    try:
                        return await process.communicate(input=stdin_bytes)
                    except Exception as e:
                        try:
                            process.kill()
                            await process.wait()
                        except Exception:
                            pass
                        raise e

                if timeout:
                    stdout, stderr = await asyncio.wait_for(
                        communicate_with_timeout(), timeout=timeout
                    )
                else:
                    stdout, stderr = await communicate_with_timeout()

                # Close file handle if using file redirection
                if isinstance(stdout_handle, IO):
                    stdout_handle.close()

                return {
                    "error": None,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "status": process.returncode,
                    "execution_time": time.time() - start_time,
                    "directory": directory,
                }

            except asyncio.TimeoutError:
                # Kill process on timeout
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass

                # Clean up file handle
                if isinstance(stdout_handle, IO):
                    stdout_handle.close()

                return {
                    "error": f"Command timed out after {timeout} seconds",
                    "status": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "execution_time": time.time() - start_time,
                }

        except Exception as e:
            return {
                "error": str(e),
                "status": 1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": time.time() - start_time,
            }
        finally:
            # Ensure process is terminated
            if process and process.returncode is None:
                process.kill()
                await process.wait()

    async def _execute_pipeline(
        self,
        commands: List[List[str]],
        directory: Optional[str] = None,
        timeout: Optional[int] = None,
        envs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        processes: List[asyncio.subprocess.Process] = []

        try:
            parsed_commands = []
            first_stdin: Optional[bytes] = None
            last_stdout: Optional[IO[Any]] = None

            for cmd in commands:
                parsed_cmd, redirects = self._parse_command(cmd)
                parsed_commands.append(parsed_cmd)

                if commands.index(cmd) == 0 and redirects["stdin"]:
                    stdin_path = self.directory_manager.get_absolute_path(
                        str(redirects["stdin"]), directory
                    )
                    with open(stdin_path, "r") as f:
                        first_stdin = f.read().encode()

                if commands.index(cmd) == len(commands) - 1 and redirects["stdout"]:
                    stdout_path = self.directory_manager.get_absolute_path(
                        str(redirects["stdout"]), directory
                    )
                    last_stdout = open(
                        stdout_path, "a" if redirects["stdout_append"] else "w"
                    )
                    last_stdout = open(
                        stdout_path, "a" if redirects["stdout_append"] else "w"
                    )

            # Execute pipeline
            prev_stdout: Optional[bytes] = first_stdin
            final_stderr: bytes = b""
            final_stdout: bytes = b""

            for i, cmd in enumerate(parsed_commands):
                shell_cmd = self._create_shell_command(cmd)

                # Get default shell for the first command and set interactive mode
                if i == 0:
                    shell = self._get_default_shell()
                    shell_cmd = f"{shell} -i -c {shlex.quote(shell_cmd)}"

                process = await asyncio.create_subprocess_shell(
                    shell_cmd,
                    stdin=asyncio.subprocess.PIPE if prev_stdout is not None else None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, **(envs or {})},  # Merge environment variables
                    cwd=directory,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input=prev_stdout), timeout=timeout
                    )

                    prev_stdout = stdout if stdout else b""

                    if i == len(parsed_commands) - 1:
                        final_stdout = stdout if stdout else b""

                    final_stderr += stderr if stderr else b""
                    processes.append(process)

                    if process.returncode != 0:
                        raise ValueError(
                            f"Command failed with exit code {process.returncode}"
                        )

                except asyncio.TimeoutError:
                    process.kill()
                    raise

            if last_stdout:
                last_stdout.write(final_stdout.decode("utf-8", errors="replace"))
                final_output = ""
            else:
                final_output = final_stdout.decode("utf-8", errors="replace")

            return {
                "error": None,
                "stdout": final_output,
                "stderr": final_stderr.decode("utf-8", errors="replace"),
                "status": processes[-1].returncode if processes else 1,
                "execution_time": time.time() - start_time,
                "directory": directory,
            }

        except Exception as e:
            return {
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "status": 1,
                "execution_time": time.time() - start_time,
            }

        finally:
            # Ensure all processes are terminated
            for process in processes:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            if isinstance(last_stdout, IO):
                last_stdout.close()
