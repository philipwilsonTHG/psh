"""
Array operations support for the PSH executor.

This module handles array initialization and element assignment operations,
including indexed and associative arrays.
"""

import re
import glob
from typing import List, Optional, Tuple, Union, TYPE_CHECKING

from ..core.exceptions import ReadonlyVariableError
from ..core.variables import IndexedArray, AssociativeArray, VarAttributes
from ..arithmetic import evaluate_arithmetic

if TYPE_CHECKING:
    from ..shell import Shell
    from ..ast_nodes import ArrayInitialization, ArrayElementAssignment
    from ..expansion.manager import ExpansionManager


class ArrayOperationExecutor:
    """
    Handles array initialization and element operations.
    
    This class encapsulates all logic for array operations including:
    - Array initialization (indexed and associative)
    - Array element assignment
    - Array expansion and indexing
    - Append mode operations
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize the array operation executor with a shell instance."""
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
    
    def execute_array_initialization(self, node: 'ArrayInitialization') -> int:
        """
        Execute array initialization: arr=(a b c)
        
        Args:
            node: The ArrayInitialization AST node
            
        Returns:
            Exit status code (0 for success)
        """
        # Handle append mode
        if node.is_append:
            # Get existing array or create new one
            var_obj = self.state.scope_manager.get_variable_object(node.name)
            if var_obj and isinstance(var_obj.value, IndexedArray):
                array = var_obj.value
                # Find next index for appending
                start_index = max(array._elements.keys()) + 1 if array._elements else 0
            else:
                array = IndexedArray()
                start_index = 0
        else:
            # Create new array
            array = IndexedArray()
            start_index = 0
        
        # Expand and add elements
        next_sequential_index = start_index
        
        for i, element in enumerate(node.elements):
            element_type = node.element_types[i] if i < len(node.element_types) else 'WORD'
            
            # Check if this is an explicit index assignment: [index]=value
            if element_type in ('COMPOSITE', 'COMPOSITE_QUOTED') and self._is_explicit_array_assignment(element):
                # Parse explicit index assignment (this will handle expansion internally)
                index, value = self._parse_explicit_array_assignment(element)
                if index is not None:
                    # Evaluate arithmetic in index (bash always evaluates indices as arithmetic)
                    try:
                        evaluated_index = evaluate_arithmetic(str(index), self.shell)
                        array.set(evaluated_index, value)
                        # Update next sequential index to be after this explicit index
                        next_sequential_index = max(next_sequential_index, evaluated_index + 1)
                    except (ValueError, Exception):
                        # If index evaluation fails, treat as regular sequential element
                        next_sequential_index = self._add_expanded_element_to_array(
                            array, element, next_sequential_index, split_words=False)
                else:
                    # Failed to parse as explicit assignment, treat as regular element
                    next_sequential_index = self._add_expanded_element_to_array(
                        array, element, next_sequential_index, split_words=False)
            elif element_type in ('WORD', 'COMPOSITE'):
                # Split unquoted words/composites on whitespace for sequential assignment with glob expansion
                next_sequential_index = self._add_expanded_element_to_array(
                    array, element, next_sequential_index, split_words=True)
            elif element_type in ('COMMAND_SUB', 'ARITH_EXPANSION', 'VARIABLE'):
                # Command substitution, arithmetic expansion, and variables should be word-split in arrays
                next_sequential_index = self._add_expanded_element_to_array(
                    array, element, next_sequential_index, split_words=True)
            else:
                # Keep as single element for sequential assignment (STRING, etc.)
                # Quoted strings should not be glob expanded or word split
                next_sequential_index = self._add_expanded_element_to_array(
                    array, element, next_sequential_index, split_words=False)
        
        # Set array in shell state
        self.state.scope_manager.set_variable(node.name, array, attributes=VarAttributes.ARRAY)
        return 0
    
    def execute_array_element_assignment(self, node: 'ArrayElementAssignment') -> int:
        """
        Execute array element assignment: arr[i]=value
        
        Args:
            node: The ArrayElementAssignment AST node
            
        Returns:
            Exit status code (0 for success)
        """
        # Handle index - can be string or list of tokens
        if isinstance(node.index, list):
            # Expand each token if it's a variable
            expanded_parts = []
            for token in node.index:
                if hasattr(token, 'type') and str(token.type) == 'TokenType.VARIABLE':
                    # This is a variable token, expand it
                    var_name = token.value
                    expanded_parts.append(self.state.get_variable(var_name, ''))
                else:
                    # Regular token, use its value
                    expanded_parts.append(token.value if hasattr(token, 'value') else str(token))
            index_str = ''.join(expanded_parts)
        else:
            index_str = node.index
        
        # Expand any remaining variables in the index (e.g., ${var})
        expanded_index = self.expansion_manager.expand_string_variables(index_str, process_escapes=False)
        
        # Get the variable to check if it's an associative array
        var_obj = self.state.scope_manager.get_variable_object(node.name)
        
        # Determine index type based on array type
        if var_obj and isinstance(var_obj.value, AssociativeArray):
            # For associative arrays, index is always a string
            index = expanded_index
        else:
            # For indexed arrays, evaluate arithmetic if needed
            try:
                if any(op in expanded_index for op in ['+', '-', '*', '/', '%', '(', ')']):
                    index = evaluate_arithmetic(expanded_index, self.shell)
                else:
                    index = int(expanded_index)
            except (ValueError, Exception):
                # Bash compatibility: when string indices are used on indexed arrays
                # (often due to failed declare -A conversion), treat as index 0
                index = 0
        
        # Expand value
        expanded_value = self.expansion_manager.expand_string_variables(node.value, process_escapes=False)
        
        # Get or create array
        if var_obj and (isinstance(var_obj.value, IndexedArray) or isinstance(var_obj.value, AssociativeArray)):
            array = var_obj.value
        else:
            # Create new indexed array by default
            array = IndexedArray()
            self.state.scope_manager.set_variable(node.name, array, attributes=VarAttributes.ARRAY)
        
        # Handle append mode
        if node.is_append:
            # Get current value and append
            current = array.get(index)
            if current is not None:
                expanded_value = current + expanded_value
        
        # Set element
        array.set(index, expanded_value)
        return 0
    
    # Helper methods
    
    def _add_expanded_element_to_array(self, array: IndexedArray, element: str, 
                                       start_index: int, split_words: bool = True) -> int:
        """
        Add expanded element to array with glob expansion.
        
        Args:
            array: The array to add elements to
            element: The element to expand and add
            start_index: Starting index for sequential assignment
            split_words: Whether to split on whitespace after expansion
            
        Returns:
            Next available index after adding elements
        """
        # Expand variables first (don't process escape sequences in array context)
        expanded = self.expansion_manager.expand_string_variables(element, process_escapes=False)
        
        if split_words:
            # Split on whitespace for WORD and command substitution elements
            words = expanded.split()
        else:
            # Keep as single element for STRING and composite elements
            words = [expanded] if expanded else ['']
        
        # Handle glob expansion on each word (like for loops do)
        next_index = start_index
        for word in words:
            matches = glob.glob(word)
            if matches:
                # Glob pattern matched files - add all matches (already sorted)
                for match in sorted(matches):
                    array.set(next_index, match)
                    next_index += 1
            else:
                # No matches, add literal word
                array.set(next_index, word)
                next_index += 1
        
        return next_index
    
    def _is_explicit_array_assignment(self, element: str) -> bool:
        """Check if element has explicit array assignment syntax: [index]=value"""
        # Match [anything]=anything pattern
        return bool(re.match(r'^\[[^\]]*\]=', element))
    
    def _parse_explicit_array_assignment(self, element: str) -> Tuple[Optional[Union[str, int]], Optional[str]]:
        """
        Parse explicit array assignment: [index]=value
        
        Returns:
            tuple: (index, value) or (None, None) if parsing fails
        """
        match = re.match(r'^\[([^\]]*)\]=(.*)$', element)
        if match:
            index_str = match.group(1)
            value = match.group(2)
            
            # Expand any variables in the index
            expanded_index = self.expansion_manager.expand_string_variables(index_str, process_escapes=False)
            expanded_value = self.expansion_manager.expand_string_variables(value, process_escapes=False)
            
            return expanded_index, expanded_value
        
        return None, None