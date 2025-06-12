"""Function-related builtin commands."""
import sys
from typing import List, TYPE_CHECKING

from .base import Builtin
from .registry import builtin
from ..utils.shell_formatter import ShellFormatter

if TYPE_CHECKING:
    from ..shell import Shell


class FunctionReturn(Exception):
    """Exception used to implement the return builtin."""
    def __init__(self, exit_code: int):
        self.exit_code = exit_code
        super().__init__()


@builtin
class DeclareBuiltin(Builtin):
    """Declare variables and functions."""
    
    @property
    def name(self) -> str:
        return "declare"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the declare builtin."""
        # Check for function-related flags
        show_names_only = '-F' in args
        show_functions = '-f' in args or show_names_only
        
        if show_functions:
            # Filter out the flags from args to get function names
            func_names = [arg for arg in args[1:] if not arg.startswith('-')]
            
            stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
            
            if not func_names:
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
                for name in func_names:
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
        else:
            # For now, just list variables (like set with no args)
            stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
            for var, value in sorted(shell.state.variables.items()):
                print(f"{var}={value}", file=stdout)
        return 0
    
    def _print_function_definition(self, name, func, stdout):
        """Print a function definition in a format that can be re-executed."""
        print(f"{name} () ", file=stdout, end='')
        print(ShellFormatter.format_function_body(func), file=stdout)
    
    @property
    def help(self) -> str:
        return """declare: declare [-f] [-F] [name ...]
    
    Declare variables and functions.
    
    Options:
      -f    Restrict action to function names and definitions
      -F    Display function names only (no definitions)
    
    With no options, display all shell variables.
    With -f, display all function definitions.
    With -F, display all function names.
    With -f name, display the definition of the named function.
    With -F name, display the name if it's a function."""


@builtin
class TypesetBuiltin(DeclareBuiltin):
    """Typeset builtin - alias for declare (ksh compatibility)."""
    
    @property
    def name(self) -> str:
        return "typeset"
    
    @property
    def help(self) -> str:
        return """typeset: typeset [-f] [-F] [name ...]
    
    Declare variables and functions (alias for declare).
    
    Options:
      -f    Restrict action to function names and definitions
      -F    Display function names only (no definitions)
    
    With no options, display all shell variables.
    With -f, display all function definitions.
    With -F, display all function names.
    With -f name, display the definition of the named function.
    With -F name, display the name if it's a function.
    
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