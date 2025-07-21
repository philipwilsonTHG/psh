"""Expansion evaluator for Word AST nodes.

This module evaluates expansion AST nodes to produce strings,
providing a clean separation between parsing and evaluation.
"""

from typing import TYPE_CHECKING, Optional
import os
import sys

from ..ast_nodes import (
    Expansion, VariableExpansion, CommandSubstitution,
    ParameterExpansion, ArithmeticExpansion
)
from ..core.exceptions import ExpansionError

if TYPE_CHECKING:
    from ..shell import Shell


class ExpansionEvaluator:
    """Evaluates expansion AST nodes to produce strings."""
    
    # Special variables that need custom handling
    SPECIAL_VARS = {'?', '$', '!', '#', '@', '*', '0', '-'}
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
    
    def evaluate(self, expansion: Expansion) -> str:
        """Evaluate any expansion type.
        
        Args:
            expansion: The expansion AST node to evaluate
            
        Returns:
            The expanded string value
            
        Raises:
            ExpansionError: If expansion fails
            ValueError: If expansion type is unknown
        """
        if isinstance(expansion, VariableExpansion):
            return self._evaluate_variable(expansion)
        elif isinstance(expansion, CommandSubstitution):
            return self._evaluate_command_sub(expansion)
        elif isinstance(expansion, ParameterExpansion):
            return self._evaluate_parameter(expansion)
        elif isinstance(expansion, ArithmeticExpansion):
            return self._evaluate_arithmetic(expansion)
        else:
            raise ValueError(f"Unknown expansion type: {type(expansion)}")
    
    def _evaluate_variable(self, expansion: VariableExpansion) -> str:
        """Evaluate simple variable expansion.
        
        Args:
            expansion: VariableExpansion node
            
        Returns:
            The variable's value or empty string if unset
        """
        name = expansion.name
        
        # Handle special variables
        if name in self.SPECIAL_VARS:
            return self._get_special_var(name)
        
        # Handle positional parameters
        if name.isdigit():
            params = self.state.positional_params
            index = int(name) - 1
            return params[index] if 0 <= index < len(params) else ''
        
        # Regular variables
        value = self.state.scope_manager.get_variable(name)
        return str(value) if value is not None else ''
    
    def _get_special_var(self, name: str) -> str:
        """Get value of special shell variable.
        
        Args:
            name: Special variable name (?, $, !, #, @, *, 0, -)
            
        Returns:
            The variable's value
        """
        if name == '?':
            return str(self.state.last_exit_code)
        elif name == '$':
            return str(os.getpid())
        elif name == '!':
            return str(self.state.last_bg_pid) if self.state.last_bg_pid else ''
        elif name == '#':
            return str(len(self.state.positional_params))
        elif name == '-':
            return self.state.get_option_string()
        elif name == '0':
            # If in a function, return function name; otherwise script name
            if self.state.function_stack:
                return self.state.function_stack[-1]
            return self.state.script_name
        elif name == '@':
            # When in expansion context, join with spaces
            return ' '.join(self.state.positional_params)
        elif name == '*':
            # Join with first character of IFS
            ifs = self.state.get_variable('IFS', ' \t\n')
            separator = ifs[0] if ifs else ' '
            return separator.join(self.state.positional_params)
        else:
            return ''
    
    def _evaluate_command_sub(self, expansion: CommandSubstitution) -> str:
        """Evaluate command substitution.
        
        Args:
            expansion: CommandSubstitution node
            
        Returns:
            The command output with trailing newlines removed
        """
        # Reconstruct the command substitution syntax
        if expansion.backtick_style:
            cmd_sub = f"`{expansion.command}`"
        else:
            cmd_sub = f"$({expansion.command})"
        
        # Use expansion manager's existing implementation
        return self.expansion_manager.command_sub.execute(cmd_sub)
    
    def _evaluate_parameter(self, expansion: ParameterExpansion) -> str:
        """Evaluate parameter expansion with operators.
        
        Args:
            expansion: ParameterExpansion node
            
        Returns:
            The expanded value after applying the operator
            
        Raises:
            ExpansionError: If required parameter is unset
        """
        param = expansion.parameter
        operator = expansion.operator
        word = expansion.word or ''
        
        # Get current value
        if param in self.SPECIAL_VARS:
            value = self._get_special_var(param)
        elif param.isdigit():
            params = self.state.positional_params
            index = int(param) - 1
            value = params[index] if 0 <= index < len(params) else ''
        else:
            var_value = self.state.scope_manager.get_variable(param)
            value = str(var_value) if var_value is not None else ''
        
        # Apply operator
        if operator == ':-':
            # Use default if unset or null
            return value if value else word
        elif operator == '-':
            # Use default if unset
            if param in self.SPECIAL_VARS or param.isdigit():
                return value if value else word
            else:
                var_value = self.state.scope_manager.get_variable(param)
                return str(var_value) if var_value is not None else word
        elif operator == ':=':
            # Assign default if unset or null
            if not value:
                # Can't assign to special variables or positional parameters
                if not (param in self.SPECIAL_VARS or param.isdigit()):
                    self.state.scope_manager.set_variable(param, word)
                return word
            return value
        elif operator == '=':
            # Assign default if unset
            if param not in self.SPECIAL_VARS and not param.isdigit():
                var_value = self.state.scope_manager.get_variable(param)
                if var_value is None:
                    self.state.scope_manager.set_variable(param, word)
                    return word
                return str(var_value)
            return value
        elif operator == ':?':
            # Error if unset or null
            if not value:
                error_msg = word or f"{param}: parameter null or not set"
                raise ExpansionError(error_msg)
            return value
        elif operator == '?':
            # Error if unset
            if param in self.SPECIAL_VARS or param.isdigit():
                if not value:
                    error_msg = word or f"{param}: parameter not set"
                    raise ExpansionError(error_msg)
            else:
                var_value = self.state.scope_manager.get_variable(param)
                if var_value is None:
                    error_msg = word or f"{param}: parameter not set"
                    raise ExpansionError(error_msg)
                value = str(var_value)
            return value
        elif operator == ':+':
            # Use alternate if set and non-null
            return word if value else ''
        elif operator == '+':
            # Use alternate if set
            if param in self.SPECIAL_VARS or param.isdigit():
                return word if value else ''
            else:
                var_value = self.state.scope_manager.get_variable(param)
                return word if var_value is not None else ''
        elif operator == '#':
            # Length (special case when word is None)
            if word:
                # Remove shortest prefix matching pattern
                return self._remove_prefix(value, word, shortest=True)
            else:
                # Return length of value
                return str(len(value))
        elif operator == '##':
            # Remove longest prefix matching pattern
            return self._remove_prefix(value, word, shortest=False)
        elif operator == '%':
            # Remove shortest suffix matching pattern
            return self._remove_suffix(value, word, shortest=True)
        elif operator == '%%':
            # Remove longest suffix matching pattern
            return self._remove_suffix(value, word, shortest=False)
        elif operator == '/':
            # Replace first occurrence
            return self._replace_pattern(value, word, first_only=True)
        elif operator == '//':
            # Replace all occurrences
            return self._replace_pattern(value, word, first_only=False)
        elif operator == '^':
            # Convert first character to uppercase
            return self._uppercase_pattern(value, word, first_only=True)
        elif operator == '^^':
            # Convert all matching characters to uppercase
            return self._uppercase_pattern(value, word, first_only=False)
        elif operator == ',':
            # Convert first character to lowercase
            return self._lowercase_pattern(value, word, first_only=True)
        elif operator == ',,':
            # Convert all matching characters to lowercase
            return self._lowercase_pattern(value, word, first_only=False)
        elif operator == ':':
            # Substring extraction
            return self._extract_substring(value, word)
        else:
            raise ValueError(f"Unknown parameter expansion operator: {operator}")
    
    def _evaluate_arithmetic(self, expansion: ArithmeticExpansion) -> str:
        """Evaluate arithmetic expansion.
        
        Args:
            expansion: ArithmeticExpansion node
            
        Returns:
            The result of arithmetic evaluation as a string
        """
        # Use expansion manager's existing implementation
        result = self.expansion_manager.execute_arithmetic_expansion(
            f"$(({expansion.expression}))"
        )
        return str(result)
    
    def _remove_prefix(self, value: str, pattern: str, shortest: bool) -> str:
        """Remove prefix matching pattern from value.
        
        Args:
            value: The string to process
            pattern: The pattern to match
            shortest: If True, remove shortest match; else longest
            
        Returns:
            Value with prefix removed
        """
        # Use existing parameter expansion implementation
        from ..expansion.parameter_expansion import ParameterExpansion
        param_exp = ParameterExpansion(self.shell)
        
        if shortest:
            return param_exp.remove_shortest_prefix(value, pattern)
        else:
            return param_exp.remove_longest_prefix(value, pattern)
    
    def _remove_suffix(self, value: str, pattern: str, shortest: bool) -> str:
        """Remove suffix matching pattern from value.
        
        Args:
            value: The string to process
            pattern: The pattern to match
            shortest: If True, remove shortest match; else longest
            
        Returns:
            Value with suffix removed
        """
        # Use existing parameter expansion implementation
        from ..expansion.parameter_expansion import ParameterExpansion
        param_exp = ParameterExpansion(self.shell)
        
        if shortest:
            return param_exp.remove_shortest_suffix(value, pattern)
        else:
            return param_exp.remove_longest_suffix(value, pattern)
    
    def _replace_pattern(self, value: str, word: str, first_only: bool) -> str:
        """Replace pattern in value.
        
        Args:
            value: The string to process
            word: Pattern/replacement string (pattern/replacement)
            first_only: If True, replace first match only
            
        Returns:
            Value with replacements made
        """
        # Split pattern and replacement
        if '/' in word:
            # Find first unescaped /
            i = 0
            pattern_parts = []
            while i < len(word):
                if i + 1 < len(word) and word[i:i+2] == '\\/':
                    pattern_parts.append('\\/')
                    i += 2
                elif word[i] == '/':
                    pattern = ''.join(pattern_parts)
                    replacement = word[i+1:] if i+1 < len(word) else ''
                    break
                else:
                    pattern_parts.append(word[i])
                    i += 1
            else:
                # No separator found
                pattern = word
                replacement = ''
        else:
            pattern = word
            replacement = ''
        
        # Use existing parameter expansion implementation
        from ..expansion.parameter_expansion import ParameterExpansion
        param_exp = ParameterExpansion(self.shell)
        
        if first_only:
            return param_exp.substitute_first(value, pattern, replacement)
        else:
            return param_exp.substitute_all(value, pattern, replacement)
    
    def _uppercase_pattern(self, value: str, pattern: str, first_only: bool) -> str:
        """Convert characters matching pattern to uppercase.
        
        Args:
            value: The string to process
            pattern: Pattern to match (empty means all)
            first_only: If True, convert first match only
            
        Returns:
            Value with matching characters uppercased
        """
        # Use existing parameter expansion implementation
        from ..expansion.parameter_expansion import ParameterExpansion
        param_exp = ParameterExpansion(self.shell)
        
        if first_only:
            return param_exp.uppercase_first(value, pattern)
        else:
            return param_exp.uppercase_all(value, pattern)
    
    def _lowercase_pattern(self, value: str, pattern: str, first_only: bool) -> str:
        """Convert characters matching pattern to lowercase.
        
        Args:
            value: The string to process
            pattern: Pattern to match (empty means all)
            first_only: If True, convert first match only
            
        Returns:
            Value with matching characters lowercased
        """
        # Use existing parameter expansion implementation
        from ..expansion.parameter_expansion import ParameterExpansion
        param_exp = ParameterExpansion(self.shell)
        
        if first_only:
            return param_exp.lowercase_first(value, pattern)
        else:
            return param_exp.lowercase_all(value, pattern)
    
    def _extract_substring(self, value: str, params: str) -> str:
        """Extract substring from value.
        
        Args:
            value: The string to process
            params: Offset or offset:length
            
        Returns:
            The extracted substring
        """
        # Parse offset and length
        if ':' in params:
            parts = params.split(':', 1)
            try:
                offset = int(parts[0])
                length = int(parts[1]) if parts[1] else None
            except ValueError:
                # Invalid offset or length
                return ''
        else:
            try:
                offset = int(params)
                length = None
            except ValueError:
                return ''
        
        # Use existing parameter expansion implementation
        from ..expansion.parameter_expansion import ParameterExpansion
        param_exp = ParameterExpansion(self.shell)
        
        if length is not None:
            return param_exp.extract_substring(value, offset, length)
        else:
            return param_exp.extract_substring(value, offset)