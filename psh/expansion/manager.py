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
        Expand all arguments in a command using Word AST nodes.

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
        return self._expand_word_ast_arguments(command)
    
    def _expand_word_ast_arguments(self, command: SimpleCommand) -> List[str]:
        """Expand arguments using Word AST nodes."""
        from ..ast_nodes import Word
        args = []

        # Debug: show pre-expansion words
        if self.state.options.get('debug-expansion'):
            print(f"[EXPANSION] Expanding Word AST command: {[str(w) for w in command.words]}", file=self.state.stderr)

        # Handle process substitutions — detect via Word AST
        has_proc_sub = self._has_process_substitution(command)
        if has_proc_sub:
            fds, substituted_args, child_pids = self.shell.io_manager.setup_process_substitutions(command)
            self.shell._process_sub_fds = fds
            self.shell._process_sub_pids = child_pids
            command.args = substituted_args
            command.arg_types = ['WORD'] * len(substituted_args)
            command.quote_types = [None] * len(substituted_args)
            command.words = [Word.from_string(a) for a in substituted_args]

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
        """Expand a Word AST node using per-part quote context.

        Uses structural information from Word parts instead of \\x00
        markers to determine glob suppression, word splitting, and
        tilde expansion behavior.

        Returns:
            Either a single string or a list of strings (for word splitting
            or ``$@`` expansion).
        """
        from ..ast_nodes import (
            Word, LiteralPart, ExpansionPart,
            VariableExpansion, CommandSubstitution,
            ParameterExpansion, ArithmeticExpansion,
        )

        if not isinstance(word, Word):
            return str(word)

        # Single-quoted word: no expansion at all
        if word.quote_type == "'":
            return self._word_to_string(word)

        # ANSI-C quoted word ($'...'): lexer already processed escapes, treat as literal
        if word.quote_type == "$'":
            return self._word_to_string(word)

        # Double-quoted word (uniform quote_type on the Word itself):
        # expand variables/commands but no word splitting or globbing
        if word.quote_type == '"':
            return self._expand_double_quoted_word(word)

        # --- Composite / unquoted word ---
        # Track properties needed for post-expansion steps
        has_unquoted_glob = False
        has_expansion = False
        has_unquoted_expansion = False
        all_parts_quoted = True
        result_parts: list = []

        for part in word.parts:
            if isinstance(part, LiteralPart):
                text = part.text
                if part.quoted and part.quote_char == "'":
                    # Single-quoted literal: completely literal
                    result_parts.append(text)
                elif part.quoted and part.quote_char == "$'":
                    # ANSI-C quoted literal: lexer already processed escapes
                    result_parts.append(text)
                elif part.quoted and part.quote_char == '"':
                    # Double-quoted literal: after WordBuilder decomposition,
                    # expansions are separate ExpansionPart nodes, so this
                    # LiteralPart is purely literal text.  But backslash
                    # escapes (\$, \\, \", \`) still need processing.
                    if '\\' in text:
                        text = self._process_dquote_escapes(text)
                    result_parts.append(text)
                else:
                    all_parts_quoted = False
                    had_escapes = False
                    # Process escape sequences in unquoted text
                    if '\\' in text:
                        had_escapes = True
                        text, escaped_globs = self._process_unquoted_escapes(text)
                        # If glob chars remain that weren't escaped, track them
                        if any(c in text for c in '*?[') and not escaped_globs:
                            has_unquoted_glob = True
                    else:
                        # Track unquoted glob chars
                        if any(c in text for c in '*?['):
                            has_unquoted_glob = True
                    # Unquoted literal: tilde on first part if leading ~
                    # Skip tilde expansion if ~ came from escape processing (\~)
                    if (not has_expansion and not result_parts
                            and text.startswith('~') and not had_escapes):
                        text = self.expand_tilde(text)
                    result_parts.append(text)

            elif isinstance(part, ExpansionPart):
                has_expansion = True
                expanded = self._expand_expansion(part.expansion)
                if part.quoted:
                    # Quoted expansion: no word splitting, no globbing on result
                    result_parts.append(expanded)
                else:
                    all_parts_quoted = False
                    has_unquoted_expansion = True
                    # Glob chars from unquoted expansion trigger globbing
                    if any(c in expanded for c in '*?['):
                        has_unquoted_glob = True
                    result_parts.append(expanded)

        result = ''.join(result_parts)

        # Word splitting: only if there are unquoted expansion results
        # but NOT for assignment words (VAR=value) per POSIX
        is_assignment = (len(word.parts) >= 1 and
                         isinstance(word.parts[0], LiteralPart) and
                         '=' in word.parts[0].text and
                         not word.parts[0].text.startswith('='))
        if has_unquoted_expansion and not is_assignment:
            words = self._split_with_ifs(result, None)
            if len(words) > 1:
                # Glob each split word if there are unquoted glob chars
                if has_unquoted_glob and not self.state.options.get('noglob', False):
                    return self._glob_words(words)
                return words
            elif len(words) == 1:
                result = words[0]
            else:
                return ''

        # Check for extglob patterns in unquoted text
        if not has_unquoted_glob and not all_parts_quoted and self.state.options.get('extglob', False):
            from .extglob import contains_extglob
            if contains_extglob(result):
                has_unquoted_glob = True

        # Glob expansion on the single result
        if has_unquoted_glob and not self.state.options.get('noglob', False):
            globbed = self._glob_words([result])
            if len(globbed) == 1:
                return globbed[0]
            return globbed

        return result
    
    def _expand_double_quoted_word(self, word) -> Union[str, List[str]]:
        """Expand a uniformly double-quoted Word (quote_type='"').

        Handles ``$@`` splitting and variable/command expansion but
        suppresses word splitting and globbing.
        """
        from ..ast_nodes import LiteralPart, ExpansionPart, VariableExpansion

        result_parts: list = []
        for part in word.parts:
            if isinstance(part, LiteralPart):
                # After WordBuilder decomposition, expansions are separate
                # ExpansionPart nodes, so LiteralPart text is purely literal.
                # But backslash escapes (\$, \\, \", \`) still need processing.
                text = part.text
                if '\\' in text:
                    text = self._process_dquote_escapes(text)
                result_parts.append(text)
            elif isinstance(part, ExpansionPart):
                exp = part.expansion
                # Handle "$@" splitting
                if isinstance(exp, VariableExpansion) and exp.name == '@':
                    params = list(self.state.positional_params)
                    if not params:
                        continue  # "$@" with no params produces nothing
                    # If there's surrounding text, distribute prefix/suffix
                    prefix = ''.join(result_parts)
                    result_parts.clear()
                    # Collect suffix parts
                    suffix_parts = []
                    found = False
                    for p2 in word.parts:
                        if p2 is part:
                            found = True
                            continue
                        if found:
                            if isinstance(p2, LiteralPart):
                                suffix_parts.append(p2.text)
                            elif isinstance(p2, ExpansionPart):
                                suffix_parts.append(self._expand_expansion(p2.expansion))
                    suffix = ''.join(suffix_parts)

                    if len(params) == 1:
                        return prefix + params[0] + suffix
                    words = [prefix + params[0]]
                    words.extend(params[1:-1])
                    words.append(params[-1] + suffix)
                    return words

                expanded = self._expand_expansion(exp)
                result_parts.append(expanded)

        return ''.join(result_parts)

    @staticmethod
    def _process_dquote_escapes(text: str) -> str:
        """Process backslash escapes in double-quoted literal text.

        In double quotes, only ``\\$``, ``\\\\``, ``\\"``, and ``\\``` are
        special escapes.  All other ``\\X`` sequences are kept literally.
        """
        result = []
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                nxt = text[i + 1]
                if nxt in ('$', '\\', '"', '`'):
                    result.append(nxt)
                    i += 2
                    continue
                elif nxt == '\n':
                    # Line continuation — drop both chars
                    i += 2
                    continue
            result.append(text[i])
            i += 1
        return ''.join(result)

    @staticmethod
    def _process_unquoted_escapes(text: str) -> tuple:
        """Process backslash escapes in unquoted literal text.

        Returns (processed_text, all_globs_escaped) where all_globs_escaped
        is True when glob chars were present but ALL were escaped (meaning
        the result should NOT trigger globbing).
        """
        result = []
        had_glob_chars = False
        all_globs_escaped = True
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                nxt = text[i + 1]
                if nxt in ('$', '\\', '`', '"', "'", '~', ' ', '\n'):
                    result.append(nxt)
                    i += 2
                    continue
                elif nxt in ('*', '?', '['):
                    # Escaped glob char: emit the literal char
                    had_glob_chars = True
                    result.append(nxt)
                    i += 2
                    continue
                else:
                    # Other backslash: remove backslash, keep char
                    result.append(nxt)
                    i += 2
                    continue
            if text[i] in ('*', '?', '['):
                # Unescaped glob char
                had_glob_chars = True
                all_globs_escaped = False
            result.append(text[i])
            i += 1
        return ''.join(result), had_glob_chars and all_globs_escaped

    def _glob_words(self, words: List[str]) -> List[str]:
        """Apply glob expansion to a list of words."""
        result = []
        check_extglob = self.state.options.get('extglob', False)
        for w in words:
            is_glob = any(c in w for c in '*?[')
            if not is_glob and check_extglob:
                from .extglob import contains_extglob
                is_glob = contains_extglob(w)
            if is_glob:
                matches = self.glob_expander.expand(w)
                if matches:
                    result.extend(sorted(matches))
                elif self.state.options.get('nullglob', False):
                    pass  # nullglob: no matches -> nothing
                else:
                    result.append(w)
            else:
                result.append(w)
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
    
    @staticmethod
    def _has_process_substitution(command: SimpleCommand) -> bool:
        """Check if a command has any process substitution arguments.

        Detects process substitution via the Word AST: process substitution
        arguments are stored as LiteralPart nodes with text starting with
        '<(' or '>('.
        """
        from ..ast_nodes import LiteralPart
        if not command.words:
            return False
        for word in command.words:
            if (len(word.parts) == 1 and
                    isinstance(word.parts[0], LiteralPart) and
                    not word.parts[0].quoted):
                text = word.parts[0].text
                if text.startswith('<(') or text.startswith('>('):
                    return True
        return False

    def _expand_expansion(self, expansion) -> str:
        """Evaluate an expansion AST node."""
        from ..core.exceptions import UnboundVariableError
        # Use ExpansionEvaluator for clean evaluation
        try:
            return self.evaluator.evaluate(expansion)
        except (ExpansionError, UnboundVariableError):
            raise  # Propagate expansion errors (e.g., ${var:?msg}, nounset)
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
        if ifs == '':
            return text

        words = self.word_splitter.split(text, ifs)

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
    
    def expand_string_variables(self, text: str, process_escapes: bool = True) -> str:
        """
        Expand variables and arithmetic in a string.
        Used for here strings and double-quoted strings.

        Args:
            text: The text to expand
            process_escapes: Whether to process escape sequences (default True)
        """
        return self.variable_expander.expand_string_variables(
            text, process_escapes
        )
    
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
