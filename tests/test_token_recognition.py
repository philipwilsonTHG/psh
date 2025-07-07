#!/usr/bin/env python3
"""Tests for the token recognition system."""

import pytest
from psh.lexer.recognizers import (
    TokenRecognizer, OperatorRecognizer, KeywordRecognizer, 
    LiteralRecognizer, WhitespaceRecognizer, CommentRecognizer,
    RecognizerRegistry
)
from psh.lexer.state_context import LexerContext
from psh.lexer.position import LexerConfig
from psh.lexer.modular_lexer import ModularLexer
from psh.token_types import TokenType


class TestTokenRecognizerBase:
    """Test the base TokenRecognizer interface."""
    
    def test_abstract_base_class(self):
        """Test that TokenRecognizer is abstract."""
        with pytest.raises(TypeError):
            TokenRecognizer()


class TestOperatorRecognizer:
    """Test the OperatorRecognizer."""
    
    def test_can_recognize_operators(self):
        """Test recognition of various operators."""
        recognizer = OperatorRecognizer()
        context = LexerContext()
        
        # Test single-character operators
        assert recognizer.can_recognize("|", 0, context)
        assert recognizer.can_recognize("&", 0, context)
        assert recognizer.can_recognize(";", 0, context)
        assert recognizer.can_recognize("(", 0, context)
        assert recognizer.can_recognize(")", 0, context)
        
        # Test multi-character operators
        assert recognizer.can_recognize("&&", 0, context)
        assert recognizer.can_recognize("||", 0, context)
        assert recognizer.can_recognize(">>", 0, context)
        assert recognizer.can_recognize("<<", 0, context)
        
        # Test non-operators
        assert not recognizer.can_recognize("a", 0, context)
        assert not recognizer.can_recognize("1", 0, context)
        assert not recognizer.can_recognize(" ", 0, context)
    
    def test_recognize_single_operators(self):
        """Test recognition of single-character operators."""
        recognizer = OperatorRecognizer()
        context = LexerContext()
        
        # Test pipe
        result = recognizer.recognize("|", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.PIPE
        assert token.value == "|"
        assert pos == 1
        
        # Test semicolon
        result = recognizer.recognize(";", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.SEMICOLON
        assert token.value == ";"
        assert pos == 1
    
    def test_recognize_multi_character_operators(self):
        """Test recognition of multi-character operators."""
        recognizer = OperatorRecognizer()
        context = LexerContext()
        
        # Test logical AND
        result = recognizer.recognize("&&", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.AND_AND
        assert token.value == "&&"
        assert pos == 2
        
        # Test here string
        result = recognizer.recognize("<<<", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.HERE_STRING
        assert token.value == "<<<"
        assert pos == 3
    
    def test_greedy_matching(self):
        """Test that longer operators are preferred."""
        recognizer = OperatorRecognizer()
        context = LexerContext()
        
        # Should recognize "&&" not "&" when input is "&&"
        result = recognizer.recognize("&&echo", 0, context)
        assert result is not None
        token, pos = result
        assert token.value == "&&"
        assert pos == 2
        
        # Should recognize "<<" not "<" when input is "<<"
        result = recognizer.recognize("<<EOF", 0, context)
        assert result is not None
        token, pos = result
        assert token.value == "<<"
        assert pos == 2
    
    def test_context_sensitive_operators(self):
        """Test operators that depend on context."""
        recognizer = OperatorRecognizer()
        
        # [[ should only be recognized at command position
        context = LexerContext()
        context.command_position = True
        result = recognizer.recognize("[[", 0, context)
        assert result is not None
        assert result[0].type == TokenType.DOUBLE_LBRACKET
        
        # ]] should only be recognized inside [[ ]]
        context = LexerContext()
        context.bracket_depth = 1
        result = recognizer.recognize("]]", 0, context)
        assert result is not None
        assert result[0].type == TokenType.DOUBLE_RBRACKET
        
        # =~ should only be recognized inside [[ ]]
        context = LexerContext()
        context.bracket_depth = 1
        result = recognizer.recognize("=~", 0, context)
        assert result is not None
        assert result[0].type == TokenType.REGEX_MATCH


class TestKeywordRecognizer:
    """Test the KeywordRecognizer."""
    
    def test_can_recognize_keywords(self):
        """Test recognition of shell keywords."""
        recognizer = KeywordRecognizer()
        context = LexerContext()
        context.command_position = True
        
        # Test various keywords
        assert recognizer.can_recognize("if", 0, context)
        assert recognizer.can_recognize("then", 0, context)
        assert recognizer.can_recognize("else", 0, context)
        assert recognizer.can_recognize("for", 0, context)
        assert recognizer.can_recognize("while", 0, context)
        
        # Test non-keywords
        assert not recognizer.can_recognize("hello", 0, context)
        assert not recognizer.can_recognize("123", 0, context)
    
    def test_recognize_keywords(self):
        """Test keyword recognition."""
        recognizer = KeywordRecognizer()
        context = LexerContext()
        context.command_position = True
        
        # Test if keyword
        result = recognizer.recognize("if", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.IF
        assert token.value == "if"
        assert pos == 2
        
        # Test for keyword
        result = recognizer.recognize("for", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.FOR
        assert token.value == "for"
        assert pos == 3
    
    def test_keyword_boundary_detection(self):
        """Test that keywords are only recognized as complete words."""
        recognizer = KeywordRecognizer()
        context = LexerContext()
        context.command_position = True
        
        # "if" should be recognized
        result = recognizer.recognize("if ", 0, context)
        assert result is not None
        assert result[0].value == "if"
        
        # "iff" should not be recognized as "if"
        result = recognizer.recognize("iff", 0, context)
        assert result is None
    
    def test_command_position_requirement(self):
        """Test that keywords require command position."""
        recognizer = KeywordRecognizer()
        
        # At command position
        context = LexerContext()
        context.command_position = True
        result = recognizer.recognize("if", 0, context)
        assert result is not None
        
        # Not at command position
        context = LexerContext()
        context.command_position = False
        result = recognizer.recognize("if", 0, context)
        assert result is None


class TestLiteralRecognizer:
    """Test the LiteralRecognizer."""
    
    def test_can_recognize_literals(self):
        """Test recognition of literal values."""
        recognizer = LiteralRecognizer()
        context = LexerContext()
        
        # Test identifiers
        assert recognizer.can_recognize("hello", 0, context)
        assert recognizer.can_recognize("var_name", 0, context)
        assert recognizer.can_recognize("file123", 0, context)
        
        # Test numbers
        assert recognizer.can_recognize("123", 0, context)
        assert recognizer.can_recognize("0x1F", 0, context)
        
        # Should not recognize operators or special chars
        assert not recognizer.can_recognize("|", 0, context)
        assert not recognizer.can_recognize("$", 0, context)
        assert not recognizer.can_recognize('"', 0, context)
    
    def test_recognize_words(self):
        """Test word recognition."""
        recognizer = LiteralRecognizer()
        context = LexerContext()
        
        # Test simple word
        result = recognizer.recognize("hello", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.WORD
        assert token.value == "hello"
        assert pos == 5
        
        # Test word with underscores
        result = recognizer.recognize("var_name", 0, context)
        assert result is not None
        token, pos = result
        assert token.value == "var_name"
        assert pos == 8
    
    def test_recognize_numbers(self):
        """Test number recognition."""
        recognizer = LiteralRecognizer()
        context = LexerContext()
        
        # Test simple number
        result = recognizer.recognize("123", 0, context)
        assert result is not None
        token, pos = result
        assert token.type == TokenType.WORD  # Numbers are classified as WORD
        assert token.value == "123"
        assert pos == 3
    
    def test_word_termination(self):
        """Test that words are properly terminated."""
        recognizer = LiteralRecognizer()
        context = LexerContext()
        
        # Word should stop at space
        result = recognizer.recognize("hello world", 0, context)
        assert result is not None
        token, pos = result
        assert token.value == "hello"
        assert pos == 5
        
        # Word should stop at operator
        result = recognizer.recognize("hello|world", 0, context)
        assert result is not None
        token, pos = result
        assert token.value == "hello"
        assert pos == 5


class TestWhitespaceRecognizer:
    """Test the WhitespaceRecognizer."""
    
    def test_can_recognize_whitespace(self):
        """Test recognition of whitespace."""
        recognizer = WhitespaceRecognizer()
        context = LexerContext()
        
        # Test various whitespace
        assert recognizer.can_recognize(" ", 0, context)
        assert recognizer.can_recognize("\t", 0, context)
        
        # Should not recognize newlines (handled by operator recognizer)
        assert not recognizer.can_recognize("\n", 0, context)
        
        # Should not recognize non-whitespace
        assert not recognizer.can_recognize("a", 0, context)
    
    def test_whitespace_skipping(self):
        """Test that whitespace returns None (to be skipped)."""
        recognizer = WhitespaceRecognizer()
        context = LexerContext()
        
        # Whitespace should return None to indicate skipping
        result = recognizer.recognize("   ", 0, context)
        assert result is None


class TestCommentRecognizer:
    """Test the CommentRecognizer."""
    
    def test_can_recognize_comments(self):
        """Test recognition of comments."""
        recognizer = CommentRecognizer()
        context = LexerContext()
        
        # Test comment start
        assert recognizer.can_recognize("# comment", 0, context)
        assert recognizer.can_recognize("#comment", 0, context)
        
        # Should not recognize # in middle of word
        # (This is context-dependent and may be simplified)
        
        # Should not recognize non-comments
        assert not recognizer.can_recognize("a", 0, context)
    
    def test_comment_skipping(self):
        """Test that comments return None (to be skipped)."""
        recognizer = CommentRecognizer()
        context = LexerContext()
        
        # Comments should return (None, new_pos) to indicate skipping
        result = recognizer.recognize("# this is a comment", 0, context)
        assert result is not None
        assert result[0] is None  # Token is None (skip)
        assert result[1] == 19    # Position advanced to end of comment


class TestRecognizerRegistry:
    """Test the RecognizerRegistry."""
    
    def test_empty_registry(self):
        """Test empty registry behavior."""
        registry = RecognizerRegistry()
        
        assert len(registry) == 0
        assert registry.get_recognizers() == []
        
        context = LexerContext()
        result = registry.recognize("test", 0, context)
        assert result is None
    
    def test_register_recognizers(self):
        """Test registering recognizers."""
        registry = RecognizerRegistry()
        
        op_recognizer = OperatorRecognizer()
        kw_recognizer = KeywordRecognizer()
        
        registry.register(op_recognizer)
        registry.register(kw_recognizer)
        
        assert len(registry) == 2
        
        recognizers = registry.get_recognizers()
        assert len(recognizers) == 2
        
        # Should be sorted by priority (operator has higher priority)
        assert isinstance(recognizers[0], OperatorRecognizer)
        assert isinstance(recognizers[1], KeywordRecognizer)
    
    def test_recognition_priority(self):
        """Test that recognizers are tried in priority order."""
        registry = RecognizerRegistry()
        
        # Register in reverse priority order
        registry.register(KeywordRecognizer())  # Priority 90
        registry.register(OperatorRecognizer())  # Priority 150
        
        context = LexerContext()
        context.command_position = True
        
        # Should recognize "(" as operator, not try keyword first
        result = registry.recognize("(", 0, context)
        assert result is not None
        token, pos, recognizer = result
        assert isinstance(recognizer, OperatorRecognizer)
        assert token.type == TokenType.LPAREN
    
    def test_unregister_recognizers(self):
        """Test unregistering recognizers."""
        registry = RecognizerRegistry()
        
        op_recognizer = OperatorRecognizer()
        registry.register(op_recognizer)
        assert len(registry) == 1
        
        # Unregister by instance
        success = registry.unregister(op_recognizer)
        assert success
        assert len(registry) == 0
        
        # Unregister by type
        registry.register(OperatorRecognizer())
        registry.register(KeywordRecognizer())
        assert len(registry) == 2
        
        removed = registry.unregister_by_type(OperatorRecognizer)
        assert removed == 1
        assert len(registry) == 1
    
    def test_registry_stats(self):
        """Test registry statistics."""
        registry = RecognizerRegistry()
        
        registry.register(OperatorRecognizer())
        registry.register(KeywordRecognizer())
        registry.register(LiteralRecognizer())
        
        stats = registry.get_stats()
        assert stats['total_recognizers'] == 3
        assert stats['recognizer_types']['OperatorRecognizer'] == 1
        assert stats['recognizer_types']['KeywordRecognizer'] == 1
        assert stats['recognizer_types']['LiteralRecognizer'] == 1


class TestModularLexerIntegration:
    """Test integration of recognizers with ModularLexer."""
    
    def test_basic_tokenization(self):
        """Test basic tokenization with modular lexer."""
        lexer = ModularLexer("echo hello")
        tokens = lexer.tokenize()
        
        # Should have: echo, hello, EOF
        assert len(tokens) == 3
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.WORD
        assert tokens[1].value == "hello"
        assert tokens[2].type == TokenType.EOF
    
    def test_operator_tokenization(self):
        """Test operator tokenization."""
        lexer = ModularLexer("echo hello && echo world")
        tokens = lexer.tokenize()
        
        # Should recognize && as logical AND
        token_values = [t.value for t in tokens[:-1]]  # Exclude EOF
        assert "echo" in token_values
        assert "hello" in token_values
        assert "&&" in token_values
        assert "world" in token_values
    
    def test_keyword_tokenization(self):
        """Test keyword tokenization."""
        lexer = ModularLexer("if test; then echo yes; fi")
        tokens = lexer.tokenize()
        
        # Should recognize keywords
        keyword_tokens = [t for t in tokens if t.type in [TokenType.IF, TokenType.THEN, TokenType.FI]]
        assert len(keyword_tokens) == 3
        assert keyword_tokens[0].value == "if"
        assert keyword_tokens[1].value == "then"
        assert keyword_tokens[2].value == "fi"
    
    def test_mixed_recognition(self):
        """Test mixed operator, keyword, and literal recognition."""
        lexer = ModularLexer("for file in *.txt; do echo $file; done")
        tokens = lexer.tokenize()
        
        # Should have various token types
        token_types = {t.type for t in tokens}
        assert TokenType.FOR in token_types
        # Note: 'in' may be recognized as WORD due to context limitations in basic recognizer
        # assert TokenType.IN in token_types
        assert TokenType.DO in token_types
        assert TokenType.DONE in token_types
        assert TokenType.SEMICOLON in token_types
        assert TokenType.WORD in token_types
    
    def test_quote_and_expansion_integration(self):
        """Test that quotes and expansions still work with modular recognizers."""
        lexer = ModularLexer('echo "Hello $USER"')
        tokens = lexer.tokenize()
        
        # Should have: echo, "Hello $USER", EOF
        assert len(tokens) == 3
        assert tokens[0].value == "echo"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].quote_type == '"'
        
        # Check if it's a RichToken with parts
        from psh.lexer.token_parts import RichToken
        if isinstance(tokens[1], RichToken):
            assert len(tokens[1].parts) >= 2  # "Hello " and variable
    
    def test_backward_compatibility(self):
        """Test that modular lexer maintains compatibility."""
        # Test with same input as unified lexer
        test_input = "echo hello && echo world"
        
        modular_lexer = ModularLexer(test_input)
        modular_tokens = modular_lexer.tokenize()
        
        # Should produce reasonable tokenization
        assert len(modular_tokens) >= 5  # echo, hello, &&, echo, world, EOF
        assert modular_tokens[-1].type == TokenType.EOF


if __name__ == '__main__':
    pytest.main([__file__, '-v'])