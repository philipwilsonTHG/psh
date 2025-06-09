"""Test parser with unified control structure types."""

import pytest
from psh.state_machine_lexer import tokenize
from psh.parser_refactored import Parser
from psh.ast_nodes import (
    WhileLoop, ForLoop, ExecutionContext, WhileStatement, WhileCommand,
    ForStatement, ForCommand, CommandList
)


class TestUnifiedParser:
    """Test unified control structure parsing."""
    
    def test_while_loop_statement_mode(self):
        """Test parsing while loop as statement with unified types."""
        tokens = tokenize("while [ $i -lt 5 ]; do echo $i; done")
        parser = Parser(tokens)
        parser._use_unified_types = True
        
        ast = parser.parse()
        # With unified types, control structures at top level go into TopLevel
        from psh.ast_nodes import TopLevel
        assert isinstance(ast, TopLevel)
        assert len(ast.items) == 1
        
        while_loop = ast.items[0]
        assert isinstance(while_loop, WhileLoop)
        assert while_loop.execution_context == ExecutionContext.STATEMENT
    
    def test_while_loop_pipeline_mode(self):
        """Test parsing while loop in pipeline with unified types."""
        tokens = tokenize("echo test | while read line; do echo $line; done")
        parser = Parser(tokens)
        parser._use_unified_types = True
        
        ast = parser.parse()
        pipeline = ast.statements[0].pipelines[0]
        assert len(pipeline.commands) == 2
        
        # Second command should be unified WhileLoop
        while_loop = pipeline.commands[1]
        assert isinstance(while_loop, WhileLoop)
        assert while_loop.execution_context == ExecutionContext.PIPELINE
    
    def test_for_loop_statement_mode(self):
        """Test parsing for loop as statement with unified types."""
        tokens = tokenize("for i in 1 2 3; do echo $i; done")
        parser = Parser(tokens)
        parser._use_unified_types = True
        
        ast = parser.parse()
        from psh.ast_nodes import TopLevel
        assert isinstance(ast, TopLevel)
        
        for_loop = ast.items[0]
        assert isinstance(for_loop, ForLoop)
        assert for_loop.execution_context == ExecutionContext.STATEMENT
        assert for_loop.variable == "i"
        assert for_loop.items == ["1", "2", "3"]
    
    def test_for_loop_pipeline_mode(self):
        """Test parsing for loop in pipeline with unified types."""
        tokens = tokenize("seq 3 | for i in $(cat); do echo $i; done")
        parser = Parser(tokens)
        parser._use_unified_types = True
        
        ast = parser.parse()
        pipeline = ast.statements[0].pipelines[0]
        assert len(pipeline.commands) == 2
        
        for_loop = pipeline.commands[1]
        assert isinstance(for_loop, ForLoop)
        assert for_loop.execution_context == ExecutionContext.PIPELINE
    
    def test_backward_compatibility_disabled(self):
        """Test that old types are still created when unified types are disabled."""
        from psh.ast_nodes import TopLevel
        
        # While statement
        tokens = tokenize("while true; do echo hi; done")
        parser = Parser(tokens)
        parser._use_unified_types = False  # Default
        
        ast = parser.parse()
        # Control structures at top level go into TopLevel
        assert isinstance(ast, TopLevel)
        while_stmt = ast.items[0]
        assert isinstance(while_stmt, WhileStatement)
        assert not isinstance(while_stmt, WhileLoop)
        
        # While in pipeline
        tokens = tokenize("echo | while read; do echo $REPLY; done")
        parser = Parser(tokens)
        
        ast = parser.parse()
        while_cmd = ast.statements[0].pipelines[0].commands[1]
        assert isinstance(while_cmd, WhileCommand)
        assert not isinstance(while_cmd, WhileLoop)
    
    def test_unified_type_inheritance(self):
        """Test that unified types have correct inheritance."""
        from psh.ast_nodes import Statement, CompoundCommand, TopLevel
        
        tokens = tokenize("while true; do echo hi; done")
        parser = Parser(tokens)
        parser._use_unified_types = True
        
        ast = parser.parse()
        assert isinstance(ast, TopLevel)
        while_loop = ast.items[0]
        
        # Check multiple inheritance
        assert isinstance(while_loop, WhileLoop)
        assert isinstance(while_loop, Statement)
        assert isinstance(while_loop, CompoundCommand)