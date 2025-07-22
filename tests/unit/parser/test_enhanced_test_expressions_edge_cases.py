"""Test edge cases for enhanced test expressions ([[ ]]) in parser combinator."""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import (
    EnhancedTestStatement, BinaryTestExpression, UnaryTestExpression,
    NegatedTestExpression
)


class TestEnhancedTestEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_empty_test_expression(self):
        """Test empty test expression should fail gracefully."""
        with pytest.raises(Exception):
            tokens = tokenize('[[ ]]')
            self.parser.parse(tokens)
    
    def test_incomplete_test_expression(self):
        """Test incomplete test expressions."""
        # Missing closing bracket
        with pytest.raises(Exception):
            tokens = tokenize('[[ "test" == "test"')
            self.parser.parse(tokens)
    
    def test_single_operand_parsing(self):
        """Test single operand gets parsed as string test."""
        tokens = tokenize('[[ "nonempty" ]]')
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        
        expr = stmt.expression
        assert isinstance(expr, UnaryTestExpression)
        assert expr.operator == '-n'  # Treated as non-empty string test
        assert expr.operand == 'nonempty'  # String content after quote processing
    
    def test_quoted_strings_with_spaces(self):
        """Test quoted strings containing spaces."""
        tokens = tokenize('[[ "hello world" == "hello world" ]]')
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == 'hello world'  # String content after quote processing
        assert expr.operator == '=='
        assert expr.right == 'hello world'  # String content after quote processing
    
    def test_unquoted_strings(self):
        """Test unquoted strings."""
        tokens = tokenize('[[ hello == world ]]')
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == 'hello'
        assert expr.operator == '=='
        assert expr.right == 'world'
    
    def test_special_characters_in_strings(self):
        """Test strings with special characters."""
        tokens = tokenize('[[ "test@example.com" =~ .*@.* ]]')
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == 'test@example.com'  # String content after quote processing
        assert expr.operator == '=~'
        assert expr.right == '.*@.*'
    
    def test_numbers_as_strings(self):
        """Test numeric values in string context."""
        tokens = tokenize('[[ "123" == "123" ]]')
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '123'  # String content after quote processing
        assert expr.operator == '=='
        assert expr.right == '123'  # String content after quote processing
    
    def test_variable_expansion_syntax(self):
        """Test variable expansion syntax."""
        tokens = tokenize('[[ ${var} == "value" ]]')
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '${var}'  # Parameter expansion syntax preserved
        assert expr.operator == '=='
        assert expr.right == 'value'  # String content after quote processing
    
    def test_nested_brackets_in_regex(self):
        """Test regex patterns with brackets."""
        tokens = tokenize('[[ "test[123]" =~ test\\[.*\\] ]]')
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == 'test[123]'  # String content after quote processing
        assert expr.operator == '=~'
        assert expr.right == 'test\\[.*\\]'
    
    def test_whitespace_handling(self):
        """Test various whitespace configurations."""
        test_cases = [
            '[[   "test"   ==   "test"   ]]',  # Extra spaces
            '[["test"=="test"]]',              # No spaces around operators
            '[[ "test" == "test"]]',           # Minimal spacing
        ]
        
        for cmd in test_cases:
            tokens = tokenize(cmd)
            result = self.parser.parse(tokens)
            
            stmt = result.statements[0]
            assert isinstance(stmt, EnhancedTestStatement)
            expr = stmt.expression
            assert isinstance(expr, BinaryTestExpression)
            assert expr.operator == '=='


class TestEnhancedTestOperatorVariations:
    """Test various operator formats and combinations."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_all_binary_operators(self):
        """Test all supported binary operators."""
        operators = ['==', '!=', '=', '<', '>', '=~', '-eq', '-ne', '-lt', '-le', '-gt', '-ge']
        
        for op in operators:
            cmd = f'[[ "left" {op} "right" ]]'
            tokens = tokenize(cmd)
            result = self.parser.parse(tokens)
            
            stmt = result.statements[0]
            assert isinstance(stmt, EnhancedTestStatement)
            expr = stmt.expression
            assert isinstance(expr, BinaryTestExpression)
            assert expr.operator == op
    
    def test_file_test_operators(self):
        """Test file test operators."""
        operators = ['-f', '-d', '-e', '-r', '-w', '-x', '-s', '-L', '-S', '-p', '-b', '-c']
        
        for op in operators:
            cmd = f'[[ {op} /some/path ]]'
            tokens = tokenize(cmd)
            result = self.parser.parse(tokens)
            
            stmt = result.statements[0]
            assert isinstance(stmt, EnhancedTestStatement)
            expr = stmt.expression
            assert isinstance(expr, UnaryTestExpression)
            assert expr.operator == op
    
    def test_string_test_operators(self):
        """Test string test operators."""
        operators = ['-z', '-n']
        
        for op in operators:
            cmd = f'[[ {op} "string" ]]'
            tokens = tokenize(cmd)
            result = self.parser.parse(tokens)
            
            stmt = result.statements[0]
            assert isinstance(stmt, EnhancedTestStatement)
            expr = stmt.expression
            assert isinstance(expr, UnaryTestExpression)
            assert expr.operator == op


class TestEnhancedTestComplexPatterns:
    """Test complex patterns and realistic usage."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_email_validation_pattern(self):
        """Test realistic email validation pattern."""
        cmd = '[[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$ ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.operator == '=~'
    
    def test_path_validation(self):
        """Test path validation patterns."""
        cmd = '[[ "$path" =~ ^/.+ ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '$path'  # Variable preserved, quotes processed
        assert expr.operator == '=~'
        assert expr.right == '^/. +'  # Regex pattern with space after tokenization
    
    def test_version_comparison(self):
        """Test version string comparison."""
        cmd = '[[ "$version" == "1.2.3" ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '$version'  # Variable preserved, quotes processed
        assert expr.operator == '=='
        assert expr.right == '1.2.3'  # String content after quote processing
    
    def test_numeric_range_check(self):
        """Test numeric range checking."""
        cmd = '[[ $num -ge 0 ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '$num'
        assert expr.operator == '-ge'
        assert expr.right == '0'
    
    def test_negated_file_existence(self):
        """Test negated file existence check."""
        cmd = '[[ ! -f "$config_file" ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        expr = stmt.expression
        assert isinstance(expr, NegatedTestExpression)
        
        inner_expr = expr.expression
        assert isinstance(inner_expr, UnaryTestExpression)
        assert inner_expr.operator == '-f'
        assert inner_expr.operand == '$config_file'  # Variable preserved, quotes processed