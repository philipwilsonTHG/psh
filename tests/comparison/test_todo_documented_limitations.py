#!/usr/bin/env python3
"""
Tests specifically for limitations documented in TODO.md

This file tests the exact limitations described in TODO.md to:
1. Verify they are real limitations (tests should FAIL until fixed)
2. Track progress on fixing them (tests will PASS when limitations are resolved)
3. Update TODO.md when limitations are fixed
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestParserLimitations:
    """Test parser limitations documented in TODO.md section 'Parser Limitations'"""
    
    def test_composite_argument_quote_handling_in_redirection(self):
        """
        TODO.md: "Parser loses quote information when creating composite arguments"
        Example: "file'*'.txt may incorrectly expand wildcards"
        
        ✅ **FIXED**: Redirection now correctly handles quoted composite arguments
        PSH now correctly creates 'testfile.txt' from test'file'.txt
        """
        # This now works correctly - both shells should match
        bash_compare.assert_shells_match(
            "echo hello > test'file'.txt; ls testfile.txt 2>/dev/null && echo 'created testfile.txt' || echo 'failed to create testfile.txt'",
            check_stderr=False
        )

    def test_composite_argument_quote_handling_status(self):
        """
        TODO.md: "Status: Partially mitigated by disabling glob expansion for composites"
        
        This tests what IS working - echo with quoted composites
        """
        # These work correctly (the mitigation is effective)
        bash_compare.assert_shells_match("echo file'*'.txt")
        bash_compare.assert_shells_match("echo prefix'middle'suffix")
        bash_compare.assert_shells_match('echo "double"\'single\'unquoted')


class TestTokenizerIssues:
    """Test tokenizer issues documented in TODO.md section 'Tokenizer Issues'"""
    
    def test_quote_handling_in_words_tokenizer_behavior(self):
        """
        TODO.md: "Quotes within words included in token value"
        Example: "a'b'c tokenizes as a'b'c instead of abc"
        Impact: "Incorrect output for concatenated quoted strings"
        
        DOCUMENTED BUT COMPENSATED: The tokenizer does split into separate tokens,
        but the final output is correct due to post-processing.
        """
        # The output is correct despite tokenizer limitation
        bash_compare.assert_shells_match("echo a'b'c")
        
        # But the tokenizer debug shows: WORD 'a', STRING 'b', WORD 'c'
        # This test documents that the limitation exists but is compensated for
        print("\nNote: Tokenizer splits a'b'c but final output is correct")


class TestOtherLimitations:
    """Test other limitations that aren't in the main TODO.md sections"""
    
    def test_backslash_escaping_limitation(self):
        """
        Backslash escaping for special characters like $ and *.
        ✅ **FIXED**: PSH now correctly handles backslash escaping like bash.
        """
        # This now works correctly - both shells should match
        bash_compare.assert_shells_match("echo \\$variable")
        bash_compare.assert_shells_match("echo \\$HOME")
        bash_compare.assert_shells_match('echo "\\$variable"')


class TestLimitationProgression:
    """Track which limitations from TODO.md have been resolved"""
    
    def test_fixed_quote_concatenation(self):
        """
        These quote concatenation cases work correctly now.
        TODO.md may need updating - these limitations appear to be resolved.
        """
        # All these work correctly now
        bash_compare.assert_shells_match("echo 'first''second''third'")
        bash_compare.assert_shells_match("echo a''b")
        bash_compare.assert_shells_match("echo pre'middle'post")
        bash_compare.assert_shells_match('echo outer\'inner"nested"inner\'outer')
    
    def test_fixed_composite_quote_handling_in_echo(self):
        """
        Composite quote handling works correctly in echo context.
        The limitation is specific to redirection/parser contexts.
        """
        # These all work correctly
        bash_compare.assert_shells_match("echo file'*'.txt")
        bash_compare.assert_shells_match("ls file'*'.txt 2>/dev/null || echo 'no files'")
        bash_compare.assert_shells_match("touch test'name'.txt; ls test'name'.txt && rm test'name'.txt")


class TestTodoDocumentationAccuracy:
    """Test if TODO.md accurately reflects current limitations"""
    
    def test_todo_parser_limitations_section_accuracy(self):
        """
        Verify that the examples in TODO.md 'Parser Limitations' section are accurate.
        """
        # Example from TODO.md: `file'*'.txt` may incorrectly expand wildcards
        # This works correctly in echo context:
        bash_compare.assert_shells_match("echo file'*'.txt")
        
        # ✅ FIXED: Redirection with composite arguments now works correctly:
        bash_compare.assert_shells_match(
            "echo test > prefix'suffix'.txt; ls prefixsuffix.txt 2>/dev/null && echo 'created prefixsuffix.txt' || echo 'failed to create prefixsuffix.txt'",
            check_stderr=False
        )
    
    def test_todo_tokenizer_issues_section_accuracy(self):
        """
        Verify that TODO.md 'Tokenizer Issues' section accurately describes current behavior.
        """
        # Example from TODO.md: `a'b'c` tokenizes as `a'b'c` instead of `abc`
        # The tokenizer DOES split this, but output is correct:
        bash_compare.assert_shells_match("echo a'b'c")
        
        # This suggests the "Impact: Incorrect output" in TODO.md needs updating
        print("\nTODO.md may need updating: tokenizer splits tokens but output is correct")


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    pytest.main([__file__, "-v"])