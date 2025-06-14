"""Central expansion manager that orchestrates all shell expansions."""
from typing import List, TYPE_CHECKING
from ..ast_nodes import Command, SimpleCommand, Redirect, ProcessSubstitution
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
    
    def expand_arguments(self, command: SimpleCommand) -> List[str]:
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
        
        # Debug: show pre-expansion args
        if self.state.options.get('debug-expansion'):
            print(f"[EXPANSION] Expanding command: {command.args}", file=self.state.stderr)
            if self.state.options.get('debug-expansion-detail'):
                print(f"[EXPANSION]   arg_types: {command.arg_types}", file=self.state.stderr)
                print(f"[EXPANSION]   quote_types: {command.quote_types}", file=self.state.stderr)
        
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
            
            
            
            if self.state.options.get('debug-expansion-detail'):
                print(f"[EXPANSION]   Processing arg[{i}]: '{arg}' (type={arg_type}, quote={quote_type})", file=self.state.stderr)
            
            if arg_type == 'STRING':
                # Handle quoted strings
                if quote_type == '"' and '$' in arg:
                    # Double-quoted string with variables - expand them
                    # Special handling for "$@"
                    if arg == '$@':
                        # "$@" expands to multiple arguments, each properly quoted
                        if self.state.options.get('debug-expansion-detail'):
                            print(f"[EXPANSION]     Expanding \"$@\" to: {self.state.positional_params}", file=self.state.stderr)
                        args.extend(self.state.positional_params)
                        continue
                    else:
                        # Expand variables within the string
                        original = arg
                        arg = self.expand_string_variables(arg)
                        if self.state.options.get('debug-expansion-detail') and original != arg:
                            print(f"[EXPANSION]     String variable expansion: '{original}' -> '{arg}'", file=self.state.stderr)
                        args.append(arg)
                else:
                    # Single-quoted string or no variables - no expansion
                    args.append(arg)
            elif arg_type == 'VARIABLE':
                # Variable token from lexer (includes braces but not $ prefix)
                # Add $ prefix for expand_variable
                var_expr = '$' + arg if not arg.startswith('$') else arg
                
                # Check if this is an array expansion that produces multiple words
                if self.variable_expander.is_array_expansion(var_expr):
                    # Expand to list of words
                    expanded_list = self.variable_expander.expand_array_to_list(var_expr)
                    if self.state.options.get('debug-expansion-detail'):
                        print(f"[EXPANSION]     Array expansion: '{var_expr}' -> {expanded_list}", file=self.state.stderr)
                    args.extend(expanded_list)
                else:
                    # Regular variable expansion
                    expanded = self.expand_variable(var_expr)
                    if self.state.options.get('debug-expansion-detail'):
                        print(f"[EXPANSION]     Variable expansion: '{var_expr}' -> '{expanded}'", file=self.state.stderr)
                    args.append(expanded)
            elif '\x00$' in arg:
                # Contains escaped dollar sign marker - replace with literal $
                args.append(arg.replace('\x00$', '$'))
            elif arg_type != 'COMPOSITE' and arg.startswith('$') and not (arg.startswith('$(') or arg.startswith('`')):
                # Variable expansion for unquoted variables (but not COMPOSITE args)
                # Check if this is an array expansion that produces multiple words
                if self.variable_expander.is_array_expansion(arg):
                    # Expand to list of words
                    expanded_list = self.variable_expander.expand_array_to_list(arg)
                    args.extend(expanded_list)
                else:
                    # Regular variable expansion
                    expanded = self.expand_variable(arg)
                    args.append(expanded)
            elif arg_type == 'WORD' and '\\$' in arg:
                # Escaped dollar sign in word - replace with literal $
                args.append(arg.replace('\\$', '$'))
            elif arg_type == 'COMPOSITE' or arg_type == 'COMPOSITE_QUOTED':
                # Composite argument - already concatenated in parser
                # If it's COMPOSITE_QUOTED, it had quoted parts and shouldn't be glob expanded
                
                # First, expand variables if present
                if '$' in arg:
                    arg = self.expand_string_variables(arg)
                
                # Only expand globs for non-quoted composites
                if arg_type == 'COMPOSITE' and any(c in arg for c in ['*', '?', '[']):
                    # Perform glob expansion
                    matches = glob.glob(arg)
                    if matches:
                        # Sort matches for consistent output
                        args.extend(sorted(matches))
                    else:
                        # No matches, use literal argument (bash behavior)
                        args.append(arg)
                else:
                    # No glob expansion - quoted composite or no glob chars
                    args.append(arg)
            elif arg_type in ('COMMAND_SUB', 'COMMAND_SUB_BACKTICK'):
                # Command substitution
                output = self.execute_command_substitution(arg)
                if self.state.options.get('debug-expansion-detail'):
                    print(f"[EXPANSION]     Command substitution: '{arg}' -> '{output}'", file=self.state.stderr)
                # POSIX: apply word splitting to unquoted command substitution
                if output:
                    # Split on whitespace
                    words = output.split()
                    if self.state.options.get('debug-expansion-detail') and len(words) > 1:
                        print(f"[EXPANSION]     Word splitting: '{output}' -> {words}", file=self.state.stderr)
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
                    original = arg
                    arg = self.expand_tilde(arg)
                    if self.state.options.get('debug-expansion-detail') and original != arg:
                        print(f"[EXPANSION]     Tilde expansion: '{original}' -> '{arg}'", file=self.state.stderr)
                
                # Check if the argument contains glob characters and wasn't quoted
                if any(c in arg for c in ['*', '?', '[']) and arg_type != 'STRING':
                    # Perform glob expansion
                    matches = glob.glob(arg)
                    if matches:
                        # Sort matches for consistent output
                        if self.state.options.get('debug-expansion-detail'):
                            print(f"[EXPANSION]     Glob expansion: '{arg}' -> {sorted(matches)}", file=self.state.stderr)
                        args.extend(sorted(matches))
                    else:
                        # No matches, use literal argument (bash behavior)
                        if self.state.options.get('debug-expansion-detail'):
                            print(f"[EXPANSION]     Glob expansion: '{arg}' -> no matches", file=self.state.stderr)
                        args.append(arg)
                else:
                    args.append(arg)
        
        # Debug: show post-expansion args
        if self.state.options.get('debug-expansion'):
            print(f"[EXPANSION] Result: {args}", file=self.state.stderr)
        
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
        
        # Pre-expand variables in the arithmetic expression
        # This handles $var syntax which the arithmetic parser doesn't understand
        arith_expr = self._expand_vars_in_arithmetic(arith_expr)
        
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
    
    def _expand_vars_in_arithmetic(self, expr: str) -> str:
        """Expand $var syntax in arithmetic expression.
        
        This method finds all $var patterns in the arithmetic expression
        and replaces them with their values before arithmetic evaluation.
        The arithmetic parser only understands bare variable names.
        
        Args:
            expr: The arithmetic expression potentially containing $var
            
        Returns:
            The expression with all $var expanded to their values
        """
        result = []
        i = 0
        
        while i < len(expr):
            if expr[i] == '$' and i + 1 < len(expr):
                # Check if next char could start a variable name
                if expr[i + 1].isalpha() or expr[i + 1] == '_' or expr[i + 1].isdigit():
                    # Simple variable like $x, $1, $_
                    j = i + 1
                    while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                        j += 1
                    
                    var_name = expr[i+1:j]
                    # Check if it's a special variable (positional param, etc)
                    if var_name.isdigit() or var_name in ('?', '$', '!', '#', '@', '*'):
                        value = self.shell.state.get_special_variable(var_name)
                    else:
                        value = self.shell.state.get_variable(var_name, '0')
                    
                    # Convert empty or non-numeric to 0
                    if not value:
                        value = '0'
                    try:
                        int(value)
                    except ValueError:
                        value = '0'
                    
                    result.append(value)
                    i = j
                    continue
                elif expr[i + 1] == '{':
                    # Variable like ${x}
                    j = i + 2
                    brace_count = 1
                    while j < len(expr) and brace_count > 0:
                        if expr[j] == '{':
                            brace_count += 1
                        elif expr[j] == '}':
                            brace_count -= 1
                        j += 1
                    
                    if brace_count == 0:
                        var_expr = expr[i:j]  # Include ${...}
                        value = self.expand_variable(var_expr)
                        
                        # Convert empty or non-numeric to 0
                        if not value:
                            value = '0'
                        try:
                            int(value)
                        except ValueError:
                            value = '0'
                        
                        result.append(value)
                        i = j
                        continue
            
            # Not a variable expansion, copy character as-is
            result.append(expr[i])
            i += 1
        
        return ''.join(result)