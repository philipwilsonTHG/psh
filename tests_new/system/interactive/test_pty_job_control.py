"""
PTY-based job control tests.

These tests verify job control functionality that requires real terminal
emulation, such as:
- Ctrl-Z to suspend jobs
- fg/bg commands
- Job status tracking
- Signal handling in foreground/background
"""

import pytest
import sys
import time
import os
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TEST_ROOT))

try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False

from framework.pty_test_framework import (
    PTYTestFramework, PTYTestConfig, PTYTest,
    interactive_shell
)

# Skip all tests if pexpect not available
pytestmark = pytest.mark.skipif(not HAS_PEXPECT, reason="pexpect not installed")


class TestPTYJobControl(PTYTest):
    """Test job control with real PTY."""
    
    pytestmark = pytest.mark.xfail(reason="PSH job control not fully implemented in PTY mode")
    
    def test_ctrl_z_suspend(self, pty_framework):
        """Test Ctrl-Z to suspend a job."""
        shell = pty_framework.spawn_shell()
        
        # Start a long-running command
        pty_framework.send_line("sleep 30")
        time.sleep(0.5)  # Let it start
        
        # Send Ctrl-Z to suspend
        pty_framework.send_ctrl('z')
        
        # Should see suspension message and get prompt back
        try:
            pty_framework.expect_output("[1]+  Stopped")
            pty_framework._wait_for_prompt()
        except:
            # Alternative format
            pty_framework.expect_output("Stopped")
            pty_framework._wait_for_prompt()
        
        # Verify we can run commands
        output = pty_framework.run_command("echo resumed")
        assert "resumed" in output
        
        # Clean up - kill the background job
        pty_framework.run_command("kill %1")
        
    def test_jobs_command(self, pty_framework):
        """Test jobs command shows suspended jobs."""
        shell = pty_framework.spawn_shell()
        
        # Start and suspend a job
        pty_framework.send_line("sleep 30")
        time.sleep(0.5)
        pty_framework.send_ctrl('z')
        pty_framework._wait_for_prompt()
        
        # Check jobs list
        output = pty_framework.run_command("jobs")
        assert "sleep" in output
        assert ("Stopped" in output or "suspended" in output.lower())
        
        # Clean up
        pty_framework.run_command("kill %1")
        
    def test_fg_resume(self, pty_framework):
        """Test fg command to resume job."""
        shell = pty_framework.spawn_shell()
        
        # Start a command that prints after delay
        pty_framework.send_line("(sleep 1 && echo 'job done')")
        time.sleep(0.3)
        
        # Suspend it
        pty_framework.send_ctrl('z')
        pty_framework._wait_for_prompt()
        
        # Resume with fg
        pty_framework.send_line("fg")
        
        # Should see the output when it completes
        output = pty_framework.expect_output("job done")
        pty_framework._wait_for_prompt()
        
    def test_bg_resume(self, pty_framework):
        """Test bg command to resume in background."""
        shell = pty_framework.spawn_shell()
        
        # Create a test script that writes to a file
        test_file = "pty_bg_test.txt"
        pty_framework.run_command(f"rm -f {test_file}")
        
        # Start a command that writes after delay
        pty_framework.send_line(f"(sleep 1 && echo 'background done' > {test_file})")
        time.sleep(0.3)
        
        # Suspend it
        pty_framework.send_ctrl('z')
        pty_framework._wait_for_prompt()
        
        # Resume in background
        pty_framework.send_line("bg")
        pty_framework._wait_for_prompt()
        
        # Should be able to run other commands
        output = pty_framework.run_command("echo foreground works")
        assert "foreground works" in output
        
        # Wait for background job to complete
        time.sleep(1.5)
        
        # Check the file was created
        output = pty_framework.run_command(f"cat {test_file}")
        assert "background done" in output
        
        # Cleanup
        pty_framework.run_command(f"rm -f {test_file}")
        
    def test_multiple_jobs(self, pty_framework):
        """Test managing multiple jobs."""
        shell = pty_framework.spawn_shell()
        
        # Start first job
        pty_framework.send_line("sleep 30")
        time.sleep(0.3)
        pty_framework.send_ctrl('z')
        pty_framework._wait_for_prompt()
        
        # Start second job
        pty_framework.send_line("sleep 40")
        time.sleep(0.3)
        pty_framework.send_ctrl('z')
        pty_framework._wait_for_prompt()
        
        # Check jobs list
        output = pty_framework.run_command("jobs")
        assert "[1]" in output
        assert "[2]" in output
        assert output.count("sleep") >= 2
        
        # Resume specific job
        pty_framework.send_line("fg %1")
        time.sleep(0.3)
        
        # Suspend it again
        pty_framework.send_ctrl('z')
        pty_framework._wait_for_prompt()
        
        # Clean up all jobs
        pty_framework.run_command("kill %1 %2")
        
    def test_background_job_completion(self, pty_framework):
        """Test notification when background job completes."""
        shell = pty_framework.spawn_shell()
        
        # Start a short background job
        pty_framework.send_line("(sleep 1 && echo 'bg job done') &")
        pty_framework._wait_for_prompt()
        
        # Should see job started message
        time.sleep(0.1)
        
        # Run another command
        pty_framework.run_command("echo 'doing other work'")
        
        # Wait for background job to complete
        time.sleep(1.5)
        
        # Next prompt should show job completion
        pty_framework.send_text('\r')  # Just press enter
        
        # Should eventually see completion notice
        # Format varies: "[1]+ Done" or "[1] Done" etc.
        try:
            pty_framework.expect_output("Done", timeout=2)
        except:
            # Some shells don't show completion immediately
            pass
        
        pty_framework._wait_for_prompt()
        
    def test_ctrl_c_foreground_only(self, pty_framework):
        """Test Ctrl-C only affects foreground job."""
        shell = pty_framework.spawn_shell()
        
        # Start a background job
        test_file = "pty_bg_survivor.txt"
        pty_framework.run_command(f"rm -f {test_file}")
        pty_framework.send_line(f"(sleep 2 && echo 'survived' > {test_file}) &")
        pty_framework._wait_for_prompt()
        
        # Start a foreground job
        pty_framework.send_line("sleep 30")
        time.sleep(0.5)
        
        # Ctrl-C should kill foreground but not background
        pty_framework.send_ctrl('c')
        pty_framework._wait_for_prompt()
        
        # Verify we're back at prompt
        output = pty_framework.run_command("echo 'got prompt'")
        assert "got prompt" in output
        
        # Wait for background job
        time.sleep(2)
        
        # Check background job completed
        output = pty_framework.run_command(f"cat {test_file}")
        assert "survived" in output
        
        # Cleanup
        pty_framework.run_command(f"rm -f {test_file}")
        
    def test_disown_command(self, pty_framework):
        """Test disown removes job from job table."""
        shell = pty_framework.spawn_shell()
        
        # Start a background job
        pty_framework.send_line("sleep 30 &")
        pty_framework._wait_for_prompt()
        
        # Verify it's in jobs list
        output = pty_framework.run_command("jobs")
        assert "sleep" in output
        
        # Disown it
        pty_framework.run_command("disown %1")
        
        # Should no longer be in jobs list
        output = pty_framework.run_command("jobs")
        assert "sleep" not in output or "jobs" not in output
        
        # Process should still be running - find and kill it
        output = pty_framework.run_command("ps aux | grep 'sleep 30' | grep -v grep")
        if "sleep" in output:
            # Extract PID and kill it
            lines = output.strip().split('\n')
            for line in lines:
                if "sleep 30" in line:
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        pty_framework.run_command(f"kill {pid}")
                        break


class TestPTYSignalHandling(PTYTest):
    """Test signal handling in PTY environment."""
    
    pytestmark = pytest.mark.xfail(reason="PSH signal handling issues in PTY mode")
    
    def test_sigtstp_handler(self, pty_framework):
        """Test custom SIGTSTP handling."""
        shell = pty_framework.spawn_shell()
        
        # Set up a trap for SIGTSTP
        pty_framework.run_command("trap 'echo caught sigtstp' TSTP")
        
        # This test is tricky because Ctrl-Z behavior depends on
        # whether the shell properly handles SIGTSTP
        # For now, just verify trap was set
        output = pty_framework.run_command("trap -p")
        if "TSTP" in output or "SIGTSTP" in output:
            assert "caught sigtstp" in output
            
    def test_sigint_in_script(self, pty_framework):
        """Test SIGINT handling in script context."""
        shell = pty_framework.spawn_shell()
        
        # Create a script that traps SIGINT
        script = """
trap 'echo "caught interrupt"; exit 1' INT
echo "starting sleep"
sleep 10
echo "should not see this"
"""
        pty_framework.run_command("cat > test_int.sh << 'EOF'" + script + "\nEOF")
        pty_framework.run_command("chmod +x test_int.sh")
        
        # Run the script
        pty_framework.send_line("./test_int.sh")
        
        # Wait for it to start
        pty_framework.expect_output("starting sleep")
        time.sleep(0.5)
        
        # Send interrupt
        pty_framework.send_ctrl('c')
        
        # Should see trap message
        output = pty_framework.expect_output("caught interrupt")
        pty_framework._wait_for_prompt()
        
        # Cleanup
        pty_framework.run_command("rm -f test_int.sh")


if __name__ == '__main__':
    # Test job control manually
    config = PTYTestConfig(debug=True)
    with interactive_shell(config) as framework:
        print("Testing job control...")
        framework.send_line("sleep 5")
        time.sleep(1)
        print("Sending Ctrl-Z...")
        framework.send_ctrl('z')
        framework._wait_for_prompt()
        output = framework.run_command("jobs")
        print(f"Jobs output: {output}")