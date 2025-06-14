"""Compatibility helpers for tests to work with both capsys and CaptureShell."""

import sys
from io import StringIO


class CaptureCompat:
    """Wrapper that provides capsys-like interface for CaptureShell."""
    
    def __init__(self, shell):
        self.shell = shell
    
    def readouterr(self):
        """Read captured output and clear buffers, like capsys.readouterr()."""
        stdout, stderr = self.shell.get_captured_output()
        self.shell.clear_captured_output()
        
        # Return an object with .out and .err attributes like capsys
        class CapturedOutput:
            def __init__(self, out, err):
                self.out = out
                self.err = err
        
        return CapturedOutput(stdout, stderr)


def get_capture(shell, capsys):
    """
    Get a capture object that works with both old and new test methods.
    
    If shell has capture methods (CaptureShell), use those.
    Otherwise fall back to capsys.
    """
    if hasattr(shell, 'get_captured_output'):
        return CaptureCompat(shell)
    else:
        return capsys