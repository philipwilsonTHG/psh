"""Test control structures in pipelines functionality."""
import pytest
import os
import tempfile
from psh.shell import Shell

def test_while_command_parsing():
    """Test that while loops can be parsed as pipeline components."""
    from psh.state_machine_lexer import tokenize
    from psh.parser import parse
    from psh.ast_nodes import WhileCommand, SimpleCommand
    
    # Test parsing while loop in pipeline
    tokens = tokenize('echo "test" | while read x; do echo $x; done')
    ast = parse(tokens)
    
    # Should have one statement with one pipeline
    assert len(ast.statements) == 1
    and_or_list = ast.statements[0]
    assert len(and_or_list.pipelines) == 1
    pipeline = and_or_list.pipelines[0]
    
    # Pipeline should have two commands: SimpleCommand and WhileCommand
    assert len(pipeline.commands) == 2
    assert isinstance(pipeline.commands[0], SimpleCommand)
    assert isinstance(pipeline.commands[1], WhileCommand)
    
    # Check the while command structure
    while_cmd = pipeline.commands[1]
    assert while_cmd.condition is not None
    assert while_cmd.body is not None

def test_while_in_pipeline_simple():
    """Test basic execution of while loop in a pipeline."""
    shell = Shell()
    
    # Test that the command executes without error
    # Note: Due to variable scoping in subshells, complex while loops may not work
    # as expected, but this tests that the parsing and execution infrastructure works
    exit_code = shell.run_command('echo "test" | while false; do echo "never"; done')
    
    # Should execute without error (exit code 0 means success)
    assert exit_code == 0

def test_for_in_pipeline_simple():
    """Test basic for loop in a pipeline."""
    shell = Shell()
    
    # Simple for loop in pipeline (testing parsing and basic execution)
    exit_code = shell.run_command('echo "input" | for x in 1 2 3\ndo\necho "item"\ndone')
    
    # Should execute without error
    assert exit_code == 0

def test_if_in_pipeline_simple():
    """Test basic if statement in a pipeline."""
    shell = Shell()
    
    # Simple if statement in pipeline
    exit_code = shell.run_command('echo "input" | if true; then echo "success"; fi')
    
    assert exit_code == 0

def test_if_in_pipeline_false_condition():
    """Test if statement with false condition in pipeline."""
    shell = Shell()
    
    # If statement with false condition
    exit_code = shell.run_command('echo "input" | if false; then echo "never"; else echo "else"; fi')
    
    assert exit_code == 0

def test_case_in_pipeline():
    """Test case statement in a pipeline.""" 
    shell = Shell()
    
    # Simple case statement in pipeline
    exit_code = shell.run_command('echo "input" | case test in test) echo "match";; *) echo "no match";; esac')
    
    assert exit_code == 0

def test_arithmetic_command_in_pipeline():
    """Test arithmetic command in pipeline."""
    shell = Shell()
    
    # Simple arithmetic command in pipeline
    exit_code = shell.run_command('echo "input" | ((5 > 3)) && echo "true"')
    
    assert exit_code == 0