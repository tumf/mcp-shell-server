"""Process management for argv-based command execution."""

import asyncio
import asyncio.streams
import io
import logging
import os
import shlex
import signal
from collections.abc import Sequence
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakSet

DEFAULT_SAFE_PATH = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_OUTPUT_LIMIT_BYTES = 1024 * 1024
ENV_ALLOWLIST_VAR = "MCP_SHELL_ENV_ALLOWLIST"
SAFE_PATH_VAR = "MCP_SHELL_SAFE_PATH"
OUTPUT_LIMIT_VAR = "MCP_SHELL_OUTPUT_LIMIT_BYTES"
TIMEOUT_VAR = "MCP_SHELL_DEFAULT_TIMEOUT_SECONDS"

logger = logging.getLogger("mcp-shell-server.process")


class OutputLimitExceeded(RuntimeError):
    """Raised when stdout or stderr exceeds the configured output cap."""

    def __init__(
        self,
        stream_name: str,
        limit: int,
        stdout: bytes = b"",
        stderr: bytes = b"",
    ):
        self.stream_name = stream_name
        self.limit = limit
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"{stream_name} exceeded output limit of {limit} bytes")


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
    """Manages process creation, execution, and cleanup for argv commands."""

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

            if signum == signal.SIGINT and self._original_sigint_handler:
                signal.signal(signal.SIGINT, self._original_sigint_handler)
            elif signum == signal.SIGTERM and self._original_sigterm_handler:
                signal.signal(signal.SIGTERM, self._original_sigterm_handler)

            os.kill(os.getpid(), signum)

        self._original_sigint_handler = signal.signal(signal.SIGINT, handle_termination)
        self._original_sigterm_handler = signal.signal(
            signal.SIGTERM, handle_termination
        )

    @staticmethod
    def _configured_int(name: str, default: int) -> int:
        raw = os.environ.get(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            value = int(raw)
        except ValueError:
            logger.warning("Invalid integer configuration; using default", extra={"name": name})
            return default
        return value if value > 0 else default

    @staticmethod
    def _normalize_argv(argv: Union[str, Sequence[str]]) -> List[str]:
        if isinstance(argv, str):
            # Backward-compatible internal adapter only. Runtime callers pass argv lists.
            argv = shlex.split(argv)
        normalized = [str(part) for part in argv if str(part) != ""]
        if not normalized:
            raise ValueError("Empty command")
        return normalized

    def build_child_environment(
        self, envs: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Build a minimal child environment without inheriting parent secrets."""
        child_env: Dict[str, str] = {
            "PATH": os.environ.get(SAFE_PATH_VAR, DEFAULT_SAFE_PATH),
            "LANG": "C",
            "LC_ALL": "C",
        }

        allowlist = {
            name.strip()
            for name in os.environ.get(ENV_ALLOWLIST_VAR, "").split(",")
            if name.strip()
        }
        for name in allowlist:
            if name in os.environ:
                child_env[name] = os.environ[name]

        if envs:
            child_env.update({str(key): str(value) for key, value in envs.items()})

        return child_env

    async def start_process_async(
        self, cmd: List[str], timeout: Optional[int] = None
    ) -> asyncio.subprocess.Process:
        """Start a new process asynchronously."""
        process = await self.create_process(cmd, directory=None, timeout=timeout)
        process.is_running = lambda self=process: self.returncode is None  # type: ignore
        return process

    async def start_process(
        self, cmd: List[str], timeout: Optional[int] = None
    ) -> asyncio.subprocess.Process:
        """Start a new process asynchronously."""
        process = await self.create_process(cmd, directory=None, timeout=timeout)
        process.is_running = lambda self=process: self.returncode is None  # type: ignore
        return process

    async def cleanup_processes(
        self, processes: Optional[List[asyncio.subprocess.Process]] = None
    ) -> None:
        """Clean up processes by killing them if they're still running."""
        if processes is None:
            processes = list(self._processes)

        cleanup_tasks = []
        for process in processes:
            if process.returncode is None:
                try:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=0.5)
                    except asyncio.TimeoutError:
                        process.kill()
                        cleanup_tasks.append(asyncio.create_task(process.wait()))
                except ProcessLookupError:
                    pass
                except Exception as e:
                    logging.warning(f"Error killing process: {e}")

        if cleanup_tasks:
            try:
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
        argv: Union[str, Sequence[str]],
        directory: Optional[str],
        stdin: Optional[str] = None,
        stdout_handle: Any = asyncio.subprocess.PIPE,
        envs: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> asyncio.subprocess.Process:
        """Create a subprocess using argv-based execution.

        The public execution path passes argv lists; string input is split only for
        backward-compatible internal tests and is never handed to a shell.
        Additional envs are forwarded only when they are listed in
        MCP_SHELL_CHILD_ENV_ALLOWLIST.
        """
        del stdin, timeout
        normalized_argv = self._normalize_argv(argv)
        child_env = build_child_environment(envs)
        logger.debug(
            "creating subprocess",
            extra={
                "argv0": normalized_argv[0],
                "argc": len(normalized_argv),
                "cwd": directory,
                "env_keys": sorted(child_env),
            },
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *normalized_argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=stdout_handle,
                stderr=asyncio.subprocess.PIPE,
                env=child_env,
                cwd=directory,
            )
            self._processes.add(process)
            return process
        except OSError as e:
            raise ValueError(f"Failed to create process: {str(e)}") from e
        except Exception as e:
            raise ValueError(
                f"Unexpected error during process creation: {str(e)}"
            ) from e

    async def _kill_process(self, process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        try:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                if process.returncode is None:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=1.0)
        except ProcessLookupError:
            pass
        except Exception as e:
            logging.warning(f"Error killing process: {e}")

    async def _read_stream_limited(
        self,
        stream: Any,
        stream_name: str,
        limit: int,
    ) -> bytes:
        if stream is None:
            return b""
        data = bytearray()
        while True:
            remaining = max(1, limit + 1 - len(data))
            chunk = await stream.read(min(8192, remaining))
            if not chunk:
                return bytes(data)
            data.extend(chunk)
            if len(data) > limit:
                partial = bytes(data[:limit])
                if stream_name == "stdout":
                    raise OutputLimitExceeded(stream_name, limit, stdout=partial)
                raise OutputLimitExceeded(stream_name, limit, stderr=partial)

    async def _communicate_with_output_limit(
        self,
        process: asyncio.subprocess.Process,
        stdin_bytes: Optional[bytes],
        output_limit: int,
    ) -> Tuple[bytes, bytes]:
        stdout_stream = getattr(process, "stdout", None)
        stderr_stream = getattr(process, "stderr", None)
        stdin_stream = getattr(process, "stdin", None)

        streams_are_real = isinstance(stdout_stream, asyncio.streams.StreamReader) or isinstance(
            stderr_stream, asyncio.streams.StreamReader
        )
        if not streams_are_real:
            stdout, stderr = await process.communicate(input=stdin_bytes)
            stdout = stdout or b""
            stderr = stderr or b""
            if len(stdout) > output_limit:
                raise OutputLimitExceeded(
                    "stdout", output_limit, stdout=stdout[:output_limit]
                )
            if len(stderr) > output_limit:
                raise OutputLimitExceeded(
                    "stderr", output_limit, stdout=stdout, stderr=stderr[:output_limit]
                )
            return stdout, stderr

        if stdin_stream is not None:
            if stdin_bytes:
                stdin_stream.write(stdin_bytes)
                await stdin_stream.drain()
            stdin_stream.close()
            if hasattr(stdin_stream, "wait_closed"):
                await stdin_stream.wait_closed()

        stdout_task = asyncio.create_task(
            self._read_stream_limited(stdout_stream, "stdout", output_limit)
        )
        stderr_task = asyncio.create_task(
            self._read_stream_limited(stderr_stream, "stderr", output_limit)
        )

        try:
            stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
            await process.wait()
            return stdout, stderr
        except OutputLimitExceeded:
            for task in (stdout_task, stderr_task):
                if not task.done():
                    task.cancel()
            await self._kill_process(process)
            raise

    async def execute_with_timeout(
        self,
        process: asyncio.subprocess.Process,
        stdin: Optional[str] = None,
        timeout: Optional[int] = None,
        output_limit: Optional[int] = None,
    ) -> Tuple[bytes, bytes]:
        """Execute the process with timeout and output-cap handling."""
        stdin_bytes = stdin.encode() if stdin else None
        effective_timeout = timeout or self._configured_int(
            TIMEOUT_VAR, DEFAULT_TIMEOUT_SECONDS
        )
        effective_limit = output_limit or self._configured_int(
            OUTPUT_LIMIT_VAR, DEFAULT_OUTPUT_LIMIT_BYTES
        )

        try:
            return await asyncio.wait_for(
                self._communicate_with_output_limit(
                    process, stdin_bytes=stdin_bytes, output_limit=effective_limit
                ),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            await self._kill_process(process)
            raise
        except OutputLimitExceeded:
            raise
        except Exception:
            await self._kill_process(process)
            raise

    async def execute_pipeline(
        self,
        commands: List[List[str]],
        first_stdin: Optional[bytes] = None,
        last_stdout: Any = None,
        directory: Optional[str] = None,
        timeout: Optional[int] = None,
        envs: Optional[Dict[str, str]] = None,
        output_limit: Optional[int] = None,
    ) -> Tuple[bytes, bytes, int]:
        """Execute a pipeline of argv command segments sequentially."""
        if not commands:
            raise ValueError("No commands provided")

        processes: List[asyncio.subprocess.Process] = []
        try:
            prev_stdout: Optional[bytes] = first_stdin
            final_stderr: bytes = b""
            final_stdout: bytes = b""

            for i, cmd in enumerate(commands):
                stdout_target = (
                    asyncio.subprocess.PIPE
                    if i < len(commands) - 1 or not last_stdout
                    else last_stdout
                )
                process = await self.create_process(
                    cmd,
                    directory,
                    stdout_handle=stdout_target,
                    envs=envs,
                    timeout=timeout,
                )
                if not hasattr(process, "is_running"):
                    process.is_running = lambda self=process: self.returncode is None  # type: ignore
                processes.append(process)

                stdout, stderr = await self.execute_with_timeout(
                    process,
                    stdin=prev_stdout.decode() if prev_stdout else None,
                    timeout=timeout,
                    output_limit=output_limit,
                )

                final_stderr += stderr if stderr else b""
                if process.returncode != 0:
                    error_msg = stderr.decode("utf-8", errors="replace").strip()
                    if not error_msg:
                        error_msg = f"Command failed with exit code {process.returncode}"
                    raise ValueError(error_msg)

                if i == len(commands) - 1:
                    final_stdout = stdout if stdout else b""
                    if last_stdout and hasattr(last_stdout, "write") and stdout:
                        last_stdout.write(stdout.decode("utf-8", errors="replace"))
                else:
                    prev_stdout = stdout if stdout else b""

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
