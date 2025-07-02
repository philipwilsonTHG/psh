"""
Command execution module for the PSH executor.

This module handles the execution of simple commands, including:
- Variable assignments
- Command expansion
- Builtin, function, and external command execution
- Redirection handling
"""

import os
import sys
import signal
from typing import List, Tuple, Optional, TYPE_CHECKING
from contextlib import contextmanager

from .strategies import (
    ExecutionStrategy, 
    BuiltinExecutionStrategy,
    FunctionExecutionStrategy,
    ExternalExecutionStrategy
)

if TYPE_CHECKING:
    from ..shell import Shell
    from ..ast_nodes import SimpleCommand, Redirect
    from ..expansion.manager import ExpansionManager
    from ..io_redirect.manager import IOManager
    from ..job_control import JobManager
    from .context import ExecutionContext


class CommandExecutor:
    """
    Handles execution of simple commands.
    
    This class encapsulates all logic for executing SimpleCommand nodes,
    including variable assignments, expansions, and delegating to appropriate
    execution strategies.
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize the command executor with a shell instance."""
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = shell.builtin_registry
        self.function_manager = shell.function_manager
        
        # Initialize execution strategies
        self.strategies = [
            BuiltinExecutionStrategy(),
            FunctionExecutionStrategy(),
            ExternalExecutionStrategy()
        ]
    
    def execute(self, node: 'SimpleCommand', context: 'ExecutionContext') -> int:
        """
        Execute a simple command and return exit status.
        
        Args:
            node: The SimpleCommand AST node to execute
            context: The current execution context
            
        Returns:
            Exit status code
        """
        try:
            # Handle array assignments first
            if node.array_assignments:
                for assignment in node.array_assignments:
                    self._handle_array_assignment(assignment)
            
            # Perform expansions
            expanded_args = self._expand_arguments(node)
            
            if not expanded_args:
                return 0
            
            # Check for variable assignments
            assignments = self._extract_assignments(expanded_args)
            if assignments and len(expanded_args) == len(assignments):
                # Pure assignment (no command)
                return self._handle_pure_assignments(node, assignments)
            
            # Apply assignments for this command
            saved_vars = self._apply_command_assignments(assignments)
            
            try:
                # Remove assignments from args
                command_args = expanded_args[len(assignments):]
                
                if not command_args:
                    return 0
                
                cmd_name = command_args[0]
                cmd_args = command_args[1:]
                
                # Check for empty command after expansion
                if not cmd_name:
                    return 0
                
                # Handle xtrace option
                if self.state.options.get('xtrace'):
                    self._print_xtrace(cmd_name, cmd_args)
                
                # Special handling for exec builtin
                if cmd_name == 'exec':
                    return self._handle_exec_builtin(node, command_args, assignments)
                
                # Execute the command using appropriate strategy
                return self._execute_with_strategy(
                    cmd_name, cmd_args, node, context
                )
                
            finally:
                # Restore variables (unless exported)
                self._restore_command_assignments(saved_vars)
                
        except Exception as e:
            # Import these here to avoid circular imports
            from ..core.exceptions import LoopBreak, LoopContinue, ReadonlyVariableError
            from ..builtins.function_support import FunctionReturn
            
            # Re-raise control flow exceptions
            if isinstance(e, (FunctionReturn, LoopBreak, LoopContinue, SystemExit)):
                raise
            
            # Handle other exceptions
            if isinstance(e, ReadonlyVariableError):
                print(f"psh: {e.name}: readonly variable", file=self.state.stderr)
                return 1
            
            print(f"psh: {e}", file=sys.stderr)
            return 1
    
    def _expand_arguments(self, node: 'SimpleCommand') -> List[str]:
        """Expand all arguments in a command."""
        return self.expansion_manager.expand_arguments(node)
    
    def _extract_assignments(self, args: List[str]) -> List[Tuple[str, str]]:
        """Extract variable assignments from beginning of arguments."""
        assignments = []
        
        for arg in args:
            if '=' in arg and self._is_valid_assignment(arg):
                var, value = arg.split('=', 1)
                assignments.append((var, value))
            else:
                # Stop at first non-assignment
                break
        
        return assignments
    
    def _is_valid_assignment(self, arg: str) -> bool:
        """Check if argument is a valid variable assignment."""
        if '=' not in arg:
            return False
        
        var_name = arg.split('=', 1)[0]
        # Variable name must start with letter or underscore
        if not var_name or not (var_name[0].isalpha() or var_name[0] == '_'):
            return False
        
        # Rest must be alphanumeric or underscore
        return all(c.isalnum() or c == '_' for c in var_name[1:])
    
    def _handle_pure_assignments(self, node: 'SimpleCommand', 
                                assignments: List[Tuple[str, str]]) -> int:
        """Handle pure variable assignments (no command)."""
        # Apply redirections first
        with self._apply_redirections(node.redirects):
            # Handle xtrace for assignments
            if self.state.options.get('xtrace'):
                ps4 = self.state.get_variable('PS4', '+ ')
                for var, value in assignments:
                    trace_line = ps4 + f"{var}={value}\n"
                    self.state.stderr.write(trace_line)
                    self.state.stderr.flush()
            
            # Save the current exit code before expansions
            saved_exit_code = self.state.last_exit_code
            
            for var, value in assignments:
                # Apply all expansions to assignment values
                value = self._expand_assignment_value(value)
                try:
                    self.state.set_variable(var, value)
                except:
                    from ..core.exceptions import ReadonlyVariableError
                    print(f"psh: {var}: readonly variable", file=self.state.stderr)
                    return 1
            
            # Return current exit code (from any command substitutions)
            return self.state.last_exit_code
    
    def _apply_command_assignments(self, assignments: List[Tuple[str, str]]) -> dict:
        """Apply variable assignments for command execution."""
        saved_vars = {}
        
        for var, value in assignments:
            saved_vars[var] = self.state.get_variable(var)
            # Apply all expansions to assignment values
            value = self._expand_assignment_value(value)
            try:
                self.state.set_variable(var, value)
            except:
                from ..core.exceptions import ReadonlyVariableError
                raise ReadonlyVariableError(var)
        
        return saved_vars
    
    def _restore_command_assignments(self, saved_vars: dict):
        """Restore variables after command execution."""
        for var, old_value in saved_vars.items():
            if not self._is_exported(var):
                if old_value is None:
                    self.state.unset_variable(var)
                else:
                    self.state.set_variable(var, old_value)
    
    def _is_exported(self, var_name: str) -> bool:
        """Check if a variable is exported."""
        return var_name in os.environ
    
    def _expand_assignment_value(self, value: str) -> str:
        """Expand a value used in variable assignment."""
        # Handle all expansions in order, without word splitting
        
        # 1. Tilde expansion (only at start)
        if value.startswith('~'):
            value = self.expansion_manager.expand_tilde(value)
        
        # 2. Variable and command substitution expansion
        if '$' in value or '`' in value:
            # This complex expansion logic will use the expansion manager
            # For now, use a simplified version
            value = self.expansion_manager.expand_string_variables(value)
        
        return value
    
    def _print_xtrace(self, cmd_name: str, args: List[str]):
        """Print command trace if xtrace is enabled."""
        ps4 = self.state.get_variable('PS4', '+ ')
        trace_line = ps4 + ' '.join([cmd_name] + args) + '\n'
        self.state.stderr.write(trace_line)
        self.state.stderr.flush()
    
    def _execute_with_strategy(self, cmd_name: str, args: List[str],
                              node: 'SimpleCommand', context: 'ExecutionContext') -> int:
        """Execute command using the appropriate strategy."""
        # Find the right strategy
        for strategy in self.strategies:
            if strategy.can_execute(cmd_name, self.shell):
                # Check if this is a builtin that needs special redirection handling
                if isinstance(strategy, BuiltinExecutionStrategy) and not context.in_pipeline:
                    return self._execute_builtin_with_redirections(
                        cmd_name, args, node, context, strategy
                    )
                else:
                    # Apply normal redirections for other commands or builtins in pipelines
                    with self._apply_redirections(node.redirects):
                        return strategy.execute(
                            cmd_name, args, self.shell, context,
                            node.redirects, node.background
                        )
        
        # Should never reach here as ExternalExecutionStrategy handles everything
        return 127
    
    def _execute_builtin_with_redirections(self, cmd_name: str, args: List[str],
                                          node: 'SimpleCommand', context: 'ExecutionContext',
                                          strategy: ExecutionStrategy) -> int:
        """Execute builtin with special redirection handling."""
        # DEBUG: Log builtin redirection setup
        if self.state.options.get('debug-exec'):
            print(f"DEBUG CommandExecutor: Setting up builtin redirections for '{cmd_name}'", 
                  file=sys.stderr)
            print(f"DEBUG CommandExecutor: Redirections: {[r.type for r in node.redirects]}", 
                  file=sys.stderr)
        
        # Builtins need special redirection handling
        stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup = \
            self.io_manager.setup_builtin_redirections(node)
        try:
            # Update shell streams for builtins that might use them
            self.shell.stdout = sys.stdout
            self.shell.stderr = sys.stderr
            self.shell.stdin = sys.stdin
            
            # Execute builtin
            return strategy.execute(
                cmd_name, args, self.shell, context,
                node.redirects, node.background
            )
        finally:
            self.io_manager.restore_builtin_redirections(
                stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup
            )
            # Reset shell stream references
            # Preserve StringIO objects for test frameworks
            import io
            if not isinstance(self.shell.stdout, io.StringIO):
                self.shell.stdout = sys.stdout
            if not isinstance(self.shell.stderr, io.StringIO):
                self.shell.stderr = sys.stderr
            if not isinstance(self.shell.stdin, io.StringIO):
                self.shell.stdin = sys.stdin
    
    @contextmanager
    def _apply_redirections(self, redirects):
        """Context manager for applying and restoring redirections."""
        if not redirects:
            yield
            return
            
        saved_fds = self.io_manager.apply_redirections(redirects)
        try:
            yield
        finally:
            self.io_manager.restore_redirections(saved_fds)
    
    def _handle_array_assignment(self, assignment):
        """Handle array initialization or element assignment."""
        from ..ast_nodes import ArrayInitialization, ArrayElementAssignment
        from .array import ArrayOperationExecutor
        
        # Create array executor for this operation
        array_executor = ArrayOperationExecutor(self.shell)
        
        if isinstance(assignment, ArrayInitialization):
            return array_executor.execute_array_initialization(assignment)
        elif isinstance(assignment, ArrayElementAssignment):
            return array_executor.execute_array_element_assignment(assignment)
        else:
            return 0
    
    def _handle_exec_builtin(self, node: 'SimpleCommand', command_args: List[str], 
                            assignments: List[tuple]) -> int:
        """Handle exec builtin with access to redirections."""
        # Exec builtin handling is complex and will be fully implemented
        # when we have the complete external execution strategy
        raise NotImplementedError("Exec builtin will be implemented with external execution")