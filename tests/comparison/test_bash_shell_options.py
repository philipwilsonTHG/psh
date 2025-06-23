#!/usr/bin/env python3
"""
Test shell options using bash comparison framework.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestPOSIXOptions:
    """Test POSIX shell options."""
    
    def test_allexport_option(self):
        """Test set -a (allexport) option."""
        # Enable allexport and set a variable
        bash_compare.assert_shells_match(
            'set -a; myvar=test; bash -c "echo $myvar"'
        )
        
        # Disable allexport and verify
        bash_compare.assert_shells_match(
            'set +a; myvar2=test2; bash -c "echo ${myvar2:-unset}"'
        )
        
    def test_verbose_option(self):
        """Test set -v (verbose) option."""
        # Verbose mode prints commands to stderr
        # Test that command execution still works correctly
        bash_compare.assert_shells_match(
            'set -v; echo test 2>/dev/null'
        )
        
    def test_option_combinations(self):
        """Test combining multiple options."""
        bash_compare.assert_shells_match(
            'set -ev; echo "Exit on error enabled" 2>/dev/null; true'
        )
        
    @pytest.mark.xfail(reason="PSH $- special parameter doesn't include 'e' for errexit")
    def test_special_parameter_dash(self):
        """Test $- special parameter reflects set options."""
        # Check default options
        bash_compare.assert_shells_match(
            'echo "$-" | grep -q "i" || echo "not interactive"'
        )
        
        # Check after setting options
        bash_compare.assert_shells_match(
            'set -e; echo "$-" | grep -q "e" && echo "errexit set"'
        )
        
    def test_noclobber_option(self):
        """Test set -C (noclobber) option."""
        # Create a temp file and test noclobber
        # Both shells should prevent overwriting with noclobber
        bash_compare.assert_shells_match(
            'tmpfile=$(mktemp); echo "test" > "$tmpfile"; set -C; echo "new" > "$tmpfile" 2>&1; echo "Exit: $?"; rm -f "$tmpfile"',
            check_stderr=False  # Error messages differ but both fail correctly
        )
        
    def test_noglob_option(self):
        """Test set -f (noglob) option."""
        bash_compare.assert_shells_match(
            'set -f; echo *'
        )
        
        bash_compare.assert_shells_match(
            'set +f; echo "test" > /tmp/psh_test_file; cd /tmp; echo psh_test_*; rm -f psh_test_file'
        )
        
    @pytest.mark.xfail(reason="PSH handles noexec differently - executes set +n before noexec takes effect")
    def test_noexec_option(self):
        """Test set -n (noexec) option."""
        # noexec prevents command execution but still parses
        # This is tricky to test via comparison since it affects the shell itself
        # Test that it can be set and unset
        bash_compare.assert_shells_match(
            'set -n; set +n; echo "noexec disabled"'
        )


class TestShellOptions:
    """Test shell option handling."""
    
    def test_combined_options(self):
        """Test setting multiple options at once."""
        bash_compare.assert_shells_match(
            'set -ev 2>/dev/null; echo "test"'
        )
        
    def test_option_persistence(self):
        """Test that options persist across commands."""
        bash_compare.assert_shells_match(
            'set -e; true; echo "Still running after true"'
        )
        
    def test_option_in_function(self):
        """Test options within functions."""
        bash_compare.assert_shells_match(
            'f() { set -e; false || echo "Caught error"; }; f'
        )
        
    def test_pipefail_option(self):
        """Test set -o pipefail option."""
        # Test pipeline fails if any command fails
        bash_compare.assert_shells_match(
            'set -o pipefail; false | true; echo "Exit: $?"'
        )
        
        # Test without pipefail
        bash_compare.assert_shells_match(
            'set +o pipefail; false | true; echo "Exit: $?"'
        )


class TestBashCompatibility:
    """Test bash-specific behaviors with POSIX options."""
    
    def test_allexport_existing_vars(self):
        """Test that existing variables are exported when allexport is enabled."""
        # This is a complex test that involves environment inheritance
        bash_compare.assert_shells_match(
            'unset testvar; testvar=value; set -a; bash -c "echo ${testvar:-unset}"'
        )
        
    def test_set_builtin_output(self):
        """Test set builtin output format."""
        # Just verify it doesn't error
        bash_compare.assert_shells_match(
            'set > /dev/null; echo "set succeeded"'
        )


class TestOptionEdgeCases:
    """Test edge cases for shell options."""
    
    @pytest.mark.xfail(reason="Complex interaction between verbose and noexec")
    def test_verbose_with_noexec(self):
        """Test interaction between verbose and noexec."""
        bash_compare.assert_shells_match(
            'set -vn; echo "This should not execute" 2>&1'
        )
        
    def test_errexit_exceptions(self):
        """Test when errexit is ignored."""
        # errexit is ignored in conditionals
        bash_compare.assert_shells_match(
            'set -e; if false; then echo "not reached"; else echo "false in conditional"; fi'
        )
        
        # errexit is ignored in pipeline except last
        bash_compare.assert_shells_match(
            'set -e; false | echo "pipeline continues"'
        )