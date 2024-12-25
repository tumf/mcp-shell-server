# tests/test_process_manager_macos.py
import pytest
import platform
import signal
import time
import os
import subprocess
from typing import Generator

pytestmark = [
    pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="These tests only run on macOS"
    ),
    pytest.mark.macos,
    pytest.mark.slow
]

@pytest.fixture
def process_manager():
    from mcp_shell_server.process_manager import ProcessManager
    pm = ProcessManager()
    yield pm
    pm.cleanup_all()

def get_process_status(pid: int) -> str:
    """Get process status using ps command."""
    try:
        ps = subprocess.run(
            ['ps', '-o', 'stat=', '-p', str(pid)],
            capture_output=True,
            text=True
        )
        return ps.stdout.strip()
    except subprocess.CalledProcessError:
        return ""

def test_zombie_process_cleanup(process_manager):
    """Test that background processes don't become zombies."""
    cmd = ["sh", "-c", "sleep 0.5 & wait"]
    process = process_manager.start_process(cmd)
    
    # Wait for the background process to finish
    time.sleep(1)
    
    # Get process status
    status = get_process_status(process.pid)
    
    # Verify process is either gone or not zombie (Z state)
    assert 'Z' not in status, f"Process {process.pid} is zombie (status: {status})"

def test_process_timeout(process_manager):
    """Test process timeout functionality."""
    # Start a process that should timeout
    cmd = ["sleep", "10"]
    process = process_manager.start_process(cmd, timeout=1)
    
    # Wait slightly longer than the timeout
    time.sleep(1.5)
    
    # Verify process was terminated
    assert not process.is_running()
    assert process.returncode is not None

def test_multiple_process_cleanup(process_manager):
    """Test cleanup of multiple processes."""
    # Start multiple background processes
    processes = [
        process_manager.start_process(["sleep", "2"])
        for _ in range(3)
    ]
    
    # Give them a moment to start
    time.sleep(0.1)
    
    # Verify they're all running
    assert all(p.is_running() for p in processes)
    
    # Cleanup
    process_manager.cleanup_all()
    
    # Give cleanup a moment to complete
    time.sleep(0.1)
    
    # Verify all processes are gone
    for p in processes:
        status = get_process_status(p.pid)
        assert status == "", f"Process {p.pid} still exists with status: {status}"

def test_process_group_termination(process_manager):
    """Test that entire process group is terminated."""
    # Create a process that spawns children
    cmd = ["sh", "-c", "sleep 10 & sleep 10 & sleep 10 & wait"]
    process = process_manager.start_process(cmd)
    
    # Give processes time to start
    time.sleep(0.5)
    
    # Kill the main process
    process.kill()
    
    # Wait a moment for cleanup
    time.sleep(0.5)
    
    # Check if any processes from the group remain
    ps = subprocess.run(
        ["pgrep", "-g", str(process.pid)],
        capture_output=True
    )
    assert ps.returncode != 0, "Process group still exists"
