#!/usr/bin/env python3
"""
Test for loops with command substitution against bash for compatibility.
Replaces tests/test_for_loops_command_substitution.py with bash comparison tests.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestForLoopsCommandSubstitution:
    """Test for loops with command substitution compatibility with bash."""
    
    def test_basic_command_substitution_in_for_loop(self):
        """Test basic command substitution in for loop."""
        bash_compare.assert_shells_match('for i in $(echo 1 2 3); do echo "num:$i"; done')
    
    def test_backtick_substitution_in_for_loop(self):
        """Test backtick command substitution in for loop."""
        bash_compare.assert_shells_match('for c in `echo a b c`; do echo "char:$c"; done')
    
    def test_mixed_for_loop_items(self):
        """Test for loop with mixed literal and command substitution."""
        bash_compare.assert_shells_match('for x in start $(echo mid1 mid2) end; do echo "$x"; done')
    
    def test_command_substitution_with_variables(self):
        """Test command substitution that uses variables."""
        bash_compare.assert_shells_match('x="1 2"; for i in $(echo $x 3); do echo "$i"; done')
    
    def test_empty_command_substitution(self):
        """Test for loop with empty command substitution."""
        # Empty command substitution should result in no iterations
        bash_compare.assert_shells_match('for i in $(echo -n); do echo "should not print"; done')
    
    def test_nested_command_substitution_in_for(self):
        """Test nested structures with command substitution in for loop."""
        bash_compare.assert_shells_match('''
for n in $(echo 1 2); do
    if [ "$n" = "1" ]; then
        echo "first"
    else
        echo "second"
    fi
done
''')
    
    def test_command_substitution_with_whitespace(self):
        """Test command substitution that outputs multiple lines."""
        # Use printf to generate multi-line output
        bash_compare.assert_shells_match('for line in $(printf "line1\\nline2\\nline3"); do echo "Got: $line"; done')
    
    def test_arithmetic_in_command_substitution(self):
        """Test arithmetic expansion within command substitution in for loop."""
        bash_compare.assert_shells_match('for i in $(echo $((1+1)) $((2*2))); do echo "val=$i"; done')
    
    def test_nested_command_substitution(self):
        """Test nested command substitution in for loop."""
        bash_compare.assert_shells_match('for i in $(echo $(echo nested)); do echo "got: $i"; done')
    
    def test_command_substitution_with_quotes(self):
        """Test command substitution with quoted strings."""
        bash_compare.assert_shells_match('for word in $(echo "one two" three); do echo "[$word]"; done')