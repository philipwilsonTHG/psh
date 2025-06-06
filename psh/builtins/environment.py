"""Environment and variable management builtins (env, export, set, unset)."""

import os
import sys
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class EnvBuiltin(Builtin):
    """Display or modify environment variables."""
    
    @property
    def name(self) -> str:
        return "env"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Display environment variables or run command with modified environment."""
        if len(args) == 1:
            # No arguments, print all environment variables
            for key, value in sorted(shell.env.items()):
                print(f"{key}={value}", 
                      file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
            return 0
        else:
            # TODO: Run command with modified environment
            self.error("running commands not yet implemented", shell)
            return 1
    
    @property
    def help(self) -> str:
        return """env: env [name=value ...] [command [args ...]]
    
    Display environment variables or run a command with modified environment.
    With no arguments, print all environment variables.
    Setting variables and running commands is not yet implemented."""


@builtin
class ExportBuiltin(Builtin):
    """Export variables to environment."""
    
    @property
    def name(self) -> str:
        return "export"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Export variables to environment."""
        if len(args) == 1:
            # No arguments, print all exported variables
            for key, value in sorted(shell.env.items()):
                print(f'export {key}="{value}"', 
                      file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        else:
            for arg in args[1:]:
                if '=' in arg:
                    # Variable assignment
                    key, value = arg.split('=', 1)
                    shell.state.export_variable(key, value)
                else:
                    # Export existing variable
                    value = shell.state.get_variable(arg)
                    if value is not None:
                        shell.state.export_variable(arg, value)
        return 0
    
    @property
    def help(self) -> str:
        return """export: export [name[=value] ...]
    
    Export variables to the environment.
    With no arguments, print all exported variables.
    With name=value, set the variable and export it.
    With just name, export an existing shell variable."""


@builtin
class SetBuiltin(Builtin):
    """Set shell options and positional parameters."""
    
    @property
    def name(self) -> str:
        return "set"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Set shell options and positional parameters."""
        if len(args) == 1:
            # No arguments, display all variables
            for var, value in sorted(shell.state.variables.items()):
                print(f"{var}={value}", 
                      file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
            # Also show set options
            print(f"edit_mode={shell.edit_mode}", 
                  file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
            return 0
        
        # Handle -o option
        if len(args) >= 3 and args[1] == '-o':
            option = args[2].lower().replace('_', '-')  # Allow debug_ast or debug-ast
            
            # Editor modes
            if option in ('vi', 'emacs'):
                shell.edit_mode = option
                print(f"Edit mode set to {option}", 
                      file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
                return 0
            # Debug options
            elif option == 'debug-ast':
                shell.state.debug_ast = True
                return 0
            elif option == 'debug-tokens':
                shell.state.debug_tokens = True
                return 0
            elif option == 'debug-scopes':
                shell.state.debug_scopes = True
                shell.state.scope_manager.enable_debug(True)
                return 0
            else:
                self.error(f"invalid option: {option}", shell)
                print("Valid options: vi, emacs, debug-ast, debug-tokens, debug-scopes", 
                      file=shell.stderr if hasattr(shell, 'stderr') else sys.stderr)
                return 1
        elif args[1] == '-o' and len(args) == 2:
            # Show current options
            stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
            print(f"edit_mode            {shell.edit_mode}", file=stdout)
            print(f"debug-ast            {'on' if shell.state.debug_ast else 'off'}", file=stdout)
            print(f"debug-tokens         {'on' if shell.state.debug_tokens else 'off'}", file=stdout)
            print(f"debug-scopes         {'on' if shell.state.debug_scopes else 'off'}", file=stdout)
            return 0
        elif args[1] == '+o' and len(args) == 2:
            # Show current options as set commands
            stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
            print(f"set {'+o' if shell.edit_mode == 'emacs' else '-o'} vi", file=stdout)
            print(f"set {'-o' if shell.state.debug_ast else '+o'} debug-ast", file=stdout)
            print(f"set {'-o' if shell.state.debug_tokens else '+o'} debug-tokens", file=stdout)
            print(f"set {'-o' if shell.state.debug_scopes else '+o'} debug-scopes", file=stdout)
            return 0
        elif args[1] == '+o' and len(args) >= 3:
            # Unset option
            option = args[2].lower().replace('_', '-')
            if option == 'vi':
                shell.edit_mode = 'emacs'
                print("Edit mode set to emacs", 
                      file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
            elif option == 'debug-ast':
                shell.state.debug_ast = False
            elif option == 'debug-tokens':
                shell.state.debug_tokens = False
            elif option == 'debug-scopes':
                shell.state.debug_scopes = False
                shell.state.scope_manager.enable_debug(False)
            return 0
        else:
            # Set positional parameters
            # Handle -- to separate options from arguments
            if len(args) > 1 and args[1] == '--':
                shell.positional_params = args[2:]
            else:
                shell.positional_params = args[1:]
            return 0
    
    @property
    def help(self) -> str:
        return """set: set [-o option] [+o option] [arg ...]
    
    Set shell options and positional parameters.
    With no arguments, print all shell variables.
    
    Options:
      -o                Show current option settings
      -o vi             Set vi editing mode
      -o emacs          Set emacs editing mode (default)
      -o debug-ast      Enable AST debug output
      -o debug-tokens   Enable token debug output
      -o debug-scopes   Enable variable scope debug output
      +o vi             Unset vi mode (switch to emacs)
      +o debug-ast      Disable AST debug output
      +o debug-tokens   Disable token debug output
      +o debug-scopes   Disable variable scope debug output
    
    With arguments, set positional parameters ($1, $2, etc.)."""


@builtin
class UnsetBuiltin(Builtin):
    """Unset variables and functions."""
    
    @property
    def name(self) -> str:
        return "unset"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Unset variables and functions."""
        if len(args) < 2:
            self.error("not enough arguments", shell)
            return 1
        
        # Check for -f flag
        if '-f' in args:
            # Remove functions
            exit_code = 0
            for arg in args[1:]:
                if arg != '-f':
                    if not shell.function_manager.undefine_function(arg):
                        self.error(f"{arg}: not a function", shell)
                        exit_code = 1
            return exit_code
        else:
            # Remove variables
            for var in args[1:]:
                # Remove from both shell variables and environment
                shell.state.scope_manager.unset_variable(var)
                shell.env.pop(var, None)
            return 0
    
    @property
    def help(self) -> str:
        return """unset: unset [-f] name [name ...]
    
    Unset variables or functions.
    
    Options:
      -f    Treat names as functions
    
    Without -f, remove the named variables from both shell
    variables and the environment."""