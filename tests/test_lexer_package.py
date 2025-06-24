#!/usr/bin/env python3
"""Tests for the lexer package structure and API."""

import pytest
from psh.lexer import (
    StateMachineLexer, tokenize, TokenPart, RichToken,
    KEYWORDS, OPERATORS_BY_LENGTH,
    is_identifier_start, is_whitespace
)
from psh.lexer import LexerConfig


class TestLexerPackageAPI:
    """Test the public API of the lexer package."""
    
    def test_main_imports(self):
        """Test that main components can be imported."""
        assert StateMachineLexer is not None
        assert tokenize is not None
        assert TokenPart is not None
        assert RichToken is not None
    
    def test_constants_available(self):
        """Test that constants are available."""
        assert len(KEYWORDS) > 0
        assert len(OPERATORS_BY_LENGTH) > 0
        assert 'if' in KEYWORDS
        assert '&&' in OPERATORS_BY_LENGTH[2]
    
    def test_unicode_functions_available(self):
        """Test that Unicode functions are available."""
        assert is_identifier_start('a')
        assert is_identifier_start('_')
        assert not is_identifier_start('1')
        assert is_whitespace(' ')
        assert is_whitespace('\t')
    
    def test_tokenize_function(self):
        """Test the main tokenize function."""
        tokens = tokenize('echo hello')
        assert len(tokens) == 3  # echo, hello, EOF
        assert tokens[0].value == 'echo'
        assert tokens[1].value == 'hello'
    
    def test_lexer_class(self):
        """Test the StateMachineLexer class."""
        lexer = StateMachineLexer('echo test')
        tokens = lexer.tokenize()
        assert len(tokens) == 3  # echo, test, EOF
        assert tokens[0].value == 'echo'
        assert tokens[1].value == 'test'
    
    def test_lexer_config(self):
        """Test lexer with configuration."""
        config = LexerConfig(posix_mode=True)
        lexer = StateMachineLexer('echo αtest', config)
        tokens = lexer.tokenize()
        # In POSIX mode, Unicode characters should be handled differently
        assert len(tokens) >= 2


class TestBackwardCompatibility:
    """Test backward compatibility with old imports."""
    
    def test_old_import_still_works(self):
        """Test that old import pattern still works."""
        from psh.lexer import tokenize as old_tokenize
        from psh.lexer import StateMachineLexer as OldLexer
        
        tokens = old_tokenize('echo hello')
        assert len(tokens) == 3
        
        lexer = OldLexer('echo test')
        tokens = lexer.tokenize()
        assert len(tokens) == 3


class TestPackageStructure:
    """Test the internal package structure."""
    
    def test_module_imports(self):
        """Test that internal modules can be imported."""
        from psh.lexer.constants import KEYWORDS
        from psh.lexer.unicode_support import is_identifier_start
        from psh.lexer.token_parts import TokenPart
        from psh.lexer.helpers import LexerHelpers
        from psh.lexer.state_handlers import StateHandlers
        from psh.lexer.core import StateMachineLexer
        
        assert KEYWORDS is not None
        assert is_identifier_start is not None
        assert TokenPart is not None
        assert LexerHelpers is not None
        assert StateHandlers is not None
        assert StateMachineLexer is not None
    
    def test_mixin_inheritance(self):
        """Test that the lexer properly inherits from mixins."""
        lexer = StateMachineLexer('test')
        
        # Should have methods from LexerHelpers
        assert hasattr(lexer, 'read_balanced_parens')
        assert hasattr(lexer, '_check_for_operator')
        
        # Should have methods from StateHandlers  
        assert hasattr(lexer, 'handle_normal_state')
        assert hasattr(lexer, 'handle_word_state')
        
        # Should have core methods
        assert hasattr(lexer, 'tokenize')
        assert hasattr(lexer, 'emit_token')


if __name__ == '__main__':
    pytest.main([__file__])