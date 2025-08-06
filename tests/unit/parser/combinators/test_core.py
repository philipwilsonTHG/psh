"""Tests for core parser combinator framework."""

import pytest
from dataclasses import dataclass
from psh.token_types import Token, TokenType
from psh.parser.combinators.core import (
    ParseResult,
    Parser,
    ForwardParser,
    token,
    many,
    many1,
    optional,
    sequence,
    separated_by,
    lazy,
    between,
    skip,
    fail_with,
    try_parse,
    keyword,
    literal,
    with_error_context,
)


def make_token(token_type: TokenType, value: str, position: int = 0) -> Token:
    """Helper to create a token with minimal required fields."""
    return Token(type=token_type, value=value, position=position)


class TestParseResult:
    """Test the ParseResult dataclass."""
    
    def test_success_result(self):
        """Test creating a successful parse result."""
        result = ParseResult(success=True, value="test", position=5)
        assert result.success is True
        assert result.value == "test"
        assert result.position == 5
        assert result.error is None
    
    def test_failure_result(self):
        """Test creating a failed parse result."""
        result = ParseResult(success=False, error="Expected token", position=2)
        assert result.success is False
        assert result.value is None
        assert result.position == 2
        assert result.error == "Expected token"


class TestParser:
    """Test the Parser class methods."""
    
    def test_parse_function(self):
        """Test basic parser execution."""
        def parse_test(tokens, pos):
            return ParseResult(success=True, value="test", position=pos + 1)
        
        parser = Parser(parse_test)
        result = parser.parse([], 0)
        assert result.success is True
        assert result.value == "test"
        assert result.position == 1
    
    def test_map(self):
        """Test transforming parser results."""
        def parse_number(tokens, pos):
            return ParseResult(success=True, value=42, position=pos + 1)
        
        parser = Parser(parse_number).map(lambda x: x * 2)
        result = parser.parse([], 0)
        assert result.value == 84
    
    def test_map_failure(self):
        """Test that map preserves failures."""
        def parse_fail(tokens, pos):
            return ParseResult(success=False, error="Failed", position=pos)
        
        parser = Parser(parse_fail).map(lambda x: x * 2)
        result = parser.parse([], 0)
        assert result.success is False
        assert result.error == "Failed"
    
    def test_then(self):
        """Test sequencing parsers."""
        def parse_a(tokens, pos):
            return ParseResult(success=True, value="a", position=pos + 1)
        
        def parse_b(tokens, pos):
            return ParseResult(success=True, value="b", position=pos + 1)
        
        parser = Parser(parse_a).then(Parser(parse_b))
        result = parser.parse([], 0)
        assert result.success is True
        assert result.value == ("a", "b")
        assert result.position == 2
    
    def test_then_first_fails(self):
        """Test sequencing when first parser fails."""
        def parse_fail(tokens, pos):
            return ParseResult(success=False, error="Failed", position=pos)
        
        def parse_ok(tokens, pos):
            return ParseResult(success=True, value="ok", position=pos + 1)
        
        parser = Parser(parse_fail).then(Parser(parse_ok))
        result = parser.parse([], 0)
        assert result.success is False
        assert result.error == "Failed"
    
    def test_or_else(self):
        """Test alternative parsing."""
        def parse_fail(tokens, pos):
            return ParseResult(success=False, error="Failed", position=pos)
        
        def parse_ok(tokens, pos):
            return ParseResult(success=True, value="ok", position=pos + 1)
        
        parser = Parser(parse_fail).or_else(Parser(parse_ok))
        result = parser.parse([], 0)
        assert result.success is True
        assert result.value == "ok"
    
    def test_or_else_first_succeeds(self):
        """Test that or_else doesn't try alternative if first succeeds."""
        def parse_first(tokens, pos):
            return ParseResult(success=True, value="first", position=pos + 1)
        
        def parse_second(tokens, pos):
            return ParseResult(success=True, value="second", position=pos + 1)
        
        parser = Parser(parse_first).or_else(Parser(parse_second))
        result = parser.parse([], 0)
        assert result.value == "first"


class TestBasicCombinators:
    """Test basic combinator functions."""
    
    def test_token(self):
        """Test token parser."""
        tokens = [make_token(TokenType.WORD, "hello")]
        parser = token("WORD")
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "hello"
        assert result.position == 1
    
    def test_token_wrong_type(self):
        """Test token parser with wrong type."""
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        parser = token("WORD")
        result = parser.parse(tokens, 0)
        assert result.success is False
        assert "Expected WORD, got SEMICOLON" in result.error
    
    def test_token_at_end(self):
        """Test token parser at end of input."""
        parser = token("WORD")
        result = parser.parse([], 0)
        assert result.success is False
        assert "reached end of input" in result.error
    
    def test_many_empty(self):
        """Test many with no matches."""
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        parser = many(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value == []
        assert result.position == 0
    
    def test_many_multiple(self):
        """Test many with multiple matches."""
        tokens = [
            make_token(TokenType.WORD, "a"),
            make_token(TokenType.WORD, "b"),
            make_token(TokenType.SEMICOLON, ";")
        ]
        parser = many(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert len(result.value) == 2
        assert result.value[0].value == "a"
        assert result.value[1].value == "b"
        assert result.position == 2
    
    def test_many1_success(self):
        """Test many1 with at least one match."""
        tokens = [make_token(TokenType.WORD, "test")]
        parser = many1(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert len(result.value) == 1
        assert result.value[0].value == "test"
    
    def test_many1_failure(self):
        """Test many1 with no matches."""
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        parser = many1(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is False
    
    def test_optional_present(self):
        """Test optional when value is present."""
        tokens = [make_token(TokenType.WORD, "test")]
        parser = optional(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "test"
        assert result.position == 1
    
    def test_optional_absent(self):
        """Test optional when value is absent."""
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        parser = optional(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value is None
        assert result.position == 0
    
    def test_sequence(self):
        """Test sequence combinator."""
        tokens = [
            make_token(TokenType.WORD, "echo"),
            make_token(TokenType.WORD, "hello"),
            make_token(TokenType.SEMICOLON, ";")
        ]
        parser = sequence(token("WORD"), token("WORD"), token("SEMICOLON"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert len(result.value) == 3
        assert result.value[0].value == "echo"
        assert result.value[1].value == "hello"
        assert result.value[2].value == ";"
        assert result.position == 3
    
    def test_sequence_failure(self):
        """Test sequence when one parser fails."""
        tokens = [
            make_token(TokenType.WORD, "echo"),
            make_token(TokenType.SEMICOLON, ";")
        ]
        parser = sequence(token("WORD"), token("WORD"), token("SEMICOLON"))
        result = parser.parse(tokens, 0)
        assert result.success is False
    
    def test_separated_by(self):
        """Test separated_by combinator."""
        tokens = [
            make_token(TokenType.WORD, "a"),
            make_token(TokenType.PIPE, "|"),
            make_token(TokenType.WORD, "b"),
            make_token(TokenType.PIPE, "|"),
            make_token(TokenType.WORD, "c"),
            make_token(TokenType.SEMICOLON, ";")
        ]
        parser = separated_by(token("WORD"), token("PIPE"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert len(result.value) == 3
        assert result.value[0].value == "a"
        assert result.value[1].value == "b"
        assert result.value[2].value == "c"
        assert result.position == 5
    
    def test_separated_by_single(self):
        """Test separated_by with single item."""
        tokens = [make_token(TokenType.WORD, "test"), make_token(TokenType.SEMICOLON, ";")]
        parser = separated_by(token("WORD"), token("PIPE"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert len(result.value) == 1
        assert result.value[0].value == "test"
    
    def test_separated_by_failure(self):
        """Test separated_by with no items."""
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        parser = separated_by(token("WORD"), token("PIPE"))
        result = parser.parse(tokens, 0)
        assert result.success is False


class TestEnhancedCombinators:
    """Test enhanced combinator functions."""
    
    def test_lazy(self):
        """Test lazy evaluation."""
        # Simulate recursive grammar
        def create_parser():
            return token("WORD")
        
        parser = lazy(create_parser)
        tokens = [make_token(TokenType.WORD, "test")]
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "test"
    
    def test_between(self):
        """Test between combinator."""
        tokens = [
            make_token(TokenType.LPAREN, "("),
            make_token(TokenType.WORD, "content"),
            make_token(TokenType.RPAREN, ")")
        ]
        parser = between(token("LPAREN"), token("RPAREN"), token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "content"
        assert result.position == 3
    
    def test_between_missing_close(self):
        """Test between with missing closing delimiter."""
        tokens = [
            make_token(TokenType.LPAREN, "("),
            make_token(TokenType.WORD, "content")
        ]
        parser = between(token("LPAREN"), token("RPAREN"), token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is False
        assert "closing delimiter" in result.error
    
    def test_skip(self):
        """Test skip combinator."""
        tokens = [make_token(TokenType.WORD, "test")]
        parser = skip(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value is None
        assert result.position == 1
    
    def test_fail_with(self):
        """Test fail_with combinator."""
        parser = fail_with("Custom error message")
        result = parser.parse([], 0)
        assert result.success is False
        assert result.error == "Custom error message"
    
    def test_try_parse_success(self):
        """Test try_parse with successful parse."""
        tokens = [make_token(TokenType.WORD, "test")]
        parser = try_parse(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "test"
        assert result.position == 1
    
    def test_try_parse_failure(self):
        """Test try_parse with failed parse (backtracking)."""
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        parser = try_parse(token("WORD"))
        result = parser.parse(tokens, 0)
        assert result.success is True  # Still succeeds
        assert result.value is None  # But with None value
        assert result.position == 0  # And original position (backtracked)
    
    def test_keyword(self):
        """Test keyword parser."""
        tokens = [make_token(TokenType.WORD, "if")]
        parser = keyword("if")
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "if"
    
    def test_keyword_uppercase_token(self):
        """Test keyword with uppercase token type."""
        tokens = [make_token(TokenType.IF, "if")]
        parser = keyword("if")
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "if"
    
    def test_keyword_wrong(self):
        """Test keyword with wrong value."""
        tokens = [make_token(TokenType.WORD, "else")]
        parser = keyword("if")
        result = parser.parse(tokens, 0)
        assert result.success is False
        assert "Expected keyword 'if'" in result.error
    
    def test_literal(self):
        """Test literal parser."""
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        parser = literal(";")
        result = parser.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == ";"
    
    def test_literal_wrong(self):
        """Test literal with wrong value."""
        tokens = [make_token(TokenType.PIPE, "|")]
        parser = literal(";")
        result = parser.parse(tokens, 0)
        assert result.success is False
        assert "Expected ';'" in result.error
    
    def test_with_error_context(self):
        """Test error context wrapper."""
        parser = with_error_context(token("WORD"), "parsing command")
        tokens = [make_token(TokenType.SEMICOLON, ";")]
        result = parser.parse(tokens, 0)
        assert result.success is False
        assert result.error.startswith("parsing command:")


class TestForwardParser:
    """Test the ForwardParser class."""
    
    def test_forward_definition(self):
        """Test defining a forward parser."""
        forward = ForwardParser()
        forward.define(token("WORD"))
        
        tokens = [make_token(TokenType.WORD, "test")]
        result = forward.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "test"
    
    def test_forward_undefined(self):
        """Test using forward parser before definition."""
        forward = ForwardParser()
        
        with pytest.raises(RuntimeError, match="ForwardParser used before being defined"):
            forward.parse([], 0)
    
    def test_forward_recursive(self):
        """Test forward parser for recursive grammar."""
        # Simple recursive structure: item = word | "(" item ")"
        item_parser = ForwardParser()
        
        word_parser = token("WORD")
        paren_parser = between(
            token("LPAREN"),
            token("RPAREN"),
            item_parser
        )
        
        item_parser.define(word_parser.or_else(paren_parser))
        
        # Test simple case
        tokens1 = [make_token(TokenType.WORD, "test")]
        result1 = item_parser.parse(tokens1, 0)
        assert result1.success is True
        assert result1.value.value == "test"
        
        # Test nested case
        tokens2 = [
            make_token(TokenType.LPAREN, "("),
            make_token(TokenType.WORD, "nested"),
            make_token(TokenType.RPAREN, ")")
        ]
        result2 = item_parser.parse(tokens2, 0)
        assert result2.success is True
        assert result2.value.value == "nested"