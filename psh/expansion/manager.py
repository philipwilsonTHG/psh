"""Central expansion manager that orchestrates all shell expansions."""
from typing import List, TYPE_CHECKING
from ..ast_nodes import Command, Redirect, ProcessSubstitution
from ..core.state import ShellState
from .variable import VariableExpander
from .command_sub import CommandSubstitution
from .tilde import TildeExpander
from .glob import GlobExpander

if TYPE_CHECKING:
    from ..shell import Shell


class ExpansionManager:
    """Orchestrates all shell expansions in the correct order."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize individual expanders
        self.variable_expander = VariableExpander(shell)
        self.command_sub = CommandSubstitution(shell)
        self.tilde_expander = TildeExpander(shell)
        self.glob_expander = GlobExpander(shell)
    
    def expand_arguments(self, command: Command) -> List[str]:
        """
        Expand all arguments in a command.
        
        This method orchestrates all expansions in the correct order:
        1. Brace expansion (handled by tokenizer)
        2. Tilde expansion
        3. Variable expansion
        4. Command substitution
        5. Arithmetic expansion
        6. Word splitting
        7. Pathname expansion (globbing)
        8. Quote removal
        """
        import glob
        args = []
        
        # Check if we have process substitutions
        has_proc_sub = any(command.arg_types[i] in ('PROCESS_SUB_IN', 'PROCESS_SUB_OUT') 
                          for i in range(len(command.arg_types)))
        
        if has_proc_sub:
            # Set up process substitutions first
            fds, substituted_args, child_pids = self.shell.io_manager.setup_process_substitutions(command)
            # Store for cleanup
            self.shell._process_sub_fds = fds
            self.shell._process_sub_pids = child_pids
            # Update command args with substituted paths
            command.args = substituted_args
            # Update arg_types to treat substituted paths as words
            command.arg_types = ['WORD'] * len(substituted_args)
            # Update quote_types as well
            command.quote_types = [None] * len(substituted_args)
        
        for i, arg in enumerate(command.args):
            arg_type = command.arg_types[i] if i < len(command.arg_types) else 'WORD'
            quote_type = command.quote_types[i] if i < len(command.quote_types) else None
            
            if arg_type == 'STRING':
                # Handle quoted strings
                if quote_type == '"' and '$' in arg:
                    # Double-quoted string with variables - expand them
                    # Special handling for "$@"
                    if arg == '$@':
                        # "$@" expands to multiple arguments, each properly quoted
                        args.extend(self.state.positional_params)
                        continue
                    else:
                        # Expand variables within the string
                        arg = self.expand_string_variables(arg)
                        args.append(arg)
                else:
                    # Single-quoted string or no variables - no expansion
                    args.append(arg)
            elif arg.startswith('$') and not (arg.startswith('$(') or arg.startswith('`')):
                # Variable expansion for unquoted variables
                expanded = self.expand_variable(arg)
                args.append(expanded)
            elif '\\$' in arg and arg_type == 'WORD':
                # Escaped dollar sign in word - replace with literal $
                args.append(arg.replace('\\$', '$'))
            elif arg_type == 'COMPOSITE':
                # Composite argument - already concatenated in parser
                # Just perform glob expansion if it contains wildcards
                if any(c in arg for c in ['*', '?', '[']):
                    matches = glob.glob(arg)
                    if matches:
                        args.extend(sorted(matches))
                    else:
                        args.append(arg)
                else:
                    args.append(arg)
            elif arg_type in ('COMMAND_SUB', 'COMMAND_SUB_BACKTICK'):
                # Command substitution
                output = self.execute_command_substitution(arg)
                # POSIX: apply word splitting to unquoted command substitution
                if output:
                    # Split on whitespace
                    words = output.split()
                    args.extend(words)
                # If output is empty, don't add anything
            elif arg_type == 'ARITH_EXPANSION':
                # Arithmetic expansion
                result = self.execute_arithmetic_expansion(arg)
                args.append(str(result))
            else:
                # Handle regular words
                # Tilde expansion (only for unquoted words)
                if arg.startswith('~') and arg_type == 'WORD':
                    arg = self.expand_tilde(arg)
                
                # Check if the argument contains glob characters and wasn't quoted
                if any(c in arg for c in ['*', '?', '[']) and arg_type != 'STRING':
                    # Perform glob expansion
                    matches = glob.glob(arg)
                    if matches:
                        # Sort matches for consistent output
                        args.extend(sorted(matches))
                    else:
                        # No matches, use literal argument (bash behavior)
                        args.append(arg)
                else:
                    args.append(arg)
        return args
    
    def expand_string_variables(self, text: str) -> str:
        """
        Expand variables and arithmetic in a string.
        Used for here strings and double-quoted strings.
        """
        return self.variable_expander.expand_string_variables(text)
    
    def expand_variable(self, var_expr: str) -> str:
        """Expand a variable expression."""
        return self.variable_expander.expand_variable(var_expr)
    
    def expand_tilde(self, path: str) -> str:
        """Expand tilde in a path."""
        return self.tilde_expander.expand(path)
    
    def execute_command_substitution(self, cmd_sub: str) -> str:
        """Execute command substitution and return output."""
        return self.command_sub.execute(cmd_sub)
    
    def execute_arithmetic_expansion(self, expr: str) -> int:
        """Execute arithmetic expansion and return result."""
        # Remove $(( and ))
        if expr.startswith('$((') and expr.endswith('))'):
            arith_expr = expr[3:-2]
        else:
            return 0
        
        from ..arithmetic import evaluate_arithmetic, ArithmeticError
        
        try:
            result = evaluate_arithmetic(arith_expr, self.shell)
            return result
        except ArithmeticError as e:
            import sys
            print(f"psh: arithmetic error: {e}", file=sys.stderr)
            return 0