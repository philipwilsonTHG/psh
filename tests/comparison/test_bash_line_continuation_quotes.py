#!/usr/bin/env python3
"""
Test line continuation handling in quoted strings using bash comparison framework.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestLineContinuationInQuotes:
    """Test that escaped newlines work correctly in quoted strings."""
    
    def test_escaped_newline_in_double_quotes(self):
        """Test that \\<newline> in double quotes continues the line."""
        # Basic case
        bash_compare.assert_shells_match('echo "This is a very \\\nlong line that continues"')
        
        # Multiple continuations
        bash_compare.assert_shells_match('echo "Line 1\\\nLine 2\\\nLine 3"')
        
    def test_escaped_newline_with_variables(self):
        """Test line continuation with variable expansion."""
        bash_compare.assert_shells_match('name="world"; echo "Hello, \\\n$name!"')
        
    def test_escaped_newline_preserves_whitespace(self):
        """Test that whitespace before continuation is preserved."""
        bash_compare.assert_shells_match('echo "Before   \\\nAfter"')
        
    def test_single_quotes_preserve_backslash_newline(self):
        """Test that single quotes don't process line continuations."""
        # Single quotes preserve literal backslash-n
        bash_compare.assert_shells_match("echo 'hello\\nworld'")
        
    def test_mixed_quotes_and_continuations(self):
        """Test complex cases with mixed quotes and continuations."""
        # Continuation outside quotes
        bash_compare.assert_shells_match('echo one \\\ntwo')
        
        # Continuation in command substitution
        bash_compare.assert_shells_match('result=$(echo "test \\\nvalue"); echo "$result"')
        
    def test_line_continuation_in_assignments(self):
        """Test line continuation in variable assignments."""
        bash_compare.assert_shells_match('var="first \\\nsecond"; echo "$var"')
        
    def test_heredoc_line_continuation(self):
        """Test that line continuations work in echo commands (heredocs tested elsewhere)."""
        bash_compare.assert_shells_match('echo "Line one \\\ncontinued"')
        
    def test_line_continuation_edge_cases(self):
        """Test edge cases for line continuation."""
        # Triple backslash - last one escapes newline
        bash_compare.assert_shells_match('echo "Triple\\\\\\\nbackslash"')
        
        # Backslash at end
        bash_compare.assert_shells_match('echo "end\\\\"')
        
    def test_multiple_line_continuations(self):
        """Test multiple line continuations in various contexts."""
        # Multiple continuations in one string
        bash_compare.assert_shells_match('echo "a\\\nb\\\nc"')
        
        # Line continuation in variable assignment
        bash_compare.assert_shells_match('x="hello \\\nworld"; echo "$x"')
        
    def test_line_continuation_with_command_substitution(self):
        """Test line continuation inside command substitution."""
        bash_compare.assert_shells_match('echo "$(echo "nested \\\ncontinuation")"')
        
    def test_line_continuation_in_arithmetic(self):
        """Test line continuation in arithmetic expressions."""
        bash_compare.assert_shells_match('echo "$((1 + \\\n2 + 3))"')
        
    def test_continuation_after_pipe(self):
        """Test line continuation after pipe."""
        bash_compare.assert_shells_match('echo "test" | \\\ncat')
        
    def test_continuation_in_for_loop(self):
        """Test line continuation in for loop."""
        bash_compare.assert_shells_match('for x in one \\\ntwo three; do echo $x; done')


class TestLineContinuationEdgeCases:
    """Test edge cases that might behave differently."""
    
    @pytest.mark.xfail(reason="PSH doesn't handle double backslash + newline in quotes correctly")
    def test_double_backslash_newline(self):
        """Test double backslash followed by newline."""
        # This creates a literal backslash then a real newline
        # PSH currently treats this as unclosed quote
        bash_compare.assert_shells_match(r'echo "Double\\' + '\n' + 'backslash"')
        
    @pytest.mark.xfail(reason="PSH doesn't handle backslash + space + newline in quotes correctly")
    def test_space_after_backslash(self):
        """Test space after backslash (not a continuation)."""
        # PSH currently treats this as unclosed quote
        bash_compare.assert_shells_match(r'echo "Not a\ ' + '\n' + 'continuation"')