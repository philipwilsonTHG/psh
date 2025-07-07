#!/usr/bin/env python3
"""Tests for unified quote and expansion parsers."""

import pytest
from psh.lexer.unified_lexer import UnifiedLexer
from psh.lexer.quote_parser import UnifiedQuoteParser, QuoteRules, QUOTE_RULES, QuoteParsingContext
from psh.lexer.expansion_parser import ExpansionParser, ExpansionContext
from psh.lexer.position import LexerConfig, PositionTracker
from psh.token_types import TokenType


class TestUnifiedQuoteParser:
    """Test the unified quote parser."""
    
    def test_single_quote_parsing(self):
        """Test single quote parsing with no expansions."""
        parser = UnifiedQuoteParser()
        rules = QUOTE_RULES["'"]
        
        parts, pos, closed = parser.parse_quoted_string(
            "hello world'", 0, rules
        )
        
        assert closed
        assert pos == 12  # After closing quote
        assert len(parts) == 1
        assert parts[0].value == "hello world"
        assert parts[0].quote_type == "'"
        assert not parts[0].is_expansion
    
    def test_double_quote_with_variables(self):
        """Test double quote parsing with variable expansion."""
        expansion_parser = ExpansionParser()
        parser = UnifiedQuoteParser(expansion_parser)
        rules = QUOTE_RULES['"']
        
        parts, pos, closed = parser.parse_quoted_string(
            "hello $USER world\"", 0, rules
        )
        
        assert closed
        assert len(parts) == 3  # "hello ", "$USER", " world"
        assert parts[0].value == "hello "
        assert parts[1].value == "USER"
        assert parts[1].is_variable
        assert parts[2].value == " world"
    
    def test_double_quote_with_command_substitution(self):
        """Test double quote with command substitution."""
        expansion_parser = ExpansionParser()
        parser = UnifiedQuoteParser(expansion_parser)
        rules = QUOTE_RULES['"']
        
        parts, pos, closed = parser.parse_quoted_string(
            "output: $(echo test)\"", 0, rules
        )
        
        assert closed
        assert len(parts) == 2  # "output: ", "$(echo test)"
        assert parts[0].value == "output: "
        assert parts[1].value == "$(echo test)"
        assert parts[1].is_expansion
        assert parts[1].expansion_type == "command"
    
    def test_double_quote_with_arithmetic(self):
        """Test double quote with arithmetic expansion."""
        expansion_parser = ExpansionParser()
        parser = UnifiedQuoteParser(expansion_parser)
        rules = QUOTE_RULES['"']
        
        parts, pos, closed = parser.parse_quoted_string(
            "result: $((2 + 3))\"", 0, rules
        )
        
        assert closed
        assert len(parts) == 2  # "result: ", "$((2 + 3))"
        assert parts[0].value == "result: "
        assert parts[1].value == "$((2 + 3))"
        assert parts[1].is_expansion
        assert parts[1].expansion_type == "arithmetic"
    
    def test_double_quote_with_backticks(self):
        """Test double quote with backtick command substitution."""
        expansion_parser = ExpansionParser()
        parser = UnifiedQuoteParser(expansion_parser)
        rules = QUOTE_RULES['"']
        
        parts, pos, closed = parser.parse_quoted_string(
            "output: `echo test`\"", 0, rules
        )
        
        assert closed
        assert len(parts) == 2  # "output: ", "`echo test`"
        assert parts[0].value == "output: "
        assert parts[1].value == "`echo test`"
        assert parts[1].is_expansion
        assert parts[1].expansion_type == "backtick"
    
    def test_unclosed_quote(self):
        """Test handling of unclosed quotes."""
        parser = UnifiedQuoteParser()
        rules = QUOTE_RULES["'"]
        
        parts, pos, closed = parser.parse_quoted_string(
            "hello world", 0, rules
        )
        
        assert not closed
        assert len(parts) == 1
        assert parts[0].value == "hello world"
    
    def test_empty_quote(self):
        """Test empty quoted string."""
        parser = UnifiedQuoteParser()
        rules = QUOTE_RULES["'"]
        
        parts, pos, closed = parser.parse_quoted_string(
            "'", 0, rules
        )
        
        assert closed
        assert pos == 1
        assert len(parts) == 0
    
    def test_escape_sequences_in_double_quotes(self):
        """Test escape sequence handling in double quotes."""
        parser = UnifiedQuoteParser()
        rules = QUOTE_RULES['"']
        
        parts, pos, closed = parser.parse_quoted_string(
            "line1\\nline2\\t\"", 0, rules
        )
        
        assert closed
        assert len(parts) == 1
        # The escape sequences should be preserved as literal backslashes
        assert "\\n" in parts[0].value
        assert "\\t" in parts[0].value


class TestExpansionParser:
    """Test the expansion parser."""
    
    def test_simple_variable_expansion(self):
        """Test simple $VAR expansion."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("$USER", 0)
        
        assert part.is_variable
        assert part.is_expansion
        assert part.value == "USER"
        assert part.expansion_type == "variable"
        assert pos == 5
    
    def test_brace_variable_expansion(self):
        """Test ${VAR} expansion."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("${USER}", 0)
        
        assert part.is_variable
        assert part.is_expansion
        assert part.value == "${USER}"
        assert part.expansion_type == "parameter"
        assert pos == 7
    
    def test_command_substitution(self):
        """Test $(command) expansion."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("$(echo hello)", 0)
        
        assert part.is_expansion
        assert not part.is_variable
        assert part.value == "$(echo hello)"
        assert part.expansion_type == "command"
        assert pos == 13
    
    def test_arithmetic_expansion(self):
        """Test $((expr)) expansion."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("$((2 + 3))", 0)
        
        assert part.is_expansion
        assert not part.is_variable
        assert part.value == "$((2 + 3))"
        assert part.expansion_type == "arithmetic"
        assert pos == 10
    
    def test_nested_parentheses(self):
        """Test command substitution with nested parentheses."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("$(echo $(date))", 0)
        
        assert part.is_expansion
        assert part.value == "$(echo $(date))"
        assert part.expansion_type == "command"
        assert pos == 15
    
    def test_unclosed_expansion(self):
        """Test unclosed expansion handling."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("$(echo hello", 0)
        
        assert part.is_expansion
        assert part.value == "$(echo hello"
        assert part.expansion_type == "command_unclosed"
        assert pos == 12
    
    def test_backtick_substitution(self):
        """Test `command` substitution."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_backtick_substitution("`echo hello`", 0)
        
        assert part.is_expansion
        assert part.value == "`echo hello`"
        assert part.expansion_type == "backtick"
        assert pos == 12
    
    def test_special_variables(self):
        """Test special variable handling."""
        parser = ExpansionParser()
        
        for var in ['$?', '$#', '$$', '$!', '$0', '$1']:
            part, pos = parser.parse_expansion(var, 0)
            assert part.is_variable
            assert part.is_expansion
            assert len(part.value) == 1  # Just the special char
    
    def test_invalid_variable_name(self):
        """Test invalid variable name handling."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("$+", 0)
        
        # Should treat $ as literal since + is not a valid variable name
        assert not part.is_variable
        assert not part.is_expansion
        assert part.value == "$"
        assert pos == 1
    
    def test_expansion_in_quote_context(self):
        """Test expansion parsing in quote context."""
        parser = ExpansionParser()
        
        part, pos = parser.parse_expansion("$USER", 0, quote_context='"')
        
        assert part.is_variable
        assert part.quote_type == '"'
        assert part.value == "USER"


class TestExpansionContext:
    """Test the expansion context wrapper."""
    
    def test_context_creation(self):
        """Test context creation and basic functionality."""
        config = LexerConfig()
        tracker = PositionTracker("$USER test")
        context = ExpansionContext("$USER test", config, tracker)
        
        assert context.is_expansion_start(0)
        assert not context.is_expansion_start(1)
        assert not context.is_expansion_start(5)
    
    def test_parse_at_position(self):
        """Test parsing expansion at specific position."""
        context = ExpansionContext("echo $USER test")
        
        part, pos = context.parse_expansion_at_position(5)  # Position of $
        
        assert part.is_variable
        assert part.value == "USER"
        assert pos == 10


class TestQuoteParsingContext:
    """Test the quote parsing context wrapper."""
    
    def test_context_creation(self):
        """Test context creation and basic functionality."""
        config = LexerConfig()
        tracker = PositionTracker("'hello world'")
        context = QuoteParsingContext("'hello world'", tracker, config)
        
        assert context.is_quote_character("'")
        assert context.is_quote_character('"')
        assert not context.is_quote_character('x')
    
    def test_parse_at_position(self):
        """Test parsing quote at specific position."""
        context = QuoteParsingContext("'hello world'")
        
        parts, pos, closed = context.parse_quote_at_position(0, "'")
        
        assert closed
        assert len(parts) == 1
        assert parts[0].value == "hello world"
        assert pos == 13


class TestUnifiedLexerIntegration:
    """Test integration of unified parsers with main lexer."""
    
    def test_basic_tokenization(self):
        """Test basic word tokenization."""
        lexer = UnifiedLexer("echo hello")
        tokens = lexer.tokenize()
        
        assert len(tokens) == 3  # echo, hello, EOF
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.WORD
        assert tokens[1].value == "hello"
        assert tokens[2].type == TokenType.EOF
    
    def test_single_quoted_string(self):
        """Test single quoted string tokenization."""
        lexer = UnifiedLexer("echo 'hello world'")
        tokens = lexer.tokenize()
        
        assert len(tokens) == 3  # echo, 'hello world', EOF
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "hello world"
        assert tokens[1].quote_type == "'"
    
    def test_double_quoted_string_with_variable(self):
        """Test double quoted string with variable expansion."""
        lexer = UnifiedLexer('echo "hello $USER"')
        tokens = lexer.tokenize()
        
        assert len(tokens) == 3  # echo, "hello $USER", EOF
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].quote_type == '"'
        
        # Check if it's a RichToken with parts
        from psh.lexer.token_parts import RichToken
        if isinstance(tokens[1], RichToken):
            assert len(tokens[1].parts) == 2  # "hello " and "$USER"
            assert tokens[1].parts[0].value == "hello "
            assert tokens[1].parts[1].value == "USER"
            assert tokens[1].parts[1].is_variable
    
    def test_command_substitution_tokenization(self):
        """Test command substitution tokenization."""
        lexer = UnifiedLexer("echo $(date)")
        tokens = lexer.tokenize()
        
        # Should have: echo, $(date), EOF
        assert len(tokens) == 3
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.COMMAND_SUB
        assert tokens[1].value == "$(date)"
    
    def test_arithmetic_expansion_tokenization(self):
        """Test arithmetic expansion tokenization."""
        lexer = UnifiedLexer("echo $((2 + 3))")
        tokens = lexer.tokenize()
        
        # Should have: echo, $((2 + 3)), EOF
        assert len(tokens) == 3
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.ARITH_EXPANSION
        assert tokens[1].value == "$((2 + 3))"
    
    def test_variable_tokenization(self):
        """Test simple variable tokenization."""
        lexer = UnifiedLexer("echo $USER")
        tokens = lexer.tokenize()
        
        # Should have: echo, $USER, EOF
        assert len(tokens) == 3
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == "USER"
    
    def test_brace_variable_tokenization(self):
        """Test brace variable tokenization."""
        lexer = UnifiedLexer("echo ${USER}")
        tokens = lexer.tokenize()
        
        # Should have: echo, ${USER}, EOF
        assert len(tokens) == 3
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == "{USER}"
    
    def test_backtick_substitution_tokenization(self):
        """Test backtick command substitution."""
        lexer = UnifiedLexer("echo `date`")
        tokens = lexer.tokenize()
        
        # Should have: echo, `date`, EOF
        assert len(tokens) == 3
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.COMMAND_SUB_BACKTICK
        assert tokens[1].value == "`date`"
    
    def test_mixed_quoting_and_expansion(self):
        """Test complex mixed quoting and expansion."""
        lexer = UnifiedLexer('''echo "Hello $USER, today is $(date)"''')
        tokens = lexer.tokenize()
        
        assert len(tokens) == 3
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].quote_type == '"'
        
        # Check parts if it's a RichToken
        from psh.lexer.token_parts import RichToken
        if isinstance(tokens[1], RichToken):
            # Should have multiple parts for the string
            assert len(tokens[1].parts) >= 3
    
    def test_operator_recognition(self):
        """Test that operators are still recognized properly."""
        lexer = UnifiedLexer("echo hello && echo world")
        tokens = lexer.tokenize()
        
        token_values = [t.value for t in tokens[:-1]]  # Exclude EOF
        assert "echo" in token_values
        assert "hello" in token_values
        assert "&&" in token_values
        assert "world" in token_values
    
    def test_redirection_operators(self):
        """Test redirection operators."""
        lexer = UnifiedLexer("echo hello > output.txt")
        tokens = lexer.tokenize()
        
        token_values = [t.value for t in tokens[:-1]]  # Exclude EOF
        assert "echo" in token_values
        assert "hello" in token_values
        assert ">" in token_values
        assert "output.txt" in token_values
    
    def test_backward_compatibility(self):
        """Test that the unified lexer maintains backward compatibility."""
        # Test that all the expected properties and methods exist
        lexer = UnifiedLexer("test")
        
        # Position properties
        assert hasattr(lexer, 'position')
        assert hasattr(lexer, 'current_char')
        assert hasattr(lexer, 'advance')
        
        # State properties  
        assert hasattr(lexer, 'state')
        assert hasattr(lexer, 'in_double_brackets')
        assert hasattr(lexer, 'command_position')
        
        # Token emission
        assert hasattr(lexer, 'emit_token')
        assert hasattr(lexer, 'tokenize')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])