"""
Unit tests for basic tokenization functionality.

Tests the lexer in isolation without involving other components.
"""

import sys
from pathlib import Path

# Add PSH to path
PSH_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PSH_ROOT))

from psh.lexer import tokenize
from psh.token_types import TokenType
import pytest


class TestBasicTokenization:
    """Test basic token recognition."""
    
    def test_simple_command(self):
        """Test tokenization of simple commands."""
        tokens = list(tokenize("echo hello world"))
        
        assert len(tokens) == 4  # 3 words + EOF
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.WORD
        assert tokens[1].value == "hello"
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == "world"
        assert tokens[3].type == TokenType.EOF
        
    def test_single_quoted_string(self):
        """Test single-quoted string tokenization."""
        tokens = list(tokenize("echo 'hello world'"))
        
        assert len(tokens) == 3  # echo + quoted string + EOF
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "hello world"
        
    def test_double_quoted_string(self):
        """Test double-quoted string tokenization."""
        tokens = list(tokenize('echo "hello world"'))
        
        assert len(tokens) == 3
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "hello world"
        
    def test_pipe_operator(self):
        """Test pipe operator tokenization."""
        tokens = list(tokenize("echo hello | grep world"))
        
        assert len(tokens) == 6  # echo hello | grep world EOF
        assert tokens[2].type == TokenType.PIPE
        assert tokens[2].value == "|"
        
    def test_redirect_operators(self):
        """Test various redirection operators."""
        test_cases = [
            ("echo > file", TokenType.REDIRECT_OUT, ">"),
            ("echo >> file", TokenType.REDIRECT_APPEND, ">>"),
            ("cat < file", TokenType.REDIRECT_IN, "<"),
            ("cmd 2> errors", TokenType.REDIRECT_ERR, "2>"),
            # Note: PSH tokenizes 2>&1 as separate tokens: 2> & 1
        ]
        
        for command, expected_type, expected_value in test_cases:
            tokens = list(tokenize(command))
            # Find the redirect token
            redirect_token = next(t for t in tokens if t.type in (
                TokenType.REDIRECT_OUT, TokenType.REDIRECT_APPEND, 
                TokenType.REDIRECT_IN, TokenType.REDIRECT_ERR,
                TokenType.REDIRECT_DUP
            ))
            assert redirect_token.type == expected_type
            assert redirect_token.value == expected_value
            
    def test_command_separator(self):
        """Test command separator tokenization."""
        tokens = list(tokenize("echo hello; echo world"))
        
        separator = next(t for t in tokens if t.type == TokenType.SEMICOLON)
        assert separator.value == ";"
        
    def test_background_operator(self):
        """Test background operator tokenization."""
        tokens = list(tokenize("sleep 10 &"))
        
        assert tokens[-2].type == TokenType.AMPERSAND
        assert tokens[-2].value == "&"
        
    def test_logical_operators(self):
        """Test logical AND and OR operators."""
        # Test &&
        tokens = list(tokenize("true && echo success"))
        and_token = next(t for t in tokens if t.type == TokenType.AND_AND)
        assert and_token.value == "&&"
        
        # Test ||
        tokens = list(tokenize("false || echo failure"))
        or_token = next(t for t in tokens if t.type == TokenType.OR_OR)
        assert or_token.value == "||"
        
    def test_empty_input(self):
        """Test tokenization of empty input."""
        tokens = list(tokenize(""))
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF
        
    def test_whitespace_only(self):
        """Test tokenization of whitespace-only input."""
        tokens = list(tokenize("   \t\n  "))
        # PSH tokenizes newlines as separate tokens
        assert tokens[-1].type == TokenType.EOF
        # May have NEWLINE tokens from the \n
        
    def test_comment(self):
        """Test comment tokenization."""
        tokens = list(tokenize("echo hello # this is a comment"))
        
        # Comments should be stripped during tokenization
        assert len(tokens) == 3  # echo hello EOF
        assert all(t.value != "#" for t in tokens)
        
    def test_newline_handling(self):
        """Test newline tokenization."""
        tokens = list(tokenize("echo hello\necho world"))
        
        # Find newline token
        newline = next(t for t in tokens if t.type == TokenType.NEWLINE)
        assert newline.value == "\n"


class TestTokenPosition:
    """Test token position tracking."""
    
    def test_token_positions(self):
        """Test that tokens track their position correctly."""
        tokens = list(tokenize("echo hello | grep world"))
        
        # Check positions
        assert tokens[0].position == 0  # echo
        assert tokens[1].position == 5  # hello
        assert tokens[2].position == 11  # |
        assert tokens[3].position == 13  # grep
        assert tokens[4].position == 18  # world
        
    def test_multiline_positions(self):
        """Test position tracking across multiple lines."""
        tokens = list(tokenize("echo hello\necho world"))
        
        # Second line positions should continue from first
        echo2_token = tokens[3]  # Second echo after newline
        assert echo2_token.value == "echo"
        assert echo2_token.position == 11  # After "echo hello\n"


class TestEscapeSequences:
    """Test escape sequence handling in tokenization."""
    
    def test_backslash_escape(self):
        """Test backslash escaping."""
        tokens = list(tokenize(r"echo hello\ world"))
        
        # Escaped space should keep words together
        assert len(tokens) == 3  # echo + "hello\ world" + EOF
        # PSH preserves the escape in the token value
        assert tokens[1].value == "hello\\ world"
        
    def test_escape_special_chars(self):
        """Test escaping of special characters."""
        tokens = list(tokenize(r"echo \$ \| \> \&"))
        
        # PSH preserves escapes in token values
        assert tokens[1].value == "\\$"
        assert tokens[2].value == "\\|"
        assert tokens[3].value == "\\>"
        assert tokens[4].value == "\\&"


class TestComplexTokenization:
    """Test more complex tokenization scenarios."""
    
    def test_nested_quotes(self):
        """Test nested quote handling."""
        tokens = list(tokenize('''echo "hello 'world'" '''))
        
        assert len(tokens) == 3
        assert tokens[1].value == "hello 'world'"
        
    def test_command_substitution_tokens(self):
        """Test command substitution tokenization."""
        # $() form
        tokens = list(tokenize("echo $(date)"))
        assert any(t.type == TokenType.COMMAND_SUB for t in tokens)
        
        # Backtick form
        tokens = list(tokenize("echo `date`"))
        assert any(t.type == TokenType.COMMAND_SUB_BACKTICK for t in tokens)
        
    def test_variable_tokens(self):
        """Test variable-related tokenization."""
        tokens = list(tokenize("VAR=value echo $VAR ${VAR}"))
        
        # Should have assignment
        assert any(t.value == "VAR=value" for t in tokens)
        # Should have variable references - PSH tokenizes variables without $
        assert any(t.type == TokenType.VARIABLE and t.value == "VAR" for t in tokens)
        assert any(t.type == TokenType.VARIABLE and t.value == "{VAR}" for t in tokens)