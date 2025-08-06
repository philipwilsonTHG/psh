"""Tests for ParserContext centralized state management."""

import pytest
from unittest.mock import Mock

from psh.parser.recursive_descent.context import ParserContext, ParserProfiler, HeredocInfo
from psh.parser.recursive_descent.support.context_factory import ParserContextFactory
from psh.parser.recursive_descent.support.context_snapshots import ContextSnapshot, BacktrackingParser, SpeculativeParser
from psh.parser.config import ParserConfig, ParsingMode, ErrorHandlingMode
from psh.parser.recursive_descent.helpers import ParseError
from psh.token_types import Token, TokenType


class TestParserContext:
    """Test ParserContext functionality."""
    
    def test_context_creation(self):
        """Test basic context creation."""
        tokens = [
            Token(TokenType.WORD, "echo", 0),
            Token(TokenType.WORD, "hello", 5),
            Token(TokenType.EOF, "", 10)
        ]
        
        ctx = ParserContext(tokens=tokens)
        
        assert ctx.tokens == tokens
        assert ctx.current == 0
        assert isinstance(ctx.config, ParserConfig)
        assert ctx.errors == []
        assert not ctx.error_recovery_mode
        assert ctx.nesting_depth == 0
        assert ctx.scope_stack == []
    
    def test_token_access(self):
        """Test token access methods."""
        tokens = [
            Token(TokenType.WORD, "echo", 0),
            Token(TokenType.WORD, "hello", 5),
            Token(TokenType.EOF, "", 10)
        ]
        
        ctx = ParserContext(tokens=tokens)
        
        # Test peek
        assert ctx.peek() == tokens[0]
        assert ctx.peek(1) == tokens[1]
        assert ctx.peek(2) == tokens[2]
        assert ctx.peek(5) == tokens[2]  # Should return EOF for out of bounds
        
        # Test advance
        token = ctx.advance()
        assert token == tokens[0]
        assert ctx.current == 1
        
        # Test at_end
        assert not ctx.at_end()
        ctx.current = 2
        assert ctx.at_end()
        
        # Test match
        ctx.current = 0
        assert ctx.match(TokenType.WORD)
        assert not ctx.match(TokenType.SEMICOLON)
        assert ctx.match(TokenType.WORD, TokenType.SEMICOLON)
    
    def test_consume_success(self):
        """Test successful token consumption."""
        tokens = [
            Token(TokenType.WORD, "echo", 0),
            Token(TokenType.EOF, "", 5)
        ]
        
        ctx = ParserContext(tokens=tokens)
        
        token = ctx.consume(TokenType.WORD)
        assert token == tokens[0]
        assert ctx.current == 1
    
    def test_consume_error_strict(self):
        """Test consume error in strict mode."""
        tokens = [
            Token(TokenType.WORD, "echo", 0),
            Token(TokenType.EOF, "", 5)
        ]
        
        config = ParserConfig(collect_errors=False)
        ctx = ParserContext(tokens=tokens, config=config)
        
        with pytest.raises(ParseError):
            ctx.consume(TokenType.SEMICOLON)
    
    def test_consume_error_collect(self):
        """Test consume error in error collection mode."""
        tokens = [
            Token(TokenType.WORD, "echo", 0),
            Token(TokenType.EOF, "", 5)
        ]
        
        config = ParserConfig(collect_errors=True)
        ctx = ParserContext(tokens=tokens, config=config)
        
        # Should not raise, but add to errors
        token = ctx.consume(TokenType.SEMICOLON)
        assert token == tokens[0]  # Returns current token
        assert len(ctx.errors) == 1
        assert isinstance(ctx.errors[0], ParseError)
    
    def test_scope_management(self):
        """Test parsing scope management."""
        ctx = ParserContext(tokens=[])
        
        # Test entering scopes
        ctx.enter_scope("function")
        assert ctx.in_scope("function")
        assert ctx.function_depth == 1
        assert ctx.nesting_depth == 1
        
        ctx.enter_scope("loop")
        assert ctx.in_scope("loop")
        assert ctx.in_scope("function")
        assert ctx.loop_depth == 1
        assert ctx.nesting_depth == 2
        
        # Test current scope
        assert ctx.current_scope() == "loop"
        
        # Test exiting scopes
        scope = ctx.exit_scope()
        assert scope == "loop"
        assert not ctx.in_scope("loop")
        assert ctx.in_scope("function")
        assert ctx.loop_depth == 0
        assert ctx.nesting_depth == 1
        
        scope = ctx.exit_scope()
        assert scope == "function"
        assert not ctx.in_scope("function")
        assert ctx.function_depth == 0
        assert ctx.nesting_depth == 0
    
    def test_rule_tracking(self):
        """Test parse rule tracking."""
        config = ParserConfig(trace_parsing=True)
        ctx = ParserContext(tokens=[], config=config)
        
        # Test rule stack
        ctx.enter_rule("statement")
        assert ctx.current_rule() == "statement"
        assert ctx.rule_stack_depth() == 1
        
        ctx.enter_rule("command")
        assert ctx.current_rule() == "command"
        assert ctx.rule_stack_depth() == 2
        
        ctx.exit_rule("command")
        assert ctx.current_rule() == "statement"
        assert ctx.rule_stack_depth() == 1
        
        ctx.exit_rule("statement")
        assert ctx.current_rule() is None
        assert ctx.rule_stack_depth() == 0
    
    def test_state_queries(self):
        """Test context state query methods."""
        ctx = ParserContext(tokens=[])
        
        # Initially not in any special context
        assert not ctx.in_loop()
        assert not ctx.in_function()
        assert not ctx.in_conditional()
        
        # Enter loop context
        ctx.enter_scope("loop")
        assert ctx.in_loop()
        assert not ctx.in_function()
        assert not ctx.in_conditional()
        
        # Enter function context
        ctx.enter_scope("function")
        assert ctx.in_loop()
        assert ctx.in_function()
        assert not ctx.in_conditional()
        
        # Enter conditional context
        ctx.enter_scope("if")
        assert ctx.in_loop()
        assert ctx.in_function()
        assert ctx.in_conditional()
    
    def test_error_state_queries(self):
        """Test error-related state queries."""
        config = ParserConfig(
            collect_errors=True,
            enable_error_recovery=True,
            max_errors=5
        )
        # Add a token so we're not at end
        tokens = [Token(TokenType.WORD, "test", 0)]
        ctx = ParserContext(tokens=tokens, config=config)
        
        assert ctx.should_collect_errors()
        assert ctx.should_attempt_recovery()
        assert ctx.can_continue_parsing()
        
        # Add errors up to limit
        for i in range(4):  # Changed to 4 to stay under limit
            ctx.errors.append(Mock(spec=ParseError))
        
        # Should still be able to continue under limit
        assert ctx.can_continue_parsing()
        
        # Add one more error to reach limit
        ctx.errors.append(Mock(spec=ParseError))
        assert not ctx.can_continue_parsing()
    
    def test_heredoc_management(self):
        """Test heredoc tracking."""
        ctx = ParserContext(tokens=[])
        
        # Register a heredoc
        key = ctx.register_heredoc("EOF", strip_tabs=True, quoted=False)
        assert key in ctx.heredoc_trackers
        
        heredoc = ctx.heredoc_trackers[key]
        assert heredoc.delimiter == "EOF"
        assert heredoc.strip_tabs is True
        assert heredoc.quoted is False
        assert not heredoc.closed
        
        # Add content
        ctx.add_heredoc_line(key, "\tline 1")
        ctx.add_heredoc_line(key, "\tline 2")
        
        # Should strip tabs
        assert heredoc.content_lines == ["line 1", "line 2"]
        
        # Close heredoc
        content = ctx.close_heredoc(key)
        assert content == "line 1\nline 2\n"
        assert heredoc.closed
        
        # Test open heredocs list
        key2 = ctx.register_heredoc("END")
        open_heredocs = ctx.get_open_heredocs()
        assert key not in open_heredocs  # closed
        assert key2 in open_heredocs      # open
    
    def test_state_summary(self):
        """Test state summary generation."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        ctx = ParserContext(tokens=tokens)
        
        ctx.enter_scope("function")
        ctx.enter_scope("loop")
        ctx.enter_rule("statement")
        
        summary = ctx.get_state_summary()
        
        assert summary['position'] == 0
        assert summary['total_tokens'] == 1
        assert summary['nesting_depth'] == 2
        assert summary['scope_stack'] == ["function", "loop"]
        assert summary['parse_stack'] == ["statement"]
        assert summary['function_depth'] == 1
        assert summary['loop_depth'] == 1
        assert summary['error_count'] == 0
        assert summary['open_heredocs'] == 0
    
    def test_context_reset(self):
        """Test context state reset."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        ctx = ParserContext(tokens=tokens)
        
        # Modify state
        ctx.current = 1
        ctx.enter_scope("function")
        ctx.enter_rule("statement")
        ctx.errors.append(Mock(spec=ParseError))
        ctx.error_recovery_mode = True
        ctx.register_heredoc("EOF")
        
        # Reset
        ctx.reset_state()
        
        # Check everything is reset
        assert ctx.current == 0
        assert ctx.errors == []
        assert not ctx.error_recovery_mode
        assert ctx.nesting_depth == 0
        assert ctx.scope_stack == []
        assert ctx.parse_stack == []
        assert ctx.heredoc_trackers == {}
        assert ctx.function_depth == 0
        assert ctx.loop_depth == 0


class TestParserProfiler:
    """Test ParserProfiler functionality."""
    
    def test_profiler_disabled(self):
        """Test profiler when disabled."""
        config = ParserConfig(profile_parsing=False)
        profiler = ParserProfiler(config)
        
        assert not profiler.enabled
        
        # Operations should be no-ops
        profiler.enter_rule("test")
        profiler.exit_rule("test")
        profiler.record_token_consumption()
        profiler.record_backtrack()
        profiler.record_error_recovery()
        
        report = profiler.report()
        assert report == "Profiling disabled"
    
    def test_profiler_enabled(self):
        """Test profiler when enabled."""
        config = ParserConfig(profile_parsing=True)
        profiler = ParserProfiler(config)
        
        assert profiler.enabled
        
        # Start parsing
        profiler.start_parsing()
        
        # Record some operations
        profiler.enter_rule("statement")
        profiler.record_token_consumption()
        profiler.record_token_consumption()
        profiler.exit_rule("statement")
        
        profiler.record_backtrack()
        profiler.record_error_recovery()
        
        # End parsing
        profiler.end_parsing()
        
        # Check metrics
        assert profiler.token_consumption_count == 2
        assert profiler.backtrack_count == 1
        assert profiler.error_recovery_count == 1
        assert "statement" in profiler.rule_counts
        assert profiler.rule_counts["statement"] == 1
        assert profiler.get_total_parse_time() > 0
        
        # Test report generation
        report = profiler.report()
        assert "Parser Performance Report" in report
        assert "Total Parse Time" in report
        assert "Tokens Consumed: 2" in report
        assert "Backtrack Operations: 1" in report
        assert "Error Recoveries: 1" in report
        assert "statement" in report


class TestParserContextFactory:
    """Test ParserContextFactory functionality."""
    
    def test_create_basic(self):
        """Test basic context creation."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        
        ctx = ParserContextFactory.create(tokens)
        
        assert ctx.tokens == tokens
        assert isinstance(ctx.config, ParserConfig)
        assert ctx.source_text is None
    
    def test_create_with_config(self):
        """Test context creation with custom config."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        config = ParserConfig(parsing_mode=ParsingMode.STRICT_POSIX)
        
        ctx = ParserContextFactory.create(tokens, config)
        
        assert ctx.config.parsing_mode == ParsingMode.STRICT_POSIX
    
    def test_create_strict_posix(self):
        """Test strict POSIX context creation."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        
        ctx = ParserContextFactory.create_strict_posix(tokens)
        
        assert ctx.config.parsing_mode == ParsingMode.STRICT_POSIX
    
    def test_create_bash_compatible(self):
        """Test Bash-compatible context creation."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        
        ctx = ParserContextFactory.create_bash_compatible(tokens)
        
        assert ctx.config.parsing_mode == ParsingMode.BASH_COMPAT
    
    def test_create_permissive(self):
        """Test permissive context creation."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        
        ctx = ParserContextFactory.create_permissive(tokens)
        
        assert ctx.config.parsing_mode == ParsingMode.PERMISSIVE
        assert ctx.config.collect_errors
        assert ctx.config.enable_error_recovery
    
    def test_create_for_repl(self):
        """Test REPL context creation."""
        ctx = ParserContextFactory.create_for_repl()
        
        assert ctx.config.parsing_mode == ParsingMode.BASH_COMPAT
        assert ctx.config.error_handling == ErrorHandlingMode.COLLECT
        assert ctx.config.collect_errors
        assert ctx.config.interactive_parsing
    
    def test_create_sub_parser_context(self):
        """Test sub-parser context creation."""
        parent_tokens = [Token(TokenType.WORD, "parent", 0)]
        parent_ctx = ParserContext(tokens=parent_tokens)
        parent_ctx.function_depth = 1
        parent_ctx.nesting_depth = 2
        
        sub_tokens = [Token(TokenType.WORD, "sub", 0)]
        sub_ctx = ParserContextFactory.create_sub_parser_context(
            parent_ctx, sub_tokens, inherit_state=True
        )
        
        assert sub_ctx.tokens == sub_tokens
        assert sub_ctx.config == parent_ctx.config
        assert sub_ctx.function_depth == 1  # inherited
        assert sub_ctx.nesting_depth == 3   # incremented
        assert sub_ctx.in_command_substitution


class TestContextSnapshot:
    """Test ContextSnapshot functionality."""
    
    def test_snapshot_capture_restore(self):
        """Test capturing and restoring context snapshots."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        ctx = ParserContext(tokens=tokens)
        
        # Modify context state
        ctx.current = 1
        ctx.enter_scope("function")
        ctx.nesting_depth = 5
        ctx.in_arithmetic = True
        
        # Capture snapshot
        snapshot = ContextSnapshot.capture(ctx)
        
        # Modify state further
        ctx.current = 2
        ctx.enter_scope("loop")
        ctx.in_arithmetic = False
        
        # Restore snapshot
        snapshot.restore(ctx)
        
        # Check state is restored
        assert ctx.current == 1
        assert ctx.scope_stack == ["function"]
        assert ctx.nesting_depth == 5
        assert ctx.in_arithmetic is True


class TestBacktrackingParser:
    """Test BacktrackingParser functionality."""
    
    def test_try_parse_success(self):
        """Test successful try_parse."""
        tokens = [Token(TokenType.WORD, "test", 0), Token(TokenType.EOF, "", 4)]
        ctx = ParserContext(tokens=tokens)
        parser = BacktrackingParser(ctx)
        
        def successful_parse():
            ctx.advance()
            return "success"
        
        result = parser.try_parse(successful_parse)
        assert result == "success"
        assert ctx.current == 1
    
    def test_try_parse_failure(self):
        """Test failed try_parse with backtracking."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        ctx = ParserContext(tokens=tokens)
        parser = BacktrackingParser(ctx)
        
        original_position = ctx.current
        
        def failing_parse():
            ctx.advance()
            raise ValueError("Parse failed")
        
        result = parser.try_parse(failing_parse)
        assert result is None
        assert ctx.current == original_position  # Backtracked
    
    def test_try_alternatives(self):
        """Test trying multiple parsing alternatives."""
        tokens = [Token(TokenType.WORD, "test", 0)]
        ctx = ParserContext(tokens=tokens)
        parser = BacktrackingParser(ctx)
        
        def failing_parse():
            raise ValueError("Failed")
        
        def successful_parse():
            return "success"
        
        result = parser.try_alternatives(failing_parse, successful_parse)
        assert result == "success"


class TestSpeculativeParser:
    """Test SpeculativeParser functionality."""
    
    def test_speculation_context_manager(self):
        """Test speculative parsing with context manager."""
        tokens = [Token(TokenType.WORD, "test", 0), Token(TokenType.WORD, "test2", 5), Token(TokenType.EOF, "", 10)]
        ctx = ParserContext(tokens=tokens)
        parser = SpeculativeParser(ctx)
        
        # Successful speculation
        with parser.speculate(lambda: ctx.advance()) as spec:
            result = spec.execute()
            assert ctx.current == 1
        
        # Should commit changes
        assert ctx.current == 1
        
        # Failed speculation
        try:
            with parser.speculate(lambda: None) as spec:
                ctx.advance()
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should rollback changes
        assert ctx.current == 1  # Back to position after first speculation
    
    def test_explicit_commit_rollback(self):
        """Test explicit commit and rollback operations."""
        tokens = [Token(TokenType.WORD, "test", 0), Token(TokenType.WORD, "test2", 5), Token(TokenType.EOF, "", 10)]
        ctx = ParserContext(tokens=tokens)
        parser = SpeculativeParser(ctx)
        
        snapshot_id = parser.enter_speculation()
        ctx.advance()
        
        # Test explicit commit
        parser.exit_speculation(snapshot_id, commit=True)
        assert ctx.current == 1
        
        # Test explicit rollback
        snapshot_id = parser.enter_speculation()
        original_position = ctx.current
        ctx.advance()
        parser.exit_speculation(snapshot_id, commit=False)
        assert ctx.current == original_position