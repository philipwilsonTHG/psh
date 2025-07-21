"""Test parameter expansion parsing in both parsers."""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.recursive_descent_adapter import RecursiveDescentAdapter
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import SimpleCommand, StatementList


def test_param_expansion_recursive_descent():
    """Test that recursive descent parser handles PARAM_EXPANSION tokens."""
    parser = RecursiveDescentAdapter()
    
    # Test simple parameter expansion
    tokens = tokenize("echo ${USER:-nobody}")
    ast = parser.parse(tokens)
    
    assert isinstance(ast, StatementList)
    cmd = ast.statements[0].pipelines[0].commands[0]
    assert isinstance(cmd, SimpleCommand)
    assert len(cmd.args) == 2
    assert cmd.args[0] == "echo"
    assert cmd.args[1] == "${USER:-nobody}"
    
    # Test multiple parameter expansions
    tokens = tokenize("echo ${HOME:-/tmp} ${SHELL:=/bin/bash}")
    ast = parser.parse(tokens)
    
    cmd = ast.statements[0].pipelines[0].commands[0]
    assert len(cmd.args) == 3
    assert cmd.args[1] == "${HOME:-/tmp}"
    assert cmd.args[2] == "${SHELL:=/bin/bash}"


def test_param_expansion_parser_combinator():
    """Test that parser combinator handles PARAM_EXPANSION tokens."""
    parser = ParserCombinatorShellParser()
    
    # Test simple parameter expansion
    tokens = tokenize("echo ${USER:-nobody}")
    ast = parser.parse(tokens)
    
    assert isinstance(ast, StatementList)
    cmd = ast.statements[0].pipelines[0].commands[0]
    assert isinstance(cmd, SimpleCommand)
    assert len(cmd.args) == 2
    assert cmd.args[0] == "echo"
    assert cmd.args[1] == "${USER:-nobody}"
    
    # Test multiple parameter expansions
    tokens = tokenize("echo ${HOME:-/tmp} ${SHELL:=/bin/bash}")
    ast = parser.parse(tokens)
    
    cmd = ast.statements[0].pipelines[0].commands[0]
    assert len(cmd.args) == 3
    assert cmd.args[1] == "${HOME:-/tmp}"
    assert cmd.args[2] == "${SHELL:=/bin/bash}"


def test_mixed_expansions_recursive_descent():
    """Test mixed expansion types with recursive descent parser."""
    parser = RecursiveDescentAdapter()
    
    tokens = tokenize("echo $USER $(date) ${PATH##*/}")
    ast = parser.parse(tokens)
    
    cmd = ast.statements[0].pipelines[0].commands[0]
    assert len(cmd.args) == 4
    assert cmd.args[0] == "echo"
    assert cmd.args[1] == "$USER"  # Simple variable
    assert cmd.args[2] == "$(date)"  # Command substitution
    assert cmd.args[3] == "${PATH##*/}"  # Parameter expansion


def test_mixed_expansions_parser_combinator():
    """Test mixed expansion types with parser combinator."""
    parser = ParserCombinatorShellParser()
    
    tokens = tokenize("echo $USER $(date) ${PATH##*/}")
    ast = parser.parse(tokens)
    
    cmd = ast.statements[0].pipelines[0].commands[0]
    assert len(cmd.args) == 4
    assert cmd.args[0] == "echo"
    assert cmd.args[1] == "$USER"  # Simple variable
    assert cmd.args[2] == "$(date)"  # Command substitution
    assert cmd.args[3] == "${PATH##*/}"  # Parameter expansion


def test_complex_param_expansions():
    """Test various complex parameter expansion forms."""
    test_cases = [
        "${VAR:-default}",      # Default value
        "${VAR:=default}",      # Assign default
        "${VAR:?error msg}",    # Error if unset
        "${VAR:+alternate}",    # Alternate value
        "${#VAR}",              # Length
        "${VAR#pattern}",       # Remove prefix
        "${VAR##pattern}",      # Remove longest prefix
        "${VAR%pattern}",       # Remove suffix
        "${VAR%%pattern}",      # Remove longest suffix
        "${VAR/old/new}",       # Replace first
        "${VAR//old/new}",      # Replace all
    ]
    
    for expansion in test_cases:
        # Test with recursive descent
        rd_parser = RecursiveDescentAdapter()
        tokens = tokenize(f"echo {expansion}")
        ast = rd_parser.parse(tokens)
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert cmd.args[1] == expansion
        
        # Test with parser combinator
        pc_parser = ParserCombinatorShellParser()
        tokens = tokenize(f"echo {expansion}")
        ast = pc_parser.parse(tokens)
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert cmd.args[1] == expansion


def test_param_expansion_in_function():
    """Test parameter expansion inside function definitions."""
    code = """process() {
        echo ${1:-"No argument"}
        echo ${USER:-unknown}
    }"""
    
    # Test with parser combinator (which supports functions)
    parser = ParserCombinatorShellParser()
    tokens = tokenize(code)
    ast = parser.parse(tokens)
    
    # Verify the function contains parameter expansions
    func = ast.statements[0]
    assert func.name == "process"
    
    # Check the echo commands in the function body
    echo1 = func.body.statements[0].pipelines[0].commands[0]
    assert echo1.args[1] == '${1:-"No argument"}'
    
    echo2 = func.body.statements[1].pipelines[0].commands[0]
    assert echo2.args[1] == "${USER:-unknown}"