"""
Subshell and brace group execution support for the PSH executor.

This module handles execution of subshells and brace groups with proper
process isolation and environment management.
"""

import os
import sys
from typing import List, TYPE_CHECKING
from contextlib import contextmanager

if TYPE_CHECKING:
    from ..shell import Shell
    from ..ast_nodes import SubshellGroup, BraceGroup, Redirect
    from .context import ExecutionContext
    from ..visitor.base import ASTVisitor
    from ..job_control import Job, JobManager
    from ..io_manager import IOManager


class SubshellExecutor:
    """
    Handles subshell and brace group execution.
    
    This class encapsulates logic for:
    - Subshell execution with process isolation
    - Brace group execution in current shell
    - Background execution of both constructs
    - Proper job control integration
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize the subshell executor with a shell instance."""
        self.shell = shell
        self.state = shell.state
        self.job_manager = shell.job_manager
        self.io_manager = shell.io_manager
    
    @contextmanager
    def _apply_redirections(self, redirects: List['Redirect']):
        """Context manager for applying and restoring redirections."""
        if not redirects:
            yield
            return
            
        saved_fds = self.io_manager.apply_redirections(redirects)
        try:
            yield
        finally:
            self.io_manager.restore_redirections(saved_fds)
    
    def execute_subshell(self, node: 'SubshellGroup', context: 'ExecutionContext',
                        visitor: 'ASTVisitor[int]') -> int:
        """
        Execute subshell group (...) in isolated environment.
        
        Args:
            node: The SubshellGroup AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        return self._execute_in_subshell(node.statements, node.redirects, node.background)
    
    def execute_brace_group(self, node: 'BraceGroup', context: 'ExecutionContext',
                           visitor: 'ASTVisitor[int]') -> int:
        """
        Execute brace group {...} in current shell environment.
        
        Key differences from subshells:
        - No fork() - executes in current process
        - Variable assignments persist
        - Directory changes persist
        - More efficient (no subprocess overhead)
        
        Args:
            node: The BraceGroup AST node
            context: Current execution context
            visitor: Visitor for executing child nodes
            
        Returns:
            Exit status code
        """
        # Save pipeline context
        old_pipeline = context.in_pipeline
        context.in_pipeline = False
        
        try:
            # Apply redirections
            with self._apply_redirections(node.redirects):
                # Execute statements in current environment
                exit_code = visitor.visit(node.statements)
                
                # Handle background execution
                if node.background:
                    # For background brace groups, we need to fork
                    # Only the execution needs to be backgrounded
                    return self._execute_background_brace_group(node, visitor)
                
                return exit_code
        finally:
            context.in_pipeline = old_pipeline
    
    def _execute_in_subshell(self, statements, redirects: List['Redirect'], background: bool) -> int:
        """Execute statements in an isolated subshell environment."""
        if background:
            # Handle background subshell - for now, treat as foreground
            # TODO: Implement proper background job management for subshells
            pass
        
        # Execute in foreground subshell with proper isolation
        return self._execute_foreground_subshell(statements, redirects)
    
    def _execute_foreground_subshell(self, statements, redirects: List['Redirect']) -> int:
        """Execute subshell in foreground with proper isolation."""
        pid = os.fork()
        
        if pid == 0:
            # Child process - create isolated shell
            try:
                # Create new process group for the subshell
                os.setpgid(0, 0)
                
                # Import Shell here to avoid circular import
                from ..shell import Shell
                
                # Create new shell instance with copied environment
                subshell = Shell(
                    debug_ast=self.shell.state.debug_ast,
                    debug_tokens=self.shell.state.debug_tokens,
                    parent_shell=self.shell,  # Copy variables/functions
                    norc=True
                )
                subshell.state._in_forked_child = True
                
                # Inherit I/O streams from parent shell for test compatibility
                subshell.stdout = self.shell.stdout
                subshell.stderr = self.shell.stderr
                subshell.stdin = self.shell.stdin
                
                # Apply redirections if any
                saved_fds = None
                if redirects:
                    saved_fds = subshell.io_manager.apply_redirections(redirects)
                
                # Execute statements in isolated environment  
                exit_code = subshell.execute_command_list(statements)
                os._exit(exit_code)
                
            except SystemExit as e:
                # Handle explicit exit calls
                os._exit(e.code if e.code is not None else 0)
            except Exception as e:
                print(f"psh: subshell error: {e}", file=sys.stderr)
                os._exit(1)
        else:
            # Parent process - use job manager to wait for child
            try:
                # Set the child's process group 
                os.setpgid(pid, pid)
            except OSError:
                # Race condition - child may have already done it
                pass
            
            # Create job for tracking the subshell
            job = self.job_manager.create_job(pid, "<subshell>")
            job.add_process(pid, "subshell")
            job.foreground = True
            
            # Use job manager to wait (handles SIGCHLD properly)
            exit_status = self.job_manager.wait_for_job(job)
            
            # Clean up job
            if job.state.name == 'DONE':
                self.job_manager.remove_job(job.job_id)
            
            return exit_status
    
    def _execute_background_brace_group(self, node: 'BraceGroup', 
                                       visitor: 'ASTVisitor[int]') -> int:
        """
        Execute brace group in background.
        
        Note: Background execution requires forking, but the brace group
        semantics are preserved within the forked process.
        """
        pid = os.fork()
        
        if pid == 0:
            # Child process
            try:
                # Create new process group
                os.setpgid(0, 0)
                
                # Execute the brace group in current environment (no new shell)
                # Apply redirections first
                saved_fds = None
                if node.redirects:
                    saved_fds = self.io_manager.apply_redirections(node.redirects)
                
                try:
                    exit_code = visitor.visit(node.statements)
                    os._exit(exit_code)
                finally:
                    # Restore file descriptors if they were saved
                    if saved_fds:
                        self.io_manager.restore_redirections(saved_fds)
                        
            except Exception as e:
                print(f"psh: background brace group error: {e}", file=sys.stderr)
                os._exit(1)
        else:
            # Parent process
            # Register background job
            self.job_manager.add_job(pid, str(node), background=True)
            return 0