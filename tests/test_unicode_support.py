#!/usr/bin/env python3
"""
Tests for Unicode support in the lexer.

This module tests the lexer's ability to handle Unicode characters in various
contexts, including variable names, whitespace, and edge cases.
"""

import pytest
from psh.lexer import (
    tokenize, is_identifier_start, is_identifier_char, 
    is_whitespace, normalize_identifier, validate_identifier,
    LexerConfig
)
from psh.token_types import TokenType


class TestUnicodeCharacterClassification:
    """Test Unicode character classification functions."""
    
    def test_ascii_identifier_functions(self):
        """Test that ASCII identifiers work in both modes."""
        # ASCII letters should work in both modes
        assert is_identifier_start('a', posix_mode=True) is True
        assert is_identifier_start('a', posix_mode=False) is True
        assert is_identifier_start('Z', posix_mode=True) is True
        assert is_identifier_start('Z', posix_mode=False) is True
        
        # Underscore should work in both modes
        assert is_identifier_start('_', posix_mode=True) is True
        assert is_identifier_start('_', posix_mode=False) is True
        
        # ASCII digits should work as identifier chars (not start)
        assert is_identifier_start('0', posix_mode=True) is False
        assert is_identifier_start('0', posix_mode=False) is False
        assert is_identifier_char('0', posix_mode=True) is True
        assert is_identifier_char('0', posix_mode=False) is True
    
    def test_unicode_identifier_functions(self):
        """Test Unicode identifier support."""
        # Unicode letters should work in Unicode mode only
        assert is_identifier_start('α', posix_mode=True) is False   # Greek alpha
        assert is_identifier_start('α', posix_mode=False) is True
        assert is_identifier_start('中', posix_mode=True) is False   # Chinese character
        assert is_identifier_start('中', posix_mode=False) is True
        assert is_identifier_start('ñ', posix_mode=True) is False   # Spanish n with tilde
        assert is_identifier_start('ñ', posix_mode=False) is True
        
        # Unicode numbers should work as identifier chars in Unicode mode
        assert is_identifier_char('৭', posix_mode=True) is False    # Bengali digit
        assert is_identifier_char('৭', posix_mode=False) is True
        assert is_identifier_char('²', posix_mode=True) is False    # Superscript 2
        assert is_identifier_char('²', posix_mode=False) is True
        
        # Unicode marks (combining chars) should work as identifier chars
        assert is_identifier_char('́', posix_mode=True) is False     # Combining acute accent
        assert is_identifier_char('́', posix_mode=False) is True
    
    def test_unicode_whitespace_functions(self):
        """Test Unicode whitespace detection."""
        # ASCII whitespace should work in both modes
        assert is_whitespace(' ', posix_mode=True) is True
        assert is_whitespace(' ', posix_mode=False) is True
        assert is_whitespace('\t', posix_mode=True) is True
        assert is_whitespace('\t', posix_mode=False) is True
        assert is_whitespace('\n', posix_mode=True) is True
        assert is_whitespace('\n', posix_mode=False) is True
        
        # Unicode whitespace should work in Unicode mode only
        assert is_whitespace('\u00A0', posix_mode=True) is False   # Non-breaking space
        assert is_whitespace('\u00A0', posix_mode=False) is True
        assert is_whitespace('\u2000', posix_mode=True) is False   # En quad
        assert is_whitespace('\u2000', posix_mode=False) is True
        assert is_whitespace('\u3000', posix_mode=True) is False   # Ideographic space
        assert is_whitespace('\u3000', posix_mode=False) is True
    
    def test_identifier_validation(self):
        """Test complete identifier validation."""
        # ASCII identifiers should work in both modes
        assert validate_identifier('test', posix_mode=True) is True
        assert validate_identifier('test', posix_mode=False) is True
        assert validate_identifier('_var', posix_mode=True) is True
        assert validate_identifier('_var', posix_mode=False) is True
        assert validate_identifier('var123', posix_mode=True) is True
        assert validate_identifier('var123', posix_mode=False) is True
        
        # Invalid ASCII identifiers should fail in both modes
        assert validate_identifier('123var', posix_mode=True) is False
        assert validate_identifier('123var', posix_mode=False) is False
        assert validate_identifier('', posix_mode=True) is False
        assert validate_identifier('', posix_mode=False) is False
        
        # Unicode identifiers should work in Unicode mode only
        assert validate_identifier('тест', posix_mode=True) is False    # Cyrillic
        assert validate_identifier('тест', posix_mode=False) is True
        assert validate_identifier('変数', posix_mode=True) is False    # Japanese
        assert validate_identifier('変数', posix_mode=False) is True
        assert validate_identifier('αβγ', posix_mode=True) is False     # Greek
        assert validate_identifier('αβγ', posix_mode=False) is True
    
    def test_identifier_normalization(self):
        """Test identifier normalization."""
        # ASCII should remain unchanged
        assert normalize_identifier('test') == 'test'
        assert normalize_identifier('TEST', case_sensitive=False) == 'test'
        assert normalize_identifier('TEST', case_sensitive=True) == 'TEST'
        
        # Unicode normalization (NFC)
        # é can be composed (é) or decomposed (e + ́)
        composed = 'café'  # é as single character
        decomposed = 'cafe\u0301'  # e + combining acute accent
        assert normalize_identifier(decomposed, posix_mode=False) == composed
        assert normalize_identifier(decomposed, posix_mode=True) == decomposed  # No normalization in POSIX
        
        # Case folding should work with Unicode
        assert normalize_identifier('Αβγ', case_sensitive=False) == 'αβγ'  # Greek


class TestUnicodeLexerBehavior:
    """Test lexer behavior with Unicode characters."""
    
    def test_unicode_variables_enabled(self):
        """Test Unicode variable names when enabled."""
        # Note: tokenize function doesn't directly support config yet
        # This test may need to be updated when config support is added
        tokens = tokenize('echo $тест', strict=False)
        
        assert len(tokens) == 3  # echo, $тест, EOF
        assert tokens[0].value == 'echo'
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == 'тест'  # Cyrillic 'test'
    
    def test_unicode_variables_disabled_posix(self):
        """Test that Unicode variables don't work in POSIX mode."""
        # POSIX mode via strict=True
        tokens = tokenize('echo $тест', strict=True)
        
        # Creates empty variable + word (as expected)
        # TODO: Could improve to treat entire $тест as literal word  
        assert len(tokens) == 4  # echo, $'', тест, EOF
        assert tokens[0].value == 'echo'
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == ''  # Empty variable name
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == 'тест'  # Unicode text as word
    
    def test_unicode_whitespace_handling(self):
        """Test Unicode whitespace handling."""
        # Use Unicode whitespace characters
        unicode_space = '\u00A0'  # Non-breaking space
        ideographic_space = '\u3000'  # Ideographic space
        
        # Unicode whitespace handling
        tokens = tokenize(f'echo{unicode_space}hello{ideographic_space}world', strict=False)
        
        assert len(tokens) == 4  # echo, hello, world, EOF
        assert tokens[0].value == 'echo'
        assert tokens[1].value == 'hello'
        assert tokens[2].value == 'world'
    
    def test_unicode_whitespace_posix_mode(self):
        """Test that Unicode whitespace is treated as word chars in POSIX mode."""
        unicode_space = '\u00A0'  # Non-breaking space
        
        # POSIX mode
        tokens = tokenize(f'echo{unicode_space}hello', strict=True)
        
        # Unicode space should be part of the word in POSIX mode (treated as single word)
        assert len(tokens) == 2  # echo{unicode_space}hello, EOF
        assert tokens[0].value == f'echo{unicode_space}hello'
    
    def test_mixed_unicode_ascii_variables(self):
        """Test variables with mixed Unicode and ASCII characters."""
        # Mixed Unicode/ASCII variables
        tokens = tokenize('echo $test_тест_123', strict=False)
        
        assert len(tokens) == 3  # echo, $test_тест_123, EOF
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == 'test_тест_123'
    
    def test_unicode_brace_variables(self):
        """Test Unicode in brace variable expansion."""
        # Unicode in brace expansion
        tokens = tokenize('echo ${αβγ:-default}', strict=False)
        
        assert len(tokens) == 3  # echo, ${αβγ:-default}, EOF
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == '{αβγ:-default}'
    
    def test_case_insensitive_unicode(self):
        """Test case-insensitive Unicode identifiers."""
        # Case-insensitive Unicode
        # Note: case sensitivity config not directly supported yet
        tokens = tokenize('echo $ΑΒΓΔ', strict=False)
        
        assert len(tokens) == 3
        assert tokens[1].type == TokenType.VARIABLE
        # Should be normalized to lowercase
        assert tokens[1].value == 'αβγδ'
    
    def test_unicode_normalization(self):
        """Test Unicode normalization in identifiers."""
        # Use decomposed form of café (e + combining acute)
        decomposed_var = 'cafe\u0301'
        tokens = tokenize(f'echo ${decomposed_var}', strict=False)
        
        assert len(tokens) == 3
        assert tokens[1].type == TokenType.VARIABLE
        # Should be normalized to composed form
        normalized = tokens[1].value.strip('{}')
        assert normalized == 'café'  # Composed form


class TestUnicodeEdgeCases:
    """Test Unicode edge cases and error conditions."""
    
    def test_empty_unicode_variable(self):
        """Test handling of empty variable after Unicode char."""
        # Valid Unicode var followed by lone $
        tokens = tokenize('echo $α$', strict=False)
        
        assert len(tokens) == 4  # echo, $α, $, EOF
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == 'α'
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == '$'
    
    def test_unicode_special_variables(self):
        """Test that special variables remain ASCII-only."""
        # Special variables remain ASCII-only
        tokens = tokenize('echo $? $0 $#', strict=False)
        
        assert len(tokens) == 5  # echo, $?, $0, $#, EOF
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == '?'
        assert tokens[2].type == TokenType.VARIABLE
        assert tokens[2].value == '0'
        assert tokens[3].type == TokenType.VARIABLE
        assert tokens[3].value == '#'
    
    def test_invalid_unicode_sequences(self):
        """Test handling of invalid Unicode sequences."""
        # Test with some Unicode punctuation that shouldn't be valid in identifiers
        tokens = tokenize('echo $test™', strict=False)  # Trademark symbol
        
        # Should stop at the trademark symbol
        assert len(tokens) == 4  # echo, $test, ™, EOF
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == 'test'
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == '™'
    
    def test_combining_characters_in_variables(self):
        """Test combining characters in variable names."""
        # Base character + combining characters
        var_with_accents = 'e\u0301\u0304'  # e + acute + macron
        tokens = tokenize(f'echo ${var_with_accents}', strict=False)
        
        assert len(tokens) == 3
        assert tokens[1].type == TokenType.VARIABLE
        # Should include combining characters as part of identifier
        variable_content = tokens[1].value.strip('{}')
        assert len(variable_content) >= 1  # At least the base character
    
    def test_configuration_inheritance(self):
        """Test that Unicode settings are properly inherited."""
        # Test POSIX config factory
        posix_config = LexerConfig.create_posix_config()
        assert posix_config.unicode_identifiers is False
        assert posix_config.posix_mode is True
        
        # Test default config
        default_config = LexerConfig()
        assert default_config.unicode_identifiers is True
        assert default_config.posix_mode is False