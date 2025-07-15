"""Test parser handling of escaped dollar followed by parenthesis."""

import pytest
from psh.parser import Parser, ParseError
from psh.lexer import tokenize


class TestEscapedDollarSyntax:
    """Test that PSH correctly rejects \$( as a syntax error like bash does."""
    
    def test_escaped_dollar_paren_is_syntax_error(self):
        """Test that \$( produces a syntax error matching bash behavior."""
        # This is a syntax error in bash: echo \$(echo test)
        tokens = tokenize(r'echo \$(echo test)')
        parser = Parser(tokens)
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse()
        
        assert "syntax error near unexpected token '('" in str(exc_info.value)
    
    def test_escaped_dollar_alone_is_valid(self):
        """Test that \$ alone is valid."""
        tokens = tokenize(r'echo \$')
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None
    
    def test_normal_command_substitution_is_valid(self):
        """Test that normal command substitution works."""
        tokens = tokenize(r'echo $(echo test)')
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None
    
    def test_escaped_dollar_and_parens_is_valid(self):
        """Test that \$\(...\) is valid (all escaped)."""
        tokens = tokenize(r'echo \$\(echo test\)')
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None
    
    def test_escaped_dollar_in_quotes_is_valid(self):
        """Test that "\$(echo test)" is valid."""
        tokens = tokenize(r'echo "\$(echo test)"')
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None
    
    def test_multiple_escaped_dollars(self):
        """Test various multiple escape scenarios."""
        # \\$(echo test) should work - double backslash then command sub
        tokens = tokenize(r'echo \\$(echo test)')
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None
        
        # \\\$(echo test) should fail - escaped dollar then paren
        tokens = tokenize(r'echo \\\$(echo test)')
        parser = Parser(tokens)
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse()
        
        assert "syntax error near unexpected token '('" in str(exc_info.value)
    
    def test_escaped_dollar_at_end(self):
        """Test that escaped dollar at end of command works."""
        tokens = tokenize(r'\$')
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None
    
    def test_escaped_dollar_with_just_paren(self):
        """Test \$( with nothing after is also an error."""
        tokens = tokenize(r'\$(')
        parser = Parser(tokens)
        
        with pytest.raises(ParseError) as exc_info:
            parser.parse()
        
        assert "syntax error near unexpected token '('" in str(exc_info.value)