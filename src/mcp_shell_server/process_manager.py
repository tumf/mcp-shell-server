"""Process management for shell command execution."""
import asyncio
import logging
import os
from typing import Dict, IO, Optional, Tuple, Any, List


class ProcessManager:
    """Manages process creation, execution, and cleanup for shell commands."""

    async def create_process(
        self,
        shell_cmd: str,
        directory: Optional[str],
        stdin: Optional[str] = None,
        stdout_handle: Any = asyncio.subprocess.PIPE,
        envs: Optional[Dict[str, str]] = None,
    ) -> asyncio.subprocess.Process:
        """Create a new subprocess with the given parameters.

        Args:
            shell_cmd (str): Shell command to execute
            directory (Optional[str]): Working directory
            stdin (Optional[str]): Input to be passed to the process
            stdout_handle: File handle or PIPE for stdout
            envs (Optional[Dict[str, str]]): Additional environment variables

        Returns:
            asyncio.subprocess.Process: Created process
        """
        return await asyncio.create_subprocess_shell(
            shell_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=stdout_handle,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **(envs or {})},
            cwd=directory,
        )

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

        async def communicate_with_timeout():
            try:
                return await process.communicate(input=stdin_bytes)
            except Exception as e:
                try:
                    await process.wait()
                except Exception:
                    pass
                raise e

        if timeout:
            return await asyncio.wait_for(communicate_with_timeout(), timeout=timeout)
        return await communicate_with_timeout()

    async def execute_pipeline(
        self,
        commands: List[str],
        first_stdin: Optional[bytes] = None,
        last_stdout: Optional[IO[Any]] = None,
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
        """
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
                processes.append(process)

                try:
                    stdout, stderr = await self.execute_with_timeout(
                        process, stdin=prev_stdout.decode() if prev_stdout else None, timeout=timeout
                    )

                    final_stderr += stderr if stderr else b""
                    if process.returncode != 0:
                        error_msg = stderr.decode("utf-8", errors="replace").strip()
                        if not error_msg:
                            error_msg = f"Command failed with exit code {process.returncode}"
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

            return final_stdout, final_stderr, processes[-1].returncode if processes else 1

        finally:
            await self.cleanup_processes(processes)

    async def cleanup_processes(self, processes: List[asyncio.subprocess.Process]) -> None:
        """Clean up processes by killing them if they're still running.

        Args:
            processes: List of processes to clean up
        """
        for process in processes:
            if process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception as e:
                    logging.warning(f"Error cleaning up process: {e}")
