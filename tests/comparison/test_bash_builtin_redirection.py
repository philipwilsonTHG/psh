#!/usr/bin/env python3
"""
Test builtin command redirection issues.
This file documents known issues with builtin redirection in command substitution.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestBuiltinRedirection:
    """Test builtin redirection behavior."""
    
    @pytest.mark.xfail(reason="pwd builtin doesn't redirect properly in command substitution")
    def test_pwd_in_command_substitution(self):
        """Test pwd builtin in command substitution."""
        bash_compare.assert_shells_match('x=$(pwd); echo "path=[$x]"')
    
    @pytest.mark.xfail(reason="Builtin redirection in command substitution not implemented")
    def test_builtin_redirect_in_command_sub(self):
        """Test builtin redirection within command substitution."""
        bash_compare.assert_shells_match('result=$(pwd 2>&1); echo "[$result]"')
    
    def test_echo_in_command_substitution(self):
        """Test echo builtin works in command substitution."""
        bash_compare.assert_shells_match('x=$(echo hello); echo "x=$x"')
    
    def test_external_command_in_substitution(self):
        """Test external commands work correctly in command substitution."""
        bash_compare.assert_shells_match('x=$(echo test | cat); echo "x=$x"')