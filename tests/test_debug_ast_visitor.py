"""
Tests for the debug AST visitor implementation.

These tests verify that the visitor-based debug AST formatter produces
correct output and can be used as a drop-in replacement for ASTFormatter.
"""

import pytest
from psh.ast_nodes import (
    TopLevel, StatementList, SimpleCommand, Pipeline, AndOrList,
    WhileLoop, ForLoop, IfConditional, FunctionDef, Redirect,
    ArrayInitialization, ArrayElementAssignment
)
from psh.visitor import DebugASTVisitor
from psh.utils.ast_formatter import ASTFormatter


class TestDebugASTVisitor:
    """Test the debug AST visitor."""
    
    def test_simple_command(self):
        """Test formatting a simple command."""
        cmd = SimpleCommand(args=['echo', 'hello'], arg_types=['WORD', 'WORD'])
        visitor = DebugASTVisitor()
        result = visitor.visit(cmd)
        
        assert 'SimpleCommand: echo hello' in result
        assert 'Arg Types: ' in result
    
    def test_pipeline(self):
        """Test formatting a pipeline."""
        pipeline = Pipeline(commands=[
            SimpleCommand(args=['cat', 'file'], arg_types=['WORD', 'WORD']),
            SimpleCommand(args=['grep', 'test'], arg_types=['WORD', 'WORD'])
        ])
        visitor = DebugASTVisitor()
        result = visitor.visit(pipeline)
        
        assert 'Pipeline:' in result
        assert 'SimpleCommand: cat file' in result
        assert 'SimpleCommand: grep test' in result
    
    def test_function_definition(self):
        """Test formatting a function definition."""
        func = FunctionDef(
            name='test_func',
            body=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['echo', 'test'], arg_types=['WORD', 'WORD'])
                    ])
                ])
            ])
        )
        visitor = DebugASTVisitor()
        result = visitor.visit(func)
        
        assert 'FunctionDef (name: test_func)' in result
        assert 'Body:' in result
        assert 'CommandList:' in result
    
    def test_control_structures(self):
        """Test formatting control structures."""
        # While loop
        while_loop = WhileLoop(
            condition=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['true'], arg_types=['WORD'])
                    ])
                ])
            ]),
            body=StatementList(statements=[
                AndOrList(pipelines=[
                    Pipeline(commands=[
                        SimpleCommand(args=['echo', 'loop'], arg_types=['WORD', 'WORD'])
                    ])
                ])
            ])
        )
        visitor = DebugASTVisitor()
        result = visitor.visit(while_loop)
        
        assert 'WhileLoop:' in result
        assert 'Condition:' in result
        assert 'Body:' in result
        
        # For loop
        for_loop = ForLoop(
            variable='i',
            items=['1', '2', '3'],
            body=StatementList(statements=[])
        )
        result = visitor.visit(for_loop)
        
        assert 'ForLoop (var: i)' in result
        assert "Items: ['1', '2', '3']" in result
    
    def test_redirections(self):
        """Test formatting redirections."""
        cmd = SimpleCommand(
            args=['echo', 'test'],
            arg_types=['WORD', 'WORD'],
            redirects=[
                Redirect(type='>', target='output.txt'),
                Redirect(type='2>', target='error.log', fd=2)
            ]
        )
        visitor = DebugASTVisitor()
        result = visitor.visit(cmd)
        
        assert 'Redirects:' in result
        assert "Redirect: type=>, target='output.txt'" in result
        assert "Redirect: fd=2, type=2>, target='error.log'" in result
    
    def test_array_assignments(self):
        """Test formatting array assignments."""
        cmd = SimpleCommand(
            args=['echo'],
            arg_types=['WORD'],
            array_assignments=[
                ArrayInitialization(name='arr', elements=['a', 'b', 'c']),
                ArrayElementAssignment(name='arr', index='0', value='x')
            ]
        )
        visitor = DebugASTVisitor()
        result = visitor.visit(cmd)
        
        assert 'Array Assignments:' in result
        assert "ArrayInit: arr=('a' 'b' 'c')" in result
        assert "ArrayElement: arr[0]='x'" in result
    
    def test_nested_structure(self):
        """Test formatting deeply nested structures."""
        ast = TopLevel(items=[
            FunctionDef(
                name='nested',
                body=StatementList(statements=[
                    AndOrList(pipelines=[
                        Pipeline(commands=[
                            SimpleCommand(args=['if'], arg_types=['WORD'])
                        ])
                    ], operators=['&&']),
                    AndOrList(pipelines=[
                        Pipeline(commands=[
                            SimpleCommand(args=['then'], arg_types=['WORD'])
                        ])
                    ])
                ])
            )
        ])
        
        visitor = DebugASTVisitor()
        result = visitor.visit(ast)
        
        # Check indentation is working
        lines = result.strip().split('\n')
        assert lines[0] == 'TopLevel:'
        assert lines[1].startswith('  FunctionDef')
        assert any('    Body:' in line for line in lines)
        assert any('      CommandList:' in line for line in lines)
    
    def test_comparison_with_old_formatter(self):
        """Test that both formatters handle basic cases similarly."""
        # Simple command
        cmd = SimpleCommand(args=['ls', '-la'], arg_types=['WORD', 'WORD'])
        
        old_output = ASTFormatter.format(cmd)
        new_visitor = DebugASTVisitor()
        new_output = new_visitor.visit(cmd)
        
        # Both should mention SimpleCommand and the command
        assert 'SimpleCommand' in old_output
        assert 'SimpleCommand' in new_output
        assert 'ls -la' in old_output
        assert 'ls -la' in new_output


def test_visitor_import():
    """Test that DebugASTVisitor can be imported from visitor module."""
    from psh.visitor import DebugASTVisitor
    assert DebugASTVisitor is not None