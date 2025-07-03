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

from ..executor import ExecutorVisitor
from ..ast_nodes import SimpleCommand, Redirect


class MockExecutorVisitor(ExecutorVisitor):
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
            # Replace the external execution strategy with our capturing version
            self._replace_external_strategy()
    
    def _setup_capture_files(self):
        """Set up temporary files for output capture."""
        self._stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self._stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    
    def _replace_external_strategy(self):
        """Replace the external execution strategy with a capturing version."""
        from ..executor.strategies import ExternalExecutionStrategy
        
        # Create our capturing external strategy
        capturing_strategy = CapturingExternalStrategy(self)
        
        # Replace the external strategy in the command executor
        for i, strategy in enumerate(self.command_executor.strategies):
            if isinstance(strategy, ExternalExecutionStrategy):
                self.command_executor.strategies[i] = capturing_strategy
                break
    
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
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> int:
        """Execute a simple command with proper stream preservation."""
        if not self.capture_output:
            return super().visit_SimpleCommand(node)
        
        # Save the current shell streams (which might be StringIO from tests)
        saved_stdout = self.shell.stdout
        saved_stderr = self.shell.stderr
        saved_stdin = self.shell.stdin
        
        # Also temporarily replace sys.stdout/stderr/stdin to prevent
        # the parent class from resetting shell streams to them
        saved_sys_stdout = sys.stdout
        saved_sys_stderr = sys.stderr  
        saved_sys_stdin = sys.stdin
        
        # If we have StringIO streams, use them as sys streams temporarily
        if hasattr(saved_stdout, 'write') and hasattr(saved_stdout, 'getvalue'):
            sys.stdout = saved_stdout
        if hasattr(saved_stderr, 'write') and hasattr(saved_stderr, 'getvalue'):
            sys.stderr = saved_stderr
        if hasattr(saved_stdin, 'read'):
            sys.stdin = saved_stdin
        
        try:
            # Execute the command
            result = super().visit_SimpleCommand(node)
            
            return result
        finally:
            # Restore sys streams
            sys.stdout = saved_sys_stdout
            sys.stderr = saved_sys_stderr
            sys.stdin = saved_sys_stdin
            
            # Always restore shell streams
            self.shell.stdout = saved_stdout
            self.shell.stderr = saved_stderr
            self.shell.stdin = saved_stdin
    
    def _execute_external(self, args: List[str], background: bool = False, redirects: List[Redirect] = None) -> int:
        """Execute an external command with output capture."""
        if not self.capture_output or self._in_pipeline:
            # Use normal execution if not capturing or in pipeline
            return super()._execute_external(args, background, redirects)
        
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
        
        # Just execute the builtin - the visit_SimpleCommand method
        # will preserve any StringIO streams set by tests
        exit_code = super()._execute_builtin(name, args)
        
        return exit_code
    
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


class CapturingExternalStrategy:
    """External execution strategy that captures output for testing."""
    
    def __init__(self, mock_executor: MockExecutorVisitor):
        self.mock_executor = mock_executor
    
    def can_execute(self, cmd_name: str, shell: 'Shell') -> bool:
        """External commands are the fallback - always return True."""
        return True
    
    def execute(self, cmd_name: str, args: List[str], 
                shell: 'Shell', context,
                redirects: Optional[List['Redirect']] = None,
                background: bool = False) -> int:
        """Execute an external command with output capture."""
        full_args = [cmd_name] + args
        
        if context.in_pipeline:
            # In pipeline, we still need to use the original strategy
            # as pipelines require actual processes
            from ..executor.strategies import ExternalExecutionStrategy
            original_strategy = ExternalExecutionStrategy()
            return original_strategy.execute(cmd_name, args, shell, context, redirects, background)
        
        # Use subprocess for output capture
        try:
            result = subprocess.run(
                full_args,
                capture_output=True,
                text=True,
                shell=False,
                env=shell.env
            )
            
            # Capture output
            if result.stdout:
                self.mock_executor.captured_stdout.append(result.stdout)
                # Also write to shell's stdout for compatibility
                shell.stdout.write(result.stdout)
                shell.stdout.flush()
            
            if result.stderr:
                self.mock_executor.captured_stderr.append(result.stderr)
                # Also write to shell's stderr for compatibility
                shell.stderr.write(result.stderr)
                shell.stderr.flush()
            
            return result.returncode
            
        except FileNotFoundError:
            error_msg = f"psh: {cmd_name}: command not found\n"
            self.mock_executor.captured_stderr.append(error_msg)
            shell.stderr.write(error_msg)
            shell.stderr.flush()
            return 127
        except Exception as e:
            error_msg = f"psh: {cmd_name}: {e}\n"
            self.mock_executor.captured_stderr.append(error_msg)
            shell.stderr.write(error_msg)
            shell.stderr.flush()
            return 126