"""
Function operations support for the PSH executor.

This module handles function definition and execution operations.
"""

from typing import List, Optional, TYPE_CHECKING
import sys

from ..builtins.function_support import FunctionReturn
from ..core.exceptions import UnboundVariableError

if TYPE_CHECKING:
    from ..shell import Shell
    from ..ast_nodes import FunctionDef, Redirect
    from ..core.function_manager import FunctionManager
    from .context import ExecutionContext
    from ..visitor.base import ASTVisitor


class FunctionOperationExecutor:
    """
    Handles function definition and execution.
    
    This class encapsulates logic for:
    - Function definition
    - Function execution (will be implemented in Phase 7)
    - Function scope management
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize the function operation executor with a shell instance."""
        self.shell = shell
        self.function_manager = shell.function_manager
    
    def execute_function_def(self, node: 'FunctionDef') -> int:
        """
        Define a function.
        
        Args:
            node: The FunctionDef AST node
            
        Returns:
            Exit status code (0 for success)
        """
        self.function_manager.define_function(node.name, node.body)
        return 0
    
    def execute_function_call(self, name: str, args: List[str], 
                             context: 'ExecutionContext',
                             visitor: 'ASTVisitor[int]',
                             redirects: Optional[List['Redirect']] = None) -> int:
        """
        Execute a function call.
        
        Args:
            name: Function name
            args: Function arguments (including $0)
            context: Execution context
            visitor: The visitor to use for executing the function body
            redirects: Optional redirections to apply
            
        Returns:
            Exit status code
        """
        func = self.function_manager.get_function(name)
        if not func:
            return 127  # Command not found
        
        # Extract the actual body from the Function object
        func_body = func.body
        
        # Save current context
        old_function = context.current_function
        old_positional_params = self.shell.state.positional_params[:]
        
        
        # Set up function context
        context.current_function = name
        
        # Set up positional parameters ($1, $2, etc.)
        # Note: $0 is handled separately by state.script_name
        self.shell.state.positional_params = args
        
        # Save old script name and set it to function name for $0
        old_script_name = self.shell.state.script_name
        self.shell.state.script_name = name
        
        # Handle special variables
        self.shell.state.set_variable('#', str(len(args)))
        self.shell.state.set_variable('@', args)
        self.shell.state.set_variable('*', ' '.join(args) if args else '')
        
        # Push function onto stack for return builtin
        self.shell.state.function_stack.append(name)
        
        try:
            # Execute function body
            exit_code = visitor.visit(func_body)
            return exit_code
        except FunctionReturn as fr:
            # Handle return statement
            return fr.exit_code
        except UnboundVariableError:
            # Let unbound variable errors propagate
            raise
        except Exception as e:
            print(f"psh: {name}: {e}", file=sys.stderr)
            return 1
        finally:
            # Pop function from stack
            if self.shell.state.function_stack:
                self.shell.state.function_stack.pop()
            
            # Restore context
            context.current_function = old_function
            self.shell.state.positional_params = old_positional_params
            self.shell.state.script_name = old_script_name
            
            # Restore special variables
            if old_positional_params:
                self.shell.state.set_variable('#', str(len(old_positional_params) - 1))
                self.shell.state.set_variable('@', old_positional_params[1:])
                self.shell.state.set_variable('*', ' '.join(old_positional_params[1:]))
            else:
                self.shell.state.set_variable('#', '0')
                self.shell.state.set_variable('@', [])
                self.shell.state.set_variable('*', '')