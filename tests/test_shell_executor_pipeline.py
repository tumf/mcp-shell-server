"""Test pipeline execution and cleanup scenarios."""

import os
import tempfile

import pytest

from mcp_shell_server.command_preprocessor import CommandPreProcessor
from mcp_shell_server.shell_executor import ShellExecutor


def clear_env(monkeypatch):
    monkeypatch.delenv("ALLOW_COMMANDS", raising=False)
    monkeypatch.delenv("ALLOWED_COMMANDS", raising=False)


@pytest.fixture
def executor():
    return ShellExecutor()


@pytest.fixture
def temp_test_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Return the real path to handle macOS /private/tmp symlink
        yield os.path.realpath(tmpdirname)


@pytest.mark.asyncio
async def test_pipeline_split(executor):
    """Test pipeline command splitting functionality"""
    # Test basic pipe command
    commands = executor.preprocessor.split_pipe_commands(
        ["echo", "hello", "|", "grep", "h"]
    )
    assert len(commands) == 2
    assert commands[0] == ["echo", "hello"]
    assert commands[1] == ["grep", "h"]

    # Test empty pipe sections
    commands = executor.preprocessor.split_pipe_commands(["|", "grep", "pattern"])
    assert len(commands) == 1
    assert commands[0] == ["grep", "pattern"]

    # Test multiple pipes
    commands = executor.preprocessor.split_pipe_commands(
        ["cat", "file.txt", "|", "grep", "pattern", "|", "wc", "-l"]
    )
    assert len(commands) == 3
    assert commands[0] == ["cat", "file.txt"]
    assert commands[1] == ["grep", "pattern"]
    assert commands[2] == ["wc", "-l"]

    # Test trailing pipe
    commands = executor.preprocessor.split_pipe_commands(["echo", "hello", "|"])
    assert len(commands) == 1
    assert commands[0] == ["echo", "hello"]


@pytest.mark.parametrize(
    "argv",
    [
        # Embedded pipe: a regular expression alternation.
        ["grep", "-E", "error|warning", "file.txt"],
        # Trailing pipe attached to argument data.
        ["echo", "text|", "id"],
        # Leading pipe attached to argument data.
        ["echo", "|text"],
        # Multiple embedded pipes plus surrounding whitespace.
        ["echo", " a|b|c "],
        # Pipe inside a URL-ish / JSON-ish payload.
        ["echo", '{"filter":"a|b"}'],
    ],
)
def test_preprocess_command_preserves_literal_pipe_arguments(argv):
    """Pipe characters inside argv elements stay literal argument data."""
    assert CommandPreProcessor().preprocess_command(argv) == argv


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["ls"],
        ["ls", "|", "grep", "test"],
        ["cat", "file", "|", "grep", "pattern", "|", "wc", "-l"],
        ["echo", "hello", "&&", "ls"],
        ["echo", "hello", "||", "ls"],
        ["echo", "hello", ";", "ls"],
    ],
)
def test_preprocess_command_only_discrete_pipe_token_is_syntax(argv):
    """Only a discrete `|` argv element is pipeline syntax; argv is otherwise unchanged."""
    assert CommandPreProcessor().preprocess_command(argv) == argv


def test_split_pipe_commands_ignores_embedded_pipe_characters():
    """Segment splitting keys off discrete `|` tokens only."""
    preprocessor = CommandPreProcessor()

    assert preprocessor.split_pipe_commands(
        ["grep", "-E", "error|warning", "file.txt"]
    ) == [["grep", "-E", "error|warning", "file.txt"]]
    assert preprocessor.split_pipe_commands(["echo", "text|", "id"]) == [
        ["echo", "text|", "id"]
    ]


@pytest.mark.asyncio
async def test_embedded_pipe_argument_is_not_a_pipeline_stage(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """A regex alternation argument reaches the process as one intact argv element."""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "grep")

    result = await shell_executor_with_mock.execute(
        ["grep", "-E", "error|warning", "file.txt"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    mock_process_manager.execute_pipeline.assert_not_awaited()
    mock_process_manager.create_process.assert_awaited_once()
    assert mock_process_manager.create_process.await_args.args[0] == [
        "grep",
        "-E",
        "error|warning",
        "file.txt",
    ]


@pytest.mark.asyncio
async def test_trailing_pipe_argument_cannot_smuggle_a_command_stage(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """`['echo', 'text|', 'id']` never turns `id` into an independent pipeline stage."""
    clear_env(monkeypatch)
    # `id` is deliberately NOT allowed: if it became its own stage the pipeline
    # path would surface a "Command not allowed" rejection instead of running.
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")

    result = await shell_executor_with_mock.execute(
        ["echo", "text|", "id"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    mock_process_manager.execute_pipeline.assert_not_awaited()
    mock_process_manager.create_process.assert_awaited_once()
    assert mock_process_manager.create_process.await_args.args[0] == [
        "echo",
        "text|",
        "id",
    ]


@pytest.mark.asyncio
async def test_leading_pipe_argument_remains_literal(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """A leading pipe character inside an argument is preserved verbatim."""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo")

    result = await shell_executor_with_mock.execute(
        ["echo", "|text"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    mock_process_manager.execute_pipeline.assert_not_awaited()
    assert mock_process_manager.create_process.await_args.args[0] == ["echo", "|text"]


@pytest.mark.asyncio
async def test_pipe_in_command_name_is_still_rejected(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Command-name validation keeps rejecting `|` in the command position."""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,ls")

    result = await shell_executor_with_mock.execute(
        ["ls|", "hello"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["status"] == 1
    assert "Unsafe command name: ls|" in result["error"]
    mock_process_manager.create_process.assert_not_awaited()
    mock_process_manager.execute_pipeline.assert_not_awaited()


@pytest.mark.asyncio
async def test_awk_embedded_pipe_payload_rejected_before_any_process(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """The reported awk payload is policy-rejected before any process is created."""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "awk,id")

    result = await shell_executor_with_mock.execute(
        ["awk", 'BEGIN{print "x" | "id"}'],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["status"] == 1
    assert "awk external access" in result["error"]
    mock_process_manager.create_process.assert_not_awaited()
    mock_process_manager.execute_pipeline.assert_not_awaited()


@pytest.mark.asyncio
async def test_awk_embedded_pipe_payload_has_no_file_side_effect(
    temp_test_dir, monkeypatch
):
    """The rejected awk payload never reaches awk, so its sentinel is not created."""
    clear_env(monkeypatch)
    monkeypatch.setenv("ALLOW_COMMANDS", "awk")
    marker = os.path.join(temp_test_dir, "awk-pwned")
    executor = ShellExecutor()

    result = await executor.execute(
        ["awk", f'BEGIN{{print "x" | "touch {marker}"}}'],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["status"] == 1
    assert "awk external access" in result["error"]
    assert not os.path.exists(marker)


@pytest.mark.asyncio
async def test_trailing_pipe_argument_has_no_subprocess_side_effect(
    temp_test_dir, monkeypatch
):
    """A trailing literal pipe cannot smuggle an extra allowlisted pipeline stage."""
    clear_env(monkeypatch)
    # Both commands are allowed, so nothing but argv preservation prevents the
    # vulnerable preprocessor from running `echo text | touch <marker>`.
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,touch")
    marker = os.path.join(temp_test_dir, "smuggled")
    executor = ShellExecutor()

    result = await executor.execute(
        ["echo", "text|", "touch", marker],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    assert result["stdout"].strip() == f"text| touch {marker}"
    assert not os.path.exists(marker)


@pytest.mark.asyncio
async def test_pipeline_execution_success(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Test successful pipeline execution with proper return value"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    # Set up mock for pipeline execution
    expected_output = b"mocked pipeline output\n"
    mock_process_manager.execute_pipeline.return_value = (expected_output, b"", 0)

    result = await shell_executor_with_mock.execute(
        ["echo", "hello world", "|", "grep", "world"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    assert result["status"] == 0
    assert result["stdout"].rstrip() == "mocked pipeline output"
    assert "execution_time" in result


@pytest.mark.asyncio
async def test_pipeline_cleanup_and_timeouts(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Test cleanup of processes in pipelines and timeout handling"""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    # Mock timeout behavior for pipeline
    mock_process_manager.execute_pipeline.side_effect = TimeoutError(
        "Command timed out after 1 seconds"
    )

    result = await shell_executor_with_mock.execute(
        ["echo", "test", "|", "grep", "test"],  # Use a pipeline command
        temp_test_dir,
        timeout=1,
    )

    assert result["status"] == -1
    assert "timed out" in result["error"].lower()

    # Verify cleanup was called
    mock_process_manager.cleanup_processes.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_preserves_full_argv_segments(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Pipeline execution passes argv segments with arguments to ProcessManager."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    mock_process_manager.execute_pipeline.return_value = (b"hello\n", b"", 0)

    result = await shell_executor_with_mock.execute(
        ["echo", "hello", "|", "grep", "h"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    mock_process_manager.execute_pipeline.assert_awaited_once()
    assert mock_process_manager.execute_pipeline.await_args.args[0] == [
        ["echo", "hello"],
        ["grep", "h"],
    ]


@pytest.mark.asyncio
async def test_pipeline_allows_newline_argument_after_safe_command_name(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Pipeline validation rejects unsafe command names without rejecting data args."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    mock_process_manager.execute_pipeline.return_value = (b"world\n", b"", 0)

    result = await shell_executor_with_mock.execute(
        ["echo", "hello\nworld", "|", "grep", "world"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["error"] is None
    assert result["stdout"].strip() == "world"
    mock_process_manager.execute_pipeline.assert_awaited_once()
    assert mock_process_manager.execute_pipeline.await_args.args[0] == [
        ["echo", "hello\nworld"],
        ["grep", "world"],
    ]


@pytest.mark.asyncio
async def test_pipeline_rejects_metacharacter_injected_command(
    shell_executor_with_mock, temp_test_dir, mock_process_manager, monkeypatch
):
    """Metacharacters embedded in a pipeline command name are rejected pre-exec."""
    monkeypatch.setenv("ALLOW_COMMANDS", "cat,ls")

    result = await shell_executor_with_mock.execute(
        ["ls; touch /tmp/pwned", "|", "cat"],
        directory=temp_test_dir,
        timeout=5,
    )

    assert result["status"] == 1
    assert "Unexpected shell operator" in result["error"]
    mock_process_manager.execute_pipeline.assert_not_awaited()


@pytest.mark.asyncio
async def test_pipeline_success_real_execution(temp_test_dir, monkeypatch):
    """Normal argv-based pipeline succeeds without shell interpretation."""
    monkeypatch.setenv("ALLOW_COMMANDS", "echo,grep")
    executor = ShellExecutor()

    result = await executor.execute(
        ["echo", "hello", "|", "grep", "h"], directory=temp_test_dir, timeout=5
    )

    assert result["error"] is None
    assert result["stdout"].strip() == "hello"


@pytest.mark.asyncio
async def test_pipeline_metacharacter_injection_rejected_without_side_effect(
    temp_test_dir, monkeypatch
):
    """Metacharacter-bearing command names are rejected and not shell-executed."""
    monkeypatch.setenv("ALLOW_COMMANDS", "ls,cat")
    marker = os.path.join(temp_test_dir, "pwned")
    executor = ShellExecutor()

    result = await executor.execute(
        [f"ls; touch {marker}", "|", "cat"], directory=temp_test_dir, timeout=5
    )

    assert result["status"] == 1
    assert "Unexpected shell operator" in result["error"]
    assert not os.path.exists(marker)
