"""
Test arithmetic commands in parser combinator implementation.

This module tests the arithmetic command ((expression)) syntax support 
in the parser combinator implementation.
"""

import pytest
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.lexer import tokenize
from psh.ast_nodes import ArithmeticEvaluation, TopLevel, CommandList


class TestArithmeticCommandsCombinator:
    """Test arithmetic commands using parser combinator."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = ParserCombinatorShellParser()
    
    def test_simple_arithmetic_command(self):
        """Test basic arithmetic command parsing."""
        tokens = list(tokenize("((5 + 3))"))
        result = self.parser.parse(tokens)
        
        assert isinstance(result, (TopLevel, CommandList))
        statements = result.statements if hasattr(result, 'statements') else [result]
        assert len(statements) == 1
        
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "5 + 3"
        assert cmd.redirects == []
        assert cmd.background is False
    
    def test_arithmetic_with_variables(self):
        """Test arithmetic command with variables."""
        tokens = list(tokenize("((x + y))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x + y"
    
    def test_complex_arithmetic_expression(self):
        """Test complex arithmetic expression."""
        tokens = list(tokenize("((x * y + z / 2 - 1))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x * y + z / 2 - 1"
    
    def test_arithmetic_with_assignment(self):
        """Test arithmetic command with assignment."""
        tokens = list(tokenize("((x = 5 + 3))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "x = 5 + 3"
    
    def test_arithmetic_increment(self):
        """Test arithmetic increment operations."""
        tokens = list(tokenize("((++x))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "++x"
    
    def test_arithmetic_decrement(self):
        """Test arithmetic decrement operations."""
        tokens = list(tokenize("((y--))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "y--"
    
    def test_arithmetic_with_parentheses(self):
        """Test arithmetic with mathematical parentheses."""
        tokens = list(tokenize("((a * b + c / d))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "a * b + c / d"
    
    def test_arithmetic_compound_assignment(self):
        """Test arithmetic compound assignment operations."""
        tokens = list(tokenize("((total += value))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "total += value"
    
    def test_arithmetic_multiple_operations(self):
        """Test arithmetic with multiple operations."""
        tokens = list(tokenize("((a *= 2, b += 3, c--))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "a *= 2, b += 3, c--"
    
    def test_arithmetic_with_special_variables(self):
        """Test arithmetic with special shell variables."""
        tokens = list(tokenize("(($# + $?))"))
        result = self.parser.parse(tokens)
        
        statements = result.statements if hasattr(result, 'statements') else [result]
        cmd = statements[0]
        assert isinstance(cmd, ArithmeticEvaluation)
        assert cmd.expression == "$# + $?"