"""Tests for enhanced ParseContext functionality."""

import pytest
from psh.parser.helpers import ParseContext
from psh.token_types import TokenType


class TestParseContext:
    """Test cases for ParseContext state management."""
    
    def test_initial_state(self):
        """Test that ParseContext starts with correct defaults."""
        context = ParseContext()
        
        assert context.in_test_expr is False
        assert context.in_arithmetic is False
        assert context.in_case_pattern is False
        assert context.in_function_body is False
        assert context.in_here_document is False
        assert context.in_command_substitution is False
        assert context.allow_keywords is True
        assert context.allow_empty_commands is False
        assert context.context_stack == []
        assert context.current_position == 0
        assert context.in_error_recovery is False
        assert context.error_sync_tokens == set()
    
    def test_context_stack_operations(self):
        """Test push/pop context operations."""
        context = ParseContext()
        
        # Test push
        context.push_context('regex_rhs')
        assert context.context_stack == ['regex_rhs']
        assert context.current_context == 'regex_rhs'
        assert context.in_context('regex_rhs') is True
        
        # Push another
        context.push_context('arithmetic')
        assert context.context_stack == ['regex_rhs', 'arithmetic']
        assert context.current_context == 'arithmetic'
        assert context.in_context('regex_rhs') is True
        assert context.in_context('arithmetic') is True
        
        # Pop
        popped = context.pop_context()
        assert popped == 'arithmetic'
        assert context.context_stack == ['regex_rhs']
        assert context.current_context == 'regex_rhs'
        
        # Pop last
        popped = context.pop_context()
        assert popped == 'regex_rhs'
        assert context.context_stack == []
        assert context.current_context is None
        
        # Pop from empty
        popped = context.pop_context()
        assert popped is None
    
    def test_context_manager_basic(self):
        """Test context manager saves and restores state."""
        context = ParseContext()
        
        # Set some initial state
        context.in_test_expr = True
        context.allow_keywords = False
        context.push_context('initial')
        
        # Use context manager
        with context:
            # Modify state
            context.in_test_expr = False
            context.in_arithmetic = True
            context.allow_keywords = True
            context.push_context('nested')
            
            # Check modified state
            assert context.in_test_expr is False
            assert context.in_arithmetic is True
            assert context.allow_keywords is True
            assert context.context_stack == ['initial', 'nested']
        
        # Check state restored
        assert context.in_test_expr is True
        assert context.in_arithmetic is False
        assert context.allow_keywords is False
        assert context.context_stack == ['initial']
    
    def test_context_manager_nested(self):
        """Test nested context managers."""
        context = ParseContext()
        
        with context:
            context.in_test_expr = True
            
            with context:
                context.in_test_expr = False
                context.in_arithmetic = True
                
                with context:
                    context.in_case_pattern = True
                    assert context.in_test_expr is False
                    assert context.in_arithmetic is True
                    assert context.in_case_pattern is True
                
                # After innermost context
                assert context.in_test_expr is False
                assert context.in_arithmetic is True
                assert context.in_case_pattern is False
            
            # After middle context
            assert context.in_test_expr is True
            assert context.in_arithmetic is False
            assert context.in_case_pattern is False
        
        # After outermost context
        assert context.in_test_expr is False
        assert context.in_arithmetic is False
        assert context.in_case_pattern is False
    
    def test_context_manager_with_exception(self):
        """Test context manager restores state even with exceptions."""
        context = ParseContext()
        context.in_test_expr = True
        
        try:
            with context:
                context.in_test_expr = False
                context.in_arithmetic = True
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # State should be restored despite exception
        assert context.in_test_expr is True
        assert context.in_arithmetic is False
    
    def test_error_recovery_state(self):
        """Test error recovery state management."""
        context = ParseContext()
        
        sync_tokens = {TokenType.SEMICOLON, TokenType.NEWLINE}
        
        with context:
            context.in_error_recovery = True
            context.error_sync_tokens = sync_tokens
            
            assert context.in_error_recovery is True
            assert context.error_sync_tokens == sync_tokens
        
        assert context.in_error_recovery is False
        assert context.error_sync_tokens == set()
    
    def test_all_flags_in_context_manager(self):
        """Test that all flags are properly saved/restored."""
        context = ParseContext()
        
        # Set all flags to non-default values
        context.in_test_expr = True
        context.in_arithmetic = True
        context.in_case_pattern = True
        context.in_function_body = True
        context.in_here_document = True
        context.in_command_substitution = True
        context.allow_keywords = False
        context.allow_empty_commands = True
        context.push_context('test1')
        context.push_context('test2')
        context.in_error_recovery = True
        context.error_sync_tokens = {TokenType.EOF}
        
        with context:
            # Reset all to defaults
            context.in_test_expr = False
            context.in_arithmetic = False
            context.in_case_pattern = False
            context.in_function_body = False
            context.in_here_document = False
            context.in_command_substitution = False
            context.allow_keywords = True
            context.allow_empty_commands = False
            context.context_stack = []
            context.in_error_recovery = False
            context.error_sync_tokens = set()
        
        # All should be restored
        assert context.in_test_expr is True
        assert context.in_arithmetic is True
        assert context.in_case_pattern is True
        assert context.in_function_body is True
        assert context.in_here_document is True
        assert context.in_command_substitution is True
        assert context.allow_keywords is False
        assert context.allow_empty_commands is True
        assert context.context_stack == ['test1', 'test2']
        assert context.in_error_recovery is True
        assert context.error_sync_tokens == {TokenType.EOF}