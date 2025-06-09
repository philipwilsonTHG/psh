"""Tests for control structures with unified types support."""

import pytest
from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse as parse_legacy
from psh.parser_refactored import parse as parse_refactored
from psh.ast_nodes import (
    # Legacy types
    WhileStatement, ForStatement, CStyleForStatement, IfStatement, 
    CaseStatement, SelectStatement, ArithmeticCommand,
    # Unified types
    WhileLoop, ForLoop, CStyleForLoop, IfConditional,
    CaseConditional, SelectLoop, ArithmeticEvaluation,
    # Common types
    ExecutionContext, TopLevel, CommandList, StatementList
)


class TestControlStructuresUnified:
    """Test control structures with both legacy and unified types."""
    
    @pytest.mark.parametrize("use_unified,expected_type", [
        (False, WhileStatement),
        (True, WhileLoop),
    ])
    def test_while_loop_type(self, use_unified, expected_type):
        """Test that while loops parse to correct type."""
        code = "while true; do echo test; done"
        tokens = tokenize(code)
        
        if use_unified:
            ast = parse_refactored(tokens, use_unified_types=True)
        else:
            ast = parse_legacy(tokens)
        
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], expected_type)
        
        if use_unified:
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    
    @pytest.mark.parametrize("use_unified,expected_type", [
        (False, ForStatement),
        (True, ForLoop),
    ])
    def test_for_loop_type(self, use_unified, expected_type):
        """Test that for loops parse to correct type."""
        code = "for i in a b c; do echo $i; done"
        tokens = tokenize(code)
        
        if use_unified:
            ast = parse_refactored(tokens, use_unified_types=True)
        else:
            ast = parse_legacy(tokens)
        
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], expected_type)
        
        if use_unified:
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    
    @pytest.mark.parametrize("use_unified,expected_type", [
        (False, CStyleForStatement),
        (True, CStyleForLoop),
    ])
    def test_c_style_for_loop_type(self, use_unified, expected_type):
        """Test that C-style for loops parse to correct type."""
        code = "for ((i=0; i<5; i++)); do echo $i; done"
        tokens = tokenize(code)
        
        if use_unified:
            ast = parse_refactored(tokens, use_unified_types=True)
        else:
            ast = parse_legacy(tokens)
        
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], expected_type)
        
        if use_unified:
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    
    @pytest.mark.parametrize("use_unified,expected_type", [
        (False, IfStatement),
        (True, IfConditional),
    ])
    def test_if_statement_type(self, use_unified, expected_type):
        """Test that if statements parse to correct type."""
        code = "if true; then echo yes; else echo no; fi"
        tokens = tokenize(code)
        
        if use_unified:
            ast = parse_refactored(tokens, use_unified_types=True)
        else:
            ast = parse_legacy(tokens)
        
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], expected_type)
        
        if use_unified:
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    
    @pytest.mark.parametrize("use_unified,expected_type", [
        (False, CaseStatement),
        (True, CaseConditional),
    ])
    def test_case_statement_type(self, use_unified, expected_type):
        """Test that case statements parse to correct type."""
        code = 'case $x in a) echo "A";; b) echo "B";; esac'
        tokens = tokenize(code)
        
        if use_unified:
            ast = parse_refactored(tokens, use_unified_types=True)
        else:
            ast = parse_legacy(tokens)
        
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], expected_type)
        
        if use_unified:
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    
    @pytest.mark.parametrize("use_unified,expected_type", [
        (False, SelectStatement),
        (True, SelectLoop),
    ])
    def test_select_statement_type(self, use_unified, expected_type):
        """Test that select statements parse to correct type."""
        code = 'select item in a b c; do echo $item; done'
        tokens = tokenize(code)
        
        if use_unified:
            ast = parse_refactored(tokens, use_unified_types=True)
        else:
            ast = parse_legacy(tokens)
        
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], expected_type)
        
        if use_unified:
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    
    @pytest.mark.parametrize("use_unified,expected_type", [
        (False, ArithmeticCommand),
        (True, ArithmeticEvaluation),
    ])
    def test_arithmetic_command_type(self, use_unified, expected_type):
        """Test that arithmetic commands parse to correct type."""
        code = '((x = 5 + 3))'
        tokens = tokenize(code)
        
        if use_unified:
            ast = parse_refactored(tokens, use_unified_types=True)
        else:
            ast = parse_legacy(tokens)
        
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], expected_type)
        
        if use_unified:
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    
    def test_pipeline_context_unified(self):
        """Test that control structures in pipelines get PIPELINE context."""
        code = "echo test | while read line; do echo $line; done"
        tokens = tokenize(code)
        ast = parse_refactored(tokens, use_unified_types=True)
        
        # Get the pipeline
        pipeline = ast.statements[0].pipelines[0]
        assert len(pipeline.commands) == 2
        
        # Second command should be WhileLoop with PIPELINE context
        while_loop = pipeline.commands[1]
        assert isinstance(while_loop, WhileLoop)
        assert while_loop.execution_context == ExecutionContext.PIPELINE
    
    def test_execution_compatibility(self, shell):
        """Test that both type systems execute the same way."""
        code = """
i=0
while [ $i -lt 3 ]; do
    echo $i
    i=$((i+1))
done
"""
        # Execute with legacy types
        shell.state.set_variable('i', '0')
        exit_code1 = shell.run_command(code)
        
        # Reset and execute with unified types
        shell.state.set_variable('i', '0')
        from psh.parser_refactored import parse
        tokens = tokenize(code)
        ast = parse(tokens, use_unified_types=True)
        exit_code2 = shell.execute_toplevel(ast)
        
        assert exit_code1 == exit_code2 == 0