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
            
            # Check for special array expansions first
            # Handle ${#arr[@]} or ${#arr[index]} - array length or element length
            if var_content.startswith('#') and '[' in var_content and var_content.endswith(']'):
                array_part = var_content[1:]  # Remove the #
                bracket_pos = array_part.find('[')
                array_name = array_part[:bracket_pos]
                index_expr = array_part[bracket_pos+1:-1]  # Remove [ and ]
                
                if index_expr == '@' or index_expr == '*':
                    # Get the array variable
                    from ..core.variables import IndexedArray, AssociativeArray
                    var = self.state.scope_manager.get_variable_object(array_name)
                    
                    if var and isinstance(var.value, (IndexedArray, AssociativeArray)):
                        # Return the number of elements
                        return str(var.value.length())
                    elif var and var.value:
                        # Regular variable with value - treat as single element
                        return '1'
                    else:
                        # Not an array or no value, return 0
                        return '0'
                else:
                    # ${#arr[index]} - length of specific element
                    from ..core.variables import IndexedArray, AssociativeArray
                    var = self.state.scope_manager.get_variable_object(array_name)
                    
                    if var and isinstance(var.value, IndexedArray):
                        # Evaluate the index
                        expanded_index = self.expand_array_index(index_expr)
                        try:
                            # Check if it's arithmetic
                            if any(op in expanded_index for op in ['+', '-', '*', '/', '%', '(', ')']):
                                from ..arithmetic import evaluate_arithmetic
                                index = evaluate_arithmetic(expanded_index, self.shell)
                            else:
                                index = int(expanded_index)
                            
                            element = var.value.get(index)
                            return str(len(element)) if element else '0'
                        except:
                            return '0'
                    elif var and isinstance(var.value, AssociativeArray):
                        # For associative arrays
                        expanded_key = self.expand_array_index(index_expr)
                        element = var.value.get(expanded_key)
                        return str(len(element)) if element else '0'
                    elif var and var.value:
                        # Regular variable - check if index is 0
                        try:
                            index = int(self.expand_array_index(index_expr))
                            if index == 0:
                                return str(len(str(var.value)))
                            else:
                                return '0'
                        except:
                            return '0'
                    else:
                        return '0'
            
            # Handle ${!arr[@]} - array indices  
            # Remove escaped ! if present
            if var_content.startswith('\\!'):
                var_content = var_content[1:]  # Remove the backslash
            
            if var_content.startswith('!') and '[' in var_content and var_content.endswith(']'):
                array_part = var_content[1:]  # Remove the !
                bracket_pos = array_part.find('[')
                array_name = array_part[:bracket_pos]
                index_expr = array_part[bracket_pos+1:-1]  # Remove [ and ]
                
                if index_expr == '@' or index_expr == '*':
                    # Get the array variable
                    from ..core.variables import IndexedArray, AssociativeArray
                    var = self.state.scope_manager.get_variable_object(array_name)
                    
                    if var and isinstance(var.value, IndexedArray):
                        # Return the indices as space-separated list
                        indices = var.value.indices()
                        # print(f"DEBUG: Array {array_name} indices: {indices}", file=sys.stderr)
                        return ' '.join(str(i) for i in indices)
                    elif var and isinstance(var.value, AssociativeArray):
                        # Return the keys as space-separated list
                        keys = var.value.keys()
                        return ' '.join(keys)
                    elif var and var.value:
                        # Regular variable - has index 0
                        return '0'
                    else:
                        # Not an array or no value, return empty
                        return ''
            
            # Check for array slicing first: ${arr[@]:start:length}
            if ':' in var_content and '[' in var_content and ']' in var_content:
                # This might be array slicing
                bracket_pos = var_content.find('[')
                close_bracket_pos = var_content.find(']')
                
                if bracket_pos < close_bracket_pos and close_bracket_pos < var_content.find(':'):
                    # Format is ${arr[@]:start:length} or ${arr[@]:start}
                    array_name = var_content[:bracket_pos]
                    index_expr = var_content[bracket_pos+1:close_bracket_pos]
                    slice_part = var_content[close_bracket_pos+1:]  # Should start with :
                    
                    if slice_part.startswith(':') and (index_expr == '@' or index_expr == '*'):
                        # This is array slicing
                        from ..core.variables import IndexedArray, AssociativeArray
                        var = self.state.scope_manager.get_variable_object(array_name)
                        
                        if var and isinstance(var.value, IndexedArray):
                            # Parse the slice parameters
                            slice_params = slice_part[1:].split(':', 1)  # Remove leading :
                            
                            try:
                                # Expand and evaluate start
                                start_str = self.expand_string_variables(slice_params[0])
                                if any(op in start_str for op in ['+', '-', '*', '/', '%', '(', ')']):
                                    from ..arithmetic import evaluate_arithmetic
                                    start = evaluate_arithmetic(start_str, self.shell)
                                else:
                                    start = int(start_str)
                                
                                # Get all elements
                                all_indices = var.value.indices()
                                if not all_indices:
                                    return ''
                                
                                # Convert negative start to positive
                                if start < 0:
                                    start = len(all_indices) + start
                                    if start < 0:
                                        start = 0
                                
                                # Handle length if provided
                                if len(slice_params) > 1:
                                    length_str = self.expand_string_variables(slice_params[1])
                                    if any(op in length_str for op in ['+', '-', '*', '/', '%', '(', ')']):
                                        from ..arithmetic import evaluate_arithmetic
                                        length = evaluate_arithmetic(length_str, self.shell)
                                    else:
                                        length = int(length_str)
                                    
                                    # Extract elements
                                    result_elements = []
                                    count = 0
                                    for i, idx in enumerate(all_indices):
                                        if i >= start and count < length:
                                            elem = var.value.get(idx)
                                            if elem is not None:
                                                result_elements.append(elem)
                                                count += 1
                                else:
                                    # No length specified, take from start to end
                                    result_elements = []
                                    for i, idx in enumerate(all_indices):
                                        if i >= start:
                                            elem = var.value.get(idx)
                                            if elem is not None:
                                                result_elements.append(elem)
                                
                                return ' '.join(result_elements)
                            except:
                                return ''
                        elif var and var.value:
                            # Regular variable - treat as single element array
                            try:
                                start = int(self.expand_string_variables(slice_params[0]))
                                if start == 0:
                                    if len(slice_params) > 1:
                                        length = int(self.expand_string_variables(slice_params[1]))
                                        if length > 0:
                                            return str(var.value)
                                        else:
                                            return ''
                                    else:
                                        return str(var.value)
                                else:
                                    return ''
                            except:
                                return ''
                        else:
                            return ''
            
            # Check for array subscript syntax: ${arr[index]}
            # But exclude case modification patterns like ${var^^[pattern]}
            if ('[' in var_content and var_content.endswith(']') and 
                not any(op in var_content for op in ['^^', ',,', '^', ','])):
                bracket_pos = var_content.find('[')
                array_name = var_content[:bracket_pos]
                index_expr = var_content[bracket_pos+1:-1]  # Remove [ and ]
                
                # Get the array variable
                from ..core.variables import IndexedArray, AssociativeArray
                var = self.state.scope_manager.get_variable_object(array_name)
                
                # Handle special array expansions
                if index_expr == '@' or index_expr == '*':
                    # ${arr[@]} or ${arr[*]} - expand to all array elements
                    if var and isinstance(var.value, (IndexedArray, AssociativeArray)):
                        elements = var.value.all_elements()
                        if index_expr == '@':
                            # ${arr[@]} - each element as separate word (for word splitting)
                            # In string context, join with spaces
                            return ' '.join(elements)
                        else:
                            # ${arr[*]} - all elements as single word joined with IFS
                            ifs = self.state.get_variable('IFS', ' \t\n')
                            separator = ifs[0] if ifs else ' '
                            return separator.join(elements)
                    elif var and var.value:
                        # Regular variable accessed as array - return the value
                        return str(var.value)
                    else:
                        # Not an array or doesn't exist
                        return ''
                
                # Handle regular indexed access
                if var and isinstance(var.value, IndexedArray):
                    # Evaluate the index expression (might contain variables or arithmetic)
                    expanded_index = self.expand_array_index(index_expr)
                    
                    try:
                        # Check if it's an arithmetic expression
                        if any(op in expanded_index for op in ['+', '-', '*', '/', '%', '(', ')']):
                            # Evaluate as arithmetic
                            from ..arithmetic import evaluate_arithmetic, ArithmeticError
                            try:
                                index = evaluate_arithmetic(expanded_index, self.shell)
                            except (ArithmeticError, Exception):
                                return ''
                        else:
                            # Direct integer conversion
                            index = int(expanded_index)
                        
                        result = var.value.get(index)
                        return result if result is not None else ''
                    except ValueError:
                        # Bash compatibility: treat string indices on indexed arrays as index 0
                        result = var.value.get(0)
                        return result if result is not None else ''
                elif var and isinstance(var.value, AssociativeArray):
                    # For associative arrays, use the key as-is
                    expanded_key = self.expand_array_index(index_expr)
                    result = var.value.get(expanded_key)
                    return result if result is not None else ''
                elif var and var.value:
                    # Regular variable - treat as single element array
                    expanded_index = self.expand_array_index(index_expr)
                    try:
                        index = int(expanded_index)
                        # Only index 0 is valid for regular variables
                        if index == 0:
                            return str(var.value)
                        else:
                            return ''
                    except ValueError:
                        # Invalid index
                        return ''
                else:
                    # Variable doesn't exist
                    return ''
            
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
                        # ${#*} - number of positional parameters
                        if operator == '#':
                            return str(len(self.state.positional_params))
                        value = ' '.join(self.state.positional_params)
                    elif var_name == '@':
                        # ${#@} - number of positional parameters
                        if operator == '#':
                            return str(len(self.state.positional_params))
                        value = ' '.join(self.state.positional_params)
                    elif var_name.isdigit():
                        # Positional parameter
                        index = int(var_name) - 1
                        value = self.state.positional_params[index] if 0 <= index < len(self.state.positional_params) else ''
                    elif '[' in var_name and var_name.endswith(']'):
                        # Array element with parameter expansion
                        bracket_pos = var_name.find('[')
                        array_name = var_name[:bracket_pos]
                        index_expr = var_name[bracket_pos+1:-1]
                        
                        from ..core.variables import IndexedArray, AssociativeArray
                        var = self.state.scope_manager.get_variable_object(array_name)
                        
                        # Handle special indices @ and * for whole-array operations
                        if index_expr in ('@', '*'):
                            if var and isinstance(var.value, (IndexedArray, AssociativeArray)):
                                elements = var.value.all_elements()
                            elif var and var.value:
                                # Regular variable treated as single-element array
                                elements = [str(var.value)]
                            else:
                                elements = []
                            
                            # Apply parameter expansion to each element
                            results = []
                            for element in elements:
                                # Apply the operation to this element
                                if operator == '#' and not operand:
                                    # Length operation
                                    result = self.param_expansion.get_length(element)
                                elif operator == '#' and operand:
                                    # Remove shortest prefix
                                    result = self.param_expansion.remove_shortest_prefix(element, operand)
                                elif operator == '##':
                                    # Remove longest prefix
                                    result = self.param_expansion.remove_longest_prefix(element, operand)
                                elif operator == '%%':
                                    # Remove longest suffix
                                    result = self.param_expansion.remove_longest_suffix(element, operand)
                                elif operator == '%':
                                    # Remove shortest suffix
                                    result = self.param_expansion.remove_shortest_suffix(element, operand)
                                elif operator == '//':
                                    # Replace all
                                    pattern, replacement = self._split_pattern_replacement(operand)
                                    if pattern is not None:
                                        result = self.param_expansion.substitute_all(element, pattern, replacement)
                                    else:
                                        result = element
                                elif operator == '/':
                                    # Replace first
                                    pattern, replacement = self._split_pattern_replacement(operand)
                                    if pattern is not None:
                                        result = self.param_expansion.substitute_first(element, pattern, replacement)
                                    else:
                                        result = element
                                elif operator == '/#':
                                    # Replace prefix
                                    pattern, replacement = self._split_pattern_replacement(operand)
                                    if pattern is not None:
                                        result = self.param_expansion.substitute_prefix(element, pattern, replacement)
                                    else:
                                        result = element
                                elif operator == '/%':
                                    # Replace suffix
                                    pattern, replacement = self._split_pattern_replacement(operand)
                                    if pattern is not None:
                                        result = self.param_expansion.substitute_suffix(element, pattern, replacement)
                                    else:
                                        result = element
                                elif operator == '^^':
                                    # Uppercase all characters
                                    if operand:
                                        # Pattern-based uppercase
                                        result = self.param_expansion.uppercase_all(element, operand)
                                    else:
                                        result = self.param_expansion.uppercase_all(element)
                                elif operator == ',,':
                                    # Lowercase all characters
                                    if operand:
                                        # Pattern-based lowercase
                                        result = self.param_expansion.lowercase_all(element, operand)
                                    else:
                                        result = self.param_expansion.lowercase_all(element)
                                elif operator == '^':
                                    # Uppercase first character
                                    if operand:
                                        # Pattern-based uppercase first
                                        result = self.param_expansion.uppercase_first(element, operand)
                                    else:
                                        result = self.param_expansion.uppercase_first(element)
                                elif operator == ',':
                                    # Lowercase first character
                                    if operand:
                                        # Pattern-based lowercase first
                                        result = self.param_expansion.lowercase_first(element, operand)
                                    else:
                                        result = self.param_expansion.lowercase_first(element)
                                else:
                                    # Default: return element unchanged for unknown operators
                                    result = element
                                results.append(result)
                            
                            # Join results (@ uses space, * uses first char of IFS)
                            if index_expr == '@':
                                return ' '.join(results)
                            else:  # index_expr == '*'
                                ifs = self.state.get_variable('IFS', ' \t\n')
                                separator = ifs[0] if ifs else ' '
                                return separator.join(results)
                        
                        # Handle regular indexed/associative array access
                        elif var and isinstance(var.value, IndexedArray):
                            # Evaluate index
                            expanded_index = self.expand_array_index(index_expr)
                            try:
                                if any(op in expanded_index for op in ['+', '-', '*', '/', '%', '(', ')']):
                                    from ..arithmetic import evaluate_arithmetic
                                    index = evaluate_arithmetic(expanded_index, self.shell)
                                else:
                                    index = int(expanded_index)
                                value = var.value.get(index) or ''
                            except:
                                value = ''
                        elif var and isinstance(var.value, AssociativeArray):
                            expanded_key = self.expand_array_index(index_expr)
                            value = var.value.get(expanded_key) or ''
                        else:
                            value = ''
                    else:
                        # Regular variable - use get_variable which checks scope manager
                        value = self.state.get_variable(var_name, '')
                    
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
                value = self._get_var_or_positional(var_name)
                if not value:
                    # Expand variables in the default value
                    return self.expand_string_variables(default)
                return value
            # Handle ${var:=default} syntax (assign default if unset)
            elif ':=' in var_content:
                var_name, default = var_content.split(':=', 1)
                value = self._get_var_or_positional(var_name)
                if not value:
                    # Expand the default value first
                    expanded_default = self.expand_string_variables(default)
                    # Can't assign to positional parameters
                    if not var_name.isdigit():
                        self.state.set_variable(var_name, expanded_default)
                    return expanded_default
                return value
            # Handle ${var:?message} syntax (error if unset)
            elif ':?' in var_content:
                var_name, message = var_content.split(':?', 1)
                value = self._get_var_or_positional(var_name)
                if not value:
                    # Expand the error message
                    expanded_message = self.expand_string_variables(message) if message else "parameter null or not set"
                    # Write error to stderr and set exit code
                    import sys
                    print(f"psh: {var_name}: {expanded_message}", file=sys.stderr)
                    self.state.last_exit_code = 1
                    # In a non-interactive shell, this should exit
                    # For now, just return empty string and let the caller handle the error
                    from ..core.exceptions import ExpansionError
                    raise ExpansionError(f"{var_name}: {expanded_message}")
                return value
            # Handle ${var:+alternative} syntax
            elif ':+' in var_content:
                var_name, alternative = var_content.split(':+', 1)
                value = self._get_var_or_positional(var_name)
                if value:
                    # Expand variables in the alternative value
                    return self.expand_string_variables(alternative)
                return ''
            else:
                var_name = var_content
                
                # Check nounset for simple ${var} expansion
                if self.state.options.get('nounset', False):
                    from ..core.options import OptionHandler
                    from ..core.exceptions import UnboundVariableError
                    try:
                        OptionHandler.check_unset_variable(self.state, var_name)
                    except UnboundVariableError:
                        raise UnboundVariableError(f"psh: ${{{var_name}}}: unbound variable")
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
        elif var_name == '-':
            return self.state.get_option_string()
        elif var_name == '0':
            # If in a function, return function name; otherwise script name
            if self.state.function_stack:
                return self.state.function_stack[-1]
            return self.state.script_name  # Shell or script name
        elif var_name == '@':
            # When in a string context (like echo "$@"), don't add quotes
            # The quotes are only added when $@ is unquoted
            return ' '.join(self.state.positional_params)
        elif var_name == '*':
            # Expand to single word joined with first character of IFS
            ifs = self.state.get_variable('IFS', ' \t\n')
            separator = ifs[0] if ifs else ' '
            return separator.join(self.state.positional_params)
        elif var_name.isdigit():
            # Positional parameter
            index = int(var_name) - 1
            if 0 <= index < len(self.state.positional_params):
                return self.state.positional_params[index]
            return ''
        
        # Regular variables - check shell variables first, then environment
        result = self.state.get_variable(var_name, '')
        
        # Check nounset option
        if self.state.options.get('nounset', False):
            from ..core.options import OptionHandler
            from ..core.exceptions import UnboundVariableError
            try:
                OptionHandler.check_unset_variable(self.state, var_name)
            except UnboundVariableError:
                # Re-raise with proper formatting for variable expansion
                raise UnboundVariableError(f"psh: ${var_name}: unbound variable")
        
        return result
    
    def _get_var_or_positional(self, var_name: str) -> str:
        """Get value of a variable or positional parameter."""
        if var_name.isdigit():
            index = int(var_name) - 1
            if 0 <= index < len(self.state.positional_params):
                return self.state.positional_params[index]
            return ''
        elif var_name in ['#', '?', '$', '!', '@', '*', '0', '-']:
            # Special variables
            return self.state.get_special_variable(var_name)
        else:
            return self.state.get_variable(var_name, '')
    
    def expand_array_index(self, index_expr: str) -> str:
        """Expand variables in array index expressions.
        
        In array subscripts, bare variable names should be expanded as variables.
        For example, in ${arr[i]}, 'i' should be expanded to its value.
        """
        # First try normal variable expansion in case it has $
        expanded = self.expand_string_variables(index_expr)
        
        # If no $ was found in the index, check if the whole thing is a variable name
        if expanded == index_expr:
            # Check if it's a valid variable name (letters, digits, underscore)
            if index_expr and (index_expr[0].isalpha() or index_expr[0] == '_'):
                if all(c.isalnum() or c == '_' for c in index_expr):
                    # It's a valid variable name, expand it
                    var_value = self.state.get_variable(index_expr, '')
                    if var_value:
                        return var_value
        
        return expanded

    def expand_string_variables(self, text: str, process_escapes: bool = True) -> str:
        """Expand variables and arithmetic in a string (for here strings and quoted strings)
        
        Args:
            text: The text to expand
            process_escapes: Whether to process escape sequences like \\n, \\t (default True)
                           Set to False for array contexts where escapes should be literal
        """
        
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
                                arith_result = self.shell.expansion_manager.execute_arithmetic_expansion(arith_expr)
                                result.append(str(arith_result))
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
                # Note: Standard C escape sequences like \n, \t are NOT processed in shell strings
                # They remain as literal \n, \t for compatibility with prompt expansion
                # Only backslash before special shell characters is processed
                if next_char == '\\':
                    result.append('\\')
                    i += 2
                    continue
                elif next_char in '"$`':
                    # In double quotes, these characters can be escaped
                    # But for $ and `, we need to check if they're actually escaping something
                    if next_char == '$':
                        # Check if this is escaping a variable expansion
                        if i + 2 < len(text) and (text[i + 2].isalnum() or text[i + 2] in '_${(@#*!?'):
                            # This is escaping a variable expansion, remove the backslash
                            result.append(next_char)
                            i += 2
                            continue
                        else:
                            # Not escaping a variable, keep the backslash (for PS1 compatibility)
                            result.append(text[i])
                            i += 1
                            continue
                    else:
                        # For " and `, always remove the backslash
                        result.append(next_char)
                        i += 2
                        continue
            
            result.append(text[i])
            i += 1
        
        return ''.join(result)
    
    def is_array_expansion(self, var_expr: str) -> bool:
        """Check if this is an array expansion that produces multiple words."""
        if not var_expr.startswith('$'):
            return False
        
        var_expr = var_expr[1:]  # Remove $
        
        # Check for $@ (positional parameters expansion)
        if var_expr == '@':
            return True
        
        # Check for ${arr[@]} syntax
        if var_expr.startswith('{') and var_expr.endswith('}'):
            var_content = var_expr[1:-1]
            
            # Special expansions that don't produce multiple words
            if var_content.startswith('#'):
                # ${#arr[@]} produces single word
                return False
            
            # ${!arr[@]} produces multiple words (array indices)
            # Handle escaped ! if present
            check_content = var_content
            if check_content.startswith('\\!'):
                check_content = check_content[1:]  # Remove the backslash
            
            if check_content.startswith('!') and '[' in check_content and check_content.endswith(']'):
                bracket_pos = check_content.find('[')
                index_expr = check_content[bracket_pos+1:-1]
                if index_expr == '@' or index_expr == '*':
                    return True  # This is array indices expansion
                return False  # Other ! expansions are single words
            
            # Check for array subscript with @ 
            if '[' in var_content and var_content.endswith(']'):
                bracket_pos = var_content.find('[')
                index_expr = var_content[bracket_pos+1:-1]
                return index_expr == '@'
        
        return False
    
    def expand_array_to_list(self, var_expr: str) -> list:
        """Expand an array variable to a list of words for ${arr[@]} syntax."""
        if not var_expr.startswith('$'):
            return [var_expr]
        
        var_expr = var_expr[1:]  # Remove $
        
        # Handle $@ (positional parameters)
        if var_expr == '@':
            return list(self.state.positional_params)
        
        # Handle ${var} syntax
        if var_expr.startswith('{') and var_expr.endswith('}'):
            var_content = var_expr[1:-1]
            
            # Check for array indices expansion: ${!arr[@]}
            # Handle escaped ! if present
            check_content = var_content
            if check_content.startswith('\\!'):
                check_content = check_content[1:]  # Remove the backslash
            
            if check_content.startswith('!') and '[' in check_content and check_content.endswith(']'):
                array_part = check_content[1:]  # Remove the !
                bracket_pos = array_part.find('[')
                array_name = array_part[:bracket_pos]
                index_expr = array_part[bracket_pos+1:-1]  # Remove [ and ]
                
                if index_expr == '@' or index_expr == '*':
                    # Get the array variable
                    from ..core.variables import IndexedArray, AssociativeArray
                    var = self.state.scope_manager.get_variable_object(array_name)
                    
                    if var and isinstance(var.value, IndexedArray):
                        # Return the indices as list of strings
                        indices = var.value.indices()
                        return [str(i) for i in indices]
                    elif var and isinstance(var.value, AssociativeArray):
                        # Return the keys as list
                        return var.value.keys()
                    elif var and var.value:
                        # Regular variable - has index 0
                        return ['0']
                    else:
                        # Not an array or no value, return empty
                        return []
            
            # Check for array subscript syntax: ${arr[index]}
            if '[' in var_content and var_content.endswith(']'):
                bracket_pos = var_content.find('[')
                array_name = var_content[:bracket_pos]
                index_expr = var_content[bracket_pos+1:-1]  # Remove [ and ]
                
                if index_expr == '@':
                    # Get the array variable
                    from ..core.variables import IndexedArray, AssociativeArray
                    var = self.state.scope_manager.get_variable_object(array_name)
                    
                    if var and isinstance(var.value, (IndexedArray, AssociativeArray)):
                        # Return elements as list
                        return var.value.all_elements()
                    elif var and var.value:
                        # Regular variable - return as single element list
                        return [str(var.value)]
                    else:
                        return []
        
        # Not an array expansion, return single element
        return [self.expand_variable('$' + var_expr)]
    
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