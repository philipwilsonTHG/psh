"""
Test edge cases for arithmetic commands in parser combinator implementation.

This module tests complex scenarios, error conditions, and edge cases
for arithmetic command ((expression)) syntax.
"""

import pytest
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.lexer import tokenize
from psh.ast_nodes import ArithmeticEvaluation, TopLevel, CommandList
from psh.parser.abstract_parser import ParseError


class TestArithmeticCommandsEdgeCases:
    """Test edge cases for arithmetic commands using parser combinator."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = ParserCombinatorShellParser()
    
    def test_empty_arithmetic_command(self):
        """Test empty arithmetic command."""
        tokens = list(tokenize("(())"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == ""
    
    def test_arithmetic_with_whitespace(self):
        """Test arithmetic with various whitespace patterns."""
        tokens = list(tokenize("(( x   +   y ))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        # Expression should preserve whitespace from tokens
        assert "x" in cmd.expression and "y" in cmd.expression
    
    def test_arithmetic_with_nested_parentheses_complex(self):
        """Test complex arithmetic expression."""
        tokens = list(tokenize("((a * b + c * d - e / f))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "a * b + c * d - e / f"
    
    def test_arithmetic_with_array_access(self):
        """Test arithmetic with array access."""
        tokens = list(tokenize("((arr[5] + arr[i]))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert "arr[5]" in cmd.expression and "arr[i]" in cmd.expression
    
    def test_arithmetic_bitwise_operations(self):
        """Test arithmetic with bitwise operations."""
        tokens = list(tokenize("((x & 0xFF | y << 2))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x & 0xFF | y << 2"
    
    def test_arithmetic_with_ternary(self):
        """Test arithmetic with ternary operator."""
        tokens = list(tokenize("((x > 0 ? x : -x))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x > 0 ? x : -x"
    
    def test_arithmetic_with_function_calls(self):
        """Test arithmetic with function-like syntax (base conversion)."""
        tokens = list(tokenize("((16#FF + 8#77))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "16#FF + 8#77"
    
    def test_arithmetic_logical_operators(self):
        """Test arithmetic with logical operators."""
        tokens = list(tokenize("((x && y || z))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x && y || z"
    
    def test_arithmetic_comparison_operators(self):
        """Test arithmetic with comparison operators."""
        tokens = list(tokenize("((x >= 10 && y <= 20))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x >= 10 && y <= 20"
    
    def test_arithmetic_string_length(self):
        """Test arithmetic with string length operator.""" 
        tokens = list(tokenize("((${#var} + 5))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert "${#var}" in cmd.expression
    
    def test_arithmetic_modulo_operation(self):
        """Test arithmetic modulo operation."""
        tokens = list(tokenize("((x % 10))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x % 10"
    
    def test_arithmetic_exponentiation(self):
        """Test arithmetic exponentiation operation."""
        tokens = list(tokenize("((2 ** 8))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "2 ** 8"
    
    def test_arithmetic_with_command_line_args(self):
        """Test arithmetic with command line arguments."""
        tokens = list(tokenize("(($1 + $2 * $3))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "$1 + $2 * $3"
    
    def test_arithmetic_very_long_expression(self):
        """Test very long arithmetic expression."""
        long_expr = " + ".join([f"var{i}" for i in range(20)])
        tokens = list(tokenize(f"(({long_expr}))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        # Should contain all variables
        for i in range(20):
            assert f"var{i}" in cmd.expression
    
    def test_arithmetic_with_negative_numbers(self):
        """Test arithmetic with negative numbers."""
        tokens = list(tokenize("((-5 + -10 * -2))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "-5 + -10 * -2"
    
    def test_arithmetic_scientific_notation(self):
        """Test arithmetic with scientific notation (if supported)."""
        tokens = list(tokenize("((1e3 + 2E-2))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "1e3 + 2E-2"