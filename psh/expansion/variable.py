"""Variable expansion implementation."""
import os
import sys
from typing import TYPE_CHECKING
from ..core.state import ShellState
from .parameter_expansion import ParameterExpansion

if TYPE_CHECKING:
    from ..shell import Shell


class VariableExpander:
    """Handles variable and parameter expansion."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.param_expansion = ParameterExpansion(shell)
    
    def expand_variable(self, var_expr: str) -> str:
        """Expand a variable expression starting with $"""
        
        if not var_expr.startswith('$'):
            return var_expr
        
        var_expr = var_expr[1:]  # Remove $
        
        # Handle ${var} syntax
        if var_expr.startswith('{') and var_expr.endswith('}'):
            var_content = var_expr[1:-1]
            
            # Check for advanced parameter expansion
            try:
                operator, var_name, operand = self.param_expansion.parse_expansion('${' + var_content + '}')
                
                if operator:
                    # Handle advanced expansions
                    # First get the variable value
                    if var_name == '#':
                        # Special case: ${#} is number of positional params
                        return str(len(self.state.positional_params))
                    elif var_name == '*':
                        # ${#*} - length of all positional params as string
                        if operator == '#':
                            return str(len(' '.join(self.state.positional_params)))
                        value = ' '.join(self.state.positional_params)
                    elif var_name == '@':
                        # ${#@} - length of all positional params as string
                        if operator == '#':
                            return str(len(' '.join(self.state.positional_params)))
                        value = ' '.join(self.state.positional_params)
                    elif var_name.isdigit():
                        # Positional parameter
                        index = int(var_name) - 1
                        value = self.state.positional_params[index] if 0 <= index < len(self.state.positional_params) else ''
                    else:
                        # Regular variable
                        value = self.state.variables.get(var_name, self.state.env.get(var_name, ''))
                    
                    # Apply the operation
                    if operator == '#' and not operand:
                        # Length operation (no operand means it's ${#var})
                        return self.param_expansion.get_length(value)
                    elif operator == '#' and operand:
                        # Remove shortest prefix (single # with pattern)
                        return self.param_expansion.remove_shortest_prefix(value, operand)
                    elif operator == '##':
                        # Remove longest prefix
                        return self.param_expansion.remove_longest_prefix(value, operand)
                    elif operator == '%%':
                        # Remove longest suffix
                        return self.param_expansion.remove_longest_suffix(value, operand)
                    elif operator == '%':
                        # Remove shortest suffix
                        return self.param_expansion.remove_shortest_suffix(value, operand)
                    elif operator == '//':
                        # Replace all
                        pattern, replacement = self._split_pattern_replacement(operand)
                        if pattern is not None:
                            return self.param_expansion.substitute_all(value, pattern, replacement)
                        else:
                            # Missing replacement
                            print(f"psh: ${{var//}}: missing replacement string", file=sys.stderr)
                            return value
                    elif operator == '/':
                        # Replace first
                        pattern, replacement = self._split_pattern_replacement(operand)
                        if pattern is not None:
                            return self.param_expansion.substitute_first(value, pattern, replacement)
                        else:
                            # Missing replacement
                            print(f"psh: ${{var/}}: missing replacement string", file=sys.stderr)
                            return value
                    elif operator == '/#':
                        # Replace prefix
                        pattern, replacement = self._split_pattern_replacement(operand)
                        if pattern is not None:
                            return self.param_expansion.substitute_prefix(value, pattern, replacement)
                        else:
                            print(f"psh: ${{var/#}}: missing replacement string", file=sys.stderr)
                            return value
                    elif operator == '/%':
                        # Replace suffix
                        pattern, replacement = self._split_pattern_replacement(operand)
                        if pattern is not None:
                            return self.param_expansion.substitute_suffix(value, pattern, replacement)
                        else:
                            print(f"psh: ${{var/%}}: missing replacement string", file=sys.stderr)
                            return value
                    elif operator == ':':
                        # Substring extraction
                        # Parse offset:length
                        if ':' in operand:
                            offset_str, length_str = operand.split(':', 1)
                            try:
                                offset = int(offset_str)
                                length = int(length_str)
                                return self.param_expansion.extract_substring(value, offset, length)
                            except ValueError:
                                print(f"psh: ${{var:{operand}}}: invalid offset or length", file=sys.stderr)
                                return ''
                        else:
                            # Just offset
                            try:
                                offset = int(operand)
                                return self.param_expansion.extract_substring(value, offset)
                            except ValueError:
                                print(f"psh: ${{var:{operand}}}: invalid offset", file=sys.stderr)
                                return ''
                    elif operator == '!*':
                        # Variable name matching
                        names = self.param_expansion.match_variable_names(operand, quoted=False)
                        return ' '.join(names)
                    elif operator == '!@':
                        # Variable name matching (quoted)
                        names = self.param_expansion.match_variable_names(operand, quoted=True)
                        return ' '.join(names)
                    elif operator == '^':
                        # Uppercase first
                        return self.param_expansion.uppercase_first(value, operand)
                    elif operator == '^^':
                        # Uppercase all
                        return self.param_expansion.uppercase_all(value, operand)
                    elif operator == ',':
                        # Lowercase first
                        return self.param_expansion.lowercase_first(value, operand)
                    elif operator == ',,':
                        # Lowercase all
                        return self.param_expansion.lowercase_all(value, operand)
            except Exception:
                # If parsing fails, fall back to default behavior
                pass
            
            # Handle ${var:-default} syntax
            if ':-' in var_content:
                var_name, default = var_content.split(':-', 1)
                value = self.state.variables.get(var_name, self.state.env.get(var_name, ''))
                return value if value else default
            else:
                var_name = var_content
        else:
            var_name = var_expr
        
        # Special variables
        if var_name == '?':
            return str(self.state.last_exit_code)
        elif var_name == '$':
            return str(os.getpid())
        elif var_name == '!':
            return str(self.state.last_bg_pid) if self.state.last_bg_pid else ''
        elif var_name == '#':
            return str(len(self.state.positional_params))
        elif var_name == '0':
            return self.state.script_name  # Shell or script name
        elif var_name == '@':
            # When in a string context (like echo "$@"), don't add quotes
            # The quotes are only added when $@ is unquoted
            return ' '.join(self.state.positional_params)
        elif var_name == '*':
            # Expand to single word
            return ' '.join(self.state.positional_params)
        elif var_name.isdigit():
            # Positional parameter
            index = int(var_name) - 1
            if 0 <= index < len(self.state.positional_params):
                return self.state.positional_params[index]
            return ''
        
        # Regular variables - check shell variables first, then environment
        result = self.state.variables.get(var_name, self.state.env.get(var_name, ''))
        
        
        return result
    
    def expand_string_variables(self, text: str) -> str:
        """Expand variables and arithmetic in a string (for here strings and quoted strings)"""
        
        result = []
        i = 0
        while i < len(text):
            if text[i] == '$' and i + 1 < len(text):
                if text[i + 1] == '(' and i + 2 < len(text) and text[i + 2] == '(':
                    # $((...)) arithmetic expansion
                    # Find the matching ))
                    paren_count = 0
                    j = i + 3  # Start after $((
                    while j < len(text):
                        if text[j] == '(':
                            paren_count += 1
                        elif text[j] == ')':
                            if paren_count == 0 and j + 1 < len(text) and text[j + 1] == ')':
                                # Found the closing ))
                                arith_expr = text[i:j + 2]  # Include $((...)))
                                result.append(str(self.shell.expansion_manager.execute_arithmetic_expansion(arith_expr)))
                                i = j + 2
                                break
                            else:
                                paren_count -= 1
                        j += 1
                    else:
                        # No matching )) found, treat as literal
                        result.append(text[i])
                        i += 1
                    continue
                elif text[i + 1] == '(':
                    # $(...) command substitution
                    # Find the matching )
                    paren_count = 1
                    j = i + 2
                    while j < len(text) and paren_count > 0:
                        if text[j] == '(':
                            paren_count += 1
                        elif text[j] == ')':
                            paren_count -= 1
                        j += 1
                    if paren_count == 0:
                        # Found the matching )
                        cmd_sub = text[i:j]  # Include $(...)
                        output = self.shell.expansion_manager.command_sub.execute(cmd_sub)
                        # In string context, preserve the output as-is
                        result.append(output)
                        i = j
                        continue
                elif text[i + 1] == '{':
                    # ${var} or ${var:-default}
                    j = i + 2
                    brace_count = 1
                    while j < len(text) and brace_count > 0:
                        if text[j] == '{':
                            brace_count += 1
                        elif text[j] == '}':
                            brace_count -= 1
                        j += 1
                    if brace_count == 0:
                        var_expr = text[i:j]  # Include ${...}
                        expanded = self.expand_variable(var_expr)
                        result.append(expanded)
                        i = j
                        continue
                else:
                    # Simple variable like $var
                    j = i + 1
                    # Special single-char variables
                    if j < len(text) and text[j] in '?$!#@*0123456789':
                        var_expr = text[i:j + 1]
                        result.append(self.expand_variable(var_expr))
                        i = j + 1
                        continue
                    # Regular variable name
                    while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                        j += 1
                    if j > i + 1:
                        var_expr = text[i:j]
                        result.append(self.expand_variable(var_expr))
                        i = j
                        continue
            elif text[i] == '`':
                # Backtick command substitution
                j = i + 1
                while j < len(text) and text[j] != '`':
                    if text[j] == '\\' and j + 1 < len(text):
                        j += 2  # Skip escaped character
                    else:
                        j += 1
                if j < len(text) and text[j] == '`':
                    cmd_sub = text[i:j + 1]  # Include `...`
                    output = self.shell.expansion_manager.command_sub.execute(cmd_sub)
                    result.append(output)
                    i = j + 1
                    continue
            elif text[i] == '\\' and i + 1 < len(text):
                # Handle escape sequences
                next_char = text[i + 1]
                if next_char in 'abfnrtv':
                    # Standard escape sequences
                    escape_map = {
                        'a': '\a', 'b': '\b', 'f': '\f',
                        'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'
                    }
                    result.append(escape_map[next_char])
                    i += 2
                    continue
                elif next_char == '\\':
                    result.append('\\')
                    i += 2
                    continue
                elif next_char in '"$`':
                    # In double quotes, only these need escaping
                    result.append(next_char)
                    i += 2
                    continue
            
            result.append(text[i])
            i += 1
        
        return ''.join(result)
    
    def _split_pattern_replacement(self, operand: str):
        """Split pattern/replacement handling escaped slashes."""
        i = 0
        pattern_parts = []
        
        while i < len(operand):
            if i + 1 < len(operand) and operand[i:i+2] == '\\/':
                pattern_parts.append('\\/')
                i += 2
            elif operand[i] == '/':
                # Found separator
                pattern = ''.join(pattern_parts)
                replacement = operand[i+1:] if i+1 < len(operand) else ''
                return pattern, replacement
            else:
                pattern_parts.append(operand[i])
                i += 1
        
        # No separator found
        return None, None