"""Tests for the wait builtin."""

import os
import time
import signal
import subprocess
import pytest
from unittest.mock import MagicMock, patch
from io import StringIO

from psh.builtins.job_control import WaitBuiltin
from psh.job_control import JobManager, Job, JobState, Process
from psh.core.state import ShellState


class TestWaitBuiltin:
    """Test wait builtin functionality."""
    
    def setup_method(self):
        """Set up test components."""
        self.wait_builtin = WaitBuiltin()
        
        # Create a mock shell with minimal required attributes
        self.shell = MagicMock()
        self.shell.stderr = StringIO()
        self.shell.stdout = StringIO()
        
        # Create a real job manager for proper testing
        self.shell.job_manager = JobManager()
        
        # Mock shell state
        self.shell.state = MagicMock()
        self.shell.state.last_bg_pid = None
    
    def test_wait_no_args_no_jobs(self):
        """Test wait with no arguments when no jobs exist."""
        result = self.wait_builtin.execute(['wait'], self.shell)
        assert result == 0
    
    def test_wait_invalid_pid(self):
        """Test wait with invalid PID."""
        result = self.wait_builtin.execute(['wait', 'invalid'], self.shell)
        error = self.shell.stderr.getvalue()
        
        assert result == 127
        assert "not a valid process id" in error
    
    def test_wait_invalid_job_spec(self):
        """Test wait with invalid job specification."""
        result = self.wait_builtin.execute(['wait', '%99'], self.shell)
        error = self.shell.stderr.getvalue()
        
        assert result == 127
        assert "no such job" in error
    
    def test_wait_extract_exit_status(self):
        """Test _extract_exit_status helper method."""
        # Test normal exit (shift exit code to upper byte)
        status = 42 << 8  # Exit code 42
        assert self.wait_builtin._extract_exit_status(status) == 42
        
        # Test signal termination (signal in lower byte)
        status = signal.SIGTERM  # Killed by SIGTERM
        assert self.wait_builtin._extract_exit_status(status) == 128 + signal.SIGTERM
    
    def test_wait_for_done_job(self):
        """Test waiting for a job that's already done."""
        # Create a completed job
        job = Job(1, 1000, "sleep 1")
        job.state = JobState.DONE
        proc = Process(1000, "sleep 1")
        proc.status = 0 << 8  # Exited with status 0
        proc.completed = True
        job.processes.append(proc)
        
        self.shell.job_manager.jobs[1] = job
        
        result = self.wait_builtin.execute(['wait', '%1'], self.shell)
        assert result == 0
    
    def test_wait_for_stopped_job(self):
        """Test waiting for a stopped job."""
        # Create a stopped job
        job = Job(1, 1000, "sleep 10")
        job.state = JobState.STOPPED
        proc = Process(1000, "sleep 10")
        proc.stopped = True
        job.processes.append(proc)
        
        self.shell.job_manager.jobs[1] = job
        
        result = self.wait_builtin.execute(['wait', '%1'], self.shell)
        error = self.shell.stderr.getvalue()
        
        assert result == 1
        assert "job is stopped" in error
    
    def test_wait_help_properties(self):
        """Test that help properties are properly defined."""
        assert self.wait_builtin.name == "wait"
        assert self.wait_builtin.synopsis == "wait [pid|job_id ...]"
        assert "Wait for process completion" in self.wait_builtin.description
        assert "wait %1" in self.wait_builtin.help
        assert "Examples:" in self.wait_builtin.help
    
    def test_wait_multiple_specs(self):
        """Test wait with multiple job specifications."""
        # Create two completed jobs
        job1 = Job(1, 1000, "true")
        job1.state = JobState.DONE
        proc1 = Process(1000, "true")
        proc1.status = 0 << 8  # Exit code 0
        proc1.completed = True
        job1.processes.append(proc1)
        
        job2 = Job(2, 1001, "false")
        job2.state = JobState.DONE
        proc2 = Process(1001, "false")
        proc2.status = 1 << 8  # Exit code 1
        proc2.completed = True
        job2.processes.append(proc2)
        
        self.shell.job_manager.jobs[1] = job1
        self.shell.job_manager.jobs[2] = job2
        
        # Wait for both - should return exit status of last one
        result = self.wait_builtin.execute(['wait', '%1', '%2'], self.shell)
        assert result == 1  # Exit status of job2


class TestWaitBuiltinIntegration:
    """Integration tests for wait builtin with mocked processes."""
    
    def test_wait_for_background_process(self):
        """Test waiting for an actual background process."""
        # This test verifies integration using direct Shell instance
        from psh.shell import Shell
        
        shell = Shell(norc=True)
        
        # Start a background process
        exit_code = shell.run_command("sleep 0.1 &")
        assert exit_code == 0
        
        # Verify we have a background job
        assert len(shell.job_manager.jobs) > 0
        
        # Wait for it
        exit_code = shell.run_command("wait")
        assert exit_code == 0
    
    def test_wait_for_specific_pid(self):
        """Test waiting for a specific process ID."""
        from psh.shell import Shell
        
        shell = Shell(norc=True)
        
        # Start a background process and capture its PID
        shell.run_command("sleep 0.1 &")
        pid = shell.state.last_bg_pid
        
        # Verify we have the PID
        assert pid is not None
        
        # Wait for the specific PID using PSH's wait builtin
        exit_code = shell.run_command(f"wait {pid}")
        assert exit_code == 0
    
    def test_wait_for_job_with_exit_status(self):
        """Test that wait returns correct exit status."""
        from psh.shell import Shell
        
        shell = Shell(norc=True)
        
        # Start a background process that will fail
        shell.run_command("sh -c 'sleep 0.1; exit 42' &")
        
        # Wait for it - should return exit code 42
        exit_code = shell.run_command("wait")
        assert exit_code == 42


if __name__ == '__main__':
    pytest.main([__file__])