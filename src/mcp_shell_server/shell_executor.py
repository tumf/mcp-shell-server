import asyncio
import logging
import os
import pwd
import shlex
import time
from typing import IO, Any, Dict, List, Optional, Union

from mcp_shell_server.command_preprocessor import CommandPreProcessor
from mcp_shell_server.command_validator import CommandValidator
from mcp_shell_server.directory_manager import DirectoryManager
from mcp_shell_server.io_redirection_handler import IORedirectionHandler
from mcp_shell_server.process_manager import ProcessManager


class ShellExecutor:
    """
    Executes shell commands in a secure manner by validating against a whitelist.
    """

    def __init__(self, process_manager: Optional[ProcessManager] = None):
        """
        Initialize the executor with a command validator, directory manager and IO handler.
        Args:
            process_manager: Optional ProcessManager instance for testing
        """
        self.validator = CommandValidator()
        self.directory_manager = DirectoryManager()
        self.io_handler = IORedirectionHandler()
        self.preprocessor = CommandPreProcessor()
        self.process_manager = (
            process_manager if process_manager is not None else ProcessManager()
        )

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
            preprocessed_command = self.preprocessor.preprocess_command(command)
            cleaned_command = self.preprocessor.clean_command(preprocessed_command)
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
                    commands = self.preprocessor.split_pipe_commands(cleaned_command)
                    if not commands:
                        raise ValueError("Empty command before pipe operator")

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
            try:
                cmd, redirects = self.preprocessor.parse_command(cleaned_command)
            except ValueError as e:
                return {
                    "error": str(e),
                    "status": 1,
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time": time.time() - start_time,
                }

            try:
                self.validator.validate_command(cmd)
            except ValueError as e:
                return {
                    "error": str(e),
                    "status": 1,
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time": time.time() - start_time,
                }

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
            if not cleaned_command:
                raise ValueError("Empty command")

            # Initialize stdout_handle with default value
            stdout_handle: Union[IO[Any], int] = asyncio.subprocess.PIPE

            try:
                # Process redirections
                cmd, redirects = self.io_handler.process_redirections(cleaned_command)

                # Setup handles for redirection
                handles = await self.io_handler.setup_redirects(redirects, directory)

                # Get stdin and stdout from handles if present
                stdin_data = handles.get("stdin_data")
                if isinstance(stdin_data, str):
                    stdin = stdin_data

                # Get stdout handle if present
                stdout_value = handles.get("stdout")
                if isinstance(stdout_value, (IO, int)):
                    stdout_handle = stdout_value

            except ValueError as e:
                return {
                    "error": str(e),
                    "status": 1,
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time": time.time() - start_time,
                }

            # Execute the command with interactive shell
            shell = self._get_default_shell()
            shell_cmd = self.preprocessor.create_shell_command(cmd)
            shell_cmd = f"{shell} -i -c {shlex.quote(shell_cmd)}"

            process = await self.process_manager.create_process(
                shell_cmd, directory, stdout_handle=stdout_handle, envs=envs
            )

            try:
                # Send input if provided
                stdin_bytes = stdin.encode() if stdin else None

                async def communicate_with_timeout():
                    try:
                        return await process.communicate(input=stdin_bytes)
                    except Exception as e:
                        try:
                            await process.wait()
                        except Exception:
                            pass
                        raise e

                try:
                    # プロセス通信実行
                    stdout, stderr = await asyncio.shield(
                        self.process_manager.execute_with_timeout(
                            process, stdin=stdin, timeout=timeout
                        )
                    )

                    # ファイルハンドル処理
                    if isinstance(stdout_handle, IO):
                        try:
                            stdout_handle.close()
                        except (IOError, OSError) as e:
                            logging.warning(f"Error closing stdout: {e}")

                    # Handle case where returncode is None
                    final_returncode = (
                        0 if process.returncode is None else process.returncode
                    )

                    return {
                        "error": None,
                        "stdout": stdout.decode().strip() if stdout else "",
                        "stderr": stderr.decode().strip() if stderr else "",
                        "returncode": final_returncode,
                        "status": process.returncode,
                        "execution_time": time.time() - start_time,
                        "directory": directory,
                    }

                except asyncio.TimeoutError:
                    # タイムアウト時のプロセスクリーンアップ
                    if process and process.returncode is None:
                        try:
                            process.kill()
                            await asyncio.shield(process.wait())
                        except ProcessLookupError:
                            # Process already terminated
                            pass

                    # ファイルハンドルクリーンアップ
                    if isinstance(stdout_handle, IO):
                        stdout_handle.close()

                    return {
                        "error": f"Command timed out after {timeout} seconds",
                        "status": -1,
                        "stdout": "",
                        "stderr": f"Command timed out after {timeout} seconds",
                        "execution_time": time.time() - start_time,
                    }

            except Exception as e:  # Exception handler for subprocess
                if isinstance(stdout_handle, IO):
                    stdout_handle.close()
                return {
                    "error": str(e),
                    "status": 1,
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time": time.time() - start_time,
                }

        finally:
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
        try:
            # Validate all commands before execution
            for cmd in commands:
                # Make sure each command is allowed
                self.validator.validate_command(cmd)

            # Initialize IO variables
            parsed_commands = []
            first_stdin: Optional[bytes] = None
            pipeline_stdout: Union[IO[Any], int, None] = None
            first_redirects = None
            last_redirects = None

            # Process redirections for all commands
            for i, command in enumerate(commands):
                cmd, redirects = self.io_handler.process_redirections(command)
                parsed_commands.append(cmd)

                if i == 0:  # First command
                    first_redirects = redirects
                elif i == len(commands) - 1:  # Last command
                    last_redirects = redirects

            # Setup first and last command redirections
            if first_redirects:
                handles = await self.io_handler.setup_redirects(
                    first_redirects, directory
                )
                stdin_data = handles.get("stdin_data")
                if stdin_data:
                    first_stdin = (
                        stdin_data.encode() if isinstance(stdin_data, str) else None
                    )

            if last_redirects:
                handles = await self.io_handler.setup_redirects(
                    last_redirects, directory
                )
                stdout_value = handles.get("stdout")
                pipeline_stdout = (
                    stdout_value if isinstance(stdout_value, (IO, int)) else None
                )

            # Execute pipeline
            try:
                stdout, stderr, returncode = (
                    await self.process_manager.execute_pipeline(
                        [command[0] for command in parsed_commands],
                        first_stdin=first_stdin,
                        last_stdout=pipeline_stdout,
                        directory=directory,
                        timeout=timeout,
                        envs=envs,
                    )
                )

                final_output = stdout.decode("utf-8") if stdout else ""
                final_stderr = stderr.decode("utf-8") if stderr else ""

                return {
                    "error": None,
                    "stdout": final_output,
                    "stderr": final_stderr,
                    "status": returncode,
                    "execution_time": time.time() - start_time,
                    "directory": directory,
                }

            except Exception as e:
                await self.process_manager.cleanup_processes([])
                return {
                    "error": str(e),
                    "stdout": "",
                    "stderr": str(e),
                    "status": -1 if isinstance(e, TimeoutError) else 1,
                    "execution_time": time.time() - start_time,
                }

            finally:
                await self.io_handler.cleanup_handles({"stdout": pipeline_stdout})

        except Exception as e:
            return {
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "status": 1,
                "execution_time": time.time() - start_time,
            }
