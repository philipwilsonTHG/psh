#!/usr/bin/env python3
"""
Test advanced read builtin features using bash comparison framework.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestReadAdvanced:
    """Test advanced read builtin features."""
    
    def test_read_prompt_option(self):
        """Test read with -p prompt option."""
        # Note: PSH outputs prompt to stderr differently than bash
        # Test that the variable is set correctly regardless of prompt output
        bash_compare.assert_shells_match(
            'echo "test" | read -p "Enter value: " var 2>/dev/null; echo "Got: $var"'
        )
        
    def test_read_multiple_fields(self):
        """Test read splitting input into multiple variables."""
        bash_compare.assert_shells_match(
            'echo "one two three" | read a b c; echo "$a|$b|$c"'
        )
        
    def test_read_timeout_option(self):
        """Test read with -t timeout option."""
        # Use a longer timeout to avoid immediate timeout
        # Test that read succeeds with input
        bash_compare.assert_shells_match(
            'echo "test" | read -t 1 var; echo "Exit: $?, Var: $var"'
        )
        
    def test_read_delimiter_option(self):
        """Test read with -d delimiter option."""
        bash_compare.assert_shells_match(
            'echo -n "one:two:three" | read -d : var; echo "Got: $var"'
        )
        
    def test_read_n_chars_option(self):
        """Test read with -n chars option."""
        bash_compare.assert_shells_match(
            'echo "hello world" | read -n 5 var; echo "Got: $var"'
        )
        
    def test_read_combined_options(self):
        """Test read with multiple options combined."""
        # Test -n with prompt, suppress stderr for prompt differences
        bash_compare.assert_shells_match(
            'echo "test" | read -n 3 -p "Enter: " var 2>/dev/null; echo "Got: $var"'
        )
        
    @pytest.mark.xfail(reason="PSH read doesn't support -a array option yet")
    def test_read_array_support(self):
        """Test read with -a array option."""
        bash_compare.assert_shells_match(
            'echo "one two three" | read -a arr; echo "${arr[0]} ${arr[1]} ${arr[2]}"'
        )
        
    def test_read_ifs_splitting(self):
        """Test read with custom IFS."""
        # Test IFS splitting without subshell variable assignment
        bash_compare.assert_shells_match(
            'oldifs=$IFS; IFS=:; echo "a:b:c" | read x y z; echo "$x|$y|$z"; IFS=$oldifs'
        )
        
    def test_read_backslash_handling(self):
        """Test read with and without -r option."""
        # Without -r, backslashes are processed
        bash_compare.assert_shells_match(
            'echo "test\\nline" | read var; echo "$var"'
        )
        
        # With -r, backslashes are literal
        bash_compare.assert_shells_match(
            'echo "test\\nline" | read -r var; echo "$var"'
        )
        
    def test_read_empty_input(self):
        """Test read with empty input."""
        bash_compare.assert_shells_match(
            'echo -n "" | read var; echo "Exit: $?, Var: \'$var\'"'
        )
        
    def test_read_trailing_delimiter(self):
        """Test read behavior with trailing delimiters."""
        bash_compare.assert_shells_match(
            'echo "a b c " | read x y z; echo "$x|$y|$z"'
        )
        
    def test_read_invalid_options(self):
        """Test read with invalid options."""
        # Both shells should reject invalid timeout
        bash_compare.assert_shells_match(
            'read -t abc var 2>&1 | grep -q "invalid" && echo "Error detected"',
            check_stderr=False  # We're redirecting stderr to stdout
        )


class TestReadEdgeCases:
    """Test edge cases for read builtin."""
    
    def test_read_from_closed_fd(self):
        """Test read from a closed file descriptor."""
        bash_compare.assert_shells_match(
            'exec 3<&-; read var <&3 2>&1 | grep -q -i "bad" && echo "Error detected"',
            check_stderr=False
        )
        
    def test_read_with_null_bytes(self):
        """Test read handling of null bytes."""
        # Most shells strip null bytes
        bash_compare.assert_shells_match(
            'printf "hello\\0world" | read var; echo "Got: $var"'
        )