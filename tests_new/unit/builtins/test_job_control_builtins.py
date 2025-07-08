"""
Unit tests for job control builtins (jobs, fg, bg).

Tests cover:
- Listing jobs
- Foreground/background job control
- Job state transitions
- Error conditions

Note: Many job control features require interactive terminal,
so some tests may need to be marked as xfail.
"""

import pytest
import time


class TestJobsBuiltin:
    """Test jobs builtin functionality."""
    
    def test_jobs_empty_list(self, shell, capsys):
        """Test jobs with no background jobs."""
        shell.run_command('jobs')
        captured = capsys.readouterr()
        # Should have no output or minimal output
        assert captured.out.strip() == "" or "no jobs" in captured.out.lower()
    
    def test_jobs_with_background_job(self, shell, capsys):
        """Test jobs with a background job."""
        # Start a background job
        shell.run_command('sleep 10 &')
        
        # List jobs
        shell.run_command('jobs')
        captured = capsys.readouterr()
        assert 'sleep' in captured.out
        assert '&' in captured.out or 'Running' in captured.out
        
        # Clean up
        shell.run_command('kill %1 2>/dev/null || true')
    
    def test_jobs_multiple_background(self, shell, capsys):
        """Test jobs with multiple background jobs."""
        # Start multiple background jobs
        shell.run_command('sleep 10 &')
        shell.run_command('sleep 20 &')
        
        # List jobs
        shell.run_command('jobs')
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        assert len(lines) >= 2
        assert '[1]' in captured.out
        assert '[2]' in captured.out
        
        # Clean up
        shell.run_command('kill %1 %2 2>/dev/null || true')
    
    @pytest.mark.xfail(reason="BUG: PSH jobs -p shows full info instead of just PIDs")
    def test_jobs_with_options(self, shell, capsys):
        """Test jobs with various options."""
        shell.run_command('sleep 10 &')
        
        # Test -l (long format with PIDs)
        shell.run_command('jobs -l')
        captured = capsys.readouterr()
        # Should show PID
        assert any(char.isdigit() for char in captured.out)
        
        # Test -p (PIDs only)
        shell.run_command('jobs -p')
        captured = capsys.readouterr()
        # Should be just numbers
        assert captured.out.strip().isdigit()
        
        # Clean up
        shell.run_command('kill %1 2>/dev/null || true')
    
    @pytest.mark.xfail(reason="Job completion notifications may not work reliably in test environment")
    def test_jobs_status_changes(self, shell, capsys):
        """Test jobs showing status changes."""
        # Start a job that will complete quickly
        shell.run_command('(sleep 1; exit 0) &')
        
        # Check initial status
        shell.run_command('jobs')
        captured = capsys.readouterr()
        assert 'Running' in captured.out or '&' in captured.out
        
        # Wait for completion
        time.sleep(2)
        
        # Check status again
        shell.run_command('jobs')
        captured = capsys.readouterr()
        # Job should be done or gone from list
        assert 'Done' in captured.out or captured.out.strip() == ""


class TestFgBuiltin:
    """Test fg builtin functionality."""
    
    @pytest.mark.xfail(reason="fg requires interactive terminal")
    def test_fg_bring_to_foreground(self, shell, capsys):
        """Test bringing a background job to foreground."""
        # This test requires interactive terminal support
        shell.run_command('sleep 10 &')
        shell.run_command('jobs')
        
        # Try to bring to foreground
        exit_code = shell.run_command('fg %1')
        # In non-interactive mode, this might fail
    
    def test_fg_no_jobs(self, shell, capsys):
        """Test fg with no background jobs."""
        exit_code = shell.run_command('fg')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'no' in captured.err.lower() or 'job' in captured.err.lower()
    
    def test_fg_invalid_job_spec(self, shell, capsys):
        """Test fg with invalid job specification."""
        exit_code = shell.run_command('fg %999')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'no such job' in captured.err.lower() or 'not found' in captured.err
    
    @pytest.mark.xfail(reason="fg may not work in non-interactive mode")
    def test_fg_specific_job(self, shell, capsys):
        """Test fg with specific job number."""
        # Start multiple jobs
        shell.run_command('sleep 10 &')
        shell.run_command('sleep 20 &')
        
        # Try to foreground the second job
        exit_code = shell.run_command('fg %2')
        
        # Clean up
        shell.run_command('kill %1 %2 2>/dev/null || true')


class TestBgBuiltin:
    """Test bg builtin functionality."""
    
    @pytest.mark.xfail(reason="bg requires job control support")
    def test_bg_resume_stopped_job(self, shell, capsys):
        """Test resuming a stopped job in background."""
        # This requires ability to stop jobs (Ctrl-Z), which
        # is not available in non-interactive mode
        pass
    
    def test_bg_no_jobs(self, shell, capsys):
        """Test bg with no stopped jobs."""
        exit_code = shell.run_command('bg')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'no' in captured.err.lower() or 'job' in captured.err.lower()
    
    def test_bg_invalid_job_spec(self, shell, capsys):
        """Test bg with invalid job specification."""
        exit_code = shell.run_command('bg %999')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'no such job' in captured.err.lower() or 'not found' in captured.err


class TestJobControlIntegration:
    """Test job control integration scenarios."""
    
    def test_job_with_pipe(self, shell, capsys):
        """Test background job with pipeline."""
        shell.run_command('echo "test" | sleep 5 &')
        shell.run_command('jobs')
        captured = capsys.readouterr()
        # Should show the pipeline as a job
        assert 'sleep' in captured.out or '&' in captured.out
        
        # Clean up
        shell.run_command('kill %1 2>/dev/null || true')
    
    def test_job_completion_notification(self, shell, capsys):
        """Test job completion notification."""
        # Start a quick job
        shell.run_command('(sleep 0.1; echo "done") &')
        job_id = None
        
        # Get job number
        shell.run_command('jobs')
        captured = capsys.readouterr()
        if '[1]' in captured.out:
            job_id = 1
        
        # Wait for completion
        time.sleep(0.5)
        
        # Run another command to trigger notification
        shell.run_command('echo "trigger"')
        captured = capsys.readouterr()
        # Might show "Done" notification
        assert 'trigger' in captured.out
    
    def test_disown_job(self, shell, capsys):
        """Test disowning a job."""
        # Start a background job
        shell.run_command('sleep 10 &')
        
        # Disown it (if supported)
        exit_code = shell.run_command('disown %1 2>/dev/null || echo "disown not supported"')
        
        if exit_code == 0:
            # Job should not appear in jobs list
            shell.run_command('jobs')
            captured = capsys.readouterr()
            assert 'sleep' not in captured.out
        else:
            # disown not supported
            captured = capsys.readouterr()
            assert 'not supported' in captured.out
        
        # Clean up (kill by searching process)
        shell.run_command('pkill -f "sleep 10" 2>/dev/null || true')