"""Tests for CompositeTokenProcessor."""

import pytest
from psh.token_types import Token, TokenType
from psh.composite_processor import CompositeTokenProcessor, CompositeToken


class TestCompositeTokenProcessor:
    """Test cases for composite token processing."""
    
    def test_simple_composite(self):
        """Test basic composite of adjacent tokens."""
        tokens = [
            Token(TokenType.WORD, "file", 0, end_position=4),
            Token(TokenType.VARIABLE, "num", 4, end_position=8),
            Token(TokenType.WORD, ".txt", 8, end_position=12),
            Token(TokenType.EOF, "", 13)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 2  # Composite + EOF
        assert isinstance(result[0], CompositeToken)
        assert result[0].value == "file$num.txt"
        assert len(result[0].components) == 3
        assert result[0].position == 0
        assert result[0].end_position == 12
    
    def test_composite_with_quotes(self):
        """Test composite containing quoted strings."""
        tokens = [
            Token(TokenType.STRING, "hello", 0, end_position=7, quote_type='"'),
            Token(TokenType.WORD, "world", 7, end_position=12),
            Token(TokenType.EOF, "", 13)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 2
        assert isinstance(result[0], CompositeToken)
        assert result[0].value == "helloworld"
        assert result[0].quote_type == 'mixed'  # Has quoted component
    
    def test_composite_with_command_sub(self):
        """Test composite with command substitution."""
        tokens = [
            Token(TokenType.WORD, "log_", 0, end_position=4),
            Token(TokenType.COMMAND_SUB, "$(date +%Y%m%d)", 4, end_position=19),
            Token(TokenType.WORD, ".txt", 19, end_position=23),
            Token(TokenType.EOF, "", 24)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 2
        assert isinstance(result[0], CompositeToken)
        assert result[0].value == "log_$(date +%Y%m%d).txt"
    
    def test_composite_with_array_brackets(self):
        """Test composite with array access brackets."""
        tokens = [
            Token(TokenType.VARIABLE, "array", 0, end_position=6),
            Token(TokenType.LBRACKET, "[", 6, end_position=7),
            Token(TokenType.WORD, "0", 7, end_position=8),
            Token(TokenType.RBRACKET, "]", 8, end_position=9),
            Token(TokenType.EOF, "", 10)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 2
        assert isinstance(result[0], CompositeToken)
        assert result[0].value == "$array[0]"
    
    def test_non_adjacent_tokens(self):
        """Test that non-adjacent tokens don't form composites."""
        tokens = [
            Token(TokenType.WORD, "file", 0, end_position=4),
            Token(TokenType.WORD, "name", 5, end_position=9),  # Space between
            Token(TokenType.EOF, "", 10)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 3  # No composite formed
        assert result[0].type == TokenType.WORD
        assert result[1].type == TokenType.WORD
    
    def test_composite_terminated_by_operator(self):
        """Test composite terminated by operator."""
        tokens = [
            Token(TokenType.WORD, "file", 0, end_position=4),
            Token(TokenType.VARIABLE, "num", 4, end_position=8),
            Token(TokenType.PIPE, "|", 8, end_position=9),
            Token(TokenType.WORD, "grep", 10, end_position=14),
            Token(TokenType.EOF, "", 15)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 4  # Composite, PIPE, WORD, EOF
        assert isinstance(result[0], CompositeToken)
        assert result[0].value == "file$num"
        assert result[1].type == TokenType.PIPE
    
    def test_multiple_composites(self):
        """Test multiple composites in one token stream."""
        tokens = [
            Token(TokenType.WORD, "file", 0, end_position=4),
            Token(TokenType.VARIABLE, "a", 4, end_position=6),
            Token(TokenType.WORD, " ", 7, end_position=8),  # Space
            Token(TokenType.WORD, "file", 9, end_position=13),
            Token(TokenType.VARIABLE, "b", 13, end_position=15),
            Token(TokenType.EOF, "", 16)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        # Should have: composite1, space, composite2, EOF
        assert len(result) == 4
        assert isinstance(result[0], CompositeToken)
        assert result[0].value == "file$a"
        assert result[1].type == TokenType.WORD
        assert isinstance(result[2], CompositeToken)
        assert result[2].value == "file$b"
    
    def test_keyword_not_in_composite(self):
        """Test that keywords don't participate in composites."""
        tokens = [
            Token(TokenType.WORD, "if", 0, end_position=2),
            Token(TokenType.WORD, "test", 2, end_position=6),
            Token(TokenType.EOF, "", 7)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        # Keywords should not form composites
        assert len(result) == 3
        assert result[0].type == TokenType.WORD
        assert result[0].value == "if"
        assert result[1].type == TokenType.WORD
        assert result[1].value == "test"
    
    def test_single_token_not_composite(self):
        """Test that single tokens aren't wrapped in composite."""
        tokens = [
            Token(TokenType.WORD, "hello", 0, end_position=5),
            Token(TokenType.WORD, "world", 6, end_position=11),
            Token(TokenType.EOF, "", 12)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 3
        assert all(not isinstance(t, CompositeToken) for t in result[:2])
    
    def test_empty_token_list(self):
        """Test processing empty token list."""
        processor = CompositeTokenProcessor()
        result = processor.process([])
        assert result == []
    
    def test_all_expansion_types(self):
        """Test composite with all expansion types."""
        tokens = [
            Token(TokenType.WORD, "prefix_", 0, end_position=7),
            Token(TokenType.VARIABLE, "var", 7, end_position=11),
            Token(TokenType.COMMAND_SUB, "$(cmd)", 11, end_position=17),
            Token(TokenType.ARITH_EXPANSION, "$((1+1))", 17, end_position=25),
            Token(TokenType.PROCESS_SUB_IN, "<(cat)", 25, end_position=31),
            Token(TokenType.STRING, "_suffix", 31, end_position=38, quote_type='"'),
            Token(TokenType.EOF, "", 39)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 2
        assert isinstance(result[0], CompositeToken)
        assert len(result[0].components) == 6
        assert result[0].value == "prefix_$var$(cmd)$((1+1))<(cat)_suffix"
        assert result[0].quote_type == 'mixed'
    
    def test_redirect_terminates_composite(self):
        """Test that redirects terminate composites."""
        tokens = [
            Token(TokenType.WORD, "file", 0, end_position=4),
            Token(TokenType.VARIABLE, "num", 4, end_position=8),
            Token(TokenType.REDIRECT_OUT, ">", 8, end_position=9),
            Token(TokenType.WORD, "output", 10, end_position=16),
            Token(TokenType.EOF, "", 17)
        ]
        
        processor = CompositeTokenProcessor()
        result = processor.process(tokens)
        
        assert len(result) == 4  # Composite, REDIRECT_OUT, WORD, EOF
        assert isinstance(result[0], CompositeToken)
        assert result[0].value == "file$num"
        assert result[1].type == TokenType.REDIRECT_OUT
        assert result[2].type == TokenType.WORD