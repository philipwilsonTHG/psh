#!/usr/bin/env python3
"""Comparison tests between parser combinator and recursive descent parser.

This module ensures that both parser implementations generate equivalent
AST structures for the same input, validating the correctness of the
parser combinator implementation.
"""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.recursive_descent_adapter import RecursiveDescentAdapter
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import (
    IfConditional, WhileLoop, ForLoop, CStyleForLoop, CaseConditional,
    SimpleCommand, Pipeline, AndOrList, CommandList
)


class TestParserComparison:
    """Compare AST output between parser implementations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rd_parser = RecursiveDescentAdapter()
        self.pc_parser = ParserCombinatorShellParser()
    
    def parse_both(self, command: str):
        """Parse with both parsers and return ASTs."""
        tokens_rd = tokenize(command)
        tokens_pc = tokenize(command)
        
        rd_ast = self.rd_parser.parse(tokens_rd)
        pc_ast = self.pc_parser.parse(tokens_pc)
        
        return rd_ast, pc_ast
    
    def assert_ast_equivalent(self, ast1, ast2):
        """Assert two AST nodes are equivalent."""
        # Compare types
        assert type(ast1) == type(ast2), f"Type mismatch: {type(ast1)} vs {type(ast2)}"
        
        # Compare based on node type
        if isinstance(ast1, CommandList):
            assert len(ast1.statements) == len(ast2.statements)
            for s1, s2 in zip(ast1.statements, ast2.statements):
                self.assert_ast_equivalent(s1, s2)
        
        elif isinstance(ast1, AndOrList):
            assert len(ast1.pipelines) == len(ast2.pipelines)
            assert ast1.operators == ast2.operators
            for p1, p2 in zip(ast1.pipelines, ast2.pipelines):
                self.assert_ast_equivalent(p1, p2)
        
        elif isinstance(ast1, Pipeline):
            # Handle case where pc_parser returns SimpleCommand directly
            if isinstance(ast2, SimpleCommand):
                assert len(ast1.commands) == 1
                self.assert_ast_equivalent(ast1.commands[0], ast2)
            else:
                assert len(ast1.commands) == len(ast2.commands)
                for c1, c2 in zip(ast1.commands, ast2.commands):
                    self.assert_ast_equivalent(c1, c2)
        
        elif isinstance(ast1, SimpleCommand) and isinstance(ast2, Pipeline):
            # Handle reverse case
            assert len(ast2.commands) == 1
            self.assert_ast_equivalent(ast1, ast2.commands[0])
        
        elif isinstance(ast1, SimpleCommand):
            assert ast1.args == ast2.args
            assert len(ast1.redirects) == len(ast2.redirects)
        
        elif isinstance(ast1, IfConditional):
            self.assert_ast_equivalent(ast1.condition, ast2.condition)
            self.assert_ast_equivalent(ast1.then_part, ast2.then_part)
            assert len(ast1.elif_parts) == len(ast2.elif_parts)
            for (cond1, body1), (cond2, body2) in zip(ast1.elif_parts, ast2.elif_parts):
                self.assert_ast_equivalent(cond1, cond2)
                self.assert_ast_equivalent(body1, body2)
            if ast1.else_part or ast2.else_part:
                self.assert_ast_equivalent(ast1.else_part, ast2.else_part)
        
        elif isinstance(ast1, WhileLoop):
            self.assert_ast_equivalent(ast1.condition, ast2.condition)
            self.assert_ast_equivalent(ast1.body, ast2.body)
        
        elif isinstance(ast1, ForLoop):
            assert ast1.variable == ast2.variable
            assert ast1.items == ast2.items
            self.assert_ast_equivalent(ast1.body, ast2.body)
        
        elif isinstance(ast1, CStyleForLoop):
            assert ast1.init_expr == ast2.init_expr
            assert ast1.condition_expr == ast2.condition_expr
            assert ast1.update_expr == ast2.update_expr
            self.assert_ast_equivalent(ast1.body, ast2.body)
        
        elif isinstance(ast1, CaseConditional):
            assert ast1.expr == ast2.expr
            assert len(ast1.items) == len(ast2.items)
            for item1, item2 in zip(ast1.items, ast2.items):
                assert len(item1.patterns) == len(item2.patterns)
                for p1, p2 in zip(item1.patterns, item2.patterns):
                    assert p1.pattern == p2.pattern
                self.assert_ast_equivalent(item1.commands, item2.commands)
                assert item1.terminator == item2.terminator


class TestSimpleCommandComparison(TestParserComparison):
    """Compare simple command parsing."""
    
    def test_single_command(self):
        """Test single command parsing."""
        rd_ast, pc_ast = self.parse_both("echo hello")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_command_with_args(self):
        """Test command with multiple arguments."""
        rd_ast, pc_ast = self.parse_both("ls -la /tmp")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_pipeline(self):
        """Test pipeline parsing."""
        rd_ast, pc_ast = self.parse_both("cat file | grep pattern | wc -l")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_and_or_list(self):
        """Test && and || operators."""
        rd_ast, pc_ast = self.parse_both("true && echo yes || echo no")
        self.assert_ast_equivalent(rd_ast, pc_ast)


class TestIfStatementComparison(TestParserComparison):
    """Compare if statement parsing."""
    
    def test_simple_if(self):
        """Test basic if/then/fi."""
        rd_ast, pc_ast = self.parse_both("if true; then echo yes; fi")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_if_else(self):
        """Test if/then/else/fi."""
        rd_ast, pc_ast = self.parse_both("if false; then echo no; else echo yes; fi")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_if_elif_else(self):
        """Test if/elif/else."""
        rd_ast, pc_ast = self.parse_both(
            "if test $x -eq 1; then echo one; "
            "elif test $x -eq 2; then echo two; "
            "else echo other; fi"
        )
        self.assert_ast_equivalent(rd_ast, pc_ast)


class TestWhileLoopComparison(TestParserComparison):
    """Compare while loop parsing."""
    
    def test_simple_while(self):
        """Test basic while loop."""
        rd_ast, pc_ast = self.parse_both("while true; do echo loop; done")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_while_with_condition(self):
        """Test while with complex condition."""
        rd_ast, pc_ast = self.parse_both("while test -f file; do sleep 1; done")
        self.assert_ast_equivalent(rd_ast, pc_ast)


class TestForLoopComparison(TestParserComparison):
    """Compare for loop parsing."""
    
    def test_simple_for(self):
        """Test basic for loop."""
        rd_ast, pc_ast = self.parse_both("for i in a b c; do echo $i; done")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_for_with_quotes(self):
        """Test for loop with quoted items."""
        rd_ast, pc_ast = self.parse_both('for f in "file 1" "file 2"; do cat "$f"; done')
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_c_style_for(self):
        """Test C-style for loop."""
        rd_ast, pc_ast = self.parse_both("for ((i=0; i<10; i++)); do echo $i; done")
        self.assert_ast_equivalent(rd_ast, pc_ast)


class TestCaseStatementComparison(TestParserComparison):
    """Compare case statement parsing."""
    
    def test_simple_case(self):
        """Test basic case statement."""
        rd_ast, pc_ast = self.parse_both('case $x in a) echo "A";; esac')
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_case_multiple_patterns(self):
        """Test case with multiple patterns."""
        rd_ast, pc_ast = self.parse_both('case $x in a|b|c) echo "ABC";; esac')
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_case_multiple_items(self):
        """Test case with multiple items."""
        rd_ast, pc_ast = self.parse_both(
            'case $x in a) echo "A";; b) echo "B";; *) echo "Other";; esac'
        )
        self.assert_ast_equivalent(rd_ast, pc_ast)


class TestComplexComparison(TestParserComparison):
    """Compare complex constructs."""
    
    def test_nested_if_while(self):
        """Test nested if inside while."""
        rd_ast, pc_ast = self.parse_both(
            "while true; do if test -f stop; then break; fi; sleep 1; done"
        )
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_control_with_pipeline(self):
        """Test control structure with pipeline."""
        rd_ast, pc_ast = self.parse_both(
            "if echo test | grep -q test; then echo found; fi"
        )
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_multiple_statements(self):
        """Test multiple statements."""
        rd_ast, pc_ast = self.parse_both(
            "echo one; echo two; echo three"
        )
        self.assert_ast_equivalent(rd_ast, pc_ast)


class TestEdgeCaseComparison(TestParserComparison):
    """Compare edge cases between parsers."""
    
    def test_empty_input(self):
        """Test empty input."""
        rd_ast, pc_ast = self.parse_both("")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_semicolon_only(self):
        """Test lone semicolon."""
        rd_ast, pc_ast = self.parse_both(";")
        self.assert_ast_equivalent(rd_ast, pc_ast)
    
    def test_trailing_semicolon(self):
        """Test command with trailing semicolon."""
        rd_ast, pc_ast = self.parse_both("echo hello;")
        self.assert_ast_equivalent(rd_ast, pc_ast)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])