#!/usr/bin/env python3
"""
Test parser limitations by comparing with bash behavior.

This file specifically tests the limitations documented in TODO.md
to verify they are real differences and track progress on fixes.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestCompositeArgumentQuoteHandling:
    """Test composite argument quote handling limitations."""
    
    def setup_method(self):
        """Set up test files for glob testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test files
        with open("file_star.txt", "w") as f:
            f.write("literal asterisk file")
        with open("file*.txt", "w") as f:
            f.write("actual asterisk in name")
        with open("test1.txt", "w") as f:
            f.write("test1")
        with open("test2.txt", "w") as f:
            f.write("test2")
    
    def teardown_method(self):
        """Clean up test files."""
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_quoted_glob_in_composite_argument(self):
        """Test that file'*'.txt doesn't expand wildcards - echo works but redirection doesn't"""
        # Echo works correctly
        bash_compare.assert_shells_match("echo file'*'.txt")
    
    def test_redirection_with_quoted_composite(self):
        """Test redirection with quoted composite arguments - REAL LIMITATION"""
        # This is where the parser limitation shows up
        bash_compare.expect_shells_differ(
            "echo hello > test'file'.txt; ls test'file'.txt 2>/dev/null || echo 'file not found'",
            reason="Parser loses quote information in redirection targets",
            check_stderr=False
        )
    
    def test_command_with_quoted_composite_args(self):
        """Test commands with quoted composite arguments - works for touch/ls"""
        # Touch and ls work correctly with quoted composite arguments
        bash_compare.assert_shells_match(
            "touch test'name'.txt; ls test'name'.txt 2>/dev/null || echo 'touch failed'",
            check_stderr=False
        )
    
    def test_mixed_quotes_in_composite(self):
        """Test mixed quoting in composite arguments - works in echo"""
        # PSH correctly handles mixed quoting in echo
        bash_compare.assert_shells_match("echo prefix'quoted'suffix")
        bash_compare.assert_shells_match('echo "double"\'single\'unquoted')
    
    def test_glob_with_quoted_parts(self):
        """Test glob patterns with quoted segments - works correctly"""
        # PSH correctly handles quoted asterisks in echo
        bash_compare.assert_shells_match("echo test'*'.txt")


class TestTokenizerQuoteHandling:
    """Test tokenizer quote handling issues."""
    
    def test_tokenizer_behavior_documentation(self):
        """Document that tokenizer separates quoted segments but output works"""
        # This test documents the tokenizer behavior described in TODO.md
        # The tokenizer does split a'b'c into separate tokens: WORD 'a', STRING 'b', WORD 'c'
        # But the final output is correct due to post-processing
        bash_compare.assert_shells_match("echo a'b'c")
        
        # This shows the tokenizer limitation exists but is compensated for
        print("\nTokenizer splits a'b'c into separate tokens but output is correct")
    
    def test_multiple_quoted_segments(self):
        """Test multiple quoted segments - works in echo context"""
        # These work correctly in echo context despite tokenizer limitations
        bash_compare.assert_shells_match("echo 'first''second''third'")
        bash_compare.assert_shells_match("echo pre'middle'post")
    
    def test_empty_quotes_in_concatenation(self):
        """Test empty quotes in concatenation - works correctly"""
        # These work correctly
        bash_compare.assert_shells_match("echo a''b")
        bash_compare.assert_shells_match("echo ''start")
        bash_compare.assert_shells_match("echo end''")
    
    def test_quotes_with_variables(self):
        """Test quote handling with variable expansion."""
        # Single quotes should prevent variable expansion
        bash_compare.assert_shells_match("echo 'hello $USER world'")
    
    def test_nested_quote_scenarios(self):
        """Test complex nested quote scenarios - FIXED!"""
        # PSH handles complex nested quotes correctly now
        bash_compare.assert_shells_match('echo outer\'inner"nested"inner\'outer')


class TestWorkingQuoteFeatures:
    """Test quote features that should work correctly."""
    
    def test_simple_single_quotes(self):
        """Test simple single quotes (should work)."""
        bash_compare.assert_shells_match("echo 'hello world'")
        bash_compare.assert_shells_match("echo 'no $expansion here'")
    
    def test_simple_double_quotes(self):
        """Test simple double quotes (should work)."""
        bash_compare.assert_shells_match('echo "hello world"')
        bash_compare.assert_shells_match('var=test; echo "expansion: $var"')


class TestEscapingLimitations:
    """Test backslash escaping limitations."""
    
    def test_backslash_escaping_limitation(self):
        """Test backslash escaping - REAL LIMITATION"""
        # PSH doesn't handle backslash escaping correctly
        bash_compare.expect_shells_differ(
            "echo \\$no_expansion", 
            reason="PSH doesn't handle backslash escaping like bash"
        )
        
        # Note: glob escaping actually works the same in both
        # bash_compare.assert_shells_match("echo \\*no_glob")
        
    def test_working_space_escaping(self):
        """Test space escaping - this works"""
        bash_compare.assert_shells_match("echo hello\\ world")


class TestRegressionChecks:
    """Test cases to ensure fixes don't break working features."""
    
    def test_normal_glob_expansion(self):
        """Ensure normal glob expansion still works."""
        # Set up files in a controlled way
        with tempfile.TemporaryDirectory() as temp_dir:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # Create test files
                with open("test1.txt", "w") as f:
                    f.write("test1")
                with open("test2.txt", "w") as f:
                    f.write("test2")
                
                # This should work the same in both shells
                bash_compare.assert_shells_match("echo test*.txt | tr ' ' '\\n' | sort")
                
            finally:
                os.chdir(old_cwd)
    
    def test_normal_variable_expansion(self):
        """Ensure normal variable expansion works."""
        bash_compare.assert_shells_match("var=hello; echo $var")
        bash_compare.assert_shells_match("var=world; echo ${var}")
    
    def test_normal_command_substitution(self):
        """Ensure command substitution works."""
        bash_compare.assert_shells_match("echo $(echo hello)")
        bash_compare.assert_shells_match("echo `echo world`")


# Utility test to show differences clearly
class TestLimitationDemonstration:
    """Demonstrate the limitations with clear examples."""
    
    def test_show_escaping_difference(self):
        """Show the actual difference in backslash escaping."""
        psh_result, bash_result = bash_compare.expect_shells_differ(
            "echo \\$no_expansion",
            reason="Backslash escaping difference"
        )
        
        # Log the actual differences for debugging
        print(f"\nBackslash escaping test:")
        print(f"PSH output:  '{psh_result.stdout.strip()}'")
        print(f"Bash output: '{bash_result.stdout.strip()}'")
        print(f"PSH doesn't handle backslash escaping correctly")
    
    def test_show_composite_argument_difference(self):
        """Show the composite argument handling difference."""
        # This test might need file setup
        pass


# Performance comparison (optional)
class TestPerformanceComparison:
    """Compare performance characteristics (optional)."""
    
    @pytest.mark.slow
    def test_large_output_handling(self):
        """Test handling of large outputs."""
        bash_compare.assert_shells_match("seq 1 100")
    
    @pytest.mark.slow  
    def test_complex_expansions(self):
        """Test complex expansion scenarios."""
        bash_compare.assert_shells_match("echo {1..10}{a,b,c}")


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    pytest.main([__file__, "-v"])