"""Function-related builtin commands."""
import sys
from typing import List, TYPE_CHECKING, Optional, Union, Any

from .base import Builtin
from .registry import builtin
from ..utils.shell_formatter import ShellFormatter
from ..core.variables import Variable, VarAttributes, IndexedArray, AssociativeArray
from ..core.exceptions import ReadonlyVariableError

if TYPE_CHECKING:
    from ..shell import Shell


class FunctionReturn(Exception):
    """Exception used to implement the return builtin."""
    def __init__(self, exit_code: int):
        self.exit_code = exit_code
        super().__init__()


@builtin
class DeclareBuiltin(Builtin):
    """Declare variables and functions with attributes."""
    
    @property
    def name(self) -> str:
        return "declare"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the declare builtin."""
        # Parse options
        options, positional = self._parse_options(args[1:], shell)
        if options is None:
            return 1  # Error already printed
        
        # Validate exclusive options
        if options['array'] and options['assoc_array']:
            self.error("cannot use both -a and -A options", shell)
            return 1
        
        # Handle different modes
        if options['functions'] or options['function_names']:
            return self._handle_functions(options, positional, shell)
        elif options['print']:
            return self._print_variables(options, positional, shell)
        else:
            # Pass original args for mutually exclusive attribute handling
            return self._declare_variables(options, positional, shell, args[1:])
    
    def _parse_options(self, args: List[str], shell: 'Shell') -> tuple[Optional[dict], List[str]]:
        """Parse declare options and return (options_dict, positional_args)."""
        options = {
            'array': False,          # -a
            'assoc_array': False,    # -A
            'functions': False,      # -f
            'function_names': False, # -F
            'integer': False,        # -i
            'lowercase': False,      # -l
            'print': False,          # -p
            'readonly': False,       # -r
            'trace': False,          # -t
            'uppercase': False,      # -u
            'export': False,         # -x
            'remove_export': False,  # +x
            'remove_readonly': False,# +r
            'remove_integer': False, # +i
            'remove_lowercase': False,# +l
            'remove_uppercase': False,# +u
            'remove_array': False,   # +a
            'remove_assoc_array': False,# +A
            'remove_trace': False,   # +t
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
                    elif flag == 'f':
                        options['functions'] = True
                    elif flag == 'F':
                        options['function_names'] = True
                    elif flag == 'i':
                        options['integer'] = True
                    elif flag == 'l':
                        options['lowercase'] = True
                    elif flag == 'p':
                        options['print'] = True
                    elif flag == 'r':
                        options['readonly'] = True
                    elif flag == 't':
                        options['trace'] = True
                    elif flag == 'u':
                        options['uppercase'] = True
                    elif flag == 'x':
                        options['export'] = True
                    else:
                        self.error(f"invalid option: -{flag}", shell)
                        return None, []
            elif arg.startswith('+') and len(arg) > 1:
                # Process attribute removal flags
                for flag in arg[1:]:
                    if flag == 'x':
                        options['remove_export'] = True
                    elif flag == 'r':
                        options['remove_readonly'] = True
                    elif flag == 'i':
                        options['remove_integer'] = True
                    elif flag == 'l':
                        options['remove_lowercase'] = True
                    elif flag == 'u':
                        options['remove_uppercase'] = True
                    elif flag == 'a':
                        options['remove_array'] = True
                    elif flag == 'A':
                        options['remove_assoc_array'] = True
                    elif flag == 't':
                        options['remove_trace'] = True
                    else:
                        self.error(f"invalid option: +{flag}", shell)
                        return None, []
            else:
                positional.append(arg)
            i += 1
        
        return options, positional
    
    def _handle_functions(self, options: dict, names: List[str], shell: 'Shell') -> int:
        """Handle function-related options (-f, -F)."""
        stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
        show_names_only = options['function_names']
        
        if not names:
            # List all functions
            functions = shell.function_manager.list_functions()
            if show_names_only:
                # -F flag: show only function names
                for name, _ in sorted(functions):
                    print(f"declare -f {name}", file=stdout)
            else:
                # -f flag: show full definitions
                for name, func in sorted(functions):
                    self._print_function_definition(name, func, stdout)
        else:
            # List specific functions
            exit_code = 0
            for name in names:
                func = shell.function_manager.get_function(name)
                if func:
                    if show_names_only:
                        print(f"declare -f {name}", file=stdout)
                    else:
                        self._print_function_definition(name, func, stdout)
                else:
                    self.error(f"{name}: not found", shell)
                    exit_code = 1
            return exit_code
        return 0
    
    def _declare_variables(self, options: dict, args: List[str], shell: 'Shell', original_args: List[str] = None) -> int:
        """Handle variable declarations."""
        # Build attributes from options
        attributes = VarAttributes.NONE
        if options['readonly']:
            attributes |= VarAttributes.READONLY
        if options['export']:
            attributes |= VarAttributes.EXPORT
        if options['integer']:
            attributes |= VarAttributes.INTEGER
        # Handle mutually exclusive -l and -u (bash ignores both when both are present)
        if options['lowercase'] and options['uppercase']:
            # When both -l and -u are specified, bash ignores both transformations
            # (neither lowercase nor uppercase attribute is applied)
            pass
        elif options['lowercase']:
            attributes |= VarAttributes.LOWERCASE
        elif options['uppercase']:
            attributes |= VarAttributes.UPPERCASE
        if options['array']:
            attributes |= VarAttributes.ARRAY
        if options['assoc_array']:
            attributes |= VarAttributes.ASSOC_ARRAY
        if options['trace']:
            attributes |= VarAttributes.TRACE
        
        # Handle attribute removal
        remove_attrs = VarAttributes.NONE
        if options['remove_export']:
            remove_attrs |= VarAttributes.EXPORT
        if options['remove_readonly']:
            remove_attrs |= VarAttributes.READONLY
        if options['remove_integer']:
            remove_attrs |= VarAttributes.INTEGER
        if options['remove_lowercase']:
            remove_attrs |= VarAttributes.LOWERCASE
        if options['remove_uppercase']:
            remove_attrs |= VarAttributes.UPPERCASE
        if options['remove_array']:
            remove_attrs |= VarAttributes.ARRAY
        if options['remove_assoc_array']:
            remove_attrs |= VarAttributes.ASSOC_ARRAY
        if options['remove_trace']:
            remove_attrs |= VarAttributes.TRACE
        
        # If no arguments, list all shell variables (not environment)
        if not args:
            stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
            # Get all variables with their attributes
            variables = self._get_all_variables_with_attributes(shell)
            
            # If no special options were given, use simple format
            simple_format = not any([
                options['array'], options['assoc_array'], options['export'],
                options['integer'], options['lowercase'], options['uppercase'],
                options['readonly'], options['trace'], options['print']
            ])
            
            for var in sorted(variables, key=lambda v: v.name):
                if simple_format:
                    # Simple format: NAME=value
                    self._print_simple_declaration(var, stdout)
                else:
                    # Full format: declare -flags NAME="value"
                    self._print_declaration(var, stdout)
            return 0
        
        # Process each argument
        for arg in args:
            if '=' in arg:
                # Variable assignment
                name, value = arg.split('=', 1)
                
                # Handle array initialization syntax
                if options['array'] and value.startswith('(') and value.endswith(')'):
                    # Parse indexed array initialization
                    array = IndexedArray()
                    array_values = self._parse_array_init(value)
                    for i, val in enumerate(array_values):
                        array.set(i, val)
                    self._set_variable_with_attributes(shell, name, array, attributes)
                    
                elif options['assoc_array'] and value.startswith('(') and value.endswith(')'):
                    # Parse associative array initialization  
                    array = AssociativeArray()
                    assoc_values = self._parse_assoc_array_init(value)
                    for key, val in assoc_values:
                        array.set(key, val)
                    self._set_variable_with_attributes(shell, name, array, attributes)
                    
                else:
                    # Regular variable assignment
                    # The enhanced scope manager will apply attribute transformations
                    self._set_variable_with_attributes(shell, name, value, attributes)
                    
            else:
                # Just declaring with attributes, no assignment
                if options['array']:
                    # Create empty indexed array
                    self._set_variable_with_attributes(shell, arg, IndexedArray(), attributes)
                elif options['assoc_array']:
                    # Create empty associative array
                    self._set_variable_with_attributes(shell, arg, AssociativeArray(), attributes)
                else:
                    # Apply attributes to existing variable or create new one
                    existing = self._get_variable_with_attributes(shell, arg)
                    if existing:
                        # Apply or remove attributes
                        if remove_attrs:
                            shell.state.scope_manager.remove_attribute(arg, remove_attrs)
                            # If removing export, sync to remove from environment
                            if remove_attrs & VarAttributes.EXPORT:
                                shell.state.scope_manager.sync_exports_to_environment(shell.state.env)
                        if attributes:
                            shell.state.scope_manager.apply_attribute(arg, attributes)
                            # Sync exports if needed
                            if attributes & VarAttributes.EXPORT:
                                shell.state.scope_manager.sync_exports_to_environment(shell.state.env)
                    else:
                        # Create new variable with empty value
                        self._set_variable_with_attributes(shell, arg, "", attributes)
        
        return 0
    
    def _print_variables(self, options: dict, names: List[str], shell: 'Shell') -> int:
        """Print variables with attributes using declare -p format."""
        stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
        
        if names:
            # Print specific variables
            exit_code = 0
            for name in names:
                var = self._get_variable_with_attributes(shell, name)
                if var:
                    self._print_declaration(var, stdout)
                else:
                    self.error(f"{name}: not found", shell)
                    exit_code = 1
            return exit_code
        else:
            # Print all variables that match filter criteria
            variables = self._get_all_variables_with_attributes(shell)
            for var in sorted(variables, key=lambda v: v.name):
                if self._matches_filter(var, options):
                    self._print_declaration(var, stdout)
            return 0
    
    def _print_simple_declaration(self, var: Variable, file):
        """Print variable in simple format (NAME=value)."""
        if isinstance(var.value, (IndexedArray, AssociativeArray)):
            # Arrays can't be shown in simple format, use declare format
            self._print_declaration(var, file)
        else:
            # Simple format without quotes or escaping
            print(f"{var.name}={var.value}", file=file)
    
    def _print_declaration(self, var: Variable, file):
        """Print variable declaration in reusable format."""
        # Build flags string
        flags = []
        if var.attributes & VarAttributes.ARRAY:
            flags.append('a')
        if var.attributes & VarAttributes.ASSOC_ARRAY:
            flags.append('A')  
        if var.attributes & VarAttributes.READONLY:
            flags.append('r')
        if var.attributes & VarAttributes.EXPORT:
            flags.append('x')
        if var.attributes & VarAttributes.INTEGER:
            flags.append('i')
        if var.attributes & VarAttributes.LOWERCASE:
            flags.append('l')
        if var.attributes & VarAttributes.UPPERCASE:
            flags.append('u')
        if var.attributes & VarAttributes.NAMEREF:
            flags.append('n')
        if var.attributes & VarAttributes.TRACE:
            flags.append('t')
        
        flag_str = f"-{''.join(flags)}" if flags else "--"
        
        # Format value
        if isinstance(var.value, IndexedArray):
            # declare -a name=([0]="val" [1]="val")
            elements = []
            for idx in var.value.indices():
                val = var.value.get(idx)
                elements.append(f'[{idx}]="{self._escape_value(val)}"')
            if elements:
                value_str = f"=({' '.join(elements)})"
            else:
                value_str = "=()"
        
        elif isinstance(var.value, AssociativeArray):
            # declare -A name=([key]="val" [key2]="val2")
            elements = []
            for key, val in sorted(var.value.items()):
                elements.append(f'[{key}]="{self._escape_value(val)}"')
            if elements:
                value_str = f"=({' '.join(elements)})"
            else:
                value_str = "=()"
        
        else:
            # Regular variable
            value_str = f'="{self._escape_value(str(var.value))}"'
        
        print(f"declare {flag_str} {var.name}{value_str}", file=file)
    
    def _escape_value(self, value: str) -> str:
        """Escape special characters in value for shell output."""
        # Escape backslashes first, then double quotes, dollar signs, and backticks
        value = value.replace('\\', '\\\\')
        value = value.replace('"', '\\"')
        value = value.replace('$', '\\$')
        value = value.replace('`', '\\`')
        return value
    
    def _parse_array_init(self, value: str) -> List[str]:
        """Parse array initialization: (val1 val2 val3)"""
        # Remove parentheses
        content = value[1:-1].strip()
        if not content:
            return []
        
        # Simple word splitting with quote handling
        parts = content.split()
        result = []
        for part in parts:
            # Remove surrounding quotes if present
            if (part.startswith('"') and part.endswith('"')) or \
               (part.startswith("'") and part.endswith("'")):
                result.append(part[1:-1])
            else:
                result.append(part)
        return result
    
    def _parse_assoc_array_init(self, value: str) -> List[tuple[str, str]]:
        """Parse associative array initialization: ([key]=val [key2]=val2)"""
        # Remove parentheses
        content = value[1:-1].strip()
        if not content:
            return []
        
        # Simple parsing for now
        # TODO: Proper shell parsing with quotes
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
    
    def _apply_attributes(self, value: Any, attributes: VarAttributes, shell: 'Shell') -> Any:
        """Apply attribute transformations to value."""
        if isinstance(value, (IndexedArray, AssociativeArray)):
            return value  # Arrays aren't transformed
            
        str_value = str(value)
        
        if attributes & VarAttributes.UPPERCASE:
            return str_value.upper()
        elif attributes & VarAttributes.LOWERCASE:
            return str_value.lower()
        elif attributes & VarAttributes.INTEGER:
            # Evaluate arithmetic expression
            try:
                # Use shell's arithmetic evaluator
                from ..expansion.arithmetic import ArithmeticEvaluator
                evaluator = ArithmeticEvaluator(shell.state)
                result = evaluator.evaluate(str_value)
                return str(result)  # Return as string but evaluated
            except Exception as e:
                # Fall back to simple int conversion
                try:
                    return str(int(str_value))
                except:
                    return "0"
        return str_value
    
    def _matches_filter(self, var: Variable, options: dict) -> bool:
        """Check if variable matches filter criteria."""
        # For now, show all variables
        # Could add filtering by attribute type later
        return True
    
    # Methods to interact with shell's enhanced variable storage
    
    def _get_variable_with_attributes(self, shell: 'Shell', name: str) -> Optional[Variable]:
        """Get variable with its attributes."""
        return shell.state.scope_manager.get_variable_object(name)
    
    def _get_all_variables_with_attributes(self, shell: 'Shell') -> List[Variable]:
        """Get all variables with their attributes."""
        return shell.state.scope_manager.all_variables_with_attributes()
    
    def _set_variable_with_attributes(self, shell: 'Shell', name: str, 
                                     value: Any, attributes: VarAttributes):
        """Set variable with attributes."""
        try:
            shell.state.scope_manager.set_variable(name, value, attributes=attributes, local=False)
            
            # Handle export - sync to environment
            if attributes & VarAttributes.EXPORT:
                shell.state.scope_manager.sync_exports_to_environment(shell.state.env)
        except ReadonlyVariableError:
            raise ReadonlyVariableError(f"{self.name}: {name}: readonly variable")
    
    def _print_function_definition(self, name, func, stdout):
        """Print a function definition in a format that can be re-executed."""
        print(f"{name} () ", file=stdout, end='')
        print(ShellFormatter.format_function_body(func), file=stdout)
    
    @property
    def help(self) -> str:
        return """declare: declare [-aAfFgilprtux] [name[=value] ...]
    
    Declare variables and give them attributes.
    
    Options:
      -a    Declare indexed array variables
      -A    Declare associative array variables
      -f    Restrict action to function names and definitions
      -F    Display function names only (no definitions)
      -g    Create global variables when used in a function (not yet implemented)
      -i    Make variables have the 'integer' attribute
      -l    Convert values to lowercase on assignment
      -p    Display the attributes and value of each variable
      -r    Make variables readonly
      -t    Give variables the 'trace' attribute (functions only)
      -u    Convert values to uppercase on assignment  
      -x    Make variables export to the environment
      +x    Remove export attribute
      +r    Remove readonly attribute (if possible)
    
    Using '+' instead of '-' turns off the given attribute.
    
    With no arguments, display all variables and their values.
    With -p, display variables in a reusable format.
    With -f, display all function definitions.
    With -F, display all function names."""


@builtin
class TypesetBuiltin(DeclareBuiltin):
    """Typeset builtin - alias for declare (ksh compatibility)."""
    
    @property
    def name(self) -> str:
        return "typeset"
    
    @property
    def help(self) -> str:
        return """typeset: typeset [-aAfFgilprtux] [name[=value] ...]
    
    Declare variables and give them attributes (alias for declare).
    
    Options:
      -a    Declare indexed array variables
      -A    Declare associative array variables
      -f    Restrict action to function names and definitions
      -F    Display function names only (no definitions)
      -g    Create global variables when used in a function (not yet implemented)
      -i    Make variables have the 'integer' attribute
      -l    Convert values to lowercase on assignment
      -p    Display the attributes and value of each variable
      -r    Make variables readonly
      -t    Give variables the 'trace' attribute (functions only)
      -u    Convert values to uppercase on assignment  
      -x    Make variables export to the environment
      +x    Remove export attribute
      +r    Remove readonly attribute (if possible)
    
    Using '+' instead of '-' turns off the given attribute.
    
    With no arguments, display all variables and their values.
    With -p, display variables in a reusable format.
    With -f, display all function definitions.
    With -F, display all function names.
    
    Note: typeset is supplied for compatibility with the Korn shell.
    It is exactly equivalent to declare."""


@builtin
class ReturnBuiltin(Builtin):
    """Return from a function with optional exit code."""
    
    @property
    def name(self) -> str:
        return "return"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the return builtin."""
        if not shell.function_stack:
            print("return: can only `return' from a function or sourced script", file=sys.stderr)
            return 1
        
        # Get return value
        if len(args) > 1:
            try:
                exit_code = int(args[1])
                # Ensure it's in valid range
                if exit_code < 0 or exit_code > 255:
                    print(f"return: {args[1]}: numeric argument required", file=sys.stderr)
                    return 1
            except ValueError:
                print(f"return: {args[1]}: numeric argument required", file=sys.stderr)
                return 1
        else:
            exit_code = 0
        
        # We can't actually "return" from the middle of execution in Python,
        # so we'll use an exception for control flow
        raise FunctionReturn(exit_code)