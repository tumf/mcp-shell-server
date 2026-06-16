import asyncio
import hashlib
import inspect
import io
import logging
import os
import pwd
import time
from typing import Any, Dict, List, Optional

from mcp_shell_server.command_preprocessor import CommandPreProcessor
from mcp_shell_server.command_validator import CommandValidator
from mcp_shell_server.directory_manager import DirectoryManager
from mcp_shell_server.io_redirection_handler import IORedirectionHandler
from mcp_shell_server.process_manager import OutputLimitExceeded, ProcessManager

logger = logging.getLogger("mcp-shell-server.audit")
SECRET_MARKERS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASS",
    "PASSWD",
    "API_KEY",
    "ACCESS_KEY",
    "PRIVATE_KEY",
    "KEY",
    "CREDENTIAL",
    "AUTH",
)
SECRET_REDACTION = "[REDACTED]"
HASH_REDACTION_PREFIX = "[sha256:"


class ShellExecutor:
    """Executes argv commands after validation against the configured policy."""

    def __init__(self, process_manager: Optional[ProcessManager] = None):
        """Initialize the executor with validators, IO handling, and process manager."""
        self.validator = CommandValidator()
        self.directory_manager = DirectoryManager()
        self.io_handler = IORedirectionHandler()
        self.preprocessor = CommandPreProcessor()
        self.process_manager = (
            process_manager if process_manager is not None else ProcessManager()
        )

    def _validate_command(self, command: List[str]) -> None:
        if not command:
            raise ValueError("Empty command")
        self.validator.validate_command(command)

    def _validate_directory(self, directory: Optional[str]) -> None:
        self.directory_manager.validate_directory(directory)

    def _validate_no_shell_operators(self, cmd: str) -> None:
        self.validator.validate_no_shell_operators(cmd)

    def _validate_pipeline(self, commands: List[str]) -> Dict[str, str]:
        return self.validator.validate_pipeline(commands)

    def _get_default_shell(self) -> str:
        try:
            return pwd.getpwuid(os.getuid()).pw_shell
        except (ImportError, KeyError):
            return os.environ.get("SHELL", "/bin/sh")

    async def _kill_process(self, process: Any) -> None:
        try:
            result = process.kill()
            if inspect.isawaitable(result):
                await result
        except ProcessLookupError:
            pass

    def _contains_secret_marker(self, value: str) -> bool:
        upper = value.upper()
        return any(marker in upper for marker in SECRET_MARKERS)

    def _digest_value(self, value: str) -> str:
        digest = hashlib.sha256(value.encode()).hexdigest()[:8]
        return f"{HASH_REDACTION_PREFIX}{digest}]"

    def _redact_scalar(self, value: str) -> str:
        if self._contains_secret_marker(value):
            return SECRET_REDACTION
        if len(value) > 32 and not value.isdigit():
            return self._digest_value(value)
        return value

    def _redact_value(self, value: str) -> str:
        if "=" not in value:
            return self._redact_scalar(value)

        name, raw = value.split("=", 1)
        if self._contains_secret_marker(name):
            return f"{SECRET_REDACTION}={SECRET_REDACTION}"
        return f"{name}={self._redact_scalar(raw)}"

    def _redact_argv(self, argv: List[str]) -> List[str]:
        return [self._redact_value(arg) for arg in argv]

    def _redact_envs(self, envs: Optional[Dict[str, str]]) -> Dict[str, str]:
        if not envs:
            return {}

        redacted: Dict[str, str] = {}
        for key, value in envs.items():
            safe_key = SECRET_REDACTION if self._contains_secret_marker(key) else key
            safe_value = (
                SECRET_REDACTION
                if self._contains_secret_marker(key)
                else self._redact_scalar(str(value))
            )
            redacted[safe_key] = safe_value
        return redacted

    def _audit(
        self,
        result_type: str,
        command: List[str],
        directory: Optional[str],
        start_time: float,
        *,
        stderr: str = "",
        stdout: str = "",
        stdout_bytes: Optional[int] = None,
        stderr_bytes: Optional[int] = None,
        timeout: Optional[int] = None,
        output_limit: Optional[int] = None,
        return_code: Optional[int] = None,
        redirections: Optional[Dict[str, Any]] = None,
        envs: Optional[Dict[str, str]] = None,
        rejection_reason: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> None:
        event = {
            "timestamp": time.time(),
            "command": command[0] if command else None,
            "argv": self._redact_argv(command),
            "directory": os.path.realpath(directory) if directory else None,
            "redirections": redirections or {},
            "env": self._redact_envs(envs),
            "timeout": timeout,
            "output_limit": output_limit,
            "stdout_bytes": stdout_bytes if stdout_bytes is not None else len(stdout.encode()),
            "stderr_bytes": stderr_bytes if stderr_bytes is not None else len(stderr.encode()),
            "return_code": return_code,
            "duration": time.time() - start_time,
            "result_type": result_type,
        }
        if rejection_reason is not None:
            event["rejection_reason"] = self._redact_scalar(rejection_reason)
        if error_type is not None:
            event["error_type"] = error_type
        logger.info("shell_execution_audit", extra={"audit": event})

    def _error_result(
        self,
        message: str,
        start_time: float,
        status: int = 1,
    ) -> Dict[str, Any]:
        return {
            "error": message,
            "status": status,
            "stdout": "",
            "stderr": message,
            "execution_time": time.time() - start_time,
        }

    async def execute(
        self,
        command: List[str],
        directory: str,
        stdin: Optional[str] = None,
        timeout: Optional[int] = None,
        envs: Optional[Dict[str, str]] = None,
        output_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        process = None
        audit_command = command[:]
        redirection_metadata: Dict[str, Any] = {}

        try:
            try:
                self._validate_directory(directory)
            except ValueError as e:
                self._audit(
                    "rejected",
                    audit_command,
                    directory,
                    start_time,
                    stderr=str(e),
                    timeout=timeout,
                    output_limit=output_limit,
                    envs=envs,
                    rejection_reason=str(e),
                )
                return self._error_result(str(e), start_time)

            preprocessed_command = self.preprocessor.preprocess_command(command)
            cleaned_command = self.preprocessor.clean_command(preprocessed_command)
            if not cleaned_command:
                self._audit(
                    "rejected",
                    audit_command,
                    directory,
                    start_time,
                    stderr="Empty command",
                    timeout=timeout,
                    output_limit=output_limit,
                    envs=envs,
                    rejection_reason="Empty command",
                )
                return self._error_result("Empty command", start_time)

            if "|" in cleaned_command:
                try:
                    self.validator.validate_pipeline(cleaned_command)
                    commands = self.preprocessor.split_pipe_commands(cleaned_command)
                    if not commands:
                        raise ValueError("Empty command before pipe operator")
                    return await self._execute_pipeline(
                        commands, directory, timeout, envs, output_limit=output_limit
                    )
                except ValueError as e:
                    self._audit(
                        "rejected",
                        cleaned_command,
                        directory,
                        start_time,
                        stderr=str(e),
                        timeout=timeout,
                        output_limit=output_limit,
                        envs=envs,
                        rejection_reason=str(e),
                    )
                    return self._error_result(str(e), start_time)

            for token in cleaned_command:
                try:
                    self.validator.validate_no_shell_operators(token)
                except ValueError as e:
                    self._audit(
                        "rejected",
                        cleaned_command,
                        directory,
                        start_time,
                        stderr=str(e),
                        timeout=timeout,
                        output_limit=output_limit,
                        envs=envs,
                        rejection_reason=str(e),
                    )
                    return self._error_result(str(e), start_time)

            try:
                cmd, redirects = self.preprocessor.parse_command(cleaned_command)
                # Re-run the redirection handler syntax/parser so the contained IO
                # path owns runtime redirection semantics while preserving the
                # historical parser error surface used by callers and tests.
                cmd, redirects = self.io_handler.process_redirections(cleaned_command)
                redirection_metadata = {
                    "stdin": bool(redirects.get("stdin")),
                    "stdout": bool(redirects.get("stdout")),
                    "stdout_append": bool(redirects.get("stdout_append")),
                }
                self.validator.validate_command(cmd)
            except ValueError as e:
                self._audit(
                    "rejected",
                    cleaned_command,
                    directory,
                    start_time,
                    stderr=str(e),
                    timeout=timeout,
                    output_limit=output_limit,
                    redirections=redirection_metadata,
                    envs=envs,
                    rejection_reason=str(e),
                )
                return self._error_result(str(e), start_time)

            stdout_handle: Any = asyncio.subprocess.PIPE
            try:
                handles = await self.io_handler.setup_redirects(redirects, directory)
                stdin_data = handles.get("stdin_data")
                if isinstance(stdin_data, str):
                    stdin = stdin_data

                stdout_value = handles.get("stdout")
                if isinstance(stdout_value, int) or isinstance(stdout_value, io.IOBase) or hasattr(stdout_value, "write"):
                    stdout_handle = stdout_value
            except ValueError as e:
                self._audit(
                    "rejected",
                    cmd,
                    directory,
                    start_time,
                    stderr=str(e),
                    timeout=timeout,
                    output_limit=output_limit,
                    redirections=redirection_metadata,
                    envs=envs,
                    rejection_reason=str(e),
                )
                return self._error_result(str(e), start_time)

            try:
                process = await self.process_manager.create_process(
                    cmd, directory, stdout_handle=stdout_handle, envs=envs, timeout=timeout
                )
            except Exception as e:
                if hasattr(stdout_handle, "close") and not isinstance(stdout_handle, int):
                    stdout_handle.close()
                self._audit(
                    "process_error",
                    cmd,
                    directory,
                    start_time,
                    stderr=str(e),
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=None,
                    redirections=redirection_metadata,
                    envs=envs,
                    error_type=type(e).__name__,
                )
                return self._error_result(str(e), start_time)

            try:
                stdout, stderr = await asyncio.shield(
                    self.process_manager.execute_with_timeout(
                        process,
                        stdin=stdin,
                        timeout=timeout,
                        output_limit=output_limit,
                    )
                )

                if hasattr(stdout_handle, "close") and not isinstance(stdout_handle, int):
                    try:
                        stdout_handle.close()
                    except (IOError, OSError) as e:
                        logging.warning(f"Error closing stdout: {e}")

                final_returncode = 0 if process.returncode is None else process.returncode
                stdout_text = stdout.decode(errors="replace").strip() if stdout else ""
                stderr_text = stderr.decode(errors="replace").strip() if stderr else ""
                self._audit(
                    "success",
                    cmd,
                    directory,
                    start_time,
                    stdout_bytes=len(stdout or b""),
                    stderr_bytes=len(stderr or b""),
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=final_returncode,
                    redirections=redirection_metadata,
                    envs=envs,
                )

                return {
                    "error": None,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": final_returncode,
                    "status": final_returncode,
                    "execution_time": time.time() - start_time,
                    "directory": directory,
                }

            except asyncio.TimeoutError:
                if process and process.returncode is None:
                    try:
                        await self._kill_process(process)
                        await asyncio.shield(process.wait())
                    except ProcessLookupError:
                        pass

                if hasattr(stdout_handle, "close") and not isinstance(stdout_handle, int):
                    stdout_handle.close()

                message = f"Command timed out after {timeout} seconds"
                self._audit(
                    "timeout",
                    cmd,
                    directory,
                    start_time,
                    stderr=message,
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=-1,
                    redirections=redirection_metadata,
                    envs=envs,
                    error_type="TimeoutError",
                )
                return self._error_result(message, start_time, status=-1)
            except OutputLimitExceeded as e:
                if hasattr(stdout_handle, "close") and not isinstance(stdout_handle, int):
                    stdout_handle.close()
                message = str(e)
                self._audit(
                    "output_cap",
                    cmd,
                    directory,
                    start_time,
                    stderr=message,
                    stdout_bytes=len(e.stdout),
                    stderr_bytes=len(e.stderr),
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=-1,
                    redirections=redirection_metadata,
                    envs=envs,
                    error_type=type(e).__name__,
                )
                return self._error_result(message, start_time, status=-1)
            except Exception as e:
                if hasattr(stdout_handle, "close") and not isinstance(stdout_handle, int):
                    stdout_handle.close()
                self._audit(
                    "process_error",
                    cmd,
                    directory,
                    start_time,
                    stderr=str(e),
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=getattr(process, "returncode", None),
                    redirections=redirection_metadata,
                    envs=envs,
                    error_type=type(e).__name__,
                )
                return self._error_result(str(e), start_time)

        finally:
            if process and process.returncode is None:
                await self._kill_process(process)
                await process.wait()

    async def _execute_pipeline(
        self,
        commands: List[List[str]],
        directory: Optional[str] = None,
        timeout: Optional[int] = None,
        envs: Optional[Dict[str, str]] = None,
        output_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        redirection_metadata: Dict[str, Any] = {}
        try:
            for cmd in commands:
                self.validator.validate_command(cmd)

            parsed_commands = []
            first_stdin: Optional[bytes] = None
            pipeline_stdout: Any = None
            first_redirects = None
            last_redirects = None

            for i, command in enumerate(commands):
                cmd, redirects = self.io_handler.process_redirections(command)
                parsed_commands.append(cmd)

                if i == 0:
                    first_redirects = redirects
                elif i == len(commands) - 1:
                    last_redirects = redirects

            if first_redirects:
                handles = await self.io_handler.setup_redirects(first_redirects, directory)
                stdin_data = handles.get("stdin_data")
                if stdin_data:
                    first_stdin = stdin_data.encode() if isinstance(stdin_data, str) else None
                redirection_metadata["stdin"] = bool(first_redirects.get("stdin"))

            if last_redirects:
                handles = await self.io_handler.setup_redirects(last_redirects, directory)
                stdout_value = handles.get("stdout")
                if isinstance(stdout_value, int) or isinstance(stdout_value, io.IOBase) or hasattr(stdout_value, "write"):
                    pipeline_stdout = stdout_value
                redirection_metadata["stdout"] = bool(last_redirects.get("stdout"))
                redirection_metadata["stdout_append"] = bool(last_redirects.get("stdout_append"))

            try:
                stdout, stderr, returncode = await self.process_manager.execute_pipeline(
                    parsed_commands,
                    first_stdin=first_stdin,
                    last_stdout=pipeline_stdout,
                    directory=directory,
                    timeout=timeout,
                    envs=envs,
                    output_limit=output_limit,
                )

                final_output = stdout.decode("utf-8", errors="replace") if stdout else ""
                final_stderr = stderr.decode("utf-8", errors="replace") if stderr else ""
                self._audit(
                    "success",
                    [part for cmd in parsed_commands for part in [*cmd, "|"]][:-1],
                    directory,
                    start_time,
                    stdout_bytes=len(stdout or b""),
                    stderr_bytes=len(stderr or b""),
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=returncode,
                    redirections=redirection_metadata,
                    envs=envs,
                )

                return {
                    "error": None,
                    "stdout": final_output,
                    "stderr": final_stderr,
                    "status": returncode,
                    "execution_time": time.time() - start_time,
                    "directory": directory,
                }
            except OutputLimitExceeded as e:
                await self.process_manager.cleanup_processes([])
                message = str(e)
                self._audit(
                    "output_cap",
                    commands[0] if commands else [],
                    directory,
                    start_time,
                    stderr=message,
                    stdout_bytes=len(e.stdout),
                    stderr_bytes=len(e.stderr),
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=-1,
                    redirections=redirection_metadata,
                    envs=envs,
                    error_type=type(e).__name__,
                )
                return self._error_result(message, start_time, status=-1)
            except Exception as e:
                await self.process_manager.cleanup_processes([])
                result_type = "timeout" if isinstance(e, TimeoutError) else "process_error"
                self._audit(
                    result_type,
                    commands[0] if commands else [],
                    directory,
                    start_time,
                    stderr=str(e),
                    timeout=timeout,
                    output_limit=output_limit,
                    return_code=-1,
                    redirections=redirection_metadata,
                    envs=envs,
                    error_type=type(e).__name__,
                )
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
            self._audit(
                "rejected",
                commands[0] if commands else [],
                directory,
                start_time,
                stderr=str(e),
                timeout=timeout,
                output_limit=output_limit,
                redirections=redirection_metadata,
                envs=envs,
                rejection_reason=str(e),
            )
            return self._error_result(str(e), start_time)
