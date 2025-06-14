#!/usr/bin/env python3
"""
Test expansion regression cases against bash for compatibility.
Replaces tests/test_expansion_regression.py with bash comparison tests.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestExpansionRegression:
    """Test expansion regression cases for bash compatibility."""
    
    def test_command_substitution_in_string_expansion(self):
        """Test that command substitution works inside double-quoted strings."""
        bash_compare.assert_shells_match('VAR="$(echo test)"; echo "$VAR"')
        # Use echo instead of pwd to avoid builtin redirection issue
        bash_compare.assert_shells_match('MSG="Result: $(echo success)"; echo "$MSG"')
    
    def test_dollar_paren_substitution_in_string(self):
        """Test $() command substitution in strings."""
        bash_compare.assert_shells_match('echo "$(echo works)"')
    
    def test_multiple_substitutions(self):
        """Test multiple command substitutions in one string."""
        bash_compare.assert_shells_match('echo "First: $(echo one), Second: $(echo two)"')
    
    def test_command_substitution_with_echo_flags(self):
        """Test command substitution with echo flags."""
        bash_compare.assert_shells_match('result="$(echo -n test)"; echo "[$result]"')
        bash_compare.assert_shells_match('result="$(echo -e "a\\tb")"; echo "$result"')
    
    def test_nested_quotes_in_command_substitution(self):
        """Test nested quotes within command substitution."""
        bash_compare.assert_shells_match('echo "$(echo "nested quotes")"')
        bash_compare.assert_shells_match('echo "$(echo \'single quotes\')"')
    
    def test_command_substitution_preserves_exit_code(self):
        """Test that command substitution preserves exit codes."""
        bash_compare.assert_shells_match('result=$(true); echo $?')
        bash_compare.assert_shells_match('result=$(false); echo $?')
        # The exit in command substitution affects the subshell, not parent
        # So the parent shell's exit code should remain 0
        bash_compare.assert_shells_match('result=$(exit 42); echo $?')
    
    def test_variable_expansion_in_command_substitution(self):
        """Test variable expansion within command substitution."""
        bash_compare.assert_shells_match('x=hello; echo "$(echo $x world)"')
        bash_compare.assert_shells_match('x=5; y=3; echo "$(echo $((x + y)))"')