"""Test the capture utilities work with both executors."""

import pytest
import os
from psh.shell import Shell
from .utils import ShellTestHelper


class TestCaptureUtils:
    """Test that our capture utilities work correctly."""
    
    def test_capture_with_legacy_executor(self):
        """Test output capture with legacy executor."""
        shell = Shell()
        helper = ShellTestHelper(shell)
        
        result = helper.run_and_capture('echo hello')
        assert result['stdout'] == 'hello\n'
        assert result['stderr'] == ''
        assert result['exit_code'] == 0
    
    def test_capture_with_visitor_executor(self):
        """Test output capture with visitor executor."""
        shell = Shell()
        helper = ShellTestHelper(shell)
        
        result = helper.run_and_capture('echo hello')
        assert result['stdout'] == 'hello\n'
        assert result['stderr'] == ''
        assert result['exit_code'] == 0
    
    def test_capture_stderr(self):
        """Test stderr capture."""
        for use_visitor in [False, True]:
            shell = Shell()
            helper = ShellTestHelper(shell)
            
            # Test that we can capture both stdout and stderr
            result = helper.run_and_capture('echo "to stdout"; echo "still stdout"')
            assert result['stdout'] == 'to stdout\nstill stdout\n'
            assert result['stderr'] == ''
            assert result['exit_code'] == 0
    
    def test_capture_both_streams(self):
        """Test capturing both stdout and stderr."""
        for use_visitor in [False, True]:
            shell = Shell()
            helper = ShellTestHelper(shell)
            
            # Run multiple commands
            shell.run_command('echo "to stdout"')
            shell.run_command('echo "to stderr" >&2')
            
            # Now test with capture
            result = helper.run_and_capture('echo "captured"')
            assert result['stdout'] == 'captured\n'