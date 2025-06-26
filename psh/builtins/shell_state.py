"""Shell state related builtins (history, version, local)."""

import sys
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class HistoryBuiltin(Builtin):
    """Display command history."""
    
    @property
    def name(self) -> str:
        return "history"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Display command history."""
        if len(args) > 1:
            try:
                count = int(args[1])
                if count < 0:
                    self.error(f"{args[1]}: invalid option", shell)
                    return 1
            except ValueError:
                self.error(f"{args[1]}: numeric argument required", shell)
                return 1
        else:
            # Default to showing last 10 commands (bash behavior)
            count = 10
        
        # Calculate the starting index
        history = shell.history
        start = max(0, len(history) - count)
        history_slice = history[start:]
        
        # Print with line numbers
        start_num = len(history) - len(history_slice) + 1
        for i, cmd in enumerate(history_slice):
            print(f"{start_num + i:5d}  {cmd}", 
                  file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        
        return 0
    
    @property
    def help(self) -> str:
        return """history: history [n]
    
    Display the command history list with line numbers.
    If n is given, show only the last n entries.
    Default is to show the last 10 commands."""


@builtin
class VersionBuiltin(Builtin):
    """Display version information."""
    
    @property
    def name(self) -> str:
        return "version"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Display version information."""
        from ..version import __version__, get_version_info
        
        if len(args) > 1 and args[1] == '--short':
            # Just print version number
            print(__version__, 
                  file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        else:
            # Full version info
            print(get_version_info(), 
                  file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        
        return 0
    
    @property
    def help(self) -> str:
        return """version: version [--short]
    
    Display version information for Python Shell (psh).
    With --short, display only the version number."""


@builtin
class LocalBuiltin(Builtin):
    """Create local variables within functions."""
    
    @property
    def name(self) -> str:
        return "local"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Create local variables in function scope."""
        # Check if we're in a function
        if not shell.state.scope_manager.is_in_function():
            self.error("can only be used in a function", shell)
            return 1
        
        # If no arguments, just return success (bash behavior)
        if len(args) == 1:
            return 0
        
        # Process each argument
        for arg in args[1:]:
            if '=' in arg:
                # Variable with assignment: local var=value
                var_name, var_value = arg.split('=', 1)
                
                # Check if this is an array assignment: var=(value1 value2 ...)
                if var_value.startswith('(') and var_value.endswith(')'):
                    # Parse array initialization
                    from ..core.variables import IndexedArray, VarAttributes
                    array = IndexedArray()
                    array_values = self._parse_array_init(var_value, shell)
                    for i, val in enumerate(array_values):
                        array.set(i, val)
                    # Create local array variable
                    shell.state.scope_manager.create_local(var_name, array, VarAttributes.ARRAY)
                else:
                    # Regular variable assignment
                    # Expand variables in the value
                    if '$' in var_value:
                        from ..expansion.variable import VariableExpander
                        expander = VariableExpander(shell)
                        var_value = expander.expand_string_variables(var_value)
                    
                    # Create local variable with value
                    shell.state.scope_manager.create_local(var_name, var_value)
            else:
                # Variable without assignment: local var
                # Creates unset local variable (shadows global but has no value)
                shell.state.scope_manager.create_local(arg, "")
        
        return 0
    
    def _parse_array_init(self, value: str, shell: 'Shell') -> List[str]:
        """Parse array initialization: (val1 "val2" val3)"""
        # Remove parentheses
        content = value[1:-1].strip()
        if not content:
            return []
        
        # Use the shell's expansion manager to properly parse quoted strings
        # This handles quotes, variable expansion, and proper word splitting
        from ..expansion.variable import VariableExpander
        expander = VariableExpander(shell)
        
        # Split on whitespace while respecting quotes
        # For now, do simple splitting - a full implementation would use the tokenizer
        import shlex
        try:
            # Use shlex to handle quoted strings properly
            parsed_values = shlex.split(content)
            # Expand variables in each value
            result = []
            for val in parsed_values:
                if '$' in val:
                    expanded = expander.expand_string_variables(val)
                    result.append(expanded)
                else:
                    result.append(val)
            return result
        except ValueError:
            # Fallback to simple splitting if shlex fails
            return content.split()
    
    @property
    def help(self) -> str:
        return """local: local [name[=value] ...]
    
    Create local variables within functions.
    
    When used inside a function, creates variables that are only
    visible within that function. Without an assignment, the variable
    is created but unset.
    
    Examples:
        local var              # Create unset local variable
        local var=value        # Create local with value
        local x=1 y=2 z        # Multiple variables
    
    Note: Using 'local' outside a function is an error."""