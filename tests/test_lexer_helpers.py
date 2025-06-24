#!/usr/bin/env python3
"""
Unit tests for StateMachineLexer helper methods.

These tests verify the internal helper methods work correctly in isolation.
"""

import pytest
from psh.lexer import StateMachineLexer
from psh.lexer import TokenPart
from psh.lexer_position import Position, LexerConfig
from psh.token_types import TokenType


class TestLexerHelpers:
    """Test helper methods in StateMachineLexer."""
    
    def test_validate_input_bounds(self):
        """Test input bounds validation."""
        lexer = StateMachineLexer("hello")
        assert lexer._validate_input_bounds() is True
        
        # Move to end
        lexer.position = 5
        assert lexer._validate_input_bounds() is False
    
    def test_validate_closing_character_success(self):
        """Test successful closing character validation."""
        lexer = StateMachineLexer("hello}")
        lexer.position = 5  # At the }
        
        result = lexer._validate_closing_character('}', "Missing closing brace")
        assert result is True
        assert lexer.position == 6  # Should have advanced
    
    def test_validate_closing_character_failure(self):
        """Test failed closing character validation."""
        lexer = StateMachineLexer("hello")
        lexer.position = 5  # At EOF
        
        # Configure for strict mode to get exception
        lexer.config.strict_mode = True
        
        with pytest.raises(Exception):  # Should raise LexerError
            lexer._validate_closing_character('}', "Missing closing brace")
    
    def test_create_token_simple(self):
        """Test simple token creation."""
        lexer = StateMachineLexer("hello")
        start_pos = Position(0, 1, 1)
        end_pos = Position(5, 1, 6)
        
        token = lexer._create_token(TokenType.WORD, "hello", start_pos, end_pos)
        
        assert token.type == TokenType.WORD
        assert token.value == "hello"
        assert token.position == 0
        assert token.end_position == 5
    
    def test_create_token_with_parts(self):
        """Test token creation with parts."""
        lexer = StateMachineLexer("hello")
        start_pos = Position(0, 1, 1)
        end_pos = Position(5, 1, 6)
        
        # Add some parts
        lexer.current_parts = [
            TokenPart("he", start_pos=start_pos, end_pos=Position(2, 1, 3)),
            TokenPart("llo", start_pos=Position(2, 1, 3), end_pos=end_pos)
        ]
        
        token = lexer._create_token(TokenType.WORD, "hello", start_pos, end_pos)
        
        # Should be a RichToken with parts
        assert hasattr(token, 'parts')
        assert len(token.parts) == 2
        assert token.parts[0].value == "he"
        assert token.parts[1].value == "llo"
        
        # Parts should be cleared after token creation
        assert len(lexer.current_parts) == 0
    
    def test_update_command_position_context(self):
        """Test command position context updates."""
        lexer = StateMachineLexer("test")
        
        # Test command-starting tokens
        lexer.command_position = False
        lexer._update_command_position_context(TokenType.SEMICOLON)
        assert lexer.command_position is True
        
        lexer._update_command_position_context(TokenType.PIPE)
        assert lexer.command_position is True
        
        # Test normal tokens
        lexer._update_command_position_context(TokenType.WORD)
        assert lexer.command_position is False
        
        # Test neutral tokens (redirections)
        lexer.command_position = True
        lexer._update_command_position_context(TokenType.REDIRECT_OUT)
        assert lexer.command_position is True  # Should remain unchanged
    
    def test_process_quoted_string_single_quotes(self):
        """Test unified quote processing for single quotes."""
        lexer = StateMachineLexer("'hello world'")
        lexer.position = 1  # Skip opening quote
        lexer.token_start_pos = Position(0, 1, 1)
        
        lexer._process_quoted_string("'", allow_expansions=False)
        
        assert len(lexer.tokens) == 1
        token = lexer.tokens[0]
        assert token.type == TokenType.STRING
        assert token.value == "hello world"
        assert token.quote_type == "'"
    
    def test_process_quoted_string_double_quotes(self):
        """Test unified quote processing for double quotes."""
        lexer = StateMachineLexer('"hello world"')
        lexer.position = 1  # Skip opening quote
        lexer.token_start_pos = Position(0, 1, 1)
        
        lexer._process_quoted_string('"', allow_expansions=True)
        
        assert len(lexer.tokens) == 1
        token = lexer.tokens[0]
        assert token.type == TokenType.STRING
        assert token.value == "hello world"
        assert token.quote_type == '"'
    
    def test_parse_simple_variable(self):
        """Test simple variable parsing."""
        lexer = StateMachineLexer("VAR")
        start_pos = Position(0, 1, 1)
        
        part = lexer._parse_simple_variable(start_pos, None)
        
        assert part.is_variable is True
        assert part.value == "VAR"
        assert part.quote_type is None
        assert part.start_pos == start_pos
    
    def test_parse_brace_variable_expansion(self):
        """Test brace variable expansion parsing."""
        lexer = StateMachineLexer("{VAR:-default}")
        start_pos = Position(0, 1, 1)
        
        part = lexer._parse_brace_variable_expansion(start_pos, None)
        
        assert part.is_variable is True
        assert part.value == "{VAR:-default}"
        assert part.quote_type is None
        assert part.start_pos == start_pos
    
    def test_parse_command_expansion(self):
        """Test command substitution parsing."""
        lexer = StateMachineLexer("(date)")
        start_pos = Position(0, 1, 1)
        
        part = lexer._parse_command_or_arithmetic_expansion(start_pos, None)
        
        assert part.is_expansion is True
        assert part.value == "$(date)"
        assert part.quote_type is None
        assert part.start_pos == start_pos
    
    def test_parse_arithmetic_expansion(self):
        """Test arithmetic expansion parsing."""
        lexer = StateMachineLexer("((1 + 2))")
        start_pos = Position(0, 1, 1)
        
        part = lexer._parse_command_or_arithmetic_expansion(start_pos, None)
        
        assert part.is_expansion is True
        assert part.value == "$((1 + 2))"
        assert part.quote_type is None
        assert part.start_pos == start_pos
    
    def test_read_literal_quoted_content(self):
        """Test literal quoted content reading."""
        lexer = StateMachineLexer("'hello world'")
        lexer.position = 1  # Skip opening quote
        lexer.token_start_pos = Position(0, 1, 1)
        
        parts = lexer._read_literal_quoted_content("'")
        
        assert len(parts) == 1
        part = parts[0]
        assert part.value == "hello world"
        assert part.quote_type == "'"
        assert part.is_variable is False
        assert part.is_expansion is False


class TestHelperMethodIntegration:
    """Test that helper methods work correctly together."""
    
    def test_variable_in_double_quotes(self):
        """Test variable expansion within double quotes."""
        lexer = StateMachineLexer('"Value: $USER"')
        tokens = lexer.tokenize()
        
        assert len(tokens) == 2  # STRING + EOF
        string_token = tokens[0]
        assert string_token.type == TokenType.STRING
        assert string_token.value == "Value: $USER"
        assert hasattr(string_token, 'parts')
        assert len(string_token.parts) == 2  # "Value: " + variable
    
    def test_complex_expansion_in_quotes(self):
        """Test complex expansion within quotes."""
        lexer = StateMachineLexer('"Result: $(expr 1 + 2)"')
        tokens = lexer.tokenize()
        
        assert len(tokens) == 2  # STRING + EOF
        string_token = tokens[0]
        assert string_token.type == TokenType.STRING
        assert string_token.value == "Result: $(expr 1 + 2)"
        assert hasattr(string_token, 'parts')
        assert len(string_token.parts) == 2  # "Result: " + expansion
    
    def test_mixed_quote_types(self):
        """Test different quote types are handled correctly."""
        lexer = StateMachineLexer("'literal' \"$VAR\"")
        tokens = lexer.tokenize()
        
        assert len(tokens) == 3  # STRING + STRING + EOF
        
        # First token: single-quoted literal
        literal_token = tokens[0]
        assert literal_token.value == "literal"
        assert literal_token.quote_type == "'"
        
        # Second token: double-quoted with variable
        var_token = tokens[1]
        assert var_token.value == "$VAR"
        assert var_token.quote_type == '"'