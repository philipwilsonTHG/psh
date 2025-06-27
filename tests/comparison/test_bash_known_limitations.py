#!/usr/bin/env python3
"""
Document known limitations of PSH compared to bash.
These tests are marked as xfail to track what still needs to be implemented.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestKnownLimitations:
    """Test cases that document known PSH limitations."""
    
    def test_backtick_in_assignment(self):
        """Backtick command substitution in assignments."""
        bash_compare.assert_shells_match('x=`echo hello`; echo $x')
        bash_compare.assert_shells_match('x=`pwd`; echo "path: $x"')
    
    @pytest.mark.xfail(reason="Bare command substitution doesn't set exit status")
    def test_bare_command_substitution_exit_status(self):
        """Exit status from bare command substitution like $(false)."""
        bash_compare.assert_shells_match('$(true); echo $?')
        bash_compare.assert_shells_match('$(false); echo $?')
        bash_compare.assert_shells_match('$(exit 42); echo $?')
    
    @pytest.mark.xfail(reason="Command grouping with braces not implemented")
    def test_command_grouping(self):
        """Command grouping with { } syntax."""
        bash_compare.assert_shells_match('{ echo one; echo two; }')
        bash_compare.assert_shells_match('echo test | { read x; echo "Read: $x"; }')
    
    def test_subshell_syntax(self):
        """Subshell execution with ( ) syntax."""
        bash_compare.assert_shells_match('(echo in subshell)')
        bash_compare.assert_shells_match('x=1; (x=2); echo $x')
    
    def test_multiline_string_literals(self):
        """Multi-line string literals in commands."""
        bash_compare.assert_shells_match('''echo "line1
line2"''')
    
    @pytest.mark.xfail(reason="Here documents in command substitution not working")
    def test_heredoc_in_command_substitution(self):
        """Here documents within command substitution."""
        bash_compare.assert_shells_match('''result=$(cat << EOF
test
EOF
); echo "$result"''')
    
    def test_process_substitution_with_redirection(self):
        """Complex process substitution scenarios."""
        bash_compare.assert_shells_match('cat <(echo test) > /tmp/out && cat /tmp/out && rm /tmp/out')