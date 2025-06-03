"""Single command execution."""
import os
import sys
from typing import List, Optional
from ..ast_nodes import Command
from .base import ExecutorComponent
from ..builtins.function_support import FunctionReturn

class CommandExecutor(ExecutorComponent):
    """Executes single commands (builtins, functions, or external)."""
    
    def execute(self, command: Command) -> int:
        """Execute a single command and return exit status."""
        # Handle empty command
        if not command.args:
            return 0
        
        # Expand arguments
        expanded_args = self.expansion_manager.expand_arguments(command)
        
        # Handle variable assignments
        if self._is_variable_assignment(expanded_args):
            return self._handle_variable_assignment(expanded_args)
        
        # Get command name
        cmd_name = expanded_args[0]
        
        # Check if it's a function
        if self.is_function(cmd_name):
            return self._execute_function(cmd_name, expanded_args[1:], command)
        
        # Check if it's a builtin
        if self.is_builtin(cmd_name):
            return self._execute_builtin(cmd_name, expanded_args, command)
        
        # Execute external command
        return self._execute_external(expanded_args, command)
    
    def _is_variable_assignment(self, args: List[str]) -> bool:
        """Check if command is a variable assignment."""
        if not args or '=' not in args[0] or args[0].startswith('='):
            return False
        
        # Check if all leading arguments are assignments
        for arg in args:
            if '=' not in arg:
                return False
        return True
    
    def _handle_variable_assignment(self, args: List[str]) -> int:
        """Handle variable assignment."""
        for arg in args:
            name, value = arg.split('=', 1)
            # Validate variable name
            if not name or not name[0].isalpha() and name[0] != '_':
                print(f"psh: {name}: not a valid identifier", file=sys.stderr)
                return 1
            if not all(c.isalnum() or c == '_' for c in name):
                print(f"psh: {name}: not a valid identifier", file=sys.stderr)
                return 1
            self.state.set_variable(name, value)
        return 0
    
    def _execute_function(self, name: str, args: List[str], command: Command) -> int:
        """Execute a shell function."""
        # For now, delegate back to shell's execute_function
        # This will be properly implemented when we have all components
        func = self.function_manager.get_function(name)
        if func:
            # Build full args list for shell method
            full_args = [name] + args
            return self.shell._execute_function(func, full_args, command)
        return 127  # Command not found
    
    def _execute_builtin(self, name: str, args: List[str], command: Command) -> int:
        """Execute a builtin command."""
        # Set up redirections for builtin
        stdin_backup, stdout_backup, stderr_backup = \
            self.io_manager.setup_builtin_redirections(command)
        
        try:
            # Get builtin
            builtin_class = self.builtin_registry.get_builtin(name)
            builtin = builtin_class(self.shell)
            
            # Execute builtin
            result = builtin.execute(args[1:])
            
            # Update exit code
            self.state.last_exit_code = result
            return result
            
        except FunctionReturn as e:
            # Handle return from function
            self.state.last_exit_code = e.code
            raise
        finally:
            # Restore redirections
            self.io_manager.restore_builtin_redirections(
                stdin_backup, stdout_backup, stderr_backup)
    
    def _execute_external(self, args: List[str], command: Command) -> int:
        """Execute an external command."""
        # For now, delegate back to shell's _execute_external
        # This will be properly implemented in process.py
        return self.shell._execute_external(args, command)