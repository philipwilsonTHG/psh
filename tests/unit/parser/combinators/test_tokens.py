"""Tests for token-level parsers."""

import pytest
from psh.token_types import Token, TokenType
from psh.parser.combinators.tokens import (
    TokenParsers,
    create_token_parsers,
    pipe_separator,
    semicolon_separator,
    newline_separator,
    statement_terminator,
    logical_and,
    logical_or,
    background_operator,
)


def make_token(token_type: TokenType, value: str, position: int = 0) -> Token:
    """Helper to create a token with minimal required fields."""
    return Token(type=token_type, value=value, position=position)


class TestTokenParsers:
    """Test the TokenParsers class."""
    
    def test_initialization(self):
        """Test that TokenParsers initializes all parsers."""
        parsers = TokenParsers()
        
        # Check basic tokens
        assert parsers.word is not None
        assert parsers.string is not None
        assert parsers.eof is not None
        
        # Check operators
        assert parsers.pipe is not None
        assert parsers.semicolon is not None
        assert parsers.newline is not None
        
        # Check keywords
        assert parsers.if_kw is not None
        assert parsers.while_kw is not None
        assert parsers.for_kw is not None
    
    def test_basic_tokens(self):
        """Test basic token parsers."""
        parsers = TokenParsers()
        
        # Test word token
        tokens = [make_token(TokenType.WORD, "hello")]
        result = parsers.word.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "hello"
        
        # Test string token
        tokens = [make_token(TokenType.STRING, "\"hello world\"")]
        result = parsers.string.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "\"hello world\""
    
    def test_separator_tokens(self):
        """Test separator token parsers."""
        parsers = TokenParsers()
        
        # Test semicolon
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        result = parsers.semicolon.parse(tokens, 0)
        assert result.success is True
        
        # Test newline
        tokens = [make_token(TokenType.NEWLINE, "\n")]
        result = parsers.newline.parse(tokens, 0)
        assert result.success is True
        
        # Test statement terminator (accepts both)
        tokens1 = [make_token(TokenType.SEMICOLON, ";")]
        result1 = parsers.statement_terminator.parse(tokens1, 0)
        assert result1.success is True
        
        tokens2 = [make_token(TokenType.NEWLINE, "\n")]
        result2 = parsers.statement_terminator.parse(tokens2, 0)
        assert result2.success is True
    
    def test_logical_operators(self):
        """Test logical operator parsers."""
        parsers = TokenParsers()
        
        # Test AND operator
        tokens = [make_token(TokenType.AND_AND, "&&")]
        result = parsers.and_if.parse(tokens, 0)
        assert result.success is True
        
        # Test OR operator  
        tokens = [make_token(TokenType.OR_OR, "||")]
        result = parsers.or_if.parse(tokens, 0)
        assert result.success is True
    
    def test_redirect_operators(self):
        """Test redirection operator parsers."""
        parsers = TokenParsers()
        
        # Test output redirect
        tokens = [make_token(TokenType.REDIRECT_OUT, ">")]
        result = parsers.redirect_out.parse(tokens, 0)
        assert result.success is True
        
        # Test input redirect
        tokens = [make_token(TokenType.REDIRECT_IN, "<")]
        result = parsers.redirect_in.parse(tokens, 0)
        assert result.success is True
        
        # Test append redirect
        tokens = [make_token(TokenType.REDIRECT_APPEND, ">>")]
        result = parsers.redirect_append.parse(tokens, 0)
        assert result.success is True
        
        # Test combined redirect operator
        tokens = [make_token(TokenType.REDIRECT_OUT, ">")]
        result = parsers.redirect_operator.parse(tokens, 0)
        assert result.success is True
    
    def test_delimiter_tokens(self):
        """Test delimiter token parsers."""
        parsers = TokenParsers()
        
        # Test parentheses
        tokens = [make_token(TokenType.LPAREN, "(")]
        result = parsers.lparen.parse(tokens, 0)
        assert result.success is True
        
        tokens = [make_token(TokenType.RPAREN, ")")]
        result = parsers.rparen.parse(tokens, 0)
        assert result.success is True
        
        # Test braces
        tokens = [make_token(TokenType.LBRACE, "{")]
        result = parsers.lbrace.parse(tokens, 0)
        assert result.success is True
        
        tokens = [make_token(TokenType.RBRACE, "}")]
        result = parsers.rbrace.parse(tokens, 0)
        assert result.success is True
    
    def test_keyword_parsers(self):
        """Test keyword parsers."""
        parsers = TokenParsers()
        
        # Test if keyword
        tokens = [make_token(TokenType.WORD, "if")]
        result = parsers.if_kw.parse(tokens, 0)
        assert result.success is True
        
        # Test while keyword
        tokens = [make_token(TokenType.WORD, "while")]
        result = parsers.while_kw.parse(tokens, 0)
        assert result.success is True
        
        # Test for keyword
        tokens = [make_token(TokenType.WORD, "for")]
        result = parsers.for_kw.parse(tokens, 0)
        assert result.success is True
    
    def test_expansion_tokens(self):
        """Test expansion token parsers."""
        parsers = TokenParsers()
        
        # Test variable expansion
        tokens = [make_token(TokenType.VARIABLE, "$VAR")]
        result = parsers.variable.parse(tokens, 0)
        assert result.success is True
        
        # Test command substitution
        tokens = [make_token(TokenType.COMMAND_SUB, "$(cmd)")]
        result = parsers.command_sub.parse(tokens, 0)
        assert result.success is True
        
        # Test combined expansion parser
        tokens = [make_token(TokenType.VARIABLE, "$VAR")]
        result = parsers.expansion.parse(tokens, 0)
        assert result.success is True
    
    def test_helper_methods(self):
        """Test helper/utility methods."""
        parsers = TokenParsers()
        
        # Test is_terminator
        term_token = make_token(TokenType.SEMICOLON, ";")
        assert parsers.is_terminator(term_token) is True
        
        word_token = make_token(TokenType.WORD, "hello")
        assert parsers.is_terminator(word_token) is False
        
        # Test is_keyword
        kw_token = make_token(TokenType.WORD, "if")
        assert parsers.is_keyword(kw_token) is True
        
        regular_token = make_token(TokenType.WORD, "hello")
        assert parsers.is_keyword(regular_token) is False
        
        # Test is_redirect_operator
        redirect_token = make_token(TokenType.REDIRECT_OUT, ">")
        assert parsers.is_redirect_operator(redirect_token) is True
        
        word_token = make_token(TokenType.WORD, "hello")
        assert parsers.is_redirect_operator(word_token) is False
        
        # Test is_expansion
        var_token = make_token(TokenType.VARIABLE, "$VAR")
        assert parsers.is_expansion(var_token) is True
        
        word_token = make_token(TokenType.WORD, "hello")
        assert parsers.is_expansion(word_token) is False


class TestFactoryMethods:
    """Test factory methods for creating token parsers."""
    
    def test_create_token_parsers(self):
        """Test create_token_parsers factory function."""
        parsers = create_token_parsers()
        assert isinstance(parsers, TokenParsers)
        assert parsers.word is not None
    
    def test_create_separator_parser(self):
        """Test separator parser factory method."""
        sep_parser = TokenParsers.create_separator_parser()
        
        # Should accept semicolon
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        result = sep_parser.parse(tokens, 0)
        assert result.success is True
        
        # Should accept newline
        tokens = [make_token(TokenType.NEWLINE, "\n")]
        result = sep_parser.parse(tokens, 0)
        assert result.success is True
    
    def test_create_logical_operator_parser(self):
        """Test logical operator parser factory method."""
        logic_parser = TokenParsers.create_logical_operator_parser()
        
        # Should accept &&
        tokens = [make_token(TokenType.AND_AND, "&&")]
        result = logic_parser.parse(tokens, 0)
        assert result.success is True
        
        # Should accept ||
        tokens = [make_token(TokenType.OR_OR, "||")]
        result = logic_parser.parse(tokens, 0)
        assert result.success is True
    
    def test_create_redirect_operator_parser(self):
        """Test redirect operator parser factory method."""
        redirect_parser = TokenParsers.create_redirect_operator_parser()
        
        # Should accept various redirect operators
        tokens = [make_token(TokenType.REDIRECT_OUT, ">")]
        result = redirect_parser.parse(tokens, 0)
        assert result.success is True
        
        tokens = [make_token(TokenType.REDIRECT_IN, "<")]
        result = redirect_parser.parse(tokens, 0)
        assert result.success is True
        
        tokens = [make_token(TokenType.REDIRECT_APPEND, ">>")]
        result = redirect_parser.parse(tokens, 0)
        assert result.success is True
    
    def test_create_expansion_parser(self):
        """Test expansion parser factory method."""
        exp_parser = TokenParsers.create_expansion_parser()
        
        # Should accept various expansion types
        tokens = [make_token(TokenType.VARIABLE, "$VAR")]
        result = exp_parser.parse(tokens, 0)
        assert result.success is True
        
        tokens = [make_token(TokenType.COMMAND_SUB, "$(cmd)")]
        result = exp_parser.parse(tokens, 0)
        assert result.success is True


class TestConvenienceFunctions:
    """Test convenience functions for common token parsers."""
    
    def test_pipe_separator(self):
        """Test pipe_separator function."""
        parser = pipe_separator()
        tokens = [make_token(TokenType.PIPE, "|")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_semicolon_separator(self):
        """Test semicolon_separator function."""
        parser = semicolon_separator()
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_newline_separator(self):
        """Test newline_separator function."""
        parser = newline_separator()
        tokens = [make_token(TokenType.NEWLINE, "\n")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_statement_terminator(self):
        """Test statement_terminator function."""
        parser = statement_terminator()
        
        # Accept semicolon
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        result = parser.parse(tokens, 0)
        assert result.success is True
        
        # Accept newline
        tokens = [make_token(TokenType.NEWLINE, "\n")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_logical_and(self):
        """Test logical_and function."""
        parser = logical_and()
        tokens = [make_token(TokenType.AND_AND, "&&")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_logical_or(self):
        """Test logical_or function."""
        parser = logical_or()
        tokens = [make_token(TokenType.OR_OR, "||")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_background_operator(self):
        """Test background_operator function."""
        parser = background_operator()
        tokens = [make_token(TokenType.AMPERSAND, "&")]
        result = parser.parse(tokens, 0)
        assert result.success is True