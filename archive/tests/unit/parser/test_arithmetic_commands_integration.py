"""
Test integration of arithmetic commands with control structures.

This module tests arithmetic commands used within control structures
and complex shell constructs to ensure proper integration.
"""

import pytest
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.lexer import tokenize
from psh.ast_nodes import (
    ArithmeticEvaluation, TopLevel, CommandList, IfConditional, 
    WhileLoop, ForLoop, StatementList
)


class TestArithmeticCommandsIntegration:
    """Test arithmetic commands integration with shell constructs."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = ParserCombinatorShellParser()
    
    def test_arithmetic_in_if_condition(self):
        """Test arithmetic command as if condition."""
        tokens = list(tokenize("if ((x > 10)); then echo large; fi"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        if_stmt = statements[0]
        assert isinstance(if_stmt, IfConditional)
        
        # Check condition contains arithmetic evaluation
        condition_stmt = if_stmt.condition.statements[0]
        assert isinstance(condition_stmt, ArithmeticEvaluation)
        assert condition_stmt.expression == "x > 10"
    
    def test_arithmetic_in_while_condition(self):
        """Test arithmetic command as while condition."""
        tokens = list(tokenize("while ((count < 100)); do ((count++)); done"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        while_stmt = statements[0]
        assert isinstance(while_stmt, WhileLoop)
        
        # Check condition
        condition_stmt = while_stmt.condition.statements[0]
        assert isinstance(condition_stmt, ArithmeticEvaluation)
        assert condition_stmt.expression == "count < 100"
        
        # Check body contains arithmetic increment
        body_stmt = while_stmt.body.statements[0]
        assert isinstance(body_stmt, ArithmeticEvaluation)
        assert body_stmt.expression == "count++"
    
    def test_arithmetic_in_for_loop_body(self):
        """Test arithmetic command in for loop body."""
        tokens = list(tokenize("for i in 1 2 3; do ((sum += i)); done"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        for_stmt = statements[0]
        assert isinstance(for_stmt, ForLoop)
        
        # Check body contains arithmetic operation
        body_stmt = for_stmt.body.statements[0]
        assert isinstance(body_stmt, ArithmeticEvaluation)
        assert body_stmt.expression == "sum += i"
    
    def test_multiple_arithmetic_commands(self):
        """Test multiple arithmetic commands in sequence."""
        tokens = list(tokenize("((x = 5)); ((y = 10)); ((z = x + y))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        assert len(statements) == 3
        
        # Check all three are arithmetic evaluations
        for i, expected_expr in enumerate(["x = 5", "y = 10", "z = x + y"]):
            stmt = statements[i]
            assert isinstance(stmt, ArithmeticEvaluation)
            assert stmt.expression == expected_expr
    
    def test_arithmetic_with_logical_operators(self):
        """Test arithmetic commands with logical operators."""
        tokens = list(tokenize("((x > 0)) && echo positive || echo non-positive"))
        result = self.parser.parse(tokens)
        
        # Should be parsed as an and-or list since there are operators
        statements = result.statements if hasattr(result, 'statements') else [result]
        and_or_list = statements[0]
        
        # First pipeline should contain arithmetic evaluation
        first_pipeline = and_or_list.pipelines[0]
        assert isinstance(first_pipeline, ArithmeticEvaluation)
        assert first_pipeline.expression == "x > 0"
    
    def test_arithmetic_assignment_sequences(self):
        """Test sequences of arithmetic assignments.""" 
        tokens = list(tokenize("((i = 0)); ((max = 100)); while ((i < max)); do ((i++)); done"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        assert len(statements) == 3
        
        # Check initialization assignments
        assert isinstance(statements[0], ArithmeticEvaluation)
        assert statements[0].expression == "i = 0"
        
        assert isinstance(statements[1], ArithmeticEvaluation)
        assert statements[1].expression == "max = 100"
        
        # Check while loop with arithmetic condition and body
        while_stmt = statements[2]
        assert isinstance(while_stmt, WhileLoop)
        
        condition_stmt = while_stmt.condition.statements[0]
        assert isinstance(condition_stmt, ArithmeticEvaluation)
        assert condition_stmt.expression == "i < max"
        
        body_stmt = while_stmt.body.statements[0]
        assert isinstance(body_stmt, ArithmeticEvaluation)
        assert body_stmt.expression == "i++"
    
    def test_arithmetic_with_exit_status(self):
        """Test arithmetic command exit status usage."""
        tokens = list(tokenize("((result = x * y)) && echo success"))
        result = self.parser.parse(tokens)
        
        # Should be and-or list since there's && operator
        statements = result.statements if hasattr(result, 'statements') else [result]
        and_or_list = statements[0]
        
        # First element should be arithmetic evaluation
        first_element = and_or_list.pipelines[0]
        assert isinstance(first_element, ArithmeticEvaluation)
        assert first_element.expression == "result = x * y"
    
    def test_nested_arithmetic_expressions(self):
        """Test complex nested arithmetic expressions."""
        tokens = list(tokenize("((result = (a + b) * (c - d) / e))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        arith_cmd = statements[0]
        assert isinstance(arith_cmd, ArithmeticEvaluation)
        # Note: Due to tokenization, this becomes a single expression
        assert "result" in arith_cmd.expression
        assert "a" in arith_cmd.expression and "b" in arith_cmd.expression
    
    def test_arithmetic_in_complex_pipeline(self):
        """Test arithmetic command in complex pipeline scenarios."""
        tokens = list(tokenize("echo start; ((x = 42)); echo $x"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        assert len(statements) == 3
        
        # Middle statement should be arithmetic
        arith_cmd = statements[1]
        assert isinstance(arith_cmd, ArithmeticEvaluation)
        assert arith_cmd.expression == "x = 42"