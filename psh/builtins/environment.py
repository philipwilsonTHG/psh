"""Environment and variable management builtins (env, export, set, unset)."""

import os
import sys
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin
from ..core.exceptions import ReadonlyVariableError

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
            # First sync exports from scope manager to environment
            shell.state.scope_manager.sync_exports_to_environment(shell.env)
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
        
        # Map short options to long names
        short_to_long = {
            'a': 'allexport',
            'b': 'notify',
            'C': 'noclobber',
            'e': 'errexit',
            'f': 'noglob',
            'h': 'hashcmds',
            'm': 'monitor',
            'n': 'noexec',
            'u': 'nounset',
            'v': 'verbose',
            'x': 'xtrace',
        }
        
        # Process arguments
        i = 1
        while i < len(args):
            arg = args[i]
            
            # Handle short options like -eux
            if arg.startswith('-') and not arg.startswith('-o') and len(arg) > 1 and not arg == '--':
                for opt_char in arg[1:]:
                    if opt_char in short_to_long:
                        shell.state.options[short_to_long[opt_char]] = True
                    else:
                        self.error(f"invalid option: -{opt_char}", shell)
                        return 1
                i += 1
                continue
            
            # Handle +eux to unset options
            elif arg.startswith('+') and not arg.startswith('+o') and len(arg) > 1:
                for opt_char in arg[1:]:
                    if opt_char in short_to_long:
                        shell.state.options[short_to_long[opt_char]] = False
                    else:
                        self.error(f"invalid option: +{opt_char}", shell)
                        return 1
                i += 1
                continue
            
            # Handle -o option with argument
            elif arg == '-o' and i + 1 < len(args):
                option = args[i + 1].lower().replace('_', '-')  # Allow debug_ast or debug-ast
                
                # Editor modes
                if option in ('vi', 'emacs'):
                    shell.edit_mode = option
                    print(f"Edit mode set to {option}", 
                          file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
                    return 0
                # Debug options and new shell options
                elif option in shell.state.options:
                    shell.state.options[option] = True
                    # Special handling for debug-scopes
                    if option == 'debug-scopes':
                        shell.state.scope_manager.enable_debug(True)
                    # visitor-executor option removed - visitor is now the only executor
                    elif option == 'visitor-executor':
                        pass  # Silently ignore for backward compatibility
                    return 0
                else:
                    self.error(f"invalid option: {option}", shell)
                    valid_opts = ['vi', 'emacs'] + list(sorted(shell.state.options.keys()))
                    print(f"Valid options: {', '.join(valid_opts)}", 
                          file=shell.stderr if hasattr(shell, 'stderr') else sys.stderr)
                    return 1
            
            # Handle -o without argument (show options)
            elif arg == '-o' and i + 1 == len(args):
                # Show current options
                stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
                print(f"edit_mode            {shell.edit_mode}", file=stdout)
                # Show all shell options from the centralized dict
                for opt_name, opt_value in sorted(shell.state.options.items()):
                    status = 'on' if opt_value else 'off'
                    print(f"{opt_name:<20} {status}", file=stdout)
                return 0
            
            # Handle +o without argument (show as set commands)
            elif arg == '+o' and i + 1 == len(args):
                # Show current options as set commands
                stdout = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
                print(f"set {'+o' if shell.edit_mode == 'emacs' else '-o'} vi", file=stdout)
                # Show all shell options as set commands
                for opt_name, opt_value in sorted(shell.state.options.items()):
                    print(f"set {'-o' if opt_value else '+o'} {opt_name}", file=stdout)
                return 0
            
            # Handle +o with argument
            elif arg == '+o' and i + 1 < len(args):
                # Unset option
                option = args[i + 1].lower().replace('_', '-')
                if option == 'vi':
                    shell.edit_mode = 'emacs'
                    print("Edit mode set to emacs", 
                          file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
                elif option in shell.state.options:
                    shell.state.options[option] = False
                    # Special handling for debug-scopes
                    if option == 'debug-scopes':
                        shell.state.scope_manager.enable_debug(False)
                    # visitor-executor option removed - visitor is now the only executor
                    elif option == 'visitor-executor':
                        print("psh: set: visitor-executor: option is deprecated (visitor is now the only executor)", file=sys.stderr)
                return 0
            
            # Otherwise, treat as positional parameters
            else:
                # Handle -- to separate options from arguments
                if arg == '--':
                    shell.positional_params = args[i + 1:]
                else:
                    shell.positional_params = args[i:]
                return 0
            
        return 0
    
    @property
    def help(self) -> str:
        return """set: set [-abCefhmnuvx] [+abCefhmnuvx] [-o option] [arg ...]
    
    Set shell options and positional parameters.
    With no arguments, print all shell variables.
    
    Short options:
      -a                Enable allexport (auto-export all variables)
      -b                Enable notify (async job completion notifications)
      -C                Enable noclobber (prevent file overwriting with >)
      -e                Enable errexit (exit on command failure)
      -f                Enable noglob (disable pathname expansion)
      -h                Enable hashcmds (hash command locations)
      -m                Enable monitor (job control mode)
      -n                Enable noexec (read but don't execute commands)
      -u                Enable nounset (error on undefined variables)
      -v                Enable verbose (echo input lines as read)
      -x                Enable xtrace (print commands before execution)
      +<option>         Disable the specified option
    
    Long options:
      -o                Show current option settings
      -o vi             Set vi editing mode
      -o emacs          Set emacs editing mode (default)
      -o allexport      Auto-export all variables (same as -a)
      -o notify         Async job completion notifications (same as -b)
      -o noclobber      Prevent file overwriting with > (same as -C)
      -o errexit        Exit on command failure (same as -e)
      -o noglob         Disable pathname expansion (same as -f)
      -o hashcmds       Hash command locations (same as -h)
      -o monitor        Job control mode (same as -m)
      -o noexec         Read but don't execute commands (same as -n)
      -o nounset        Error on undefined variables (same as -u)
      -o verbose        Echo input lines as read (same as -v)
      -o xtrace         Print commands before execution (same as -x)
      -o pipefail       Pipeline fails if any command fails
      -o ignoreeof      Don't exit on EOF (Ctrl-D)
      -o nolog          Don't log function definitions to history
      -o debug-ast      Enable AST debug output
      -o debug-tokens   Enable token debug output
      -o debug-scopes   Enable variable scope debug output
      +o <option>       Disable the specified option
    
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
            exit_code = 0
            for var in args[1:]:
                # Check if this is an array element syntax
                if '[' in var and var.endswith(']'):
                    # Array element unset: arr[index]
                    bracket_pos = var.find('[')
                    array_name = var[:bracket_pos]
                    index_expr = var[bracket_pos+1:-1]
                    
                    # Get the array variable
                    from ..core.variables import IndexedArray, AssociativeArray
                    var_obj = shell.state.scope_manager.get_variable_object(array_name)
                    
                    if var_obj and isinstance(var_obj.value, IndexedArray):
                        # Evaluate the index
                        try:
                            # Expand variables in index
                            expanded_index = shell.expansion_manager.expand_string_variables(index_expr)
                            
                            # Check if it's arithmetic
                            if any(op in expanded_index for op in ['+', '-', '*', '/', '%', '(', ')']):
                                from ..arithmetic import evaluate_arithmetic
                                index = evaluate_arithmetic(expanded_index, shell)
                            else:
                                index = int(expanded_index)
                            
                            # Unset the element
                            var_obj.value.unset(index)
                        except Exception as e:
                            self.error(f"{var}: bad array subscript", shell)
                            exit_code = 1
                    elif var_obj and isinstance(var_obj.value, AssociativeArray):
                        # For associative arrays
                        expanded_key = shell.expansion_manager.expand_string_variables(index_expr)
                        var_obj.value.unset(expanded_key)
                    else:
                        # Not an array
                        self.error(f"{array_name}: not an array", shell)
                        exit_code = 1
                else:
                    # Regular variable unset
                    try:
                        # Remove from both shell variables and environment
                        shell.state.scope_manager.unset_variable(var)
                        shell.env.pop(var, None)
                    except ReadonlyVariableError:
                        self.error(f"{var}: readonly variable", shell)
                        exit_code = 1
            return exit_code
    
    @property
    def help(self) -> str:
        return """unset: unset [-f] name [name ...]
    
    Unset variables or functions.
    
    Options:
      -f    Treat names as functions
    
    Without -f, remove the named variables from both shell
    variables and the environment."""