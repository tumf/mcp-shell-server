# tests/test_process_manager_macos.py
import asyncio
import platform
import signal
import subprocess

import pytest

pytestmark = [
    pytest.mark.skipif(
        platform.system() != "Darwin", reason="These tests only run on macOS"
    ),
    pytest.mark.macos,
    pytest.mark.slow,
]


@pytest.fixture
def process_manager():
    from mcp_shell_server.process_manager import ProcessManager

    pm = ProcessManager()
    try:
        yield pm
    finally:
        asyncio.run(pm.cleanup_all())


def get_process_status(pid: int) -> str:
    """Get process status using ps command."""
    try:
        ps = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True
        )
        return ps.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


@pytest.mark.asyncio
async def test_zombie_process_cleanup(process_manager):
    """Test that background processes don't become zombies."""
    cmd = ["sh", "-c", "sleep 0.5 & wait"]
    process = await process_manager.start_process(cmd)

    # Wait for the background process to finish
    await asyncio.sleep(1)

    # Get process status
    status = get_process_status(process.pid)

    # Verify process is either gone or not zombie (Z state)
    assert "Z" not in status, f"Process {process.pid} is zombie (status: {status})"


@pytest.mark.asyncio
async def test_process_timeout(process_manager):
    """Test process timeout functionality."""
    # Start a process that should timeout
    cmd = ["sleep", "10"]
    process = await process_manager.start_process(cmd)

    try:
        # Communicate with timeout
        with pytest.raises(TimeoutError):
            _, _ = await process_manager.execute_with_timeout(process, timeout=1)

        # プロセスが終了するまで待つ
        try:
            await asyncio.wait_for(process.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            process.kill()  # Force kill

        # Wait for termination
        await asyncio.wait_for(process.wait(), timeout=0.5)

        # Verify process was terminated
        assert process.returncode is not None
        assert not process.is_running()
    finally:
        if process.returncode is None:
            try:
                process.kill()
                await asyncio.wait_for(process.wait(), timeout=0.5)
            except (ProcessLookupError, asyncio.TimeoutError):
                pass


@pytest.mark.asyncio
async def test_multiple_process_cleanup(process_manager):
    """Test cleanup of multiple processes."""
    # Start multiple background processes
    # Start multiple processes in parallel
    processes = await asyncio.gather(
        *[process_manager.start_process(["sleep", "2"]) for _ in range(3)]
    )

    # Give them a moment to start
    await asyncio.sleep(0.1)

    try:
        # Verify they're all running
        assert all(p.is_running() for p in processes)

        # Cleanup
        await process_manager.cleanup_all()

        # Give cleanup a moment to complete
        await asyncio.sleep(0.1)

        # Verify all processes are gone
        for p in processes:
            status = get_process_status(p.pid)
            assert status == "", f"Process {p.pid} still exists with status: {status}"
    finally:
        # Ensure cleanup in case of test failure
        for p in processes:
            if p.returncode is None:
                try:
                    p.kill()
                except ProcessLookupError:
                    pass


@pytest.mark.asyncio
async def test_killed_parent_pipe_cleanup(process_manager):
    """Reap a killed parent and close pipes inherited by its descendants."""
    # Create a process that spawns children
    cmd = ["sh", "-c", "sleep 10 & sleep 10 & sleep 10 & wait"]
    process = await process_manager.start_process(cmd)

    try:
        # Give processes time to start
        await asyncio.sleep(0.5)

        # Kill the main process
        process.kill()

        # Wait a moment for cleanup
        await asyncio.sleep(0.5)

        assert process.returncode == -signal.SIGKILL
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        # Descendant containment is not guaranteed. Their inherited pipes must
        # reach EOF before this test's event loop closes, even after parent exit.
        await asyncio.wait_for(process.communicate(), timeout=12)

    assert process.stdin.is_closing()
    assert process.stdout.at_eof()
    assert process.stderr.at_eof()
