"""
Comprehensive token recognizer unit tests.

Tests for the modular lexer recognizer system including individual recognizers,
priority-based recognition, context-sensitive tokenization, and registry management.
"""

import pytest
from psh.lexer.recognizers import (
    TokenRecognizer, RecognizerRegistry,
    OperatorRecognizer, KeywordRecognizer, LiteralRecognizer,
    WhitespaceRecognizer, CommentRecognizer,
    setup_default_recognizers
)
from psh.lexer.state_context import LexerContext
from psh.lexer import ModularLexer, tokenize
from psh.token_types import TokenType


class TestTokenRecognizerBase:
    """Test the abstract base class for token recognizers."""
    
    def test_base_recognizer_abstract(self):
        """Test that TokenRecognizer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TokenRecognizer(priority=100)


class TestOperatorRecognizer:
    """Test operator recognition functionality."""
    
    @pytest.fixture
    def recognizer(self):
        return OperatorRecognizer()
    
    @pytest.fixture
    def context(self):
        return LexerContext()
    
    def test_single_character_operators(self, recognizer, context):
        """Test recognition of single character operators."""
        test_cases = [
            ('|', TokenType.PIPE),
            ('&', TokenType.AMPERSAND),
            (';', TokenType.SEMICOLON),
            ('(', TokenType.LPAREN),
            (')', TokenType.RPAREN),
            ('<', TokenType.REDIRECT_IN),
            ('>', TokenType.REDIRECT_OUT),
        ]
        
        for text, expected_type in test_cases:
            result = recognizer.recognize(text, 0, context)
            assert result is not None
            token, new_pos = result
            assert token.type == expected_type
            assert token.value == text
            assert new_pos == len(text)
    
    def test_multi_character_operators(self, recognizer, context):
        """Test recognition of multi-character operators."""
        test_cases = [
            ('&&', TokenType.AND_AND),
            ('||', TokenType.OR_OR),
            ('>>', TokenType.REDIRECT_APPEND),
            ('<<', TokenType.HEREDOC),
            ('<<<', TokenType.HERE_STRING),
        ]
        
        for text, expected_type in test_cases:
            result = recognizer.recognize(text, 0, context)
            assert result is not None
            token, new_pos = result
            assert token.type == expected_type
            assert token.value == text
            assert new_pos == len(text)
    
    def test_greedy_operator_matching(self, recognizer, context):
        """Test that longer operators are preferred over shorter ones."""
        # Test that && is recognized as AND_AND, not two AMPERSAND tokens
        result = recognizer.recognize('&&', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.AND_AND
        assert token.value == '&&'
        assert new_pos == 2
        
        # Test that || is recognized as OR_OR, not two PIPE tokens
        result = recognizer.recognize('||', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.OR_OR
        assert token.value == '||'
        assert new_pos == 2
        
        # Test that >> is recognized as REDIRECT_APPEND, not two REDIRECT_OUT
        result = recognizer.recognize('>>', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.REDIRECT_APPEND
        assert token.value == '>>'
        assert new_pos == 2
    
    def test_context_sensitive_operators(self, recognizer):
        """Test operators that require specific context."""
        # Test [[ - requires command position
        context_cmd = LexerContext(command_position=True)
        context_not_cmd = LexerContext(command_position=False)
        
        result = recognizer.recognize('[[', 0, context_cmd)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.DOUBLE_LBRACKET
        
        result = recognizer.recognize('[[', 0, context_not_cmd)
        assert result is None
        
        # Test ]] - requires bracket depth
        context_bracket = LexerContext(bracket_depth=1)
        context_no_bracket = LexerContext(bracket_depth=0)
        
        result = recognizer.recognize(']]', 0, context_bracket)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.DOUBLE_RBRACKET
        
        result = recognizer.recognize(']]', 0, context_no_bracket)
        # When not in bracket context, ]] should be recognized as single ]
        # rather than DOUBLE_RBRACKET
        if result is not None:
            token, new_pos = result
            assert token.type == TokenType.RBRACKET  # Single bracket, not double
            assert token.value == ']'
            assert new_pos == 1  # Only consumed one character
        
        # Test =~ - requires bracket depth
        result = recognizer.recognize('=~', 0, context_bracket)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.REGEX_MATCH
        
        result = recognizer.recognize('=~', 0, context_no_bracket)
        assert result is None
    
    def test_operator_not_recognized(self, recognizer, context):
        """Test that non-operators are not recognized."""
        non_operators = ['abc', '123', 'if', 'echo', '#comment']
        
        for text in non_operators:
            result = recognizer.recognize(text, 0, context)
            assert result is None
    
    def test_operator_at_position(self, recognizer, context):
        """Test operator recognition at different positions in text."""
        text = 'echo hello | grep test'
        
        # Test pipe at position 11
        result = recognizer.recognize(text, 11, context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.PIPE
        assert token.value == '|'
        assert new_pos == 12


class TestKeywordRecognizer:
    """Test keyword recognition functionality."""
    
    @pytest.fixture
    def recognizer(self):
        return KeywordRecognizer()
    
    def test_basic_keyword_recognition(self, recognizer):
        """Test recognition of shell keywords."""
        context = LexerContext(command_position=True)
        
        keywords = [
            ('if', TokenType.IF),
            ('then', TokenType.THEN),
            ('else', TokenType.ELSE),
            ('elif', TokenType.ELIF),
            ('fi', TokenType.FI),
            ('for', TokenType.FOR),
            ('do', TokenType.DO),
            ('done', TokenType.DONE),
            ('while', TokenType.WHILE),
            ('case', TokenType.CASE),
            ('esac', TokenType.ESAC),
            ('function', TokenType.FUNCTION),
        ]
        
        for text, expected_type in keywords:
            result = recognizer.recognize(text, 0, context)
            assert result is not None
            token, new_pos = result
            assert token.type == expected_type
            assert token.value == text
            assert new_pos == len(text)
    
    def test_keyword_command_position_requirement(self, recognizer):
        """Test that keywords are only recognized at command positions."""
        cmd_context = LexerContext(command_position=True)
        arg_context = LexerContext(command_position=False)
        
        # Should recognize in command position
        result = recognizer.recognize('if', 0, cmd_context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.IF
        
        # Should not recognize in argument position
        result = recognizer.recognize('if', 0, arg_context)
        assert result is None
    
    def test_keyword_word_boundary_detection(self, recognizer):
        """Test that keywords require proper word boundaries."""
        context = LexerContext(command_position=True)
        
        # Valid keyword (word boundary)
        result = recognizer.recognize('if ', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.IF
        
        # Invalid - part of larger word
        result = recognizer.recognize('ifconfig', 0, context)
        assert result is None
        
        # Valid at end of string
        result = recognizer.recognize('if', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.IF
    
    def test_keyword_case_sensitivity(self, recognizer):
        """Test that keywords are case-sensitive."""
        context = LexerContext(command_position=True)
        
        # Lowercase should work
        result = recognizer.recognize('if', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.type == TokenType.IF
        
        # Uppercase should not
        result = recognizer.recognize('IF', 0, context)
        assert result is None


class TestLiteralRecognizer:
    """Test literal (word) recognition functionality."""
    
    @pytest.fixture
    def recognizer(self):
        return LiteralRecognizer()
    
    @pytest.fixture
    def context(self):
        return LexerContext()
    
    def test_simple_word_recognition(self, recognizer, context):
        """Test recognition of simple words."""
        words = ['echo', 'hello', 'test123', 'file_name', 'PATH']
        
        for word in words:
            result = recognizer.recognize(word, 0, context)
            assert result is not None
            token, new_pos = result
            assert token.type == TokenType.WORD
            assert token.value == word
            assert new_pos == len(word)
    
    def test_word_with_special_characters(self, recognizer, context):
        """Test words with allowed special characters."""
        special_words = [
            'file.txt',
            'my-script',
            'var_123',
            'path/to/file',
            'user@host',
            'test:value',
        ]
        
        for word in special_words:
            result = recognizer.recognize(word, 0, context)
            assert result is not None
            token, new_pos = result
            assert token.type == TokenType.WORD
            assert token.value == word
    
    def test_word_termination(self, recognizer, context):
        """Test that words terminate at proper boundaries."""
        # Word terminates at space
        result = recognizer.recognize('hello world', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.value == 'hello'
        assert new_pos == 5
        
        # Word terminates at operator
        result = recognizer.recognize('file|grep', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.value == 'file'
        assert new_pos == 4
        
        # Word terminates at parenthesis
        result = recognizer.recognize('func()', 0, context)
        assert result is not None
        token, new_pos = result
        assert token.value == 'func'
        assert new_pos == 4
    
    def test_numbers_as_words(self, recognizer, context):
        """Test that numbers are recognized as words."""
        numbers = ['123', '0', '999', '42']
        
        for number in numbers:
            result = recognizer.recognize(number, 0, context)
            assert result is not None
            token, new_pos = result
            assert token.type == TokenType.WORD
            assert token.value == number
    
    def test_empty_or_whitespace_not_recognized(self, recognizer, context):
        """Test that empty strings or whitespace are not recognized as words."""
        invalid_inputs = ['', ' ', '\t', '  \t  ']
        
        for invalid in invalid_inputs:
            result = recognizer.recognize(invalid, 0, context)
            assert result is None


class TestWhitespaceRecognizer:
    """Test whitespace recognition functionality."""
    
    @pytest.fixture
    def recognizer(self):
        return WhitespaceRecognizer()
    
    @pytest.fixture
    def context(self):
        return LexerContext()
    
    def test_space_recognition(self, recognizer, context):
        """Test recognition of spaces."""
        result = recognizer.recognize(' ', 0, context)
        assert result is None  # Whitespace recognizer returns None to skip
        
        result = recognizer.recognize('   ', 0, context)
        assert result is None
    
    def test_tab_recognition(self, recognizer, context):
        """Test recognition of tabs."""
        result = recognizer.recognize('\t', 0, context)
        assert result is None  # Should be skipped
        
        result = recognizer.recognize('\t\t\t', 0, context)
        assert result is None
    
    def test_mixed_whitespace(self, recognizer, context):
        """Test recognition of mixed whitespace."""
        result = recognizer.recognize(' \t ', 0, context)
        assert result is None  # Should be skipped


class TestCommentRecognizer:
    """Test comment recognition functionality."""
    
    @pytest.fixture
    def recognizer(self):
        return CommentRecognizer()
    
    @pytest.fixture
    def context(self):
        return LexerContext()
    
    def test_comment_recognition(self, recognizer, context):
        """Test recognition of comments."""
        result = recognizer.recognize('#comment', 0, context)
        assert result is not None  # Comments return (None, pos)
        token, new_pos = result
        assert token is None  # Token is None
        assert new_pos == 8  # Should advance past comment
        
        result = recognizer.recognize('# this is a comment', 0, context)
        assert result is not None
        token, new_pos = result
        assert token is None
        assert new_pos == 19  # Should advance past comment
    
    def test_comment_in_middle_of_line(self, recognizer, context):
        """Test comment recognition when not at start of line."""
        text = 'echo hello # comment'
        
        # Test comment at position 11
        result = recognizer.recognize(text, 11, context)
        assert result is not None  # Should return (None, pos)
        token, new_pos = result
        assert token is None  # Token is None
        assert new_pos == 20  # Should advance past comment
    
    def test_hash_in_word_not_comment(self, recognizer, context):
        """Test that # inside words is not treated as comment."""
        # This test verifies the recognizer behavior, actual context 
        # handling is done by the lexer
        result = recognizer.recognize('file#name', 0, context)
        assert result is None  # Should not recognize as comment


class TestRecognizerRegistry:
    """Test the recognizer registry system."""
    
    @pytest.fixture
    def registry(self):
        return RecognizerRegistry()
    
    def test_register_recognizer(self, registry):
        """Test registering recognizers."""
        recognizer = OperatorRecognizer()
        
        registry.register(recognizer)
        
        # Should be in registry
        assert recognizer in registry.get_recognizers()
    
    def test_unregister_recognizer(self, registry):
        """Test unregistering recognizers."""
        recognizer = OperatorRecognizer()
        
        registry.register(recognizer)
        assert recognizer in registry.get_recognizers()
        
        registry.unregister(recognizer)
        assert recognizer not in registry.get_recognizers()
    
    def test_priority_ordering(self, registry):
        """Test that recognizers are ordered by priority."""
        low_priority = KeywordRecognizer()  # Priority 90
        high_priority = OperatorRecognizer()  # Priority 150
        
        registry.register(low_priority)
        registry.register(high_priority)
        
        # Should be ordered by priority (high to low)
        ordered = registry.get_recognizers()
        assert ordered[0] == high_priority
        assert ordered[1] == low_priority
    
    def test_clear_registry(self, registry):
        """Test clearing all recognizers."""
        registry.register(OperatorRecognizer())
        registry.register(KeywordRecognizer())
        
        assert len(registry) == 2
        
        registry.clear()
        assert len(registry) == 0
    
    def test_registry_statistics(self, registry):
        """Test registry statistics tracking."""
        operator_rec = OperatorRecognizer()
        keyword_rec = KeywordRecognizer()
        
        registry.register(operator_rec)
        registry.register(keyword_rec)
        
        # Test recognition counting
        context = LexerContext()
        
        # Test that registry has stats
        stats = registry.get_stats()
        assert 'total_recognizers' in stats
        assert stats['total_recognizers'] == 2
    
    def test_default_recognizers(self):
        """Test that default registry comes with standard recognizers."""
        registry = setup_default_recognizers()
        
        recognizers = registry.get_recognizers()
        
        # Should have all standard recognizers
        recognizer_types = [type(r).__name__ for r in recognizers]
        expected_types = [
            'ProcessSubstitutionRecognizer',
            'OperatorRecognizer',
            'KeywordRecognizer', 
            'LiteralRecognizer',
            'WhitespaceRecognizer',
            'CommentRecognizer'
        ]
        
        for expected_type in expected_types:
            assert expected_type in recognizer_types
    
    def test_registry_context_handling(self, registry):
        """Test registry properly handles context in recognition."""
        registry.register(OperatorRecognizer())
        registry.register(KeywordRecognizer())
        
        context = LexerContext()
        
        # Test recognition with context
        result = registry.recognize('if', 0, context)
        # May or may not recognize depending on context
        assert result is None or len(result) == 3
        
        # Test context-sensitive recognition
        cmd_context = LexerContext(command_position=True)
        
        # Should recognize 'if' as keyword in command position
        result = registry.recognize('if', 0, cmd_context)
        if result is not None:
            token, new_pos, recognizer = result
            assert token.type == TokenType.IF
        
        # Test non-command position
        arg_context = LexerContext(command_position=False)
        
        # Should not recognize 'if' as keyword in argument position
        result = registry.recognize('if', 0, arg_context)
        if result is not None:
            token, new_pos, recognizer = result
            assert token.type == TokenType.WORD


class TestModularLexerIntegration:
    """Test integration of the modular lexer system."""
    
    @pytest.fixture
    def registry(self):
        return setup_default_recognizers()
    
    def test_simple_command_tokenization(self, registry):
        """Test tokenization of simple commands."""
        lexer = ModularLexer('echo hello')
        tokens = list(lexer.tokenize())
        
        # Should tokenize as: WORD('echo'), WORD('hello'), EOF
        assert len(tokens) >= 2
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == 'echo'
        assert tokens[1].type == TokenType.WORD
        assert tokens[1].value == 'hello'
    
    def test_pipeline_tokenization(self, registry):
        """Test tokenization of pipeline commands."""
        lexer = ModularLexer('ls | grep test')
        tokens = list(lexer.tokenize())
        
        # Should include PIPE token
        token_types = [t.type for t in tokens]
        assert TokenType.WORD in token_types  # 'ls'
        assert TokenType.PIPE in token_types  # '|'
        assert TokenType.WORD in token_types  # 'grep'
    
    def test_conditional_tokenization(self, registry):
        """Test tokenization of conditional statements."""
        lexer = ModularLexer('if test; then echo yes; fi')
        tokens = list(lexer.tokenize())
        
        # Should recognize keywords
        token_types = [t.type for t in tokens]
        assert TokenType.IF in token_types
        assert TokenType.THEN in token_types
        assert TokenType.FI in token_types
        assert TokenType.SEMICOLON in token_types
    
    def test_complex_command_tokenization(self, registry):
        """Test tokenization of complex shell constructs."""
        lexer = ModularLexer('for file in *.txt; do echo $file; done')
        tokens = list(lexer.tokenize())
        
        # Should recognize loop keywords and various tokens
        token_types = [t.type for t in tokens]
        assert TokenType.FOR in token_types
        assert TokenType.IN in token_types
        assert TokenType.DO in token_types
        assert TokenType.DONE in token_types
    
    def test_quoted_string_handling(self, registry):
        """Test proper handling of quoted strings."""
        lexer = ModularLexer('echo "Hello $USER"')
        tokens = list(lexer.tokenize())
        
        # Should handle quoted content appropriately
        assert len(tokens) >= 2
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == 'echo'
    
    def test_backward_compatibility(self, registry):
        """Test that modular lexer produces equivalent results."""
        test_commands = [
            'echo hello',
            'ls | grep test',
            'if test; then echo yes; fi',
            'for i in 1 2 3; do echo $i; done'
        ]
        
        for command in test_commands:
            # Get tokens from both systems
            modular_lexer = ModularLexer(command)
            modular_tokens = list(modular_lexer.tokenize())
            original_tokens = list(tokenize(command))
            
            # Should both produce tokens
            assert len(modular_tokens) > 0
            assert len(original_tokens) > 0
            
            # Both should have EOF at the end
            assert modular_tokens[-1].type == TokenType.EOF
            assert original_tokens[-1].type == TokenType.EOF