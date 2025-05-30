"""Function-related builtin commands."""
import sys
from typing import List, TYPE_CHECKING

from .base import Builtin
from .registry import builtin

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
        if '-f' in args:
            if len(args) == 2:  # declare -f
                # List all functions
                for name, func in shell.function_manager.list_functions():
                    self._print_function_definition(name, func)
            else:  # declare -f name
                for arg in args[2:]:
                    func = shell.function_manager.get_function(arg)
                    if func:
                        self._print_function_definition(arg, func)
                    else:
                        print(f"psh: declare: {arg}: not found", file=sys.stderr)
                        return 1
        else:
            # For now, just list variables (like set with no args)
            for var, value in sorted(shell.variables.items()):
                print(f"{var}={value}")
        return 0
    
    def _print_function_definition(self, name, func):
        """Print a function definition in a format that can be re-executed."""
        print(f"{name} () {{")
        # We need to pretty-print the function body
        # For now, just indicate it's defined
        print(f"    # function body")
        print("}")


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