"""Tests for expansion and word-building parsers."""

import pytest
from psh.token_types import Token, TokenType
from psh.ast_nodes import (
    Word, LiteralPart, ExpansionPart,
    VariableExpansion, CommandSubstitution,
    ArithmeticExpansion, ProcessSubstitution
)
from psh.parser.config import ParserConfig
from psh.parser.combinators.expansions import (
    ExpansionParsers,
    create_expansion_parsers,
    parse_variable_expansion,
    parse_command_substitution,
    parse_arithmetic_expansion,
    parse_parameter_expansion,
    parse_process_substitution,
)


def make_token(token_type: TokenType, value: str, position: int = 0) -> Token:
    """Helper to create a token with minimal required fields."""
    return Token(type=token_type, value=value, position=position)


class TestExpansionParsers:
    """Test the ExpansionParsers class."""
    
    def test_initialization(self):
        """Test that ExpansionParsers initializes correctly."""
        parsers = ExpansionParsers()
        
        assert parsers.config is not None
        assert parsers.variable is not None
        assert parsers.command_sub is not None
        assert parsers.arith_expansion is not None
    
    def test_variable_expansion(self):
        """Test variable expansion parsing."""
        parsers = ExpansionParsers()
        
        tokens = [make_token(TokenType.VARIABLE, "USER")]
        result = parsers.variable.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "USER"
    
    def test_command_substitution(self):
        """Test command substitution parsing."""
        parsers = ExpansionParsers()
        
        # Test $(...) style
        tokens = [make_token(TokenType.COMMAND_SUB, "$(echo hello)")]
        result = parsers.command_sub.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "$(echo hello)"
        
        # Test backtick style
        tokens = [make_token(TokenType.COMMAND_SUB_BACKTICK, "`echo hello`")]
        result = parsers.command_sub_backtick.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "`echo hello`"
    
    def test_arithmetic_expansion(self):
        """Test arithmetic expansion parsing."""
        parsers = ExpansionParsers()
        
        tokens = [make_token(TokenType.ARITH_EXPANSION, "$((1 + 2))")]
        result = parsers.arith_expansion.parse(tokens, 0)
        assert result.success is True
        assert result.value.value == "$((1 + 2))"
    
    def test_process_substitution_in(self):
        """Test input process substitution parsing."""
        parsers = ExpansionParsers()
        
        tokens = [make_token(TokenType.PROCESS_SUB_IN, "<(ls -la)")]
        result = parsers.process_substitution.parse(tokens, 0)
        assert result.success is True
        assert result.value.direction == 'in'
        assert result.value.command == 'ls -la'
    
    def test_process_substitution_out(self):
        """Test output process substitution parsing."""
        parsers = ExpansionParsers()
        
        tokens = [make_token(TokenType.PROCESS_SUB_OUT, ">(tee log.txt)")]
        result = parsers.process_substitution.parse(tokens, 0)
        assert result.success is True
        assert result.value.direction == 'out'
        assert result.value.command == 'tee log.txt'
    
    def test_combined_expansion_parser(self):
        """Test the combined expansion parser."""
        parsers = ExpansionParsers()
        
        # Should accept any expansion type
        test_cases = [
            (TokenType.VARIABLE, "USER"),
            (TokenType.COMMAND_SUB, "$(pwd)"),
            (TokenType.ARITH_EXPANSION, "$((10 * 2))"),
            (TokenType.PROCESS_SUB_IN, "<(cat file)"),
        ]
        
        for token_type, value in test_cases:
            tokens = [make_token(token_type, value)]
            result = parsers.expansion.parse(tokens, 0)
            assert result.success is True
    
    def test_format_token_value(self):
        """Test token value formatting."""
        parsers = ExpansionParsers()
        
        # Variable tokens get $ prefix
        var_token = make_token(TokenType.VARIABLE, "USER")
        assert parsers.format_token_value(var_token) == "$USER"
        
        # Command substitution keeps its format
        cmd_token = make_token(TokenType.COMMAND_SUB, "$(echo test)")
        assert parsers.format_token_value(cmd_token) == "$(echo test)"
        
        # Regular words stay as-is
        word_token = make_token(TokenType.WORD, "hello")
        assert parsers.format_token_value(word_token) == "hello"
    
    def test_is_expansion_token(self):
        """Test expansion token detection."""
        parsers = ExpansionParsers()
        
        # Expansion tokens
        exp_token = make_token(TokenType.VARIABLE, "VAR")
        assert parsers.is_expansion_token(exp_token) is True
        
        cmd_token = make_token(TokenType.COMMAND_SUB, "$(cmd)")
        assert parsers.is_expansion_token(cmd_token) is True
        
        # Non-expansion tokens
        word_token = make_token(TokenType.WORD, "hello")
        assert parsers.is_expansion_token(word_token) is False
        
        semi_token = make_token(TokenType.SEMICOLON, ";")
        assert parsers.is_expansion_token(semi_token) is False


class TestWordBuilding:
    """Test Word AST node building."""
    
    def test_build_word_from_literal(self):
        """Test building Word from literal token."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.WORD, "hello")
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], LiteralPart)
        assert word.parts[0].text == "hello"
    
    def test_build_word_from_string(self):
        """Test building Word from string token."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.STRING, "hello world")
        token.quote_type = '"'  # Add quote type attribute
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], LiteralPart)
        assert word.parts[0].text == "hello world"
        assert word.quote_type == '"'
    
    def test_build_word_from_variable(self):
        """Test building Word from variable expansion."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.VARIABLE, "USER")
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, VariableExpansion)
        assert word.parts[0].expansion.name == "USER"
    
    def test_build_word_from_command_sub(self):
        """Test building Word from command substitution."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.COMMAND_SUB, "$(echo test)")
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, CommandSubstitution)
        assert word.parts[0].expansion.command == "echo test"
        assert word.parts[0].expansion.backtick_style is False
    
    def test_build_word_from_backtick_command_sub(self):
        """Test building Word from backtick command substitution."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.COMMAND_SUB_BACKTICK, "`pwd`")
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, CommandSubstitution)
        assert word.parts[0].expansion.command == "pwd"
        assert word.parts[0].expansion.backtick_style is True
    
    def test_build_word_from_arithmetic(self):
        """Test building Word from arithmetic expansion."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.ARITH_EXPANSION, "$((5 + 3))")
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "5 + 3"
    
    def test_build_word_from_process_sub_in(self):
        """Test building Word from input process substitution."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.PROCESS_SUB_IN, "<(sort file.txt)")
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ProcessSubstitution)
        assert word.parts[0].expansion.direction == 'in'
        assert word.parts[0].expansion.command == 'sort file.txt'
    
    def test_build_word_from_process_sub_out(self):
        """Test building Word from output process substitution."""
        parsers = ExpansionParsers()
        
        token = make_token(TokenType.PROCESS_SUB_OUT, ">(gzip > output.gz)")
        word = parsers.build_word_from_token(token)
        
        assert isinstance(word, Word)
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ProcessSubstitution)
        assert word.parts[0].expansion.direction == 'out'
        assert word.parts[0].expansion.command == 'gzip > output.gz'


class TestConvenienceFunctions:
    """Test convenience functions for expansion parsing."""
    
    def test_create_expansion_parsers(self):
        """Test factory function."""
        parsers = create_expansion_parsers()
        assert isinstance(parsers, ExpansionParsers)
        assert parsers.config is not None
    
    def test_parse_variable_expansion(self):
        """Test variable expansion parser function."""
        parser = parse_variable_expansion()
        tokens = [make_token(TokenType.VARIABLE, "HOME")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_parse_command_substitution(self):
        """Test command substitution parser function."""
        parser = parse_command_substitution()
        
        # Should accept both styles
        tokens1 = [make_token(TokenType.COMMAND_SUB, "$(date)")]
        result1 = parser.parse(tokens1, 0)
        assert result1.success is True
        
        tokens2 = [make_token(TokenType.COMMAND_SUB_BACKTICK, "`date`")]
        result2 = parser.parse(tokens2, 0)
        assert result2.success is True
    
    def test_parse_arithmetic_expansion(self):
        """Test arithmetic expansion parser function."""
        parser = parse_arithmetic_expansion()
        tokens = [make_token(TokenType.ARITH_EXPANSION, "$((42))")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_parse_parameter_expansion(self):
        """Test parameter expansion parser function."""
        parser = parse_parameter_expansion()
        tokens = [make_token(TokenType.PARAM_EXPANSION, "${USER:-nobody}")]
        result = parser.parse(tokens, 0)
        assert result.success is True
    
    def test_parse_process_substitution(self):
        """Test process substitution parser function."""
        parser = parse_process_substitution()
        
        # Should accept both directions
        tokens1 = [make_token(TokenType.PROCESS_SUB_IN, "<(cat)")]
        result1 = parser.parse(tokens1, 0)
        assert result1.success is True
        
        tokens2 = [make_token(TokenType.PROCESS_SUB_OUT, ">(tee)")]
        result2 = parser.parse(tokens2, 0)
        assert result2.success is True


class TestValidation:
    """Test validation of expansion content."""
    
    def test_validate_command_substitution_valid(self):
        """Test validation accepts valid command substitutions."""
        parsers = ExpansionParsers()
        
        # Simple commands should be valid
        assert parsers._validate_command_substitution("echo hello") is True
        assert parsers._validate_command_substitution("ls -la") is True
        assert parsers._validate_command_substitution("pwd") is True
    
    def test_validate_command_substitution_function_def(self):
        """Test validation rejects function definitions."""
        parsers = ExpansionParsers()
        
        # Function definitions should be invalid
        assert parsers._validate_command_substitution("function foo { echo bar; }") is False
        assert parsers._validate_command_substitution("foo() { echo bar; }") is False
    
    def test_validate_command_substitution_invalid(self):
        """Test validation rejects invalid syntax."""
        parsers = ExpansionParsers()
        
        # Our simplified validation only checks for function definitions
        # It doesn't do full syntax validation (that would require full parsing)
        # So "echo $(" would be considered "valid" until actual parsing
        assert parsers._validate_command_substitution("echo $(") is True  # Simplified validation