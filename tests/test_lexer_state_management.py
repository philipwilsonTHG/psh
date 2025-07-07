"""Tests for the new lexer state management system."""

import pytest
from psh.lexer.state_context import LexerContext
from psh.lexer.transitions import StateTransition, TransitionTable, StateManager
from psh.lexer.position import LexerState, LexerConfig
from psh.lexer.enhanced_core import EnhancedStateMachineLexer
from psh.token_types import TokenType


class TestLexerContext:
    """Test the unified LexerContext class."""
    
    def test_initial_state(self):
        """Test that context starts in correct initial state."""
        context = LexerContext()
        assert context.state == LexerState.NORMAL
        assert context.bracket_depth == 0
        assert context.paren_depth == 0
        assert context.command_position is True
        assert context.after_regex_match is False
        assert context.quote_stack == []
        assert context.heredoc_delimiters == []
    
    def test_quote_management(self):
        """Test quote stack management."""
        context = LexerContext()
        
        # Not in quotes initially
        assert not context.in_quotes()
        assert context.current_quote_type() is None
        
        # Push quotes
        context.push_quote('"')
        assert context.in_quotes()
        assert context.current_quote_type() == '"'
        
        # Nested quotes
        context.push_quote("'")
        assert context.current_quote_type() == "'"
        
        # Pop quotes
        assert context.pop_quote() == "'"
        assert context.current_quote_type() == '"'
        
        assert context.pop_quote() == '"'
        assert not context.in_quotes()
    
    def test_bracket_management(self):
        """Test double bracket management."""
        context = LexerContext()
        
        assert not context.in_double_brackets()
        
        context.enter_double_brackets()
        assert context.in_double_brackets()
        assert context.bracket_depth == 1
        
        context.enter_double_brackets()
        assert context.bracket_depth == 2
        
        context.exit_double_brackets()
        assert context.bracket_depth == 1
        assert context.in_double_brackets()
        
        context.exit_double_brackets()
        assert not context.in_double_brackets()
    
    def test_nesting_detection(self):
        """Test nested structure detection."""
        context = LexerContext()
        
        assert not context.is_in_nested_structure()
        
        context.push_quote('"')
        assert context.is_in_nested_structure()
        
        context.enter_double_brackets()
        assert context.is_in_nested_structure()
        
        context.pop_quote()
        assert context.is_in_nested_structure()  # Still in brackets
        
        context.exit_double_brackets()
        assert not context.is_in_nested_structure()
    
    def test_context_copy(self):
        """Test deep copying of context."""
        context = LexerContext()
        context.push_quote('"')
        context.enter_double_brackets()
        context.command_position = False
        
        copied = context.copy()
        
        # Verify copy is independent
        assert copied.quote_stack == ['"']
        assert copied.bracket_depth == 1
        assert copied.command_position is False
        
        # Modify original
        context.push_quote("'")
        context.enter_double_brackets()
        
        # Copy should be unchanged
        assert copied.quote_stack == ['"']
        assert copied.bracket_depth == 1
    
    def test_nesting_summary(self):
        """Test nesting summary information."""
        context = LexerContext()
        context.enter_double_brackets()
        context.enter_parentheses()
        context.push_quote('"')
        
        summary = context.get_nesting_summary()
        expected = {
            'brackets': 1,
            'parentheses': 1,
            'braces': 0,
            'arithmetic': 0,
            'quotes': 1
        }
        assert summary == expected


class TestStateTransitions:
    """Test the state transition framework."""
    
    def test_transition_creation(self):
        """Test creating state transitions."""
        condition = lambda ctx, char, pos: char == '"'
        action = lambda ctx, char, pos: ctx.push_quote('"')
        
        transition = StateTransition(
            from_state=LexerState.NORMAL,
            condition=condition,
            to_state=LexerState.IN_DOUBLE_QUOTE,
            action=action,
            priority=100
        )
        
        assert transition.from_state == LexerState.NORMAL
        assert transition.to_state == LexerState.IN_DOUBLE_QUOTE
        assert transition.priority == 100
    
    def test_transition_application(self):
        """Test applying transitions."""
        context = LexerContext()
        
        def quote_action(ctx, char, pos):
            ctx.push_quote(char)
        
        transition = StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: char == '"',
            to_state=LexerState.IN_DOUBLE_QUOTE,
            action=quote_action
        )
        
        # Should apply when conditions are met
        assert transition.can_apply(context, '"', 0)
        
        # Apply the transition
        transition.apply(context, '"', 0)
        
        assert context.state == LexerState.IN_DOUBLE_QUOTE
        assert context.current_quote_type() == '"'
        
        # Should not apply from wrong state
        assert not transition.can_apply(context, '"', 1)
    
    def test_transition_table(self):
        """Test transition table management."""
        table = TransitionTable()
        
        # Add transitions with different priorities
        high_priority = StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: char == '"',
            to_state=LexerState.IN_DOUBLE_QUOTE,
            priority=100
        )
        
        low_priority = StateTransition(
            from_state=LexerState.NORMAL,
            condition=lambda ctx, char, pos: True,  # Always matches
            to_state=LexerState.IN_WORD,
            priority=10
        )
        
        # Add in reverse priority order
        table.add_transition(low_priority)
        table.add_transition(high_priority)
        
        # Should get high priority transition first
        context = LexerContext()
        transition = table.get_applicable_transition(context, '"', 0)
        assert transition == high_priority
        
        # Low priority should be available for non-quote characters
        transition = table.get_applicable_transition(context, 'a', 0)
        assert transition == low_priority


class TestStateManager:
    """Test the high-level state manager."""
    
    def test_state_manager_initialization(self):
        """Test state manager initialization."""
        manager = StateManager()
        
        assert manager.context.state == LexerState.NORMAL
        assert isinstance(manager.transition_table, TransitionTable)
    
    def test_state_history_tracking(self):
        """Test state transition history."""
        manager = StateManager()
        
        # Simulate some transitions
        manager.context.state = LexerState.IN_WORD
        manager._state_history.append((LexerState.NORMAL, 0))
        manager._state_history.append((LexerState.IN_WORD, 5))
        
        history = manager.get_state_history()
        assert len(history) == 2
        assert history[0] == (LexerState.NORMAL, 0)
        assert history[1] == (LexerState.IN_WORD, 5)


class TestEnhancedLexer:
    """Test the enhanced lexer with unified state management."""
    
    def test_backward_compatibility(self):
        """Test that enhanced lexer maintains backward compatibility."""
        lexer = EnhancedStateMachineLexer('echo "hello"')
        
        # Test property access compatibility
        assert lexer.state == LexerState.NORMAL
        assert lexer.command_position is True
        assert lexer.in_double_brackets == 0
        assert lexer.after_regex_match is False
        
        # Test property setting
        lexer.command_position = False
        assert lexer.context.command_position is False
        
        lexer.after_regex_match = True
        assert lexer.context.after_regex_match is True
    
    def test_state_summary(self):
        """Test state summary functionality."""
        lexer = EnhancedStateMachineLexer('echo "hello"')
        
        # Initial state summary
        summary = lexer.get_state_summary()
        assert "state=NORMAL" in summary
        assert "cmd_pos" in summary
        
        # Change some state
        lexer.context.enter_double_brackets()
        lexer.context.push_quote('"')
        
        summary = lexer.get_state_summary()
        assert "brackets=1" in summary
        assert "quotes=" in summary and '"' in summary
    
    def test_nesting_info(self):
        """Test nesting information."""
        lexer = EnhancedStateMachineLexer('echo "hello"')
        
        info = lexer.get_nesting_info()
        assert all(v == 0 for v in info.values() if v != info['quotes'])
        
        lexer.context.enter_double_brackets()
        lexer.context.enter_parentheses()
        
        info = lexer.get_nesting_info()
        assert info['brackets'] == 1
        assert info['parentheses'] == 1
    
    def test_simple_tokenization(self):
        """Test that basic tokenization still works."""
        lexer = EnhancedStateMachineLexer('echo hello')
        tokens = lexer.tokenize()
        
        # Should get WORD, WORD, EOF tokens
        assert len(tokens) >= 3
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == 'echo'
        assert tokens[1].type == TokenType.WORD
        assert tokens[1].value == 'hello'
        assert tokens[-1].type == TokenType.EOF
    
    def test_quoted_string_tokenization(self):
        """Test tokenization with quotes."""
        lexer = EnhancedStateMachineLexer('echo "hello world"')
        tokens = lexer.tokenize()
        
        # Should handle quoted strings
        assert len(tokens) >= 3
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == 'echo'
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == 'hello world'
        assert tokens[-1].type == TokenType.EOF
    
    def test_context_updates_during_tokenization(self):
        """Test that context is properly updated during tokenization."""
        lexer = EnhancedStateMachineLexer('[[ $var == "test" ]]')
        
        # Track initial state
        assert lexer.command_position is True
        assert not lexer.context.in_double_brackets()
        
        # Tokenize - this should update context appropriately
        tokens = lexer.tokenize()
        
        # After tokenization, should be back to normal state
        assert lexer.state == LexerState.NORMAL
        
        # Should have found [[ and ]] tokens
        token_types = [t.type for t in tokens]
        assert TokenType.DOUBLE_LBRACKET in token_types
        assert TokenType.DOUBLE_RBRACKET in token_types


# Integration test - simplified for now
def test_enhanced_lexer_integration():
    """Integration test comparing enhanced lexer with original."""
    from psh.lexer.core import StateMachineLexer
    
    # Test just simple cases for now
    test_inputs = [
        'echo hello',
        'echo "hello world"'
    ]
    
    for input_str in test_inputs:
        # Compare outputs
        original_lexer = StateMachineLexer(input_str)
        enhanced_lexer = EnhancedStateMachineLexer(input_str)
        
        original_tokens = original_lexer.tokenize()
        enhanced_tokens = enhanced_lexer.tokenize()
        
        # Should produce same token types and values
        assert len(original_tokens) == len(enhanced_tokens)
        
        for orig, enhanced in zip(original_tokens, enhanced_tokens):
            assert orig.type == enhanced.type
            assert orig.value == enhanced.value