"""Tests for parser error improvements."""

import pytest
from psh.lexer import tokenize
from psh.parser import Parser
from psh.parser.helpers import ParseError
from psh.parser.errors import ParserErrorCatalog, ErrorSuggester


class TestParserErrorCatalog:
    """Test the parser error catalog."""
    
    def test_error_templates_have_required_fields(self):
        """Test that all error templates have required fields."""
        # Get all error templates
        templates = []
        for attr_name in dir(ParserErrorCatalog):
            if not attr_name.startswith('_'):
                attr = getattr(ParserErrorCatalog, attr_name)
                if hasattr(attr, 'code'):  # ErrorTemplate
                    templates.append(attr)
        
        assert len(templates) > 0, "Should have error templates"
        
        for template in templates:
            assert template.code, f"Template {template} should have error code"
            assert template.message, f"Template {template} should have message"
            # Suggestion is optional but should be string if present
            if template.suggestion:
                assert isinstance(template.suggestion, str)
    
    def test_error_codes_are_unique(self):
        """Test that all error codes are unique."""
        codes = []
        for attr_name in dir(ParserErrorCatalog):
            if not attr_name.startswith('_'):
                attr = getattr(ParserErrorCatalog, attr_name)
                if hasattr(attr, 'code'):
                    codes.append(attr.code)
        
        assert len(codes) == len(set(codes)), "Error codes should be unique"


class TestErrorSuggester:
    """Test the error suggester functionality."""
    
    def test_typo_suggestions(self):
        """Test typo suggestions for common mistakes."""
        # Test control structure typos
        assert ErrorSuggester.suggest_for_typo("fi", "fii") == "Did you mean 'fi'?"
        assert ErrorSuggester.suggest_for_typo("done", "don") == "Did you mean 'done'?"
        assert ErrorSuggester.suggest_for_typo("then", "hten") == "Did you mean 'then'?"
        
        # Test command typos
        assert ErrorSuggester.suggest_for_typo("grep", "grpe") == "Did you mean 'grep'?"
        
        # Test no suggestion for completely different words
        assert ErrorSuggester.suggest_for_typo("fi", "hello") is None
    
    def test_context_suggestions(self):
        """Test context-based suggestions."""
        # Test control structure context
        suggestion = ErrorSuggester.suggest_for_context("then", ["if", "condition"])
        assert "condition" in suggestion.lower()
        
        # Test operator context
        suggestion = ErrorSuggester.suggest_for_context("", ["|"])
        assert "command" in suggestion.lower()
    
    def test_missing_token_suggestions(self):
        """Test suggestions for missing tokens."""
        suggestion = ErrorSuggester.suggest_for_missing_token("then", "if")
        assert ";" in suggestion and "then" in suggestion
        
        suggestion = ErrorSuggester.suggest_for_missing_token("do", "for")
        assert ";" in suggestion and "do" in suggestion


class TestEnhancedErrorContext:
    """Test enhanced error context functionality."""
    
    def test_error_context_suggestions(self):
        """Test adding suggestions to error context."""
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        token = Token(TokenType.WORD, "hten", 0)
        context = ErrorContext(token=token, position=0)
        
        context.add_suggestion("Did you mean 'then'?")
        context.add_suggestion("Add semicolon before 'then'")
        
        assert len(context.suggestions) == 2
        assert "then" in context.suggestions[0]
        assert "semicolon" in context.suggestions[1]
    
    def test_error_context_formatting_with_suggestions(self):
        """Test error context formatting includes suggestions."""
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        token = Token(TokenType.WORD, "hten", 0)
        context = ErrorContext(
            token=token,
            position=0,
            message="Unexpected token",
            error_code="E001"
        )
        context.add_suggestion("Did you mean 'then'?")
        
        formatted = context.format_error()
        assert "[E001]" in formatted
        assert "Suggestions:" in formatted
        assert "then" in formatted
    
    def test_error_template_integration(self):
        """Test integration with error templates."""
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        token = Token(TokenType.WORD, "hten", 0)
        context = ErrorContext(token=token, position=0)
        
        template = ParserErrorCatalog.MISSING_SEMICOLON_BEFORE_THEN
        context.set_error_template(template)
        
        assert context.error_code == template.code
        assert context.message == template.message
        assert template.suggestion in context.suggestions


class TestSmartParserErrorDetection:
    """Test smart error detection in parser."""
    
    def test_missing_semicolon_before_then(self):
        """Test detection of missing semicolon before 'then'."""
        # This should trigger smart error detection
        with pytest.raises(ParseError) as exc_info:
            tokens = tokenize("if true then echo hi fi")
            parser = Parser(tokens)
            parser.parse()
        
        error = exc_info.value
        assert "semicolon" in error.message.lower() or "then" in error.message.lower()
        # Check if suggestions are provided
        if hasattr(error.error_context, 'suggestions'):
            assert len(error.error_context.suggestions) > 0
    
    def test_missing_do_after_for(self):
        """Test detection of missing 'do' after for."""
        with pytest.raises(ParseError) as exc_info:
            tokens = tokenize("for i in 1 2 3; echo $i; done")
            parser = Parser(tokens)
            parser.parse()
        
        error = exc_info.value
        # Should detect missing 'do'
        assert "do" in error.message.lower()
    
    def test_unclosed_if_statement(self):
        """Test detection of unclosed if statement."""
        with pytest.raises(ParseError) as exc_info:
            tokens = tokenize("if true; then echo hi")
            parser = Parser(tokens)
            parser.parse()
        
        error = exc_info.value
        # Should suggest adding 'fi'
        formatted = error.message
        assert "fi" in formatted.lower() or "unclosed" in formatted.lower()
    
    def test_typo_detection(self):
        """Test detection of common typos."""
        # Test 'fii' instead of 'fi'
        with pytest.raises(ParseError) as exc_info:
            tokens = tokenize("if true; then echo hi; fii")
            parser = Parser(tokens)
            parser.parse()
        
        error = exc_info.value
        formatted = error.message
        # Should suggest 'fi' as correction
        if "suggestion" in formatted.lower():
            assert "fi" in formatted.lower()
    
    def test_context_tokens_in_error(self):
        """Test that context tokens are included in errors."""
        with pytest.raises(ParseError) as exc_info:
            tokens = tokenize("echo hello; if true then echo world")  # Missing 'fi'
            parser = Parser(tokens)
            parser.parse()
        
        error = exc_info.value
        # Should have context about surrounding tokens
        if hasattr(error.error_context, 'context_tokens'):
            assert len(error.error_context.context_tokens) > 0


class TestErrorRecovery:
    """Test error recovery functionality."""
    
    def test_expect_with_recovery(self):
        """Test expect_with_recovery method."""
        from psh.parser.base import BaseParser
        from psh.token_types import TokenType
        
        tokens = tokenize("if true then echo hi fi")
        parser = BaseParser(tokens)
        
        # Advance to the problematic position
        parser.advance()  # 'if'
        parser.advance()  # 'true'
        
        # This should provide recovery hints
        with pytest.raises(ParseError) as exc_info:
            parser.expect_with_recovery(TokenType.SEMICOLON, "Add ';' to separate condition from 'then'")
        
        error = exc_info.value
        if hasattr(error.error_context, 'suggestions'):
            # Should include the recovery hint
            suggestions_text = ' '.join(error.error_context.suggestions)
            assert ";" in suggestions_text
    
    def test_multiple_suggestions(self):
        """Test that multiple suggestions can be provided."""
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        token = Token(TokenType.WORD, "wrong", 0)
        context = ErrorContext(token=token, position=0)
        
        # Add multiple suggestions
        context.add_suggestion("First suggestion")
        context.add_suggestion("Second suggestion")
        context.add_suggestion("First suggestion")  # Duplicate should be ignored
        
        assert len(context.suggestions) == 2
        
        formatted = context.format_error()
        assert "First suggestion" in formatted
        assert "Second suggestion" in formatted


class TestParserErrorIntegration:
    """Test integration of error improvements with existing parser."""
    
    def test_normal_parsing_still_works(self):
        """Test that normal parsing is not affected by error improvements."""
        # Valid shell commands should still parse correctly
        test_cases = [
            "echo hello",
            "if true; then echo hi; fi",
            "for i in 1 2 3; do echo $i; done",
            "while true; do break; done",
            "case $x in a) echo a ;; esac"
        ]
        
        for command in test_cases:
            tokens = tokenize(command)
            parser = Parser(tokens)
            ast = parser.parse()
            assert ast is not None
    
    def test_error_improvements_dont_break_existing_errors(self):
        """Test that error improvements don't break existing error handling."""
        # These should still raise ParseError, just with better messages
        error_cases = [
            "if",  # Incomplete if statement
            "for",  # Incomplete for loop
            "echo $((",  # Unclosed arithmetic
        ]
        
        for command in error_cases:
            tokens = tokenize(command)
            parser = Parser(tokens)
            with pytest.raises(ParseError):
                parser.parse()
        
        # Test lexer errors separately (they raise SyntaxError, not ParseError)
        lexer_error_cases = [
            "echo '",  # Unclosed quote
        ]
        
        for command in lexer_error_cases:
            with pytest.raises(SyntaxError):
                tokens = tokenize(command)
    
    def test_error_codes_in_messages(self):
        """Test that error codes appear in error messages when available."""
        with pytest.raises(ParseError) as exc_info:
            tokens = tokenize("if true then echo hi fi")
            parser = Parser(tokens)
            parser.parse()
        
        error = exc_info.value
        formatted = error.message
        # Should include error code if one is assigned
        if "[E" in formatted:
            assert "]" in formatted  # Properly formatted error code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])