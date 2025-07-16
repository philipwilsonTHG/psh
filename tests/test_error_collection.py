"""Tests for multi-error collection functionality."""

import pytest
from psh.lexer import tokenize
from psh.parser.main import Parser
from psh.parser.helpers import ParseError
from psh.parser.error_collector import ErrorCollector, MultiErrorParseResult, ErrorRecoveryStrategy, RecoveryPoints
from psh.token_types import TokenType


class TestErrorCollector:
    """Test the ErrorCollector class."""
    
    def test_error_collector_initialization(self):
        """Test ErrorCollector initialization."""
        collector = ErrorCollector()
        assert collector.max_errors == 10
        assert collector.stop_on_fatal == True
        assert len(collector.errors) == 0
        assert collector.fatal_error is None
    
    def test_error_collector_custom_settings(self):
        """Test ErrorCollector with custom settings."""
        collector = ErrorCollector(max_errors=5, stop_on_fatal=False)
        assert collector.max_errors == 5
        assert collector.stop_on_fatal == False
    
    def test_add_error(self):
        """Test adding errors to collector."""
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        collector = ErrorCollector()
        
        token = Token(TokenType.WORD, "test", 0)
        context = ErrorContext(token=token, message="Test error", position=0)
        error = ParseError(context)
        
        collector.add_error(error)
        assert len(collector.errors) == 1
        assert collector.errors[0] == error
    
    def test_should_continue_normal(self):
        """Test should_continue under normal conditions."""
        collector = ErrorCollector()
        assert collector.should_continue() == True
        
        # Add some errors
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        for i in range(5):
            token = Token(TokenType.WORD, f"test{i}", i)
            context = ErrorContext(token=token, message=f"Error {i}", position=i)
            error = ParseError(context)
            collector.add_error(error)
        
        assert collector.should_continue() == True
    
    def test_should_continue_max_errors(self):
        """Test should_continue when max errors reached."""
        collector = ErrorCollector(max_errors=3)
        
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        # Add max errors
        for i in range(3):
            token = Token(TokenType.WORD, f"test{i}", i)
            context = ErrorContext(token=token, message=f"Error {i}", position=i)
            error = ParseError(context)
            collector.add_error(error)
        
        assert collector.should_continue() == False
    
    def test_should_continue_fatal_error(self):
        """Test should_continue with fatal error."""
        collector = ErrorCollector()
        
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        token = Token(TokenType.WORD, "test", 0)
        context = ErrorContext(token=token, message="Fatal error", position=0, severity="fatal")
        error = ParseError(context)
        
        collector.add_error(error)
        assert collector.should_continue() == False
    
    def test_format_error_summary(self):
        """Test error summary formatting."""
        collector = ErrorCollector()
        
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        # Add a couple of errors
        token1 = Token(TokenType.WORD, "test1", 0)
        context1 = ErrorContext(token=token1, message="First error", position=0)
        context1.add_suggestion("Fix the first error")
        error1 = ParseError(context1)
        
        token2 = Token(TokenType.WORD, "test2", 10)
        context2 = ErrorContext(token=token2, message="Second error", position=10)
        error2 = ParseError(context2)
        
        collector.add_error(error1)
        collector.add_error(error2)
        
        summary = collector.format_error_summary()
        assert "Collected 2 parse error(s)" in summary
        assert "First error" in summary
        assert "Second error" in summary
        assert "Fix the first error" in summary
    
    def test_get_errors_by_severity(self):
        """Test filtering errors by severity."""
        collector = ErrorCollector()
        
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        # Add errors with different severities
        token1 = Token(TokenType.WORD, "test1", 0)
        context1 = ErrorContext(token=token1, message="Warning", position=0, severity="warning")
        error1 = ParseError(context1)
        
        token2 = Token(TokenType.WORD, "test2", 10)
        context2 = ErrorContext(token=token2, message="Error", position=10, severity="error")
        error2 = ParseError(context2)
        
        collector.add_error(error1)
        collector.add_error(error2)
        
        warnings = collector.get_errors_by_severity("warning")
        errors = collector.get_errors_by_severity("error")
        
        assert len(warnings) == 1
        assert len(errors) == 1
        assert warnings[0] == error1
        assert errors[0] == error2


class TestRecoveryPoints:
    """Test recovery point definitions."""
    
    def test_recovery_points_initialization(self):
        """Test RecoveryPoints initialization."""
        points = RecoveryPoints()
        
        assert TokenType.IF in points.STATEMENT_START
        assert TokenType.SEMICOLON in points.STATEMENT_END
        assert TokenType.FI in points.BLOCK_END
        assert len(points.ALL_SYNC) > 0
    
    def test_all_sync_contains_all_points(self):
        """Test that ALL_SYNC contains all recovery points."""
        points = RecoveryPoints()
        
        # Check that ALL_SYNC contains items from each category
        assert any(token in points.ALL_SYNC for token in points.STATEMENT_START)
        assert any(token in points.ALL_SYNC for token in points.STATEMENT_END)
        assert any(token in points.ALL_SYNC for token in points.BLOCK_END)


class TestErrorRecoveryStrategy:
    """Test error recovery strategies."""
    
    def test_skip_to_sync_token(self):
        """Test skipping to synchronization token."""
        tokens = tokenize("if true; then echo hello; fi")
        
        # Create a mock parser-like object
        class MockParser:
            def __init__(self, tokens):
                self.tokens = tokens
                self.current = 0
            
            def at_end(self):
                return self.current >= len(self.tokens) - 1
            
            def advance(self):
                if self.current < len(self.tokens) - 1:
                    self.current += 1
            
            def match_any(self, token_types):
                if self.current < len(self.tokens):
                    return self.tokens[self.current].type in token_types
                return False
        
        parser = MockParser(tokens)
        parser.current = 1  # Start at 'true'
        
        # Skip to 'then'
        from psh.token_types import TokenType
        result = ErrorRecoveryStrategy.skip_to_sync_token(parser, {TokenType.THEN})
        
        assert result == True
        assert parser.tokens[parser.current].type == TokenType.THEN
    
    def test_skip_to_sync_token_not_found(self):
        """Test skipping when sync token not found."""
        tokens = tokenize("echo hello world")
        
        class MockParser:
            def __init__(self, tokens):
                self.tokens = tokens
                self.current = 0
            
            def at_end(self):
                return self.current >= len(self.tokens) - 1
            
            def advance(self):
                if self.current < len(self.tokens) - 1:
                    self.current += 1
            
            def match_any(self, token_types):
                if self.current < len(self.tokens):
                    return self.tokens[self.current].type in token_types
                return False
        
        parser = MockParser(tokens)
        
        # Try to skip to 'fi' (not present)
        from psh.token_types import TokenType
        result = ErrorRecoveryStrategy.skip_to_sync_token(parser, {TokenType.FI})
        
        assert result == False  # EOF reached without finding sync token


class TestMultiErrorParseResult:
    """Test MultiErrorParseResult class."""
    
    def test_successful_parse_result(self):
        """Test result for successful parse."""
        from psh.ast_nodes import CommandList
        
        ast = CommandList()
        result = MultiErrorParseResult(ast, [])
        
        assert result.success == True
        assert result.partial_success == False
        assert result.has_errors() == False
        assert result.get_error_count() == 0
    
    def test_partial_success_result(self):
        """Test result for partial success with errors."""
        from psh.ast_nodes import CommandList
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        ast = CommandList()
        token = Token(TokenType.WORD, "test", 0)
        context = ErrorContext(token=token, message="Test error", position=0)
        error = ParseError(context)
        
        result = MultiErrorParseResult(ast, [error])
        
        assert result.success == False
        assert result.partial_success == True
        assert result.has_errors() == True
        assert result.get_error_count() == 1
    
    def test_failed_parse_result(self):
        """Test result for failed parse."""
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        token = Token(TokenType.WORD, "test", 0)
        context = ErrorContext(token=token, message="Test error", position=0)
        error = ParseError(context)
        
        result = MultiErrorParseResult(None, [error])
        
        assert result.success == False
        assert result.partial_success == False
        assert result.has_errors() == True
        assert result.get_error_count() == 1
    
    def test_format_errors(self):
        """Test error formatting."""
        from psh.parser.helpers import ErrorContext
        from psh.token_types import Token, TokenType
        
        token1 = Token(TokenType.WORD, "test1", 0)
        context1 = ErrorContext(token=token1, message="First error", position=0)
        error1 = ParseError(context1)
        
        token2 = Token(TokenType.WORD, "test2", 10)
        context2 = ErrorContext(token=token2, message="Second error", position=10)
        error2 = ParseError(context2)
        
        result = MultiErrorParseResult(None, [error1, error2])
        formatted = result.format_errors()
        
        assert "Error 1: First error" in formatted
        assert "Error 2: Second error" in formatted


class TestParserWithErrorCollection:
    """Test Parser class with error collection enabled."""
    
    def test_parser_with_error_collection_enabled(self):
        """Test parser with error collection enabled."""
        tokens = tokenize("echo hello")
        parser = Parser(tokens, collect_errors=True)
        
        assert parser.error_collector is not None
        assert isinstance(parser.error_collector, ErrorCollector)
    
    def test_parser_without_error_collection(self):
        """Test parser without error collection."""
        tokens = tokenize("echo hello")
        parser = Parser(tokens, collect_errors=False)
        
        assert parser.error_collector is None
    
    def test_parse_with_error_collection_success(self):
        """Test successful parsing with error collection."""
        tokens = tokenize("echo hello")
        parser = Parser(tokens, collect_errors=True)
        
        result = parser.parse_with_error_collection()
        
        assert result.success == True
        assert result.get_error_count() == 0
        assert result.ast is not None
    
    def test_parse_with_error_collection_single_error(self):
        """Test parsing with single error."""
        # This command has a syntax error (incomplete if)
        tokens = tokenize("if true")
        parser = Parser(tokens, collect_errors=True)
        
        result = parser.parse_with_error_collection()
        
        assert result.success == False
        assert result.get_error_count() >= 1
        # AST might be partial or None depending on where error occurs
    
    def test_parse_with_error_collection_enables_collector(self):
        """Test that parse_with_error_collection enables collector if not present."""
        tokens = tokenize("echo hello")
        parser = Parser(tokens, collect_errors=False)  # Start without collector
        
        assert parser.error_collector is None
        
        result = parser.parse_with_error_collection()
        
        # Should have enabled collector
        assert parser.error_collector is not None
        assert result.success == True


class TestErrorCollectionIntegration:
    """Test integration of error collection with existing parser."""
    
    def test_normal_parsing_unaffected(self):
        """Test that normal parsing is unaffected by error collection features."""
        test_cases = [
            "echo hello",
            "if true; then echo hi; fi",
            "for i in 1 2 3; do echo $i; done",
        ]
        
        for command in test_cases:
            tokens = tokenize(command)
            
            # Parse normally
            parser1 = Parser(tokens)
            ast1 = parser1.parse()
            
            # Parse with error collection disabled
            parser2 = Parser(tokens, collect_errors=False)
            ast2 = parser2.parse()
            
            # Results should be the same type
            assert type(ast1) == type(ast2)
    
    def test_error_collection_preserves_error_quality(self):
        """Test that error collection doesn't degrade error quality."""
        # Use a command that will definitely cause a parse error
        command = "if"  # Incomplete if statement
        
        tokens1 = tokenize(command)
        parser1 = Parser(tokens1)
        
        tokens2 = tokenize(command)
        parser2 = Parser(tokens2, collect_errors=True)
        
        # Normal parsing should raise ParseError
        with pytest.raises(ParseError) as exc1:
            parser1.parse()
        
        # Error collection should capture the same error
        result = parser2.parse_with_error_collection()
        
        assert result.get_error_count() >= 1
        # The error message should be similar quality
        normal_error = str(exc1.value)
        collected_error = result.format_errors()
        
        # Both should mention the fundamental issue
        assert len(normal_error) > 10  # Non-trivial error message
        assert len(collected_error) > 10  # Non-trivial error message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])