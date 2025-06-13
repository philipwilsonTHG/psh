"""Tests for TokenStream utility class."""

import pytest
from psh.token_types import Token, TokenType
from psh.token_stream import TokenStream


class TestTokenStream:
    """Test cases for TokenStream functionality."""
    
    def test_basic_operations(self):
        """Test basic peek, advance, and at_end operations."""
        tokens = [
            Token(TokenType.WORD, "echo", 0),
            Token(TokenType.WORD, "hello", 5),
            Token(TokenType.EOF, "", 10)
        ]
        stream = TokenStream(tokens)
        
        # Test peek
        assert stream.peek().value == "echo"
        assert stream.peek(1).value == "hello"
        assert stream.peek(2).type == TokenType.EOF
        assert stream.peek(3) is None
        
        # Test advance
        assert stream.advance().value == "echo"
        assert stream.peek().value == "hello"
        assert stream.advance().value == "hello"
        
        # Test at_end
        assert stream.at_end()  # EOF token
    
    def test_collect_until_balanced_parentheses(self):
        """Test collecting tokens with balanced parentheses."""
        tokens = [
            Token(TokenType.LPAREN, "(", 0),
            Token(TokenType.WORD, "echo", 1),
            Token(TokenType.LPAREN, "(", 6),
            Token(TokenType.WORD, "nested", 7),
            Token(TokenType.RPAREN, ")", 13),
            Token(TokenType.RPAREN, ")", 14),
            Token(TokenType.EOF, "", 15)
        ]
        stream = TokenStream(tokens, pos=1)  # Start after first LPAREN
        
        collected = stream.collect_until_balanced(
            TokenType.LPAREN, TokenType.RPAREN
        )
        
        assert len(collected) == 4
        assert collected[0].value == "echo"
        assert collected[1].value == "("
        assert collected[2].value == "nested"
        assert collected[3].value == ")"
        # Stream should be positioned after the closing RPAREN
        assert stream.peek().type == TokenType.EOF
    
    def test_collect_until_balanced_with_quotes(self):
        """Test respecting quotes when collecting balanced tokens."""
        tokens = [
            Token(TokenType.LBRACKET, "[", 0),
            Token(TokenType.WORD, "key", 1),
            Token(TokenType.STRING, "]quoted", 4, quote_type='"'),
            Token(TokenType.RBRACKET, "]", 12),
            Token(TokenType.EOF, "", 13)
        ]
        stream = TokenStream(tokens, pos=1)  # Start after LBRACKET
        
        # With quote respect
        collected = stream.collect_until_balanced(
            TokenType.LBRACKET, TokenType.RBRACKET, respect_quotes=True
        )
        assert len(collected) == 2
        assert collected[0].value == "key"
        assert collected[1].value == "]quoted"
    
    def test_collect_until_stop_types(self):
        """Test collecting until stop token types."""
        tokens = [
            Token(TokenType.WORD, "echo", 0),
            Token(TokenType.WORD, "hello", 5),
            Token(TokenType.SEMICOLON, ";", 10),
            Token(TokenType.WORD, "ls", 11),
            Token(TokenType.EOF, "", 13)
        ]
        stream = TokenStream(tokens)
        
        # Collect until semicolon
        collected = stream.collect_until({TokenType.SEMICOLON, TokenType.NEWLINE})
        assert len(collected) == 2
        assert collected[0].value == "echo"
        assert collected[1].value == "hello"
        assert stream.peek().type == TokenType.SEMICOLON
        
        # Include stop token
        stream.pos = 0  # Reset
        collected = stream.collect_until(
            {TokenType.SEMICOLON}, include_stop=True
        )
        assert len(collected) == 3
        assert collected[2].type == TokenType.SEMICOLON
    
    def test_peek_composite_sequence(self):
        """Test detection of adjacent tokens forming composites."""
        # Test composite detection
        tokens = [
            Token(TokenType.WORD, "file", 0, end_position=4),
            Token(TokenType.STRING, "name", 4, end_position=8),
            Token(TokenType.WORD, ".txt", 8, end_position=12),
            Token(TokenType.WORD, "other", 13, end_position=18),  # Not adjacent
            Token(TokenType.EOF, "", 19)
        ]
        stream = TokenStream(tokens)
        
        # Should detect 3-token composite
        composite = stream.peek_composite_sequence()
        assert composite is not None
        assert len(composite) == 3
        assert composite[0].value == "file"
        assert composite[1].value == "name"
        assert composite[2].value == ".txt"
        
        # Move to non-composite position
        stream.pos = 3
        composite = stream.peek_composite_sequence()
        assert composite is None  # "other" is not adjacent to anything
    
    def test_peek_composite_with_variables(self):
        """Test composite detection with variables and expansions."""
        tokens = [
            Token(TokenType.VARIABLE, "prefix", 0, end_position=7),
            Token(TokenType.WORD, "_", 7, end_position=8),
            Token(TokenType.COMMAND_SUB, "$(date)", 8, end_position=15),
            Token(TokenType.STRING, ".log", 15, end_position=19, quote_type='"'),
            Token(TokenType.EOF, "", 20)
        ]
        stream = TokenStream(tokens)
        
        composite = stream.peek_composite_sequence()
        assert composite is not None
        assert len(composite) == 4
        assert composite[0].type == TokenType.VARIABLE
        assert composite[1].value == "_"
        assert composite[2].type == TokenType.COMMAND_SUB
        assert composite[3].value == ".log"
    
    def test_save_restore_position(self):
        """Test position save and restore."""
        tokens = [
            Token(TokenType.WORD, "a", 0),
            Token(TokenType.WORD, "b", 1),
            Token(TokenType.WORD, "c", 2),
            Token(TokenType.EOF, "", 3)
        ]
        stream = TokenStream(tokens)
        
        # Advance and save
        stream.advance()
        pos = stream.save_position()
        assert stream.peek().value == "b"
        
        # Advance more
        stream.advance()
        assert stream.peek().value == "c"
        
        # Restore
        stream.restore_position(pos)
        assert stream.peek().value == "b"
    
    def test_remaining_tokens(self):
        """Test getting remaining tokens."""
        tokens = [
            Token(TokenType.WORD, "a", 0),
            Token(TokenType.WORD, "b", 1),
            Token(TokenType.WORD, "c", 2),
            Token(TokenType.EOF, "", 3)
        ]
        stream = TokenStream(tokens)
        
        stream.advance()
        remaining = stream.remaining_tokens()
        assert len(remaining) == 3
        assert remaining[0].value == "b"
        assert remaining[2].type == TokenType.EOF
    
    def test_collect_with_include_delimiters(self):
        """Test including delimiters in collected tokens."""
        tokens = [
            Token(TokenType.LPAREN, "(", 0),
            Token(TokenType.WORD, "content", 1),
            Token(TokenType.RPAREN, ")", 8),
            Token(TokenType.EOF, "", 9)
        ]
        stream = TokenStream(tokens, pos=1)
        
        # Without include_delimiters
        collected = stream.collect_until_balanced(
            TokenType.LPAREN, TokenType.RPAREN, include_delimiters=False
        )
        assert len(collected) == 1
        assert collected[0].value == "content"
        
        # With include_delimiters
        stream.pos = 1  # Reset
        collected = stream.collect_until_balanced(
            TokenType.LPAREN, TokenType.RPAREN, include_delimiters=True
        )
        assert len(collected) == 2
        assert collected[0].value == "content"
        assert collected[1].value == ")"
    
    def test_empty_balanced_collection(self):
        """Test collecting when immediately hitting close delimiter."""
        tokens = [
            Token(TokenType.LBRACKET, "[", 0),
            Token(TokenType.RBRACKET, "]", 1),
            Token(TokenType.EOF, "", 2)
        ]
        stream = TokenStream(tokens, pos=1)  # After LBRACKET
        
        collected = stream.collect_until_balanced(
            TokenType.LBRACKET, TokenType.RBRACKET
        )
        assert len(collected) == 0
        assert stream.peek().type == TokenType.EOF