#!/usr/bin/env python3
"""
Test command substitution against bash for compatibility.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestCommandSubstitution:
    """Test command substitution compatibility with bash."""
    
    def test_basic_command_substitution(self):
        """Test basic command substitution with $()."""
        bash_compare.assert_shells_match("echo $(echo hello)")
        bash_compare.assert_shells_match("echo $(echo 'hello world')")
        bash_compare.assert_shells_match("result=$(echo test); echo $result")
    
    def test_backtick_substitution(self):
        """Test command substitution with backticks."""
        bash_compare.assert_shells_match("echo `echo hello`")
        bash_compare.assert_shells_match("echo `echo 'hello world'`")
        # TODO: Fix backtick parsing in assignments
        # bash_compare.assert_shells_match("result=`echo test`; echo $result")
    
    def test_nested_command_substitution(self):
        """Test nested command substitutions."""
        bash_compare.assert_shells_match("echo $(echo $(echo nested))")
        bash_compare.assert_shells_match("echo $(echo a $(echo b) c)")
    
    def test_command_sub_in_arithmetic(self):
        """Test command substitution in arithmetic expressions."""
        bash_compare.assert_shells_match("echo $(($(echo 5) + $(echo 3)))")
        bash_compare.assert_shells_match("x=$(echo 10); echo $((x * $(echo 2)))")
    
    def test_command_sub_word_splitting(self):
        """Test word splitting on command substitution output."""
        # Create a command that outputs multiple words
        bash_compare.assert_shells_match("for word in $(echo one two three); do echo $word; done")
    
    def test_command_sub_with_variables(self):
        """Test command substitution with variable expansion."""
        bash_compare.assert_shells_match("x=hello; echo $(echo $x)")
        bash_compare.assert_shells_match("x=5; y=3; echo $(echo $((x + y)))")
    
    def test_command_sub_exit_status(self):
        """Test that command substitution preserves exit status."""
        # Note: The exit status of the assignment is 0, not the command sub
        bash_compare.assert_shells_match("result=$(false); echo $?")
        bash_compare.assert_shells_match("result=$(true); echo $?")
    
    def test_empty_command_substitution(self):
        """Test empty command substitution output."""
        bash_compare.assert_shells_match("echo x$(true)y")
        bash_compare.assert_shells_match("empty=$(true); echo \"[$empty]\"")
    
    def test_command_sub_in_double_quotes(self):
        """Test command substitution inside double quotes."""
        bash_compare.assert_shells_match('echo "Result: $(echo test)"')
        bash_compare.assert_shells_match('echo "$(echo "hello world")"')
    
    def test_command_sub_with_newlines(self):
        """Test command substitution that outputs newlines."""
        # Command substitution strips trailing newlines
        bash_compare.assert_shells_match('result=$(printf "line1\nline2\n"); echo "$result"')
        bash_compare.assert_shells_match('echo "$(printf "a\nb\nc")"')
    
    def test_command_sub_in_assignments(self):
        """Test command substitution in variable assignments."""
        bash_compare.assert_shells_match("x=$(echo test); echo $x")
        bash_compare.assert_shells_match("x=$(echo one); y=$(echo two); echo $x $y")
        bash_compare.assert_shells_match("x=$(echo $(echo nested)); echo $x")