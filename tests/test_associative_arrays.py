#!/usr/bin/env python3
"""Test script for associative arrays implementation."""

import pytest
import sys
import os

from psh.lexer import StateMachineLexer
from psh.parser import Parser
from psh.shell import Shell
from psh.core.variables import AssociativeArray, VarAttributes

class TestAssociativeArrays:
    """Test class for associative arrays functionality."""
    
    def test_declare_associative_array(self):
        """Test declare -A command."""
        shell = Shell()
        # Test declare -A command
        lexer = StateMachineLexer('declare -A colors')
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        result = shell.execute(ast)
        
        assert result == 0, f"declare -A should succeed, got {result}"
        
        # Check if variable was created
        var = shell.state.scope_manager.get_variable_object('colors')
        assert var is not None, "Variable should be created"
        assert var.attributes & VarAttributes.ASSOC_ARRAY, "Variable should have ASSOC_ARRAY attribute"
        assert isinstance(var.value, AssociativeArray), "Variable value should be AssociativeArray"
    
    def test_associative_array_element_assignment(self):
        """Test array element assignment for associative arrays."""
        shell = Shell()
        # First declare the associative array
        lexer = StateMachineLexer('declare -A colors')
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        shell.execute(ast)
        
        # Test array element assignment
        lexer = StateMachineLexer('colors[red]="#FF0000"')
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Check the array assignment in AST
        command = ast.statements[0].pipelines[0].commands[0]
        assert len(command.array_assignments) == 1, "Should have one array assignment"
        
        assignment = command.array_assignments[0]
        assert assignment.name == 'colors', "Assignment name should be 'colors'"
        assert assignment.value == '#FF0000', "Assignment value should be '#FF0000'"
        
        # Execute the assignment
        result = shell.execute(ast)
        assert result == 0, "Array assignment should succeed"
        
        # Check if value was set
        var = shell.state.scope_manager.get_variable_object('colors')
        assert var is not None, "Variable should exist"
        assert hasattr(var.value, 'get'), "Variable should have get method"
        
        value = var.value.get('red')
        assert value == '#FF0000', f"colors[red] should be '#FF0000', got {value}"
    
    def test_associative_array_with_space_key(self):
        """Test associative array with key containing spaces."""
        shell = Shell()
        # Declare associative array
        shell.execute(Parser(StateMachineLexer('declare -A colors').tokenize()).parse())
        
        # Test assignment with quoted key containing spaces
        lexer = StateMachineLexer('colors["light blue"]="#ADD8E6"')
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        result = shell.execute(ast)
        assert result == 0, "Array assignment with spaced key should succeed"
        
        # Check if value was set
        var = shell.state.scope_manager.get_variable_object('colors')
        value = var.value.get('light blue')
        assert value == '#ADD8E6', f"colors['light blue'] should be '#ADD8E6', got {value}"
    
    def test_associative_array_variable_key(self):
        """Test associative array with variable as key."""
        shell = Shell()
        # Set up variables
        shell.execute(Parser(StateMachineLexer('declare -A colors').tokenize()).parse())
        shell.execute(Parser(StateMachineLexer('key_var="red"').tokenize()).parse())
        
        # Test assignment with variable key
        lexer = StateMachineLexer('colors[$key_var]="#FF0000"')
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        result = shell.execute(ast)
        assert result == 0, "Array assignment with variable key should succeed"
        
        # Check if value was set (should be stored under "red")
        var = shell.state.scope_manager.get_variable_object('colors')
        value = var.value.get('red')
        assert value == '#FF0000', f"colors[$key_var] should resolve to colors[red]='#FF0000', got {value}"
    
    def test_associative_array_initialization_syntax(self):
        """Test associative array initialization syntax."""
        shell = Shell()
        # Test initialization with declare -A arr=([key]=value)
        cmd = 'declare -A fruits=([apple]="red" [banana]="yellow")'
        lexer = StateMachineLexer(cmd)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        result = shell.execute(ast)
        assert result == 0, "Associative array initialization should succeed"
        
        # Check if values were set
        var = shell.state.scope_manager.get_variable_object('fruits')
        assert var is not None, "Variable should exist"
        assert isinstance(var.value, AssociativeArray), "Should be AssociativeArray"
        
        assert var.value.get('apple') == 'red', "fruits[apple] should be 'red'"
        assert var.value.get('banana') == 'yellow', "fruits[banana] should be 'yellow'"
    
    def test_indexed_vs_associative_array_distinction(self):
        """Test that indexed and associative arrays are properly distinguished."""
        shell = Shell()
        # Create indexed array
        shell.execute(Parser(StateMachineLexer('declare -a indexed').tokenize()).parse())
        shell.execute(Parser(StateMachineLexer('indexed[0]="zero"').tokenize()).parse())
        
        # Create associative array
        shell.execute(Parser(StateMachineLexer('declare -A assoc').tokenize()).parse())
        shell.execute(Parser(StateMachineLexer('assoc[key]="value"').tokenize()).parse())
        
        # Check types
        indexed_var = shell.state.scope_manager.get_variable_object('indexed')
        assoc_var = shell.state.scope_manager.get_variable_object('assoc')
        
        assert indexed_var.attributes & VarAttributes.ARRAY, "indexed should have ARRAY attribute"
        assert not (indexed_var.attributes & VarAttributes.ASSOC_ARRAY), "indexed should not have ASSOC_ARRAY attribute"
        
        assert assoc_var.attributes & VarAttributes.ASSOC_ARRAY, "assoc should have ASSOC_ARRAY attribute"
        assert not (assoc_var.attributes & VarAttributes.ARRAY), "assoc should not have ARRAY attribute"
        
        # Check values
        assert indexed_var.value.get(0) == "zero", "indexed[0] should work"
        assert assoc_var.value.get("key") == "value", "assoc[key] should work"
    
    def test_associative_array_keys_expansion(self):
        """Test ${!array[@]} expansion for associative arrays."""
        shell = Shell()
        # Create associative array with multiple keys
        shell.execute(Parser(StateMachineLexer('declare -A colors=([red]="#FF0000" [green]="#00FF00" [blue]="#0000FF")').tokenize()).parse())
        
        # Test ${!colors[@]} expansion
        from unittest.mock import patch
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.execute(Parser(StateMachineLexer('echo "${!colors[@]}"').tokenize()).parse())
        
        result = ''.join(output)
        # Keys should be present (order not guaranteed in associative arrays)
        assert 'red' in result, f"'red' should be in keys output: '{result}'"
        assert 'green' in result, f"'green' should be in keys output: '{result}'"
        assert 'blue' in result, f"'blue' should be in keys output: '{result}'"
        
        # Test with empty associative array
        shell.execute(Parser(StateMachineLexer('declare -A empty').tokenize()).parse())
        output.clear()
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.execute(Parser(StateMachineLexer('echo "[${!empty[@]}]"').tokenize()).parse())
        
        result = ''.join(output).strip()
        assert result == '[]', f"Empty array keys should be empty: '{result}'"
        
        # Test with single key
        shell.execute(Parser(StateMachineLexer('declare -A single=([only]="value")').tokenize()).parse())
        output.clear()
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.execute(Parser(StateMachineLexer('echo "${!single[@]}"').tokenize()).parse())
        
        result = ''.join(output).strip()
        assert result == 'only', f"Single key should be 'only': '{result}'"


if __name__ == "__main__":
    # Adjust path for running as script
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Run tests directly
    test_instance = TestAssociativeArrays()
    
    print("Testing declare -A...")
    test_instance.test_declare_associative_array()
    print("✓ declare -A test passed")
    
    print("Testing array element assignment...")
    test_instance.test_associative_array_element_assignment()
    print("✓ Array element assignment test passed")
    
    print("Testing space keys...")
    test_instance.test_associative_array_with_space_key()
    print("✓ Space key test passed")
    
    print("Testing variable keys...")
    test_instance.test_associative_array_variable_key()
    print("✓ Variable key test passed")
    
    print("Testing initialization syntax...")
    test_instance.test_associative_array_initialization_syntax()
    print("✓ Initialization syntax test passed")
    
    print("Testing indexed vs associative distinction...")
    test_instance.test_indexed_vs_associative_array_distinction()
    print("✓ Type distinction test passed")
    
    print("\nAll associative array tests passed!")