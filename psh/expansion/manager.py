"""Central expansion manager that orchestrates all shell expansions."""
from typing import List, Union, TYPE_CHECKING, Optional
from ..ast_nodes import Command, SimpleCommand, Redirect, ProcessSubstitution
from ..core.state import ShellState
from ..core.exceptions import ExpansionError
from .variable import VariableExpander
from .command_sub import CommandSubstitution
from .tilde import TildeExpander
from .glob import GlobExpander
from .word_splitter import WordSplitter

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
        self.word_splitter = WordSplitter()
        
        # Initialize expansion evaluator (lazy import to avoid circular dependencies)
        self._evaluator = None
    
    @property
    def evaluator(self):
        """Get expansion evaluator, creating if needed."""
        if self._evaluator is None:
            from .evaluator import ExpansionEvaluator
            self._evaluator = ExpansionEvaluator(self.shell)
        return self._evaluator
    
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
        # Check if command has Word AST nodes
        if hasattr(command, 'words') and command.words:
            return self._expand_word_ast_arguments(command)
        else:
            # Fall back to existing string-based expansion
            return self._expand_string_arguments(command)
    
    def _expand_string_arguments(self, command: SimpleCommand) -> List[str]:
        """Original string-based argument expansion."""
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
                if quote_type == '"' and ('$' in arg or '`' in arg):
                    # Double-quoted string with variables - expand them
                    # Special handling for "$@"
                    if arg == '$@':
                        # "$@" expands to multiple arguments, each properly quoted
                        if self.state.options.get('debug-expansion-detail'):
                            print(f"[EXPANSION]     Expanding \"$@\" to: {self.state.positional_params}", file=self.state.stderr)
                        args.extend(self.state.positional_params)
                        continue
                    # Special handling for "${arr[@]}" - array expansions in double quotes
                    elif self.variable_expander.is_array_expansion(arg):
                        # Array expansion in double quotes should produce multiple arguments
                        expanded_list = self.variable_expander.expand_array_to_list(arg)
                        if self.state.options.get('debug-expansion-detail'):
                            print(f"[EXPANSION]     Array expansion in quotes: '{arg}' -> {expanded_list}", file=self.state.stderr)
                        args.extend(expanded_list)
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
                # The parser has already added the $ prefix to the variable
                var_expr = arg
                
                # Check if this is an array expansion that produces multiple words
                if self.variable_expander.is_array_expansion(var_expr):
                    # Expand to list of words
                    expanded_list = self.variable_expander.expand_array_to_list(var_expr)
                    if self.state.options.get('debug-expansion-detail'):
                        print(f"[EXPANSION]     Array expansion: '{var_expr}' -> {expanded_list}", file=self.state.stderr)
                    args.extend(expanded_list)
                else:
                    expanded = self.expand_variable(var_expr)
                    if self.state.options.get('debug-expansion-detail'):
                        print(f"[EXPANSION]     Variable expansion: '{var_expr}' -> '{expanded}'", file=self.state.stderr)

                    if quote_type is None:
                        words = self._split_with_ifs(expanded, quote_type)
                        if self.state.options.get('debug-expansion-detail') and len(words) > 1:
                            print(f"[EXPANSION]     Word splitting: '{expanded}' -> {words}", file=self.state.stderr)
                        for word in words:
                            self._process_single_word(word, arg_type, args)
                        continue

                    args.append(expanded)
            elif arg_type != 'COMPOSITE' and arg.startswith('$') and not (arg.startswith('$(') or arg.startswith('`')):
                # Variable expansion for unquoted variables (but not COMPOSITE args)
                # Check if this is an array expansion that produces multiple words
                if self.variable_expander.is_array_expansion(arg):
                    # Expand to list of words
                    expanded_list = self.variable_expander.expand_array_to_list(arg)
                    args.extend(expanded_list)
                else:
                    expanded = self.expand_variable(arg)
                    words = self._split_with_ifs(expanded, None)
                    if self.state.options.get('debug-expansion-detail') and len(words) > 1:
                        print(f"[EXPANSION]     Word splitting: '{expanded}' -> {words}", file=self.state.stderr)
                    for word in words:
                        self._process_single_word(word, 'WORD', args)
            elif arg_type == 'COMPOSITE' or arg_type == 'COMPOSITE_QUOTED':
                # Composite argument - already concatenated in parser
                # If it's COMPOSITE_QUOTED, it had quoted parts and shouldn't be glob expanded
                
                # First, expand variables and command substitutions if present
                if '$' in arg or '`' in arg:
                    arg = self.expand_string_variables(arg)
                
                # Only expand globs for non-quoted composites (unless noglob is set)
                if (arg_type == 'COMPOSITE' and any(c in arg for c in ['*', '?', '[']) 
                    and not self.state.options.get('noglob', False)):
                    # Perform glob expansion
                    matches = self.glob_expander.expand(arg)
                    args.extend(matches)
                else:
                    # No glob expansion - quoted composite, no glob chars, or noglob set
                    args.append(arg)
            elif arg_type in ('COMMAND_SUB', 'COMMAND_SUB_BACKTICK'):
                # Command substitution
                output = self.execute_command_substitution(arg)
                if self.state.options.get('debug-expansion-detail'):
                    print(f"[EXPANSION]     Command substitution: '{arg}' -> '{output}'", file=self.state.stderr)
                # POSIX: apply word splitting to unquoted command substitution
                if output:
                    words = self._split_with_ifs(output, None)
                    if self.state.options.get('debug-expansion-detail') and len(words) > 1:
                        print(f"[EXPANSION]     Word splitting: '{output}' -> {words}", file=self.state.stderr)
                    for word in words:
                        self._process_single_word(word, 'WORD', args)
                # If output is empty, don't add anything
                continue
            elif arg_type == 'ARITH_EXPANSION':
                # Arithmetic expansion
                result = self.execute_arithmetic_expansion(arg)
                args.append(str(result))
            else:
                if arg_type == 'WORD' and '$' in arg:
                    if self.state.options.get('debug-expansion-detail'):
                        print(f"[EXPANSION]     Before var expansion: '{arg}'", file=self.state.stderr)
                    arg = self.expand_string_variables(arg)
                    if self.state.options.get('debug-expansion-detail'):
                        print(f"[EXPANSION]     After var expansion: '{arg}'", file=self.state.stderr)

                words = self._split_with_ifs(arg, None)
                if self.state.options.get('debug-expansion-detail') and len(words) > 1:
                    print(f"[EXPANSION]     Word splitting: '{arg}' -> {words}", file=self.state.stderr)

                for word in words:
                    self._process_single_word(word, arg_type, args)
                continue
        
        # Debug: show post-expansion args
        if self.state.options.get('debug-expansion'):
            print(f"[EXPANSION] Result: {args}", file=self.state.stderr)
        
        return args
    
    def _expand_word_ast_arguments(self, command: SimpleCommand) -> List[str]:
        """Expand arguments using Word AST nodes."""
        args = []
        
        # Debug: show pre-expansion words
        if self.state.options.get('debug-expansion'):
            print(f"[EXPANSION] Expanding Word AST command: {[str(w) for w in command.words]}", file=self.state.stderr)
        
        for word in command.words:
            expanded = self._expand_word(word)
            if isinstance(expanded, list):
                args.extend(expanded)
            else:
                args.append(expanded)
        
        # Debug: show post-expansion args
        if self.state.options.get('debug-expansion'):
            print(f"[EXPANSION] Word AST Result: {args}", file=self.state.stderr)
        
        return args
    
    def _expand_word(self, word) -> Union[str, List[str]]:
        """Expand a Word AST node.
        
        Returns:
            Either a single string or a list of strings (for word splitting).
        """
        from ..ast_nodes import Word, LiteralPart, ExpansionPart
        
        if not isinstance(word, Word):
            # Not a Word node, treat as string
            return str(word)
        
        if word.quote_type == "'":
            # Single quotes: no expansion
            return self._word_to_string(word)
        
        # Process each part
        result_parts = []
        for part in word.parts:
            if isinstance(part, LiteralPart):
                result_parts.append(part.text)
            elif isinstance(part, ExpansionPart):
                expanded = self._expand_expansion(part.expansion)
                result_parts.append(expanded)
        
        # Join parts and handle word splitting if unquoted
        result = ''.join(result_parts)
        
        if word.quote_type is None:
            # Unquoted: perform word splitting
            return self._split_words(result)
        else:
            # Quoted: return as single word
            return result
    
    def _word_to_string(self, word) -> str:
        """Convert a Word AST node to a string without expansion."""
        from ..ast_nodes import LiteralPart, ExpansionPart
        
        parts = []
        for part in word.parts:
            if isinstance(part, LiteralPart):
                parts.append(part.text)
            elif isinstance(part, ExpansionPart):
                # In single quotes, expansions are literal
                parts.append(self._expansion_to_literal(part.expansion))
        return ''.join(parts)
    
    def _expansion_to_literal(self, expansion) -> str:
        """Convert an expansion to its literal representation."""
        from ..ast_nodes import VariableExpansion, CommandSubstitution, ParameterExpansion, ArithmeticExpansion
        
        if isinstance(expansion, VariableExpansion):
            return f"${expansion.name}"
        elif isinstance(expansion, CommandSubstitution):
            if expansion.backtick_style:
                return f"`{expansion.command}`"
            else:
                return f"$({expansion.command})"
        elif isinstance(expansion, ParameterExpansion):
            # Reconstruct parameter expansion syntax
            result = f"${{{expansion.parameter}"
            if expansion.operator:
                result += expansion.operator
                if expansion.word:
                    result += expansion.word
            result += "}"
            return result
        elif isinstance(expansion, ArithmeticExpansion):
            return f"$(({expansion.expression}))"
        else:
            return str(expansion)
    
    def _expand_expansion(self, expansion) -> str:
        """Evaluate an expansion AST node."""
        # Use ExpansionEvaluator for clean evaluation
        try:
            return self.evaluator.evaluate(expansion)
        except Exception as e:
            # Fallback to string representation if evaluation fails
            if self.state.options.get('debug-expansion'):
                print(f"[EXPANSION] Evaluation failed for {type(expansion).__name__}: {e}", file=self.state.stderr)
            return str(expansion)
    
    def _split_words(self, text: str) -> Union[str, List[str]]:
        """Split text on IFS characters for word splitting."""
        if not text:
            return text

        ifs = self.state.get_variable('IFS', ' \t\n')
        if not ifs:
            return text

        words = []
        current_word = ''

        for char in text:
            if char in ifs:
                if current_word:  # Don't add empty words
                    words.append(current_word)
                    current_word = ''
            else:
                current_word += char

        if current_word:  # Add final word if any
            words.append(current_word)

        # Return list only if we actually split into multiple words
        if len(words) > 1:
            return words
        elif len(words) == 1:
            return words[0]
        else:
            return ''  # Empty after splitting

    def _split_with_ifs(self, text: Optional[str], quote_type: Optional[str]) -> List[str]:
        """Split text using the current IFS, preserving quoting rules."""
        if text is None:
            return []

        if quote_type is not None:
            return [text]

        ifs = self.state.get_variable('IFS', ' \t\n')
        return self.word_splitter.split(text, ifs)
    
    def _process_single_word(self, word: str, arg_type: str, args: List[str]) -> None:
        """Process a single word through tilde expansion, escape processing, and globbing."""
        # Tilde expansion (only for unquoted words)
        if word.startswith('~') and arg_type == 'WORD':
            original = word
            word = self.expand_tilde(word)
            if self.state.options.get('debug-expansion-detail') and original != word:
                print(f"[EXPANSION]     Tilde expansion: '{original}' -> '{word}'", file=self.state.stderr)
        
        # Escape sequence processing (only for unquoted words)
        if arg_type == 'WORD' and '\\' in word:
            original = word
            word = self.process_escape_sequences(word)
            if self.state.options.get('debug-expansion-detail'):
                print(f"[EXPANSION]     Escape processing: '{original}' -> '{word}'", file=self.state.stderr)
        
        # Check if the argument contains unescaped glob characters and wasn't quoted (unless noglob is set)
        # Only expand if there are glob characters not preceded by NULL markers
        has_unescaped_globs = any(
            c in word and not (i > 0 and word[i-1] == '\x00')
            for i, c in enumerate(word) 
            if c in ['*', '?', '[']
        )
        
        if (has_unescaped_globs and arg_type != 'STRING' 
            and not self.state.options.get('noglob', False)):
            # Perform glob expansion (but clean NULL markers first for glob matching)
            import glob
            clean_word = word.replace('\x00', '')
            matches = self.glob_expander.expand(clean_word)
            if matches:
                # Sort matches for consistent output
                if self.state.options.get('debug-expansion-detail'):
                    print(f"[EXPANSION]     Glob expansion: '{clean_word}' -> {sorted(matches)}", file=self.state.stderr)
                args.extend(sorted(matches))
            else:
                # No matches, use literal argument (bash behavior)
                if self.state.options.get('debug-expansion-detail'):
                    print(f"[EXPANSION]     Glob expansion: '{clean_word}' -> no matches", file=self.state.stderr)
                # Clean NULL markers before adding
                args.append(clean_word)
        else:
            # Clean NULL markers before adding
            clean_word = word.replace('\x00', '')
            args.append(clean_word)
    
    def expand_string_variables(self, text: str, process_escapes: bool = True) -> str:
        """
        Expand variables and arithmetic in a string.
        Used for here strings and double-quoted strings.
        
        Args:
            text: The text to expand
            process_escapes: Whether to process escape sequences (default True)
        """
        return self.variable_expander.expand_string_variables(text, process_escapes)
    
    def process_escape_sequences(self, text: str) -> str:
        """Process escape sequences in unquoted words."""
        if not text or '\\' not in text:
            return text
        
        result = []
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                next_char = text[i + 1]
                # Special handling for glob characters to prevent expansion
                if next_char in '*?[':
                    # Use NULL marker to prevent glob expansion
                    result.append(f'\x00{next_char}')
                elif next_char == '$':
                    # Escaped dollar sign - just output the dollar
                    result.append('$')
                else:
                    # Regular escape processing (removes backslash)
                    result.append(next_char)
                i += 2
            else:
                result.append(text[i])
                i += 1
        
        return ''.join(result)
    
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
        """Execute arithmetic expansion and return result.
        
        Raises:
            ExpansionError: If arithmetic evaluation fails
        """
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
            # Raise exception to stop command execution (like bash)
            raise ExpansionError(f"arithmetic error: {e}")
        except Exception as e:
            import sys
            print(f"psh: unexpected arithmetic error: {e}", file=sys.stderr)
            # Raise exception to stop command execution (like bash)
            raise ExpansionError(f"unexpected arithmetic error: {e}")
    
    def _expand_command_subs_in_arithmetic(self, expr: str) -> str:
        """Expand command substitutions and nested arithmetic in arithmetic expression.
        
        This method finds all $(...) and $((...)) patterns in the arithmetic expression
        and replaces them with their evaluated output/result before arithmetic
        evaluation.
        
        Args:
            expr: The arithmetic expression potentially containing $(...) or $((...)
            
        Returns:
            The expression with all command substitutions and nested arithmetic expanded
        """
        result = []
        i = 0
        
        while i < len(expr):
            if expr[i] == '$' and i + 1 < len(expr) and expr[i + 1] == '(':
                # Check if it's arithmetic expansion $((...)) or command substitution $(...)
                if i + 2 < len(expr) and expr[i + 2] == '(':
                    # This is nested arithmetic expansion $((
                    # Find matching closing ))
                    paren_count = 2
                    j = i + 3
                    
                    while j < len(expr) and paren_count > 0:
                        if expr[j] == '(':
                            paren_count += 1
                        elif expr[j] == ')':
                            paren_count -= 1
                            if paren_count == 1 and j + 1 < len(expr) and expr[j + 1] == ')':
                                # Found closing ))
                                j += 1
                                paren_count = 0
                                break
                        j += 1
                    
                    if paren_count == 0:
                        # Valid arithmetic expansion found
                        arith_expr = expr[i:j+1]  # Include $((...))
                        
                        # Recursively execute the nested arithmetic expansion
                        arith_result = self.execute_arithmetic_expansion(arith_expr)
                        
                        # Append the result as a string
                        result.append(str(arith_result))
                        i = j + 1
                        continue
                else:
                    # This is command substitution $(
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
            
            # Not a command/arithmetic substitution, copy character as-is
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
