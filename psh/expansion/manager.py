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
            elif arg_type == 'VARIABLE':
                # Variable token from lexer (includes braces but not $ prefix)
                # Add $ prefix for expand_variable
                var_expr = '$' + arg if not arg.startswith('$') else arg
                expanded = self.expand_variable(var_expr)
                args.append(expanded)
            elif arg_type != 'COMPOSITE' and arg.startswith('$') and not (arg.startswith('$(') or arg.startswith('`')):
                # Variable expansion for unquoted variables (but not COMPOSITE args)
                expanded = self.expand_variable(arg)
                args.append(expanded)
            elif arg_type == 'WORD' and '\\$' in arg:
                # Escaped dollar sign in word - replace with literal $
                args.append(arg.replace('\\$', '$'))
            elif arg_type == 'COMPOSITE':
                # Composite argument - already concatenated in parser
                # IMPORTANT: We've lost quote information, so we can't safely
                # perform glob expansion. In bash, file'*'.txt doesn't expand
                # because the * was quoted. Since we can't tell which parts
                # were quoted, we skip glob expansion for all COMPOSITE args.
                # This is a known limitation documented in TODO.md
                
                # However, we still need to expand variables
                if '$' in arg:
                    expanded_arg = self.expand_string_variables(arg)
                    args.append(expanded_arg)
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
                # Check for embedded variables in unquoted words
                if arg_type == 'WORD' and '$' in arg:
                    # Expand embedded variables
                    arg = self.expand_string_variables(arg)
                
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
        
        # Pre-expand command substitutions in the arithmetic expression
        arith_expr = self._expand_command_subs_in_arithmetic(arith_expr)
        
        from ..arithmetic import evaluate_arithmetic, ArithmeticError
        
        try:
            result = evaluate_arithmetic(arith_expr, self.shell)
            return result
        except ArithmeticError as e:
            import sys
            print(f"psh: arithmetic error: {e}", file=sys.stderr)
            return 0
        except Exception as e:
            import sys
            print(f"psh: unexpected arithmetic error: {e}", file=sys.stderr)
            return 0
    
    def _expand_command_subs_in_arithmetic(self, expr: str) -> str:
        """Expand command substitutions in arithmetic expression.
        
        This method finds all $(...) patterns in the arithmetic expression
        and replaces them with their evaluated output before arithmetic
        evaluation.
        
        Args:
            expr: The arithmetic expression potentially containing $(...)
            
        Returns:
            The expression with all command substitutions expanded
        """
        result = []
        i = 0
        
        while i < len(expr):
            if expr[i] == '$' and i + 1 < len(expr) and expr[i + 1] == '(':
                # Found potential command substitution
                # Find matching closing parenthesis
                paren_count = 1
                j = i + 2
                
                while j < len(expr) and paren_count > 0:
                    if expr[j] == '(':
                        paren_count += 1
                    elif expr[j] == ')':
                        paren_count -= 1
                    j += 1
                
                if paren_count == 0:
                    # Valid command substitution found
                    cmd_sub_expr = expr[i:j]  # Include $(...) 
                    
                    # Execute command substitution
                    output = self.command_sub.execute(cmd_sub_expr).strip()
                    
                    # Convert empty output to 0 (bash behavior)
                    result.append(output if output else '0')
                    i = j
                    continue
            
            # Not a command substitution, copy character as-is
            result.append(expr[i])
            i += 1
        
        return ''.join(result)