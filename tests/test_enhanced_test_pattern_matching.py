#!/usr/bin/env python3
"""Test enhanced test pattern matching functionality.

Tests for the enhanced test statement [[ ]] pattern matching improvements
implemented in v0.59.6 as a critical POSIX compliance improvement.

This includes shell pattern matching with == and != operators using fnmatch.
"""

import pytest
from psh.shell import Shell


class TestEnhancedTestPatternMatching:
    """Test [[ ]] enhanced test pattern matching."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_enhanced_test_basic_pattern_matching(self):
        """Test basic pattern matching with == operator."""
        # Test wildcard pattern matching
        exit_code = self.shell.run_command('[[ "file.txt" == *.txt ]]')
        assert exit_code == 0  # Should match
        
        exit_code = self.shell.run_command('[[ "file.doc" == *.txt ]]')
        assert exit_code == 1  # Should not match
        
        exit_code = self.shell.run_command('[[ "test.log" == *.log ]]')
        assert exit_code == 0  # Should match
    
    def test_enhanced_test_pattern_negation(self):
        """Test pattern matching with != operator."""
        exit_code = self.shell.run_command('[[ "file.txt" != *.doc ]]')
        assert exit_code == 0  # Should not match .doc pattern
        
        exit_code = self.shell.run_command('[[ "file.txt" != *.txt ]]')
        assert exit_code == 1  # Should match .txt pattern, so != is false
    
    def test_enhanced_test_multiple_wildcards(self):
        """Test patterns with multiple wildcards."""
        exit_code = self.shell.run_command('[[ "test-file.tar.gz" == *-*.*.* ]]')
        assert exit_code == 0  # Should match pattern with multiple wildcards
        
        exit_code = self.shell.run_command('[[ "simple.txt" == *-*.*.* ]]')
        assert exit_code == 1  # Should not match (no dash)
    
    def test_enhanced_test_question_mark_pattern(self):
        """Test single character wildcard ? pattern."""
        exit_code = self.shell.run_command('[[ "a" == ? ]]')
        assert exit_code == 0  # Single character should match
        
        exit_code = self.shell.run_command('[[ "ab" == ? ]]')
        assert exit_code == 1  # Two characters should not match
        
        exit_code = self.shell.run_command('[[ "test.log" == test.??? ]]')
        assert exit_code == 0  # Should match three-character extension
    
    def test_enhanced_test_character_class_patterns(self):
        """Test character class patterns [abc] and [a-z]."""
        exit_code = self.shell.run_command('[[ "a" == [abc] ]]')
        assert exit_code == 0  # 'a' should match [abc]
        
        exit_code = self.shell.run_command('[[ "d" == [abc] ]]')
        assert exit_code == 1  # 'd' should not match [abc]
        
        exit_code = self.shell.run_command('[[ "file5.txt" == file[0-9].txt ]]')
        assert exit_code == 0  # Should match digit range
        
        exit_code = self.shell.run_command('[[ "filea.txt" == file[0-9].txt ]]')
        assert exit_code == 1  # Letter should not match digit range
    
    def test_enhanced_test_prefix_suffix_patterns(self):
        """Test prefix and suffix matching patterns."""
        exit_code = self.shell.run_command('[[ "prefix_something" == prefix_* ]]')
        assert exit_code == 0  # Should match prefix
        
        exit_code = self.shell.run_command('[[ "something_suffix" == *_suffix ]]')
        assert exit_code == 0  # Should match suffix
        
        exit_code = self.shell.run_command('[[ "middle_part_here" == *_part_* ]]')
        assert exit_code == 0  # Should match middle pattern
    
    def test_enhanced_test_variable_expansion_in_patterns(self):
        """Test variable expansion in patterns."""
        self.shell.run_command('ext="txt"')
        self.shell.run_command('prefix="test"')
        
        exit_code = self.shell.run_command('[[ "file.txt" == *.$ext ]]')
        assert exit_code == 0  # Should expand variable in pattern
        
        exit_code = self.shell.run_command('[[ "test123" == $prefix* ]]')
        assert exit_code == 0  # Should expand variable as prefix
    
    def test_enhanced_test_literal_matching_with_equals(self):
        """Test that = operator still does literal string matching."""
        exit_code = self.shell.run_command('[[ "*.txt" = "*.txt" ]]')
        assert exit_code == 0  # Literal equality should work
        
        exit_code = self.shell.run_command('[[ "file.txt" = "*.txt" ]]')
        assert exit_code == 1  # Should not do pattern matching with =
    
    def test_enhanced_test_case_sensitivity(self):
        """Test case sensitivity in pattern matching."""
        exit_code = self.shell.run_command('[[ "File.TXT" == *.txt ]]')
        assert exit_code == 1  # Should be case sensitive
        
        exit_code = self.shell.run_command('[[ "file.txt" == *.TXT ]]')
        assert exit_code == 1  # Should be case sensitive
        
        exit_code = self.shell.run_command('[[ "FILE.TXT" == *.TXT ]]')
        assert exit_code == 0  # Exact case should match
    
    def test_enhanced_test_empty_strings(self):
        """Test pattern matching with empty strings."""
        exit_code = self.shell.run_command('[[ "" == "" ]]')
        assert exit_code == 0  # Empty strings should match
        
        exit_code = self.shell.run_command('[[ "" == * ]]')
        assert exit_code == 0  # * should match empty string
        
        exit_code = self.shell.run_command('[[ "" == ? ]]')
        assert exit_code == 1  # ? should not match empty string
    
    def test_enhanced_test_special_characters(self):
        """Test pattern matching with special characters."""
        exit_code = self.shell.run_command('[[ "file@domain.com" == *@*.* ]]')
        assert exit_code == 0  # Should match email-like pattern
        
        exit_code = self.shell.run_command('[[ "path/to/file" == */to/* ]]')
        assert exit_code == 0  # Should match path pattern
        
        exit_code = self.shell.run_command('[[ "user-name_123" == *-*_* ]]')
        assert exit_code == 0  # Should match complex pattern


class TestEnhancedTestLogicalOperators:
    """Test logical operators within [[ ]] statements."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_enhanced_test_and_operator(self):
        """Test && operator in enhanced tests."""
        exit_code = self.shell.run_command('[[ "file.txt" == *.txt && "file.txt" == file.* ]]')
        assert exit_code == 0  # Both conditions should be true
        
        exit_code = self.shell.run_command('[[ "file.txt" == *.txt && "file.txt" == *.doc ]]')
        assert exit_code == 1  # Second condition is false
    
    def test_enhanced_test_or_operator(self):
        """Test || operator in enhanced tests."""
        exit_code = self.shell.run_command('[[ "file.txt" == *.doc || "file.txt" == *.txt ]]')
        assert exit_code == 0  # Second condition is true
        
        exit_code = self.shell.run_command('[[ "file.txt" == *.doc || "file.txt" == *.log ]]')
        assert exit_code == 1  # Both conditions are false
    
    def test_enhanced_test_negation_operator(self):
        """Test ! (negation) operator in enhanced tests."""
        exit_code = self.shell.run_command('[[ ! "file.txt" == *.doc ]]')
        assert exit_code == 0  # Negation of false is true
        
        exit_code = self.shell.run_command('[[ ! "file.txt" == *.txt ]]')
        assert exit_code == 1  # Negation of true is false
    
    def test_enhanced_test_complex_expressions(self):
        """Test complex logical expressions."""
        exit_code = self.shell.run_command('[[ ("file.txt" == *.txt && "file.txt" != *.doc) || "other" == "other" ]]')
        assert exit_code == 0  # Complex expression should be true
        
        # Test operator precedence
        exit_code = self.shell.run_command('[[ ! "file.txt" == *.doc && "file.txt" == *.txt ]]')
        assert exit_code == 0  # Should evaluate correctly with precedence


class TestEnhancedTestNumericalComparisons:
    """Test that numerical comparisons still work in [[ ]]."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_enhanced_test_numerical_operators(self):
        """Test that numerical operators are preserved."""
        exit_code = self.shell.run_command('[[ 5 -eq 5 ]]')
        assert exit_code == 0
        
        exit_code = self.shell.run_command('[[ 5 -lt 10 ]]')
        assert exit_code == 0
        
        exit_code = self.shell.run_command('[[ 10 -gt 5 ]]')
        assert exit_code == 0
        
        exit_code = self.shell.run_command('[[ 5 -ne 10 ]]')
        assert exit_code == 0
    
    def test_enhanced_test_lexicographic_operators(self):
        """Test lexicographic string comparison operators."""
        exit_code = self.shell.run_command('[[ "apple" < "banana" ]]')
        assert exit_code == 0  # Lexicographic comparison
        
        exit_code = self.shell.run_command('[[ "zebra" > "apple" ]]')
        assert exit_code == 0  # Lexicographic comparison
    
    def test_enhanced_test_regex_operator(self):
        """Test that regex operator =~ still works."""
        exit_code = self.shell.run_command('[[ "abc123" =~ [a-z]+[0-9]+ ]]')
        assert exit_code == 0  # Should match regex
        
        exit_code = self.shell.run_command('[[ "123abc" =~ [a-z]+[0-9]+ ]]')
        assert exit_code == 1  # Should not match regex


class TestEnhancedTestEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_enhanced_test_quoted_patterns(self):
        """Test behavior with quoted patterns."""
        # Quoted patterns should be treated literally
        exit_code = self.shell.run_command('[[ "*.txt" == "*.txt" ]]')
        assert exit_code == 0  # Literal match
        
        exit_code = self.shell.run_command('[[ "file.txt" == "*.txt" ]]')
        assert exit_code == 1  # Quoted pattern should not expand
    
    def test_enhanced_test_backslash_escaping(self):
        """Test backslash escaping in patterns."""
        exit_code = self.shell.run_command('[[ "file*.txt" == file\\*.txt ]]')
        assert exit_code == 0  # Escaped asterisk should match literally
    
    def test_enhanced_test_with_variables(self):
        """Test pattern matching with variables."""
        self.shell.run_command('filename="test.log"')
        self.shell.run_command('pattern="*.log"')
        
        exit_code = self.shell.run_command('[[ "$filename" == $pattern ]]')
        assert exit_code == 0  # Variable expansion should work
        
        exit_code = self.shell.run_command('[[ "$filename" == "$pattern" ]]')
        assert exit_code == 1  # Quoted pattern should not match
    
    def test_enhanced_test_mixed_quoting_patterns(self):
        """Test patterns with mixed quoting (quoted and unquoted parts)."""
        self.shell.run_command('search_term="app"')
        self.shell.run_command('element="myapp"')
        
        # Mixed quoting should be treated as unquoted (glob pattern)
        exit_code = self.shell.run_command('[[ "$element" == *"$search_term"* ]]')
        assert exit_code == 0  # Mixed quoting should work as pattern
        
        # Fully quoted should be literal
        exit_code = self.shell.run_command('[[ "$element" == "*$search_term*" ]]')
        assert exit_code == 1  # Fully quoted should not pattern match
        
        # Test other mixed patterns
        exit_code = self.shell.run_command('[[ "test.txt" == *".txt" ]]')
        assert exit_code == 0  # Mixed: unquoted * + quoted .txt
        
        exit_code = self.shell.run_command('[[ "test.txt" == "test".* ]]')
        assert exit_code == 0  # Mixed: quoted test + unquoted .*
    
    def test_enhanced_test_with_spaces_in_patterns(self):
        """Test patterns containing spaces."""
        exit_code = self.shell.run_command('[[ "hello world" == "hello world" ]]')
        assert exit_code == 0  # Exact match with spaces
        
        exit_code = self.shell.run_command('[[ "hello world" == hello* ]]')
        assert exit_code == 0  # Pattern should match despite space
    
    def test_enhanced_test_no_word_splitting(self):
        """Test that variables are not word-split in [[ ]]."""
        self.shell.run_command('var="hello world"')
        
        # This should work in [[ ]] but might fail in [ ] due to word splitting
        exit_code = self.shell.run_command('[[ $var == "hello world" ]]')
        assert exit_code == 0  # Should not word-split in [[ ]]