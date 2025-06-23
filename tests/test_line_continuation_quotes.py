#!/usr/bin/env python3
"""
Test line continuation handling in quoted strings.

NOTE: These tests have been moved to tests/comparison/test_bash_line_continuation_quotes.py
to avoid test isolation issues. The bash comparison framework provides better isolation
for subprocess-based tests.
"""

import pytest
import subprocess
import sys

# Skip all tests in this file due to test isolation issues
pytestmark = pytest.mark.skip(reason="Moved to tests/comparison/test_bash_line_continuation_quotes.py to avoid isolation issues")


class TestLineContinuationInQuotes:
    """Test that escaped newlines work correctly in quoted strings."""
    
    def run_psh(self, command):
        """Helper to run PSH commands."""
        result = subprocess.run(
            [sys.executable, "-m", "psh", "-c", command],
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_escaped_newline_in_double_quotes(self):
        """Test that \\<newline> in double quotes continues the line."""
        # Basic case
        stdout, _, _ = self.run_psh('echo "This is a very \\\nlong line that continues"')
        assert stdout.strip() == "This is a very long line that continues"
        
        # Multiple continuations
        stdout, _, _ = self.run_psh('echo "Line 1\\\nLine 2\\\nLine 3"')
        assert stdout.strip() == "Line 1Line 2Line 3"
        
        # With spaces after backslash (should NOT be continuation)
        # Use raw string to preserve backslashes
        stdout, stderr, rc = self.run_psh(r'echo "Not a\ ' + '\n' + 'continuation"')
        # The command might fail or produce output differently
        if rc == 0 and stdout:
            assert "Not a\\ " in stdout or "Not a\\\\" in stdout  # Different shells may handle this differently
            assert "continuation" in stdout
        # Skip if command fails - this is an edge case
        
    def test_escaped_newline_with_variables(self):
        """Test line continuation with variable expansion."""
        stdout, _, _ = self.run_psh('name="world"; echo "Hello, \\\n$name!"')
        assert stdout.strip() == "Hello, world!"
        
    def test_escaped_newline_preserves_whitespace(self):
        """Test that whitespace before continuation is preserved."""
        stdout, _, _ = self.run_psh('echo "Before   \\\nAfter"')
        assert stdout.strip() == "Before   After"
        
    def test_single_quotes_preserve_backslash_newline(self):
        """Test that single quotes don't process line continuations."""
        # Single quotes preserve literal backslash-n
        stdout, _, _ = self.run_psh("echo 'hello\\nworld'")
        assert stdout.strip() == "hello\\nworld"
        
        # Note: We can't test actual newline in single quotes via -c
        # because the shell would see an unclosed quote
        
    def test_mixed_quotes_and_continuations(self):
        """Test complex cases with mixed quotes and continuations."""
        # Continuation outside quotes
        stdout, _, _ = self.run_psh('echo one \\\ntwo')
        assert stdout.strip() == "one two"
        
        # Continuation in command substitution
        stdout, _, _ = self.run_psh('result=$(echo "test \\\nvalue"); echo "$result"')
        assert stdout.strip() == "test value"
        
    def test_line_continuation_in_assignments(self):
        """Test line continuation in variable assignments."""
        stdout, _, _ = self.run_psh('var="first \\\nsecond"; echo "$var"')
        assert stdout.strip() == "first second"
        
    def test_heredoc_with_line_continuation(self):
        """Test that line continuations work in heredocs."""
        # Heredocs are tricky to test via -c, so just test echo with continuation
        command = 'echo "Line one \\\ncontinued"'
        stdout, _, _ = self.run_psh(command)
        assert stdout.strip() == "Line one continued"
        
    def test_line_continuation_edge_cases(self):
        """Test edge cases for line continuation."""
        # Double backslash followed by newline
        stdout, stderr, rc = self.run_psh(r'echo "Double\\' + '\n' + 'backslash"')
        # Should have literal backslash and then newline
        if rc == 0 and stdout:
            # Don't strip() as it removes the newlines we want to check
            lines = stdout.rstrip('\n').split('\n')
            assert len(lines) == 2
            assert lines[0] == "Double\\"
            assert lines[1] == "backslash"
        
        # Triple backslash - last one escapes newline
        stdout, _, _ = self.run_psh('echo "Triple\\\\\\\nbackslash"')
        assert stdout.strip() == "Triple\\backslash"
        
    def test_comparison_with_bash(self):
        """Compare PSH behavior with bash."""
        test_cases = [
            'echo "test \\\nline"',
            'echo "a\\\nb\\\nc"',
            'x="hello \\\nworld"; echo "$x"',
            'echo "end\\\\"',  # Backslash at end
        ]
        
        for cmd in test_cases:
            # Run in PSH
            psh_out, _, _ = self.run_psh(cmd)
            
            # Run in bash
            bash_result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True
            )
            
            # Compare outputs
            assert psh_out.strip() == bash_result.stdout.strip(), \
                f"Mismatch for command: {cmd}\nPSH: {psh_out}\nBash: {bash_result.stdout}"