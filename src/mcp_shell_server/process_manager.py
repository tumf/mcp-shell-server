"""Process management for shell command execution."""

import asyncio
import logging
import os
import signal
from typing import IO, Any, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakSet


CHILD_ENV_ALLOWLIST_VAR = "MCP_SHELL_CHILD_ENV_ALLOWLIST"
DEFAULT_CHILD_ENV_KEYS = ("PATH",)
WINDOWS_CHILD_ENV_KEYS = ("COMSPEC", "PATHEXT", "SYSTEMROOT", "WINDIR")
SECRET_LIKE_ENV_NAME_PARTS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "ACCESS_KEY",
    "PRIVATE_KEY",
    "CREDENTIAL",
    "AUTH",
)


def _is_valid_env_key(key: str) -> bool:
    """Return True when key is safe to use as an environment variable name."""
    return bool(key) and all(char.isalnum() or char == "_" for char in key)


def _is_secret_like_env_key(key: str) -> bool:
    """Return True when key metadata appears likely to refer to a secret."""
    normalized = key.upper()
    return any(part in normalized for part in SECRET_LIKE_ENV_NAME_PARTS)


def _redact_env_key_for_log(key: str) -> str:
    """Redact secret-like environment names from logs."""
    if _is_secret_like_env_key(key):
        return "<redacted-secret-like-env-name>"
    return key


def _parse_env_key_list(value: Optional[str]) -> Set[str]:
    """Parse a comma-separated environment key list using strict key validation."""
    if not value:
        return set()

    parsed: Set[str] = set()
    for raw_key in value.split(","):
        key = raw_key.strip()
        if not key:
            continue
        if not _is_valid_env_key(key):
            logging.warning(
                "Ignoring invalid child environment allowlist key: %s",
                _redact_env_key_for_log(key),
            )
            continue
        parsed.add(key)
    return parsed


def build_child_environment(envs: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build the minimal, allowlist-controlled environment for child processes.

    Child processes intentionally do not inherit ``os.environ`` wholesale. The
    default environment contains only documented runtime keys required for basic
    command lookup. Additional keys are inherited from the parent or supplied via
    ``envs`` only when named in ``MCP_SHELL_CHILD_ENV_ALLOWLIST``.
    """
    child_env: Dict[str, str] = {}

    if "PATH" in os.environ:
        child_env["PATH"] = os.environ["PATH"]
    else:
        child_env["PATH"] = os.defpath

    if os.name == "nt":
        for key in WINDOWS_CHILD_ENV_KEYS:
            value = os.environ.get(key)
            if value is not None:
                child_env[key] = value

    allowlisted_keys = _parse_env_key_list(os.environ.get(CHILD_ENV_ALLOWLIST_VAR))
    for key in allowlisted_keys:
        parent_value = os.environ.get(key)
        if parent_value is not None:
            child_env[key] = parent_value

    if not envs:
        return child_env

    invalid_keys = [key for key in envs if not _is_valid_env_key(key)]
    if invalid_keys:
        logging.warning(
            "Ignoring invalid child environment keys: %s",
            ",".join(_redact_env_key_for_log(key) for key in sorted(invalid_keys)),
        )

    disallowed_keys = [
        key for key in envs if _is_valid_env_key(key) and key not in allowlisted_keys
    ]
    if disallowed_keys:
        logging.info(
            "Ignoring child environment keys not present in %s: %s",
            CHILD_ENV_ALLOWLIST_VAR,
            ",".join(_redact_env_key_for_log(key) for key in sorted(disallowed_keys)),
        )

    for key in allowlisted_keys:
        if key in envs and _is_valid_env_key(key):
            child_env[key] = envs[key]

    return child_env


class ProcessManager:
    """Manages process creation, execution, and cleanup for shell commands."""

    def __init__(self):
        """Initialize ProcessManager with signal handling setup."""
        self._processes: Set[asyncio.subprocess.Process] = WeakSet()
        self._original_sigint_handler = None
        self._original_sigterm_handler = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful process management."""
        if os.name != "posix":
            return

        def handle_termination(signum: int, _: Any) -> None:
            """Handle termination signals by cleaning up processes."""
            if self._processes:
                for process in self._processes:
                    try:
                        if process.returncode is None:
                            process.terminate()
                    except Exception as e:
                        logging.warning(
                            f"Error terminating process on signal {signum}: {e}"
                        )

            # Restore original handler and re-raise signal
            if signum == signal.SIGINT and self._original_sigint_handler:
                signal.signal(signal.SIGINT, self._original_sigint_handler)
            elif signum == signal.SIGTERM and self._original_sigterm_handler:
                signal.signal(signal.SIGTERM, self._original_sigterm_handler)

            # Re-raise signal
            os.kill(os.getpid(), signum)

        # Store original handlers
        self._original_sigint_handler = signal.signal(signal.SIGINT, handle_termination)
        self._original_sigterm_handler = signal.signal(
            signal.SIGTERM, handle_termination
        )

    async def start_process_async(
        self, cmd: List[str], timeout: Optional[int] = None
    ) -> asyncio.subprocess.Process:
        """Start a new process asynchronously.

        Args:
            cmd: Command to execute as list of strings
            timeout: Optional timeout in seconds

        Returns:
            Process object
        """
        process = await self.create_process(
            " ".join(cmd), directory=None, timeout=timeout
        )
        process.is_running = lambda self=process: self.returncode is None  # type: ignore
        return process

    async def start_process(
        self, cmd: List[str], timeout: Optional[int] = None
    ) -> asyncio.subprocess.Process:
        """Start a new process asynchronously.

        Args:
            cmd: Command to execute as list of strings
            timeout: Optional timeout in seconds

        Returns:
            Process object
        """
        process = await self.create_process(
            " ".join(cmd), directory=None, timeout=timeout
        )
        process.is_running = lambda self=process: self.returncode is None  # type: ignore
        return process

    async def cleanup_processes(
        self, processes: Optional[List[asyncio.subprocess.Process]] = None
    ) -> None:
        """Clean up processes by killing them if they're still running.

        Args:
            processes: Optional list of processes to clean up. If None, clean up all tracked processes
        """
        if processes is None:
            processes = list(self._processes)

        cleanup_tasks = []
        for process in processes:
            if process.returncode is None:
                try:
                    # First attempt graceful termination
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=0.5)
                    except asyncio.TimeoutError:
                        # Force kill if termination didn't work
                        process.kill()
                        cleanup_tasks.append(asyncio.create_task(process.wait()))
                except ProcessLookupError:
                    # Process already terminated
                    pass
                except Exception as e:
                    logging.warning(f"Error killing process: {e}")

        if cleanup_tasks:
            try:
                # Wait for all processes to be killed
                await asyncio.wait(cleanup_tasks, timeout=5)
            except asyncio.TimeoutError:
                logging.error("Process cleanup timed out")
            except Exception as e:
                logging.error(f"Error during process cleanup: {e}")

    async def cleanup_all(self) -> None:
        """Clean up all tracked processes."""
        if self._processes:
            processes = list(self._processes)
            await self.cleanup_processes(processes)
            self._processes.clear()

    async def create_process(
        self,
        shell_cmd: str,
        directory: Optional[str],
        stdin: Optional[str] = None,
        stdout_handle: Any = asyncio.subprocess.PIPE,
        envs: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> asyncio.subprocess.Process:
        """Create a new subprocess with the given parameters.

        Args:
            shell_cmd (str): Shell command to execute
            directory (Optional[str]): Working directory
            stdin (Optional[str]): Input to be passed to the process
            stdout_handle: File handle or PIPE for stdout
            envs (Optional[Dict[str, str]]): Additional environment variables. Keys are applied only when present in MCP_SHELL_CHILD_ENV_ALLOWLIST.
            timeout (Optional[int]): Timeout in seconds

        Returns:
            asyncio.subprocess.Process: Created process

        Raises:
            ValueError: If process creation fails
        """
        child_env = build_child_environment(envs)
        logging.debug(
            "Creating child process with isolated environment: command_length=%s directory=%r env_keys=%s",
            len(shell_cmd),
            directory,
            ",".join(_redact_env_key_for_log(key) for key in sorted(child_env)),
        )

        try:
            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=stdout_handle,
                stderr=asyncio.subprocess.PIPE,
                env=child_env,
                cwd=directory,
            )

            # Add process to tracked set
            self._processes.add(process)
            return process

        except OSError as e:
            raise ValueError(f"Failed to create process: {str(e)}") from e
        except Exception as e:
            raise ValueError(
                f"Unexpected error during process creation: {str(e)}"
            ) from e

    async def execute_with_timeout(
        self,
        process: asyncio.subprocess.Process,
        stdin: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Tuple[bytes, bytes]:
        """Execute the process with timeout handling.

        Args:
            process: Process to execute
            stdin (Optional[str]): Input to pass to the process
            timeout (Optional[int]): Timeout in seconds

        Returns:
            Tuple[bytes, bytes]: Tuple of (stdout, stderr)

        Raises:
            asyncio.TimeoutError: If execution times out
        """
        stdin_bytes = stdin.encode() if stdin else None

        async def _kill_process():
            if process.returncode is not None:
                return

            try:
                # Try graceful termination first
                process.terminate()
                for _ in range(5):  # Wait up to 0.5 seconds
                    if process.returncode is not None:
                        return
                    await asyncio.sleep(0.1)

                # Force kill if still running
                if process.returncode is None:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=1.0)
            except Exception as e:
                logging.warning(f"Error killing process: {e}")

        try:
            if timeout:
                try:
                    return await asyncio.wait_for(
                        process.communicate(input=stdin_bytes), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    await _kill_process()
                    raise
            return await process.communicate(input=stdin_bytes)
        except Exception as e:
            await _kill_process()
            raise e

    async def execute_pipeline(
        self,
        commands: List[str],
        first_stdin: Optional[bytes] = None,
        last_stdout: Union[IO[Any], int, None] = None,
        directory: Optional[str] = None,
        timeout: Optional[int] = None,
        envs: Optional[Dict[str, str]] = None,
    ) -> Tuple[bytes, bytes, int]:
        """Execute a pipeline of commands.

        Args:
            commands: List of shell commands to execute in pipeline
            first_stdin: Input to pass to the first command
            last_stdout: Output handle for the last command
            directory: Working directory
            timeout: Timeout in seconds
            envs: Additional environment variables

        Returns:
            Tuple[bytes, bytes, int]: Tuple of (stdout, stderr, return_code)

        Raises:
            ValueError: If no commands provided or command execution fails
        """
        if not commands:
            raise ValueError("No commands provided")

        processes: List[asyncio.subprocess.Process] = []
        try:
            prev_stdout: Optional[bytes] = first_stdin
            final_stderr: bytes = b""
            final_stdout: bytes = b""

            for i, cmd in enumerate(commands):
                process = await self.create_process(
                    cmd,
                    directory,
                    stdout_handle=(
                        asyncio.subprocess.PIPE
                        if i < len(commands) - 1 or not last_stdout
                        else last_stdout
                    ),
                    envs=envs,
                )
                if not hasattr(process, "is_running"):
                    process.is_running = lambda self=process: self.returncode is None  # type: ignore
                processes.append(process)

                try:
                    stdout, stderr = await self.execute_with_timeout(
                        process,
                        stdin=prev_stdout.decode() if prev_stdout else None,
                        timeout=timeout,
                    )

                    final_stderr += stderr if stderr else b""
                    if process.returncode != 0:
                        error_msg = stderr.decode("utf-8", errors="replace").strip()
                        if not error_msg:
                            error_msg = (
                                f"Command failed with exit code {process.returncode}"
                            )
                        raise ValueError(error_msg)

                    if i == len(commands) - 1:
                        if last_stdout and isinstance(last_stdout, IO):
                            last_stdout.write(stdout.decode("utf-8", errors="replace"))
                        else:
                            final_stdout = stdout if stdout else b""
                    else:
                        prev_stdout = stdout if stdout else b""

                except asyncio.TimeoutError:
                    process.kill()
                    raise
                except Exception:
                    process.kill()
                    raise

            return (
                final_stdout,
                final_stderr,
                (
                    processes[-1].returncode
                    if processes and processes[-1].returncode is not None
                    else 1
                ),
            )

        finally:
            await self.cleanup_processes(processes)
