#!/usr/bin/env python3
"""Test script for associative arrays implementation."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.lexer import tokenize
from psh.parser import Parser
from psh.shell import Shell


def test_associative_array_basic():
    """Test basic associative array functionality."""
    shell = Shell()

    print("=== Testing Basic Associative Array Functionality ===")

    # Test 1: declare -A
    print("\n1. Testing declare -A command")
    try:
        tokens = tokenize('declare -A colors')
        parser = Parser(tokens)
        ast = parser.parse()
        result = shell.executor_manager.execute(ast)
        print(f"declare -A colors: exit code {result}")

        # Check if variable was created
        var = shell.state.scope_manager.get_variable_object('colors')
        if var:
            print(f"Variable created: {var.name}, attributes: {var.attributes}, type: {type(var.value)}")
        else:
            print("ERROR: Variable not created")
    except Exception as e:
        print(f"ERROR in declare -A: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Array element assignment
    print("\n2. Testing array element assignment")
    try:
        tokens = tokenize('colors[red]="#FF0000"')
        print(f"Tokens: {[(t.type.name, t.value) for t in tokens]}")
        parser = Parser(tokens)
        ast = parser.parse()
        print(f"AST: {ast}")

        # Check the array assignment in AST
        command = ast.statements[0].pipelines[0].commands[0]
        if command.array_assignments:
            assignment = command.array_assignments[0]
            print(f"Assignment found: name={assignment.name}, index={assignment.index} (type: {type(assignment.index)}), value={assignment.value}")

        result = shell.executor_manager.execute(ast)
        print(f"colors[red]=\"#FF0000\": exit code {result}")

        # Check if value was set
        var = shell.state.scope_manager.get_variable_object('colors')
        if var and hasattr(var.value, 'get'):
            value = var.value.get('red')
            print(f"colors[red] = {value}")
        else:
            print("ERROR: Could not retrieve value")

    except Exception as e:
        print(f"ERROR in array assignment: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_associative_array_basic()
