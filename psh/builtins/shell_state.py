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
            # Check for -c flag to clear history
            if args[1] == '-c':
                shell.history.clear()
                return 0
            
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
        return """history: history [n] | history -c
    
    Display the command history list with line numbers.
    
    Options:
      n     Show only the last n entries
      -c    Clear the history list
    
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
        
        # Parse options and arguments
        options, positional = self._parse_options(args[1:], shell)
        if options is None:
            return 1  # Error already printed
        
        # If no arguments, just return success (bash behavior)
        if not positional:
            return 0
        
        # Build attributes from options
        from ..core.variables import VarAttributes
        attributes = VarAttributes.NONE
        if options['readonly']:
            attributes |= VarAttributes.READONLY
        if options['export']:
            attributes |= VarAttributes.EXPORT
        if options['integer']:
            attributes |= VarAttributes.INTEGER
        if options['lowercase']:
            attributes |= VarAttributes.LOWERCASE
        if options['uppercase']:
            attributes |= VarAttributes.UPPERCASE
        if options['array']:
            attributes |= VarAttributes.ARRAY
        if options['assoc_array']:
            attributes |= VarAttributes.ASSOC_ARRAY
        
        # Process each argument
        for arg in positional:
            if '=' in arg:
                # Variable with assignment: local var=value
                var_name, var_value = arg.split('=', 1)
                
                # Check if this is an array assignment: var=(value1 value2 ...)
                if var_value.startswith('(') and var_value.endswith(')'):
                    # Parse array initialization
                    from ..core.variables import IndexedArray, AssociativeArray
                    if attributes & VarAttributes.ASSOC_ARRAY:
                        # Create associative array
                        array = AssociativeArray()
                        assoc_values = self._parse_assoc_array_init(var_value, shell)
                        for key, val in assoc_values:
                            array.set(key, val)
                        shell.state.scope_manager.create_local(var_name, array, attributes | VarAttributes.ASSOC_ARRAY)
                    else:
                        # Create indexed array
                        array = IndexedArray()
                        array_values = self._parse_array_init(var_value, shell)
                        for i, val in enumerate(array_values):
                            array.set(i, val)
                        shell.state.scope_manager.create_local(var_name, array, attributes | VarAttributes.ARRAY)
                else:
                    # Regular variable assignment
                    # Expand variables in the value
                    if '$' in var_value:
                        from ..expansion.variable import VariableExpander
                        expander = VariableExpander(shell)
                        var_value = expander.expand_string_variables(var_value)
                    
                    # Apply attribute transformations
                    var_value = self._apply_attributes(var_value, attributes, shell)
                    
                    # Create local variable with value and attributes
                    shell.state.scope_manager.create_local(var_name, var_value, attributes)
            else:
                # Variable without assignment: local var
                if attributes & VarAttributes.ARRAY:
                    # Create empty indexed array
                    from ..core.variables import IndexedArray
                    shell.state.scope_manager.create_local(arg, IndexedArray(), attributes)
                elif attributes & VarAttributes.ASSOC_ARRAY:
                    # Create empty associative array
                    from ..core.variables import AssociativeArray
                    shell.state.scope_manager.create_local(arg, AssociativeArray(), attributes)
                else:
                    # Creates unset local variable (shadows global but has no value)
                    shell.state.scope_manager.create_local(arg, "", attributes)
        
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
    
    def _parse_options(self, args: List[str], shell: 'Shell') -> tuple:
        """Parse local options and return (options_dict, positional_args)."""
        options = {
            'array': False,          # -a
            'assoc_array': False,    # -A
            'integer': False,        # -i
            'lowercase': False,      # -l
            'readonly': False,       # -r
            'uppercase': False,      # -u
            'export': False,         # -x
        }
        positional = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '--':  # End of options
                positional.extend(args[i+1:])
                break
            elif arg.startswith('-') and len(arg) > 1 and not arg[1].isdigit():
                # Process flags
                for flag in arg[1:]:
                    if flag == 'a':
                        options['array'] = True
                    elif flag == 'A':
                        options['assoc_array'] = True
                    elif flag == 'i':
                        options['integer'] = True
                    elif flag == 'l':
                        options['lowercase'] = True
                    elif flag == 'r':
                        options['readonly'] = True
                    elif flag == 'u':
                        options['uppercase'] = True
                    elif flag == 'x':
                        options['export'] = True
                    else:
                        self.error(f"invalid option: -{flag}", shell)
                        return None, []
            else:
                positional.append(arg)
            i += 1
        
        return options, positional
    
    def _parse_assoc_array_init(self, value: str, shell: 'Shell') -> List[tuple]:
        """Parse associative array initialization: ([key]=val [key2]=val2)"""
        # Remove parentheses
        content = value[1:-1].strip()
        if not content:
            return []
        
        # Simple parsing for now
        result = []
        parts = content.split()
        for part in parts:
            if '=' in part and part.startswith('['):
                key_part, val = part.split('=', 1)
                key = key_part[1:-1]  # Remove [ and ]
                # Remove quotes if present
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                result.append((key, val))
        return result
    
    def _apply_attributes(self, value: str, attributes, shell: 'Shell') -> str:
        """Apply attribute transformations to value."""
        from ..core.variables import VarAttributes
        
        if attributes & VarAttributes.UPPERCASE:
            return value.upper()
        elif attributes & VarAttributes.LOWERCASE:
            return value.lower()
        elif attributes & VarAttributes.INTEGER:
            # Evaluate arithmetic expression
            try:
                # Use shell's arithmetic evaluator
                from ..arithmetic import evaluate_arithmetic
                result = evaluate_arithmetic(value, shell)
                return str(result)
            except Exception:
                # Fall back to simple int conversion
                try:
                    return str(int(value))
                except:
                    return "0"
        return value
    
    @property
    def help(self) -> str:
        return """local: local [-aAilrux] [name[=value] ...]
    
    Create local variables within functions.
    
    Options:
      -a    Declare indexed array variables
      -A    Declare associative array variables  
      -i    Make variables have the 'integer' attribute
      -l    Convert values to lowercase on assignment
      -r    Make variables readonly
      -u    Convert values to uppercase on assignment
      -x    Make variables export to the environment
    
    When used inside a function, creates variables that are only
    visible within that function. Without an assignment, the variable
    is created but unset.
    
    Examples:
        local var              # Create unset local variable
        local var=value        # Create local with value
        local -i num=42        # Create local integer variable
        local -u text=hello    # Create local uppercase variable
        local x=1 y=2 z        # Multiple variables
    
    Note: Using 'local' outside a function is an error."""