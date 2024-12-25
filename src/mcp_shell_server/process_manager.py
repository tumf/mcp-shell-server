"""Process management for shell command execution."""

import asyncio
import logging
import os
import signal
from typing import IO, Any, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakSet


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
        self, processes: List[asyncio.subprocess.Process]
    ) -> None:
        """Clean up processes by killing them if they're still running.

        Args:
            processes: List of processes to clean up
        """
        cleanup_tasks = []
        for process in processes:
            if process.returncode is None:
                try:
                    # Force kill immediately as required by tests
                    process.kill()
                    cleanup_tasks.append(asyncio.create_task(process.wait()))
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
            envs (Optional[Dict[str, str]]): Additional environment variables
            timeout (Optional[int]): Timeout in seconds

        Returns:
            asyncio.subprocess.Process: Created process

        Raises:
            ValueError: If process creation fails
        """
        try:
            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=stdout_handle,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(envs or {})},
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
