"""
Test executor visitor with output capture capabilities.

This visitor extends ExecutorVisitor to provide better output capture
for testing purposes, avoiding the limitations of fork-based execution.
"""

import io
import subprocess
from typing import List, Optional
from contextlib import redirect_stdout, redirect_stderr
from .executor_visitor import ExecutorVisitor


class TestExecutorVisitor(ExecutorVisitor):
    """
    Executor visitor that captures output for testing.
    
    This visitor modifies execution behavior to capture output that would
    normally go directly to file descriptors in forked processes.
    """
    
    def __init__(self, shell: 'Shell', capture_mode: bool = True):
        """
        Initialize test executor.
        
        Args:
            shell: The shell instance
            capture_mode: Whether to capture output (default True)
        """
        super().__init__(shell)
        self.capture_mode = capture_mode
        self.captured_stdout: List[str] = []
        self.captured_stderr: List[str] = []
        
        # Override shell stdout/stderr for builtin capture
        if capture_mode:
            self._original_stdout = shell.stdout
            self._original_stderr = shell.stderr
            self._stdout_buffer = io.StringIO()
            self._stderr_buffer = io.StringIO()
            shell.stdout = self._stdout_buffer
            shell.stderr = self._stderr_buffer
    
    def get_stdout(self) -> str:
        """Get captured stdout as a string."""
        # Combine captured output from external commands and buffer
        result = []
        
        # Add any buffered output
        if hasattr(self, '_stdout_buffer'):
            buffered = self._stdout_buffer.getvalue()
            if buffered:
                result.append(buffered)
        
        # Add captured external command output
        result.extend(self.captured_stdout)
        
        return ''.join(result)
    
    def get_stderr(self) -> str:
        """Get captured stderr as a string."""
        # Combine captured output from external commands and buffer
        result = []
        
        # Add any buffered output
        if hasattr(self, '_stderr_buffer'):
            buffered = self._stderr_buffer.getvalue()
            if buffered:
                result.append(buffered)
        
        # Add captured external command output
        result.extend(self.captured_stderr)
        
        return ''.join(result)
    
    def reset_capture(self):
        """Reset captured output."""
        self.captured_stdout.clear()
        self.captured_stderr.clear()
        
        if hasattr(self, '_stdout_buffer'):
            self._stdout_buffer.truncate(0)
            self._stdout_buffer.seek(0)
        
        if hasattr(self, '_stderr_buffer'):
            self._stderr_buffer.truncate(0)
            self._stderr_buffer.seek(0)
    
    def __del__(self):
        """Restore original stdout/stderr on cleanup."""
        if hasattr(self, '_original_stdout'):
            self.shell.stdout = self._original_stdout
        if hasattr(self, '_original_stderr'):
            self.shell.stderr = self._original_stderr
    
    def _execute_builtin(self, name: str, args: List[str]) -> int:
        """
        Execute builtin with output capture.
        
        Overrides parent to ensure builtin output goes to our buffers.
        """
        # Builtins will write to shell.stdout/stderr which we've redirected
        return super()._execute_builtin(name, args)
    
    def _execute_external(self, args: List[str], background: bool = False) -> int:
        """
        Execute external command with output capture.
        
        For non-pipeline commands in capture mode, uses subprocess.run
        to capture output instead of fork/exec.
        """
        if self.capture_mode and not self._in_pipeline and not background:
            # Use subprocess for better output capture
            try:
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=30  # Reasonable timeout for tests
                )
                
                # Capture output
                if result.stdout:
                    self.captured_stdout.append(result.stdout)
                if result.stderr:
                    self.captured_stderr.append(result.stderr)
                
                return result.returncode
                
            except subprocess.TimeoutExpired:
                self.captured_stderr.append(f"psh: {args[0]}: command timed out\n")
                return 124  # Standard timeout exit code
            except FileNotFoundError:
                self.captured_stderr.append(f"psh: {args[0]}: command not found\n")
                return 127
            except Exception as e:
                self.captured_stderr.append(f"psh: {args[0]}: {e}\n")
                return 126
        else:
            # Fall back to normal fork/exec for pipelines and background
            return super()._execute_external(args, background)
    
    def visit_Pipeline(self, node) -> int:
        """
        Execute pipeline with subprocess for better output capture.
        
        In capture mode, constructs and executes the pipeline using subprocess
        instead of manual fork/pipe management.
        """
        if self.capture_mode and len(node.commands) > 1:
            # Build shell command string for the pipeline
            pipeline_parts = []
            
            for cmd in node.commands:
                # Simple command to string conversion
                if hasattr(cmd, 'args') and cmd.args:
                    # Quote arguments that contain spaces
                    quoted_args = []
                    for arg in cmd.args:
                        if ' ' in arg or '"' in arg or "'" in arg:
                            quoted_args.append(repr(arg))
                        else:
                            quoted_args.append(arg)
                    pipeline_parts.append(' '.join(quoted_args))
            
            if pipeline_parts:
                # Execute pipeline using shell
                pipeline_str = ' | '.join(pipeline_parts)
                
                try:
                    result = subprocess.run(
                        pipeline_str,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.stdout:
                        self.captured_stdout.append(result.stdout)
                    if result.stderr:
                        self.captured_stderr.append(result.stderr)
                    
                    return result.returncode
                    
                except subprocess.TimeoutExpired:
                    self.captured_stderr.append("psh: pipeline timed out\n")
                    return 124
                except Exception as e:
                    self.captured_stderr.append(f"psh: pipeline error: {e}\n")
                    return 1
        
        # Fall back to normal pipeline execution
        return super().visit_Pipeline(node)