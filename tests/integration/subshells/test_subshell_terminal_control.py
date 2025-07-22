"""Test subshell terminal control handling.

This test ensures that subshells properly handle terminal control groups
to prevent I/O errors when returning to the parent shell.
"""

import os
import sys
import subprocess
import pytest


class TestSubshellTerminalControl:
    """Test terminal control handling for subshells."""
    
    def test_subshell_terminal_control_in_interactive_mode(self):
        """Test that subshell execution doesn't cause I/O errors in interactive mode.
        
        This test verifies the fix for the issue where running a subshell like
        (echo hello) would cause "psh: fatal: [Errno 5] Input/output error" when
        the parent shell tried to read the next command.
        """
        # Create a test script that runs psh interactively
        test_script = """(echo "Hello from subshell")
echo "Shell is still responsive"
exit
"""
        
        # Get the path to the psh module
        psh_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env = os.environ.copy()
        env['PYTHONPATH'] = psh_path
        
        try:
            # Run psh interactively
            proc = subprocess.Popen(
                [sys.executable, '-m', 'psh'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Send commands
            stdout, stderr = proc.communicate(test_script, timeout=5)
            
            # Check for the fatal I/O error that used to occur
            assert "psh: fatal: [Errno 5] Input/output error" not in stderr, \
                "Subshell execution caused I/O error in parent shell"
            
            # Check expected output
            assert "Hello from subshell" in stdout, \
                "Subshell output not found"
            assert "Shell is still responsive" in stdout, \
                "Parent shell did not execute command after subshell"
            
            # Verify clean exit
            assert proc.returncode == 0, \
                f"Shell exited with error code {proc.returncode}"
                
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Shell command timed out - possible terminal control issue")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    def test_nested_subshells_terminal_control(self):
        """Test that nested subshells handle terminal control properly."""
        test_script = """(echo "Outer")
(echo "Inner")
echo "Still working"
exit
"""
        
        psh_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env = os.environ.copy()
        env['PYTHONPATH'] = psh_path
        
        try:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'psh'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            stdout, stderr = proc.communicate(test_script, timeout=5)
            
            # Debug output
            if not stdout or "Outer" not in stdout:
                print(f"STDOUT: {repr(stdout)}")
                print(f"STDERR: {repr(stderr)}")
            
            # Check no I/O errors
            assert "psh: fatal: [Errno 5] Input/output error" not in stderr
            
            # Check output
            assert "Outer" in stdout
            assert "Inner" in stdout
            assert "Still working" in stdout
            
            assert proc.returncode == 0
            
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Nested subshells caused timeout")
    
    def test_subshell_with_complex_commands(self):
        """Test subshells with pipelines and other complex commands."""
        test_script = """(echo hello | tr a-z A-Z)
echo "After pipeline subshell"
(for i in 1 2 3; do echo $i; done)
echo "After loop subshell"
exit
"""
        
        psh_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env = os.environ.copy()
        env['PYTHONPATH'] = psh_path
        
        try:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'psh'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            stdout, stderr = proc.communicate(test_script, timeout=5)
            
            # Check no I/O errors
            assert "psh: fatal: [Errno 5] Input/output error" not in stderr
            
            # Check outputs
            assert "HELLO" in stdout  # Pipeline worked
            assert "After pipeline subshell" in stdout
            assert "1\n2\n3" in stdout.replace("After pipeline subshell\n", "")  # Loop worked
            assert "After loop subshell" in stdout
            
            assert proc.returncode == 0
            
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Complex subshells caused timeout")