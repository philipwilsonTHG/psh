"""Test enhanced test expressions ([[ ]]) in parser combinator implementation."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import (
    EnhancedTestStatement, BinaryTestExpression, UnaryTestExpression,
    NegatedTestExpression
)


class TestEnhancedTestExpressions:
    """Test basic enhanced test expression parsing."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
        
    def parse_test_expression(self, cmd: str) -> EnhancedTestStatement:
        """Helper to parse and extract enhanced test statement."""
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        return stmt
    
    def test_string_equality(self):
        """Test string equality comparisons."""
        stmt = self.parse_test_expression('[[ "hello" == "hello" ]]')
        
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == "hello"
        assert expr.operator == "=="
        assert expr.right == "hello"
    
    def test_string_inequality(self):
        """Test string inequality comparisons."""
        stmt = self.parse_test_expression('[[ "hello" != "world" ]]')
        
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == "hello"
        assert expr.operator == "!="
        assert expr.right == "world"
    
    def test_string_ordering(self):
        """Test string ordering comparisons."""
        stmt = self.parse_test_expression('[[ "apple" < "banana" ]]')
        
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == "apple"
        assert expr.operator == "<"
        assert expr.right == "banana"
    
    def test_regex_matching(self):
        """Test regex pattern matching."""
        stmt = self.parse_test_expression('[[ "hello123" =~ ^hello[0-9]+$ ]]')
        
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == "hello123"
        assert expr.operator == "=~"
        # Regex gets tokenized as separate words, joined with spaces
        assert "hello" in expr.right and "[0-9]" in expr.right
    
    def test_arithmetic_comparisons(self):
        """Test arithmetic comparison operators."""
        test_cases = [
            ('[[ 5 -eq 5 ]]', '5', '-eq', '5'),
            ('[[ 5 -ne 3 ]]', '5', '-ne', '3'),
            ('[[ 5 -gt 3 ]]', '5', '-gt', '3'),
            ('[[ 3 -lt 5 ]]', '3', '-lt', '5'),
            ('[[ 5 -ge 5 ]]', '5', '-ge', '5'),
            ('[[ 3 -le 5 ]]', '3', '-le', '5'),
        ]
        
        for cmd, left, op, right in test_cases:
            stmt = self.parse_test_expression(cmd)
            expr = stmt.expression
            assert isinstance(expr, BinaryTestExpression)
            assert expr.left == left
            assert expr.operator == op
            assert expr.right == right


class TestUnaryTestExpressions:
    """Test unary test expressions."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
        
    def parse_test_expression(self, cmd: str) -> EnhancedTestStatement:
        """Helper to parse and extract enhanced test statement."""
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        return stmt
    
    def test_file_tests(self):
        """Test file test operators."""
        test_cases = [
            ('[[ -f /etc/passwd ]]', '-f', '/etc/passwd'),
            ('[[ -d /tmp ]]', '-d', '/tmp'),
            ('[[ -e /etc/hosts ]]', '-e', '/etc/hosts'),
            ('[[ -r /etc/passwd ]]', '-r', '/etc/passwd'),
            ('[[ -w /tmp ]]', '-w', '/tmp'),
            ('[[ -x /bin/sh ]]', '-x', '/bin/sh'),
        ]
        
        for cmd, op, operand in test_cases:
            stmt = self.parse_test_expression(cmd)
            expr = stmt.expression
            assert isinstance(expr, UnaryTestExpression)
            assert expr.operator == op
            assert expr.operand == operand
    
    def test_string_tests(self):
        """Test string test operators."""
        stmt = self.parse_test_expression('[[ -z "" ]]')
        expr = stmt.expression
        assert isinstance(expr, UnaryTestExpression)
        assert expr.operator == '-z'
        assert expr.operand == ''  # Empty string after quote processing
        
        stmt = self.parse_test_expression('[[ -n "hello" ]]')
        expr = stmt.expression
        assert isinstance(expr, UnaryTestExpression)
        assert expr.operator == '-n'
        assert expr.operand == 'hello'  # String content after quote processing


class TestNegatedExpressions:
    """Test negated test expressions."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
        
    def parse_test_expression(self, cmd: str) -> EnhancedTestStatement:
        """Helper to parse and extract enhanced test statement."""
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        return stmt
    
    def test_negated_file_test(self):
        """Test negated file test expressions."""
        stmt = self.parse_test_expression('[[ ! -f /nonexistent ]]')
        
        expr = stmt.expression
        assert isinstance(expr, NegatedTestExpression)
        
        inner_expr = expr.expression
        assert isinstance(inner_expr, UnaryTestExpression)
        assert inner_expr.operator == '-f'
        assert inner_expr.operand == '/nonexistent'
    
    def test_negated_string_comparison(self):
        """Test negated string comparison."""
        stmt = self.parse_test_expression('[[ ! "hello" == "world" ]]')
        
        expr = stmt.expression
        assert isinstance(expr, NegatedTestExpression)
        
        inner_expr = expr.expression
        assert isinstance(inner_expr, BinaryTestExpression)
        assert inner_expr.left == 'hello'  # String content after quote processing
        assert inner_expr.operator == '=='
        assert inner_expr.right == 'world'  # String content after quote processing


class TestEnhancedTestIntegration:
    """Test enhanced test expressions in different contexts."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_enhanced_test_as_standalone_statement(self):
        """Test enhanced test as a standalone statement."""
        tokens = tokenize('[[ "test" == "test" ]]')
        result = self.parser.parse(tokens)
        
        # Should parse as a single enhanced test statement (not wrapped in AndOrList)
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
    
    def test_enhanced_test_with_variables(self):
        """Test enhanced test with variable references."""
        stmt_cmd = '[[ $var == "value" ]]'
        tokens = tokenize(stmt_cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '$var'  # Variable with $ prefix preserved
        assert expr.operator == '=='
        assert expr.right == 'value'  # String content after quote processing
    
    def test_enhanced_test_with_complex_expressions(self):
        """Test enhanced test with more complex expressions."""
        # Test with command substitution-like pattern (parsed as single expression for MVP)
        stmt_cmd = '[[ $(echo test) == "test" ]]'
        tokens = tokenize(stmt_cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        
        # In our MVP implementation, this gets parsed as a binary expression
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)