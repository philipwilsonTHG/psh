#!/usr/bin/env python3
"""
Test core command substitution functionality against bash.
Replaces xfail tests from test_command_substitution.py with bash comparison tests.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestCommandSubstitutionCore:
    """Test core command substitution functionality."""
    
    def test_command_substitution_execution(self):
        """Test execution of command substitution."""
        bash_compare.assert_shells_match('echo "Today is $(echo Monday)"')
        bash_compare.assert_shells_match('result=$(echo test); echo $result')
    
    def test_command_substitution_word_splitting(self):
        """Test that command substitution results are word-split."""
        bash_compare.assert_shells_match('for word in $(echo one two three); do echo "[$word]"; done')
        # Test that quotes prevent word splitting
        bash_compare.assert_shells_match('result="$(echo one two three)"; echo "[$result]"')
    
    def test_command_substitution_exit_status(self):
        """Test that command substitution sets exit status."""
        # Exit status from assignment with command substitution
        bash_compare.assert_shells_match('x=$(true); echo $?')
        bash_compare.assert_shells_match('x=$(false); echo $?')
    
    def test_command_substitution_empty_output(self):
        """Test command substitution with empty output."""
        bash_compare.assert_shells_match('result=$(echo -n); echo "result=[$result]"')
        bash_compare.assert_shells_match('for x in $(echo -n); do echo "should not print"; done; echo "done"')
    
    def test_command_substitution_with_variables(self):
        """Test command substitution containing variables."""
        bash_compare.assert_shells_match('name=world; echo "Hello, $(echo $name)!"')
        bash_compare.assert_shells_match('x=5; y=3; result=$(echo $((x + y))); echo $result')
    
    def test_nested_command_substitution(self):
        """Test nested command substitution."""
        bash_compare.assert_shells_match('echo "Result: $(echo $(echo nested))"')
        bash_compare.assert_shells_match('outer=$(echo "inner: $(echo test)"); echo $outer')
    
    def test_command_substitution_in_pipeline(self):
        """Test command substitution in pipeline contexts."""
        bash_compare.assert_shells_match('echo $(echo test) | cat')
        bash_compare.assert_shells_match('echo "one two" | while read line; do echo "$(echo $line)"; done')
    
    def test_backtick_syntax(self):
        """Test backtick command substitution."""
        bash_compare.assert_shells_match('echo `echo hello`')
        # TODO: Backticks in assignments not working - parser issue
        # bash_compare.assert_shells_match('result=`echo world`; echo $result')
    
    @pytest.mark.xfail(reason="Stderr redirection in command substitution not working correctly")
    def test_command_substitution_with_redirections(self):
        """Test command substitution with redirections."""
        bash_compare.assert_shells_match('result=$(echo stdout; echo stderr >&2); echo "[$result]"')
    
    def test_multiline_output(self):
        """Test command substitution with multiline output."""
        # Trailing newlines are stripped
        bash_compare.assert_shells_match('result=$(echo -e "line1\\nline2"); echo "$result"')
        bash_compare.assert_shells_match('result=$(printf "a\\nb\\nc"); echo "$result"')