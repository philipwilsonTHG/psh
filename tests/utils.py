"""Test utilities for PSH tests."""

import sys
from io import StringIO
from contextlib import contextmanager


@contextmanager
def capture_shell_output(shell):
    """
    Capture output from shell commands.
    
    This works with both legacy and visitor executors by replacing
    the shell's stdout/stderr streams.
    """
    # Save original streams
    original_stdout = shell.stdout
    original_stderr = shell.stderr
    original_state_stdout = shell.state.stdout
    original_state_stderr = shell.state.stderr
    
    # Create capture streams
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    
    try:
        # Replace streams
        shell.stdout = stdout_capture
        shell.stderr = stderr_capture
        shell.state.stdout = stdout_capture
        shell.state.stderr = stderr_capture
        
        # Also replace sys.stdout/stderr for builtins that might use them directly
        old_sys_stdout = sys.stdout
        old_sys_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        yield stdout_capture, stderr_capture
        
    finally:
        # Restore streams
        shell.stdout = original_stdout
        shell.stderr = original_stderr
        shell.state.stdout = original_state_stdout
        shell.state.stderr = original_state_stderr
        sys.stdout = old_sys_stdout
        sys.stderr = old_sys_stderr


class ShellTestHelper:
    """Helper class for testing shell commands with output capture."""
    
    def __init__(self, shell):
        self.shell = shell
    
    def run_and_capture(self, command):
        """Run a command and return captured stdout and stderr."""
        with capture_shell_output(self.shell) as (stdout, stderr):
            exit_code = self.shell.run_command(command)
            return {
                'exit_code': exit_code,
                'stdout': stdout.getvalue(),
                'stderr': stderr.getvalue()
            }
    
    def assert_output(self, command, expected_stdout, expected_stderr=''):
        """Run command and assert output matches expected."""
        result = self.run_and_capture(command)
        assert result['stdout'] == expected_stdout, f"Expected stdout: {repr(expected_stdout)}, got: {repr(result['stdout'])}"
        assert result['stderr'] == expected_stderr, f"Expected stderr: {repr(expected_stderr)}, got: {repr(result['stderr'])}"
        return result['exit_code']