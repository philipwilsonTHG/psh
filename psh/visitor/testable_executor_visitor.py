"""
Testable executor visitor that captures output for testing.

This visitor extends ExecutorVisitor to provide output capture capabilities
that work even with forked processes, enabling proper testing.
"""

import os
import sys
import subprocess
import tempfile
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .executor_visitor import ExecutorVisitor
from ..ast_nodes import SimpleCommand


class TestableExecutor(ExecutorVisitor):
    """
    Executor visitor with output capture for testing.
    
    This visitor modifies execution behavior to capture output from
    forked processes and builtins, making it suitable for pytest testing.
    """
    
    def __init__(self, shell: 'Shell', capture_output: bool = True):
        """
        Initialize testable executor.
        
        Args:
            shell: The shell instance
            capture_output: Whether to capture output (default True)
        """
        super().__init__(shell)
        self.capture_output = capture_output
        self.captured_stdout: List[str] = []
        self.captured_stderr: List[str] = []
        
        # Original stdout/stderr
        self._original_stdout = shell.stdout
        self._original_stderr = shell.stderr
        
        # Temporary files for capturing forked process output
        self._stdout_file = None
        self._stderr_file = None
        
        if self.capture_output:
            self._setup_capture_files()
    
    def _setup_capture_files(self):
        """Set up temporary files for output capture."""
        self._stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self._stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    
    def _cleanup_capture_files(self):
        """Clean up temporary files."""
        if self._stdout_file:
            try:
                self._stdout_file.close()
                os.unlink(self._stdout_file.name)
            except:
                pass
        if self._stderr_file:
            try:
                self._stderr_file.close()
                os.unlink(self._stderr_file.name)
            except:
                pass
    
    def __del__(self):
        """Cleanup on deletion."""
        self._cleanup_capture_files()
    
    def _execute_external(self, args: List[str], background: bool = False) -> int:
        """Execute an external command with output capture."""
        if not self.capture_output or self._in_pipeline:
            # Use normal execution if not capturing or in pipeline
            return super()._execute_external(args, background)
        
        # Use subprocess for output capture
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=False
            )
            
            # Capture output
            if result.stdout:
                self.captured_stdout.append(result.stdout)
                # Also write to shell's stdout for compatibility
                self.shell.stdout.write(result.stdout)
                self.shell.stdout.flush()
            
            if result.stderr:
                self.captured_stderr.append(result.stderr)
                # Also write to shell's stderr for compatibility
                self.shell.stderr.write(result.stderr)
                self.shell.stderr.flush()
            
            return result.returncode
            
        except FileNotFoundError:
            error_msg = f"psh: {args[0]}: command not found\n"
            self.captured_stderr.append(error_msg)
            self.shell.stderr.write(error_msg)
            self.shell.stderr.flush()
            return 127
        except Exception as e:
            error_msg = f"psh: {args[0]}: {e}\n"
            self.captured_stderr.append(error_msg)
            self.shell.stderr.write(error_msg)
            self.shell.stderr.flush()
            return 126
    
    def _execute_builtin(self, name: str, args: List[str]) -> int:
        """Execute a builtin command with output capture."""
        if not self.capture_output:
            return super()._execute_builtin(name, args)
        
        # Temporarily override shell's stdout/stderr to capture builtin output
        from io import StringIO
        
        capture_stdout = StringIO()
        capture_stderr = StringIO()
        
        # Save original streams
        orig_stdout = self.shell.stdout
        orig_stderr = self.shell.stderr
        
        # Override streams
        self.shell.stdout = capture_stdout
        self.shell.stderr = capture_stderr
        
        try:
            # Execute builtin
            exit_code = super()._execute_builtin(name, args)
            
            # Capture output
            stdout_content = capture_stdout.getvalue()
            stderr_content = capture_stderr.getvalue()
            
            if stdout_content:
                self.captured_stdout.append(stdout_content)
                # Write to original stdout
                orig_stdout.write(stdout_content)
                orig_stdout.flush()
            
            if stderr_content:
                self.captured_stderr.append(stderr_content)
                # Write to original stderr
                orig_stderr.write(stderr_content)
                orig_stderr.flush()
            
            return exit_code
            
        finally:
            # Restore original streams
            self.shell.stdout = orig_stdout
            self.shell.stderr = orig_stderr
    
    def get_captured_output(self) -> Dict[str, str]:
        """
        Get all captured output.
        
        Returns:
            Dict with 'stdout' and 'stderr' keys containing captured output
        """
        return {
            'stdout': ''.join(self.captured_stdout),
            'stderr': ''.join(self.captured_stderr)
        }
    
    def clear_captured_output(self):
        """Clear captured output buffers."""
        self.captured_stdout.clear()
        self.captured_stderr.clear()
    
    @contextmanager
    def capture_context(self):
        """
        Context manager for capturing output.
        
        Usage:
            with executor.capture_context():
                executor.visit(ast)
            output = executor.get_captured_output()
        """
        # Clear previous captures
        self.clear_captured_output()
        
        try:
            yield self
        finally:
            # Ensure files are flushed
            if self._stdout_file:
                self._stdout_file.flush()
            if self._stderr_file:
                self._stderr_file.flush()