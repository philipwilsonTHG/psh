import pytest
import os
import signal
import time
import tempfile
import subprocess
from psh.shell import Shell


class TestSignalHandling:
    def setup_method(self):
        self.shell = Shell()
        self.shell.history = []
        self.shell.history_file = "/tmp/test_psh_history"
    
    def test_signal_handler_setup(self):
        """Test that signal handlers are properly set up"""
        # Check that SIGTTOU is ignored
        handler = signal.getsignal(signal.SIGTTOU)
        assert handler == signal.SIG_IGN
        
        # Check that SIGINT has a handler
        handler = signal.getsignal(signal.SIGINT)
        assert handler == self.shell._handle_sigint
        
        # Check that SIGTSTP is ignored by the shell
        handler = signal.getsignal(signal.SIGTSTP)
        assert handler == signal.SIG_IGN
    
    def test_pipeline_process_group(self):
        """Test that pipeline creates a process group"""
        # This is hard to test directly without spawning a real subprocess
        # We'll create a pipeline that outputs its process group
        output_file = "/tmp/test_pgid.txt"
        
        # Create a script that outputs its pgid
        script = "/tmp/test_pgid.sh"
        with open(script, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("ps -o pgid= -p $$\n")
        os.chmod(script, 0o755)
        
        try:
            # Run pipeline
            self.shell.run_command(f"{script} | cat > {output_file}")
            
            # Check that the commands ran
            assert os.path.exists(output_file)
            with open(output_file, "r") as f:
                pgid = f.read().strip()
            
            # The pgid should be a number
            assert pgid.isdigit()
            
            os.unlink(output_file)
        finally:
            os.unlink(script)
    
    def test_exit_status_from_signal(self):
        """Test that exit status reflects signal termination"""
        # Create a command that will be killed by signal
        # Using sleep and killing it should give us 128 + signal number
        
        # This is tricky to test as we need to send a signal to a running process
        # For now, we'll test the exit status handling logic
        
        # When a process is killed by SIGTERM (15), exit status should be 128+15=143
        # When a process is killed by SIGINT (2), exit status should be 128+2=130
        
        # We can test this by creating a script that kills itself
        script = "/tmp/test_signal_exit.sh"
        with open(script, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("kill -INT $$\n")  # Send SIGINT to itself
        os.chmod(script, 0o755)
        
        try:
            exit_code = self.shell.run_command(script + " 2>/dev/null")
            # Exit code should be 128 + 2 (SIGINT)
            assert exit_code == 130
            assert self.shell.last_exit_code == 130
        finally:
            os.unlink(script)
    
    def test_background_process_no_terminal_control(self):
        """Test that background processes don't get terminal control"""
        # Background process should not affect foreground_pgid
        self.shell.run_command("sleep 0.1 &")
        assert self.shell.foreground_pgid is None
    
    def test_foreground_pgid_restored(self):
        """Test that foreground process group is restored after pipeline"""
        # Save initial state
        initial_pgid = self.shell.foreground_pgid
        
        # Run a quick pipeline
        self.shell.run_command("echo hello | cat > /dev/null")
        
        # foreground_pgid should be restored
        assert self.shell.foreground_pgid == initial_pgid
    
    def test_signal_in_pipeline(self):
        """Test signal handling in pipeline commands"""
        # Create a script that traps signals
        script = "/tmp/test_trap.sh"
        with open(script, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("trap 'echo caught' INT\n")
            f.write("sleep 10\n")
        os.chmod(script, 0o755)
        
        output_file = "/tmp/signal_test_output.txt"
        
        try:
            # Start pipeline in background
            proc = subprocess.Popen(
                ["python3", "simple_shell.py", "-c", f"{script} | cat > {output_file}"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            # Give it time to start
            time.sleep(0.1)
            
            # Send SIGINT to the process group
            try:
                os.killpg(proc.pid, signal.SIGINT)
            except:
                proc.kill()
            
            proc.wait()
            
            # Clean up
            if os.path.exists(output_file):
                os.unlink(output_file)
        finally:
            if os.path.exists(script):
                os.unlink(script)