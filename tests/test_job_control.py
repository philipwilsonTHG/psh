"""Test job control functionality."""

import pytest
import os
import signal
import time
import tempfile
import subprocess
from psh.shell import Shell
from psh.job_control import JobManager, Job, JobState


class TestJobControl:
    def setup_method(self):
        self.shell = Shell()
        self.shell.history = []
        self.shell.history_file = "/tmp/test_psh_history"
    
    def test_job_manager_creation(self):
        """Test that JobManager is properly initialized."""
        assert self.shell.job_manager is not None
        assert isinstance(self.shell.job_manager, JobManager)
        assert len(self.shell.job_manager.jobs) == 0
        assert self.shell.job_manager.next_job_id == 1
    
    def test_create_job(self):
        """Test job creation."""
        job = self.shell.job_manager.create_job(1234, "sleep 10")
        assert job.job_id == 1
        assert job.pgid == 1234
        assert job.command == "sleep 10"
        assert job.state == JobState.RUNNING
        assert job.foreground == True
        assert len(job.processes) == 0
    
    def test_job_state_transitions(self):
        """Test job state transitions."""
        job = Job(1, 1234, "test command")
        assert job.state == JobState.RUNNING
        
        # Add a process
        job.add_process(1235, "test")
        assert len(job.processes) == 1
        
        # Mark process as stopped
        job.processes[0].stopped = True
        job.update_state()
        assert job.state == JobState.STOPPED
        
        # Mark process as completed
        job.processes[0].stopped = False
        job.processes[0].completed = True
        job.update_state()
        assert job.state == JobState.DONE
    
    def test_job_spec_parsing(self):
        """Test job specification parsing."""
        # Create some test jobs
        job1 = self.shell.job_manager.create_job(1001, "sleep 10")
        job2 = self.shell.job_manager.create_job(1002, "cat file.txt")
        self.shell.job_manager.set_foreground_job(job2)
        
        # Test various job specs
        assert self.shell.job_manager.parse_job_spec("%1") == job1
        assert self.shell.job_manager.parse_job_spec("%2") == job2
        assert self.shell.job_manager.parse_job_spec("%+") == job2
        assert self.shell.job_manager.parse_job_spec("%%") == job2
        assert self.shell.job_manager.parse_job_spec("%") == job2
        assert self.shell.job_manager.parse_job_spec("%cat") == job2
        assert self.shell.job_manager.parse_job_spec("%sleep") == job1
        assert self.shell.job_manager.parse_job_spec("%nonexistent") is None
    
    def test_jobs_builtin(self):
        """Test jobs built-in command."""
        # No jobs initially
        exit_code = self.shell.run_command("jobs")
        assert exit_code == 0
        
        # Create some jobs
        job1 = self.shell.job_manager.create_job(2001, "sleep 5")
        job2 = self.shell.job_manager.create_job(2002, "grep pattern file.txt")
        job2.state = JobState.STOPPED
        self.shell.job_manager.set_foreground_job(job2)
        
        # Test jobs listing
        lines = self.shell.job_manager.list_jobs()
        assert len(lines) == 2
        assert "[1] " in lines[0]
        assert "Running" in lines[0]
        assert "sleep 5" in lines[0]
        assert "[2]+" in lines[1]
        assert "Stopped" in lines[1]
        assert "grep pattern file.txt" in lines[1]
    
    def test_background_job_notification(self):
        """Test background job completion notifications."""
        # Create a completed background job
        job = self.shell.job_manager.create_job(3001, "echo done")
        job.foreground = False
        job.state = JobState.DONE
        
        # Should print notification
        import io
        import sys
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        self.shell.job_manager.notify_completed_jobs()
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        assert "[1]+  Done" in output
        assert "echo done" in output
        
        # Job should be removed after notification
        assert len(self.shell.job_manager.jobs) == 0
    
    def test_signal_handlers(self):
        """Test that signal handlers are properly configured."""
        # SIGTSTP should be ignored by the shell
        handler = signal.getsignal(signal.SIGTSTP)
        assert handler == signal.SIG_IGN
        
        # SIGCHLD should have our handler
        handler = signal.getsignal(signal.SIGCHLD)
        assert handler == self.shell._handle_sigchld
        
        # SIGTTOU and SIGTTIN should be ignored
        assert signal.getsignal(signal.SIGTTOU) == signal.SIG_IGN
        assert signal.getsignal(signal.SIGTTIN) == signal.SIG_IGN
    
    def test_pipeline_job_creation(self):
        """Test that pipelines create jobs properly."""
        # Run a pipeline command
        # We'll check that the job was created by looking at the job manager
        initial_job_count = len(self.shell.job_manager.jobs)
        
        # Run a background pipeline to ensure job persists
        self.shell.run_command("echo hello | cat &")
        
        # Give it a moment to execute
        time.sleep(0.1)
        
        # Should have created a job (though it might be done already)
        # At minimum, the job_id counter should have incremented
        assert self.shell.job_manager.next_job_id > 1
    
    def test_fg_builtin_errors(self, capsys):
        """Test fg built-in error handling."""
        # No current job
        exit_code = self.shell.run_command("fg")
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "no current job" in captured.err
        
        # Invalid job spec
        exit_code = self.shell.run_command("fg %99")
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "no such job" in captured.err
        
        exit_code = self.shell.run_command("fg invalid")
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "no such job" in captured.err
    
    def test_bg_builtin_errors(self, capsys):
        """Test bg built-in error handling."""
        # No current job
        exit_code = self.shell.run_command("bg")
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "no current job" in captured.err
        
        # Invalid job spec
        exit_code = self.shell.run_command("bg %99")
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "no such job" in captured.err
    
    def test_job_process_tracking(self):
        """Test that jobs track their processes correctly."""
        job = Job(1, 5000, "test | command | pipeline")
        
        # Add processes
        job.add_process(5001, "test")
        job.add_process(5002, "command")
        job.add_process(5003, "pipeline")
        
        assert len(job.processes) == 3
        assert job.processes[0].pid == 5001
        assert job.processes[1].pid == 5002
        assert job.processes[2].pid == 5003
        
        # Test finding job by PID
        assert self.shell.job_manager.get_job_by_pid(5002) is None  # Not in manager yet
        
        # Add to manager
        self.shell.job_manager.jobs[1] = job
        assert self.shell.job_manager.get_job_by_pid(5002) == job
        assert self.shell.job_manager.get_job_by_pgid(5000) == job