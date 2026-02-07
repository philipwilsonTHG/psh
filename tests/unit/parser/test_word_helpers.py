"""
Unit tests for Word helper properties.

Tests the is_quoted, is_unquoted_literal, is_variable_expansion,
has_expansion_parts, has_unquoted_expansion, and effective_quote_char
properties on the Word AST node.
"""

import pytest
from psh.ast_nodes import (
    Word, LiteralPart, ExpansionPart,
    VariableExpansion, ParameterExpansion,
    CommandSubstitution, ArithmeticExpansion,
)


class TestIsQuoted:
    """Tests for Word.is_quoted property."""

    def test_single_quoted_word(self):
        word = Word(parts=[LiteralPart("hello")], quote_type="'")
        assert word.is_quoted is True

    def test_double_quoted_word(self):
        word = Word(parts=[LiteralPart("hello")], quote_type='"')
        assert word.is_quoted is True

    def test_ansi_c_quoted_word(self):
        word = Word(parts=[LiteralPart("hello")], quote_type="$'")
        assert word.is_quoted is True

    def test_unquoted_word(self):
        word = Word(parts=[LiteralPart("hello")])
        assert word.is_quoted is False

    def test_single_part_quoted(self):
        """Single-part word where the part itself is quoted."""
        word = Word(parts=[LiteralPart("hello", quoted=True, quote_char="'")])
        assert word.is_quoted is True

    def test_multi_part_unquoted(self):
        """Multi-part composite word with no quote_type."""
        word = Word(parts=[
            LiteralPart("hello"),
            ExpansionPart(VariableExpansion("USER")),
        ])
        assert word.is_quoted is False


class TestIsUnquotedLiteral:
    """Tests for Word.is_unquoted_literal property."""

    def test_plain_word(self):
        word = Word(parts=[LiteralPart("hello")])
        assert word.is_unquoted_literal is True

    def test_quoted_word(self):
        word = Word(parts=[LiteralPart("hello")], quote_type="'")
        assert word.is_unquoted_literal is False

    def test_word_with_expansion(self):
        word = Word(parts=[ExpansionPart(VariableExpansion("HOME"))])
        assert word.is_unquoted_literal is False

    def test_multi_part_word(self):
        word = Word(parts=[
            LiteralPart("hello"),
            LiteralPart("world"),
        ])
        assert word.is_unquoted_literal is False

    def test_single_quoted_part(self):
        word = Word(parts=[LiteralPart("hello", quoted=True, quote_char="'")])
        assert word.is_unquoted_literal is False

    def test_empty_word(self):
        word = Word(parts=[])
        assert word.is_unquoted_literal is True


class TestIsVariableExpansion:
    """Tests for Word.is_variable_expansion property."""

    def test_simple_variable(self):
        word = Word(parts=[ExpansionPart(VariableExpansion("HOME"))])
        assert word.is_variable_expansion is True

    def test_parameter_expansion(self):
        word = Word(parts=[ExpansionPart(ParameterExpansion("HOME"))])
        assert word.is_variable_expansion is True

    def test_command_substitution(self):
        word = Word(parts=[ExpansionPart(CommandSubstitution("echo hi"))])
        assert word.is_variable_expansion is False

    def test_arithmetic_expansion(self):
        word = Word(parts=[ExpansionPart(ArithmeticExpansion("1+1"))])
        assert word.is_variable_expansion is False

    def test_literal_word(self):
        word = Word(parts=[LiteralPart("hello")])
        assert word.is_variable_expansion is False

    def test_multi_part_with_variable(self):
        """Multi-part word is not a single variable expansion."""
        word = Word(parts=[
            ExpansionPart(VariableExpansion("HOME")),
            LiteralPart("/bin"),
        ])
        assert word.is_variable_expansion is False


class TestHasExpansionParts:
    """Tests for Word.has_expansion_parts property."""

    def test_word_with_expansion(self):
        word = Word(parts=[ExpansionPart(VariableExpansion("HOME"))])
        assert word.has_expansion_parts is True

    def test_word_without_expansion(self):
        word = Word(parts=[LiteralPart("hello")])
        assert word.has_expansion_parts is False

    def test_mixed_word(self):
        word = Word(parts=[
            LiteralPart("prefix"),
            ExpansionPart(VariableExpansion("VAR")),
            LiteralPart("suffix"),
        ])
        assert word.has_expansion_parts is True


class TestHasUnquotedExpansion:
    """Tests for Word.has_unquoted_expansion property."""

    def test_unquoted_expansion(self):
        word = Word(parts=[ExpansionPart(VariableExpansion("HOME"), quoted=False)])
        assert word.has_unquoted_expansion is True

    def test_quoted_expansion(self):
        word = Word(parts=[ExpansionPart(VariableExpansion("HOME"), quoted=True, quote_char='"')])
        assert word.has_unquoted_expansion is False

    def test_no_expansion(self):
        word = Word(parts=[LiteralPart("hello")])
        assert word.has_unquoted_expansion is False

    def test_mixed_quoted_unquoted(self):
        word = Word(parts=[
            ExpansionPart(VariableExpansion("A"), quoted=True, quote_char='"'),
            ExpansionPart(VariableExpansion("B"), quoted=False),
        ])
        assert word.has_unquoted_expansion is True


class TestEffectiveQuoteChar:
    """Tests for Word.effective_quote_char property."""

    def test_single_quoted(self):
        word = Word(parts=[LiteralPart("hello")], quote_type="'")
        assert word.effective_quote_char == "'"

    def test_double_quoted(self):
        word = Word(parts=[LiteralPart("hello")], quote_type='"')
        assert word.effective_quote_char == '"'

    def test_ansi_c_quoted(self):
        word = Word(parts=[LiteralPart("hello")], quote_type="$'")
        assert word.effective_quote_char == "$'"

    def test_unquoted(self):
        word = Word(parts=[LiteralPart("hello")])
        assert word.effective_quote_char is None

    def test_single_part_with_quote_char(self):
        word = Word(parts=[LiteralPart("hello", quoted=True, quote_char="'")])
        assert word.effective_quote_char == "'"

    def test_multi_part_no_quote(self):
        word = Word(parts=[
            LiteralPart("hello"),
            LiteralPart("world"),
        ])
        assert word.effective_quote_char is None
