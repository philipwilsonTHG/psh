"""
Test expression parsing for PSH shell.

This module handles parsing of enhanced test expressions ([[ ... ]]).
"""

from ..token_types import TokenType
from ..ast_nodes import EnhancedTestStatement, TestExpression, BinaryTestExpression, UnaryTestExpression, CompoundTestExpression, NegatedTestExpression
from .helpers import TokenGroups


class TestParser:
    """Parser for test expression constructs."""
    
    def __init__(self, main_parser):
        """Initialize with reference to main parser."""
        self.parser = main_parser
    
    def parse_enhanced_test_statement(self) -> EnhancedTestStatement:
        """Parse [[ ... ]] enhanced test statement."""
        with self.parser.context:
            self.parser.context.in_test_expr = True
            
            self.parser.expect(TokenType.DOUBLE_LBRACKET)
            self.parser.skip_newlines()
            
            # Parse the test expression through delegation for integration compatibility
            # Temporarily replace delegation to avoid infinite recursion
            original_delegation = self.parser.parse_test_expression
            self.parser.parse_test_expression = self.parse_test_expression
            try:
                expression = original_delegation()
            finally:
                self.parser.parse_test_expression = original_delegation
            
            self.parser.skip_newlines()
            self.parser.expect(TokenType.DOUBLE_RBRACKET)
            
            redirects = self.parser.redirections.parse_redirects()
            
            return EnhancedTestStatement(expression, redirects)
    
    def parse_test_expression(self) -> TestExpression:
        """Parse a test expression with proper precedence."""
        return self.parse_test_or_expression()
    
    def parse_test_or_expression(self) -> TestExpression:
        """Parse test expression with || operator."""
        left = self.parse_test_and_expression()
        
        while self.parser.match(TokenType.OR_OR):
            self.parser.advance()
            self.parser.skip_newlines()
            right = self.parse_test_and_expression()
            left = CompoundTestExpression(left, '||', right)
        
        return left
    
    def parse_test_and_expression(self) -> TestExpression:
        """Parse test expression with && operator."""
        left = self.parse_test_unary_expression()
        
        while self.parser.match(TokenType.AND_AND):
            self.parser.advance()
            self.parser.skip_newlines()
            right = self.parse_test_unary_expression()
            left = CompoundTestExpression(left, '&&', right)
        
        return left
    
    def parse_test_unary_expression(self) -> TestExpression:
        """Parse unary test expression (possibly negated)."""
        if self.parser.match(TokenType.EXCLAMATION):
            self.parser.advance()
            self.parser.skip_newlines()
            expr = self.parse_test_unary_expression()
            return NegatedTestExpression(expr)
        
        return self.parse_test_primary_expression()
    
    def parse_test_primary_expression(self) -> TestExpression:
        """Parse primary test expression."""
        self.parser.skip_newlines()
        
        # Empty test
        if self.parser.match(TokenType.DOUBLE_RBRACKET):
            return UnaryTestExpression('-n', '')
        
        # Parenthesized expression
        if self.parser.match(TokenType.LPAREN):
            self.parser.advance()
            expr = self.parse_test_expression()
            self.parser.expect(TokenType.RPAREN)
            return expr
        
        # Check for unary operators
        if self.parser.match(TokenType.WORD) and self._is_unary_test_operator(self.parser.peek().value):
            operator = self.parser.advance().value
            self.parser.skip_newlines()
            operand = self._parse_test_operand()
            return UnaryTestExpression(operator, operand)
        
        # Binary expression or single value
        left = self._parse_test_operand()
        self.parser.skip_newlines()
        
        # Check for binary operators
        if self.parser.match(TokenType.WORD, TokenType.REGEX_MATCH):
            token = self.parser.peek()
            if token.type == TokenType.REGEX_MATCH or self._is_binary_test_operator(token.value):
                operator = self.parser.advance().value
                self.parser.skip_newlines()
                
                # Special handling for regex patterns
                if operator == '=~':
                    self.parser.context.push_context('regex_rhs')
                
                right = self._parse_test_operand()
                
                if operator == '=~':
                    self.parser.context.pop_context()
                
                return BinaryTestExpression(left, operator, right)
        
        # Single value test
        return UnaryTestExpression('-n', left)
    
    def _parse_test_operand(self) -> str:
        """Parse a test operand, handling concatenated tokens for patterns."""
        if not self.parser.match_any(TokenGroups.WORD_LIKE):
            raise self.parser._error("Expected test operand")
        
        result_parts = []
        
        # Get first token
        token = self.parser.advance()
        
        # Add token value, preserving variable syntax
        if token.type == TokenType.VARIABLE:
            result_parts.append(f"${token.value}")
        else:
            result_parts.append(token.value)
        
        # Look ahead to see if we should concatenate more tokens
        # Only concatenate if they're immediately adjacent (no operators)
        while (self.parser.current < len(self.parser.tokens) and 
               self.parser.match_any(TokenGroups.WORD_LIKE)):
            
            next_token = self.parser.peek()
            
            # Stop if next token is a binary test operator
            if (next_token.type == TokenType.WORD and 
                self._is_binary_test_operator(next_token.value)):
                break
                
            # Stop at logical operators or closing brackets
            if next_token.type in (TokenType.AND_AND, TokenType.OR_OR, 
                                 TokenType.DOUBLE_RBRACKET, TokenType.RPAREN):
                break
            
            # Consume and add the token
            token = self.parser.advance()
            if token.type == TokenType.VARIABLE:
                result_parts.append(f"${token.value}")
            else:
                result_parts.append(token.value)
        
        return ''.join(result_parts)
    
    def _is_unary_test_operator(self, value: str) -> bool:
        """Check if a word is a unary test operator."""
        return value in {
            '-a', '-b', '-c', '-d', '-e', '-f', '-g', '-h', '-k', '-p',
            '-r', '-s', '-t', '-u', '-w', '-x', '-G', '-L', '-N', '-O',
            '-S', '-z', '-n', '-o', '-v'
        }
    
    def _is_binary_test_operator(self, value: str) -> bool:
        """Check if a word is a binary test operator."""
        return value in {
            '=', '==', '!=', '<', '>', '-eq', '-ne', '-lt', '-le', '-gt', '-ge',
            '-nt', '-ot', '-ef'
        }