"""Tests for lexer pure helper functions."""

import pytest
from psh.lexer import pure_helpers
from psh.lexer.constants import OPERATORS_BY_LENGTH, SPECIAL_VARIABLES
from psh.token_types import TokenType


class TestReadUntilChar:
    """Test the read_until_char pure function."""
    
    def test_basic_reading(self):
        """Test basic character reading."""
        content, pos = pure_helpers.read_until_char("hello world", 0, " ")
        assert content == "hello"
        assert pos == 5
    
    def test_target_not_found(self):
        """Test when target character is not found."""
        content, pos = pure_helpers.read_until_char("hello", 0, "x")
        assert content == "hello"
        assert pos == 5
    
    def test_with_escapes(self):
        """Test reading with escape sequences."""
        content, pos = pure_helpers.read_until_char("hello\\\"world", 0, '"', escape=True)
        assert content == "hello\"world"
        assert pos == 12  # No unescaped quote found
        
        content, pos = pure_helpers.read_until_char("hello\\\"world\"end", 0, '"', escape=True)
        assert content == "hello\"world"
        assert pos == 12  # Should stop at the unescaped quote
    
    def test_empty_input(self):
        """Test with empty input."""
        content, pos = pure_helpers.read_until_char("", 0, "x")
        assert content == ""
        assert pos == 0
    
    def test_start_position(self):
        """Test with different start positions."""
        content, pos = pure_helpers.read_until_char("hello world", 6, "d")
        assert content == "worl"
        assert pos == 10


class TestFindClosingDelimiter:
    """Test the find_closing_delimiter pure function."""
    
    def test_simple_parentheses(self):
        """Test simple parentheses matching."""
        pos, found = pure_helpers.find_closing_delimiter("(hello)", 1, "(", ")")
        assert found is True
        assert pos == 7
    
    def test_nested_parentheses(self):
        """Test nested parentheses."""
        pos, found = pure_helpers.find_closing_delimiter("(hello (world))", 1, "(", ")")
        assert found is True
        assert pos == 15
    
    def test_unclosed_delimiter(self):
        """Test unclosed delimiter."""
        pos, found = pure_helpers.find_closing_delimiter("(hello", 1, "(", ")")
        assert found is False
        assert pos == 6
    
    def test_with_quotes(self):
        """Test delimiter matching with quotes."""
        pos, found = pure_helpers.find_closing_delimiter('(echo "hello)")', 1, "(", ")")
        assert found is True
        assert pos == 15  # Should ignore ) inside quotes
    
    def test_with_escapes(self):
        """Test with escape sequences."""
        pos, found = pure_helpers.find_closing_delimiter("(echo \\))", 1, "(", ")", track_escapes=True)
        assert found is True
        assert pos == 9  # Should ignore escaped )
    
    def test_multi_char_delimiters(self):
        """Test with multi-character delimiters."""
        pos, found = pure_helpers.find_closing_delimiter("$((2 + 3))", 3, "(", "))", track_quotes=False)
        assert found is True
        assert pos == 10


class TestBalancedParentheses:
    """Test balanced parentheses functions."""
    
    def test_simple_balanced(self):
        """Test simple balanced parentheses."""
        pos, found = pure_helpers.find_balanced_parentheses("echo hello)", 0)
        assert found is True
        assert pos == 11
    
    def test_nested_balanced(self):
        """Test nested balanced parentheses."""
        pos, found = pure_helpers.find_balanced_parentheses("echo (nested) command)", 0)
        assert found is True
        assert pos == 22
    
    def test_double_parentheses(self):
        """Test double parentheses for arithmetic."""
        pos, found = pure_helpers.find_balanced_double_parentheses("2 + (3 * 4)))", 0)
        assert found is True
        assert pos == 13  # Should find )) at positions 11-12, so end at 13


class TestHandleEscapeSequence:
    """Test escape sequence handling."""
    
    def test_outside_quotes(self):
        """Test escape sequences outside quotes."""
        escaped, pos = pure_helpers.handle_escape_sequence("\\n", 0, None)
        assert escaped == "n"
        assert pos == 2
        
        escaped, pos = pure_helpers.handle_escape_sequence("\\$", 0, None)
        assert escaped == "\x00$"  # Special marker for escaped $
        assert pos == 2
    
    def test_in_double_quotes(self):
        """Test escape sequences in double quotes."""
        # In bash, \n is NOT converted in double quotes - it stays literal
        escaped, pos = pure_helpers.handle_escape_sequence("\\n", 0, '"')
        assert escaped == "\\n"  # Should stay literal in double quotes
        assert pos == 2
        
        escaped, pos = pure_helpers.handle_escape_sequence('\\"', 0, '"')
        assert escaped == '"'
        assert pos == 2
        
        escaped, pos = pure_helpers.handle_escape_sequence("\\$", 0, '"')
        assert escaped == "\\$"  # Should preserve backslash
        assert pos == 2
    
    def test_in_single_quotes(self):
        """Test escape sequences in single quotes."""
        escaped, pos = pure_helpers.handle_escape_sequence("\\n", 0, "'")
        assert escaped == "\\n"  # Should preserve literal backslash
        assert pos == 2
    
    def test_line_continuation(self):
        """Test line continuation with escaped newline."""
        escaped, pos = pure_helpers.handle_escape_sequence("\\\n", 0, None)
        assert escaped == ""  # Should be removed
        assert pos == 2
        
        escaped, pos = pure_helpers.handle_escape_sequence("\\\n", 0, '"')
        assert escaped == ""  # Should be removed in double quotes too
        assert pos == 2
    
    def test_end_of_input(self):
        """Test escape at end of input."""
        escaped, pos = pure_helpers.handle_escape_sequence("\\", 0, None)
        assert escaped == "\\"
        assert pos == 1


class TestFindWordBoundary:
    """Test word boundary detection."""
    
    def test_basic_word(self):
        """Test basic word boundary."""
        terminators = {' ', '\t', '\n', ';', '|'}
        pos = pure_helpers.find_word_boundary("hello world", 0, terminators)
        assert pos == 5
    
    def test_with_escapes(self):
        """Test word boundary with escapes."""
        terminators = {' '}
        pos = pure_helpers.find_word_boundary("hello\\ world", 0, terminators, handle_escapes=True)
        assert pos == 12  # Should skip escaped space
        
        pos = pure_helpers.find_word_boundary("hello\\ world", 0, terminators, handle_escapes=False)
        assert pos == 6  # Should stop at space after backslash
    
    def test_no_boundary(self):
        """Test when no boundary is found."""
        terminators = {'x'}
        pos = pure_helpers.find_word_boundary("hello", 0, terminators)
        assert pos == 5  # End of string


class TestExtractVariableName:
    """Test variable name extraction."""
    
    def test_simple_variable(self):
        """Test simple variable names."""
        name, pos = pure_helpers.extract_variable_name("var", 0, SPECIAL_VARIABLES)
        assert name == "var"
        assert pos == 3
    
    def test_special_variables(self):
        """Test special single-character variables."""
        name, pos = pure_helpers.extract_variable_name("$", 0, SPECIAL_VARIABLES)
        assert name == "$"
        assert pos == 1
        
        name, pos = pure_helpers.extract_variable_name("?", 0, SPECIAL_VARIABLES)
        assert name == "?"
        assert pos == 1
    
    def test_with_numbers(self):
        """Test variable names with numbers."""
        name, pos = pure_helpers.extract_variable_name("var123", 0, SPECIAL_VARIABLES)
        assert name == "var123"
        assert pos == 6
    
    def test_invalid_start(self):
        """Test invalid variable name start."""
        # Use a character that's not in SPECIAL_VARIABLES
        name, pos = pure_helpers.extract_variable_name("@#$", 1, SPECIAL_VARIABLES)  # Start at '#' 
        assert name == "#"  # '#' is a special variable
        assert pos == 2
    
    def test_underscore_start(self):
        """Test variable starting with underscore."""
        name, pos = pure_helpers.extract_variable_name("_var", 0, SPECIAL_VARIABLES)
        assert name == "_var"
        assert pos == 4


class TestIsCommentStart:
    """Test comment detection."""
    
    def test_start_of_line(self):
        """Test comment at start of line."""
        assert pure_helpers.is_comment_start("#comment", 0) is True
    
    def test_after_whitespace(self):
        """Test comment after whitespace."""
        assert pure_helpers.is_comment_start("echo #comment", 5) is True
    
    def test_after_operator(self):
        """Test comment after operator."""
        assert pure_helpers.is_comment_start("cmd; #comment", 5) is True
    
    def test_not_comment(self):
        """Test # that's not a comment start."""
        assert pure_helpers.is_comment_start("var#not", 3) is False
    
    def test_wrong_character(self):
        """Test non-# character."""
        assert pure_helpers.is_comment_start("hello", 0) is False


class TestScanWhitespace:
    """Test whitespace scanning."""
    
    def test_basic_whitespace(self):
        """Test basic ASCII whitespace."""
        pos = pure_helpers.scan_whitespace("   hello", 0, unicode_aware=False)
        assert pos == 3
    
    def test_mixed_whitespace(self):
        """Test mixed whitespace characters."""
        pos = pure_helpers.scan_whitespace(" \t\n hello", 0, unicode_aware=False)
        assert pos == 4
    
    def test_no_whitespace(self):
        """Test when no whitespace is present."""
        pos = pure_helpers.scan_whitespace("hello", 0, unicode_aware=False)
        assert pos == 0
    
    def test_all_whitespace(self):
        """Test when entire string is whitespace."""
        pos = pure_helpers.scan_whitespace("   ", 0, unicode_aware=False)
        assert pos == 3


class TestExtractQuotedContent:
    """Test quoted content extraction."""
    
    def test_double_quotes(self):
        """Test double-quoted content."""
        content, pos, found = pure_helpers.extract_quoted_content('hello world"', 0, '"')
        assert content == "hello world"
        assert pos == 12
        assert found is True
    
    def test_single_quotes(self):
        """Test single-quoted content."""
        content, pos, found = pure_helpers.extract_quoted_content("hello'", 0, "'", allow_escapes=False)
        assert content == "hello"
        assert pos == 6
        assert found is True
    
    def test_with_escapes(self):
        """Test quoted content with escape sequences."""
        content, pos, found = pure_helpers.extract_quoted_content('hello\\"world"', 0, '"')
        assert content == 'hello"world'
        assert pos == 13
        assert found is True
    
    def test_unclosed_quote(self):
        """Test unclosed quoted string."""
        content, pos, found = pure_helpers.extract_quoted_content("hello", 0, '"')
        assert content == "hello"
        assert pos == 5
        assert found is False
    
    def test_empty_quotes(self):
        """Test empty quoted string."""
        content, pos, found = pure_helpers.extract_quoted_content('"', 0, '"')
        assert content == ""
        assert pos == 1
        assert found is True


class TestFindOperatorMatch:
    """Test operator matching."""
    
    def test_single_char_operator(self):
        """Test single character operators."""
        result = pure_helpers.find_operator_match("|", 0, OPERATORS_BY_LENGTH)
        assert result is not None
        op, token_type, pos = result
        assert op == "|"
        assert token_type == TokenType.PIPE
        assert pos == 1
    
    def test_multi_char_operator(self):
        """Test multi-character operators."""
        result = pure_helpers.find_operator_match("&&", 0, OPERATORS_BY_LENGTH)
        assert result is not None
        op, token_type, pos = result
        assert op == "&&"
        assert token_type == TokenType.AND_AND
        assert pos == 2
    
    def test_longest_match(self):
        """Test that longest operator is matched."""
        # << should match as HEREDOC, not two < operators
        result = pure_helpers.find_operator_match("<<", 0, OPERATORS_BY_LENGTH)
        assert result is not None
        op, token_type, pos = result
        assert op == "<<"
        assert pos == 2
    
    def test_no_match(self):
        """Test when no operator matches."""
        result = pure_helpers.find_operator_match("abc", 0, OPERATORS_BY_LENGTH)
        assert result is None


class TestValidateBraceExpansion:
    """Test brace expansion validation."""
    
    def test_simple_brace(self):
        """Test simple brace expansion."""
        content, pos, found = pure_helpers.validate_brace_expansion("var}", 0)
        assert content == "var"
        assert pos == 4
        assert found is True
    
    def test_nested_braces(self):
        """Test nested brace expansions."""
        content, pos, found = pure_helpers.validate_brace_expansion("var{inner}}", 0)
        assert content == "var{inner}"
        assert pos == 11
        assert found is True
    
    def test_unclosed_brace(self):
        """Test unclosed brace expansion."""
        content, pos, found = pure_helpers.validate_brace_expansion("var", 0)
        assert content == "var"
        assert pos == 3
        assert found is False


class TestIsInsideExpansion:
    """Test expansion detection."""
    
    def test_inside_arithmetic(self):
        """Test position inside arithmetic expansion."""
        # Position 5 is inside $((2+3))
        assert pure_helpers.is_inside_expansion("$((2+3))", 5) is True
        assert pure_helpers.is_inside_expansion("$((2+3))", 8) is False
    
    def test_inside_command_sub(self):
        """Test position inside command substitution."""
        # Position 3 is inside $(echo)
        assert pure_helpers.is_inside_expansion("$(echo)", 3) is True
        assert pure_helpers.is_inside_expansion("$(echo)", 7) is False
    
    def test_inside_backticks(self):
        """Test position inside backtick substitution."""
        # Position 2 is inside `cmd`
        assert pure_helpers.is_inside_expansion("`cmd`", 2) is True
        assert pure_helpers.is_inside_expansion("`cmd`", 5) is False
    
    def test_outside_expansions(self):
        """Test position outside any expansions."""
        assert pure_helpers.is_inside_expansion("echo hello", 5) is False
        assert pure_helpers.is_inside_expansion("$var", 2) is False


# Integration tests
class TestPureFunctionIntegration:
    """Integration tests for pure functions working together."""
    
    def test_complex_parsing(self):
        """Test complex parsing scenario using multiple pure functions."""
        input_text = 'echo "hello $(echo world)" | grep test'
        
        # Find the pipe operator
        result = pure_helpers.find_operator_match(input_text, 27, OPERATORS_BY_LENGTH)
        assert result is not None
        op, token_type, pos = result
        assert op == "|"
        assert pos == 28
        
        # Extract the quoted content
        content, end_pos, found = pure_helpers.extract_quoted_content(
            input_text, 6, '"', allow_escapes=True
        )
        assert content == "hello $(echo world)"
        assert found is True
    
    def test_nested_structures(self):
        """Test parsing nested structures."""
        input_text = "$((2 + $(echo 3)))"
        
        # Should detect we're inside expansions at various positions
        assert pure_helpers.is_inside_expansion(input_text, 5) is True   # Inside arithmetic
        assert pure_helpers.is_inside_expansion(input_text, 12) is True  # Inside command sub
        assert pure_helpers.is_inside_expansion(input_text, 18) is False # After everything
    
    def test_error_recovery(self):
        """Test error recovery with unclosed structures."""
        # Test unclosed parentheses
        pos, found = pure_helpers.find_balanced_parentheses("echo (hello", 5)
        assert found is False
        assert pos == 11
        
        # Test unclosed quotes
        content, pos, found = pure_helpers.extract_quoted_content("hello", 0, '"')
        assert found is False
        assert content == "hello"