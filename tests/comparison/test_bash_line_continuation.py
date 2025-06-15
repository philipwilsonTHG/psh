#!/usr/bin/env python3
"""
Test line continuation handling against bash for compatibility.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestLineContinuationBashCompat:
    """Test line continuation behavior matches bash."""
    
    def test_escaped_newline_in_double_quotes(self):
        """Test that \\<newline> in double quotes continues the line."""
        # Basic continuation
        bash_compare.assert_shells_match('echo "This is a very \\\nlong line that continues"')
        
        # Multiple continuations
        bash_compare.assert_shells_match('echo "Line 1\\\nLine 2\\\nLine 3"')
        
        # At end of string
        bash_compare.assert_shells_match('echo "ends with continuation\\\n"')
    
    def test_escaped_newline_with_variables(self):
        """Test line continuation with variable expansion."""
        bash_compare.assert_shells_match('name="world"; echo "Hello, \\\n$name!"')
        bash_compare.assert_shells_match('x="test"; echo "Value is \\\n${x}"')
    
    def test_escaped_newline_preserves_whitespace(self):
        """Test that whitespace before continuation is preserved."""
        bash_compare.assert_shells_match('echo "Before   \\\nAfter"')
        bash_compare.assert_shells_match('echo "Tabs\t\\\nwork too"')
    
    def test_single_quotes_preserve_backslash(self):
        """Test that single quotes preserve backslashes."""
        # Single quotes preserve literal backslash-n
        bash_compare.assert_shells_match("echo 'hello\\nworld'")
        bash_compare.assert_shells_match("echo 'backslash\\\\'")
    
    def test_line_continuation_outside_quotes(self):
        """Test line continuation outside quotes."""
        bash_compare.assert_shells_match('echo one \\\ntwo')
        bash_compare.assert_shells_match('echo first \\\n    second')  # With indentation
    
    def test_line_continuation_in_assignments(self):
        """Test line continuation in variable assignments."""
        bash_compare.assert_shells_match('var="first \\\nsecond"; echo "$var"')
        bash_compare.assert_shells_match('x=hello\\\nworld; echo "$x"')  # Outside quotes
    
    def test_command_substitution_with_continuation(self):
        """Test line continuation in command substitution."""
        bash_compare.assert_shells_match('result=$(echo "test \\\nvalue"); echo "$result"')
        bash_compare.assert_shells_match('x=$(echo one \\\ntwo); echo "$x"')
    
    def test_line_continuation_edge_cases(self):
        """Test edge cases for line continuation."""
        # Note: Multi-line strings with actual newlines cannot be tested via -c
        # because they create incomplete commands. These would work in interactive
        # mode or script files.
        
        # Double backslash followed by escaped newline (line continuation)
        bash_compare.assert_shells_match('echo "Double\\\\\\\nbackslash"')
        
        # Triple backslash - last one escapes newline
        bash_compare.assert_shells_match('echo "Triple\\\\\\\\\\\nbackslash"')
        
        # Test that work with line continuations (not literal newlines)
        bash_compare.assert_shells_match('echo "Test\\\n with continuation"')
    
    @pytest.mark.skip(reason="Heredocs require multi-line input which doesn't work with -c")
    def test_heredoc_with_continuation(self):
        """Test line continuation in here documents."""
        # These tests would work in script files or interactive mode
        bash_compare.assert_shells_match('''cat << EOF
Line one \\
continued
EOF''')
        
        bash_compare.assert_shells_match('''cat << EOF
Multiple \\
lines \\
continued
EOF''')
    
    def test_continuation_in_pipelines(self):
        """Test line continuation in pipelines."""
        bash_compare.assert_shells_match('echo "test \\\ndata" | cat')
        bash_compare.assert_shells_match('echo "one\\\ntwo" | grep two')
    
    def test_continuation_with_special_chars(self):
        """Test line continuation with special characters."""
        # With command substitution syntax
        bash_compare.assert_shells_match('echo "$(echo test \\\nvalue)"')
        
        # With arithmetic
        bash_compare.assert_shells_match('echo "$((1 + \\\n2))"')
        
        # With glob patterns (in quotes, no expansion)
        bash_compare.assert_shells_match('echo "*.txt \\\ncontinued"')
    
    def test_mixed_quote_continuations(self):
        """Test continuations when switching quote types."""
        bash_compare.assert_shells_match('echo "double"\\\n\'single\'')
        bash_compare.assert_shells_match('echo \'single\'\\\n"double"')
    
    def test_function_with_continuation(self):
        """Test line continuation in function definitions."""
        bash_compare.assert_shells_match('''
f() {
    echo "function with \\\
continuation"
}
f
''')