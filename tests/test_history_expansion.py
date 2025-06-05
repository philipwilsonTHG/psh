#!/usr/bin/env python3
"""Tests for history expansion functionality."""

import pytest
import sys
from psh.shell import Shell
from io import StringIO


class TestHistoryExpansion:
    """Test history expansion functionality."""
    
    def setup_method(self, method):
        """Set up test environment."""
        # Create shell with norc to avoid loading history
        self.shell = Shell(norc=True)
        # Override history file to prevent loading
        self.shell.state.history_file = "/tmp/test_history_expansion"
        # Clear any existing history and add fresh test commands
        self.shell.history.clear()
        self.shell.history.append("echo first")
        self.shell.history.append("ls -la")
        self.shell.history.append("pwd")
        self.shell.history.append("echo test")
        self.shell.history.append("cd /tmp")
    
    def test_double_bang_expansion(self):
        """Test !! expansion (previous command)."""
        # The last command in history is "cd /tmp"
        expanded = self.shell.history_expander.expand_history("!!")
        assert expanded == "cd /tmp"
    
    def test_numeric_expansion(self):
        """Test !n expansion (nth command)."""
        # !1 should be "echo first" (1-based indexing)
        expanded = self.shell.history_expander.expand_history("!1")
        assert expanded == "echo first"
        
        # !3 should be "pwd"
        expanded = self.shell.history_expander.expand_history("!3")
        assert expanded == "pwd"
    
    def test_negative_numeric_expansion(self):
        """Test !-n expansion (n commands back)."""
        # !-1 should be the last command "cd /tmp"
        expanded = self.shell.history_expander.expand_history("!-1")
        assert expanded == "cd /tmp"
        
        # !-2 should be "echo test"
        expanded = self.shell.history_expander.expand_history("!-2")
        assert expanded == "echo test"
    
    def test_string_expansion(self):
        """Test !string expansion (most recent command starting with string)."""
        # !echo should find "echo test" (most recent echo)
        expanded = self.shell.history_expander.expand_history("!echo")
        assert expanded == "echo test"
        
        # !ls should find "ls -la"
        expanded = self.shell.history_expander.expand_history("!ls")
        assert expanded == "ls -la"
    
    def test_search_expansion(self):
        """Test !?string? expansion (command containing string)."""
        # !?la? should find "ls -la"
        expanded = self.shell.history_expander.expand_history("!?la?")
        assert expanded == "ls -la"
        
        # !?test? should find "echo test"
        expanded = self.shell.history_expander.expand_history("!?test?")
        assert expanded == "echo test"
    
    def test_expansion_in_context(self):
        """Test history expansion within a larger command."""
        # Should expand !! but leave the rest
        expanded = self.shell.history_expander.expand_history("!! | grep something")
        assert expanded == "cd /tmp | grep something"
        
        # Multiple expansions
        expanded = self.shell.history_expander.expand_history("!1 && !3")
        assert expanded == "echo first && pwd"
    
    def test_failed_expansion(self):
        """Test that failed expansions return None and print error."""
        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            # !999 should fail
            result = self.shell.history_expander.expand_history("!999")
            assert result is None
            assert "event not found" in sys.stderr.getvalue()
            
            # Reset stderr for next test
            sys.stderr = StringIO()
            
            # !xyz should fail (no command starting with xyz)
            result = self.shell.history_expander.expand_history("!xyz")
            assert result is None
            assert "event not found" in sys.stderr.getvalue()
            
        finally:
            sys.stderr = old_stderr
    
    def test_no_expansion_in_quotes(self):
        """Test that history expansion doesn't happen in certain contexts."""
        # For now, we do simple expansion everywhere
        # In the future, we might want to skip expansion in single quotes
        expanded = self.shell.history_expander.expand_history("echo '!!'")
        # Currently, we expand everywhere - this is a known limitation
        assert expanded == "echo 'cd /tmp'"
    
    def test_empty_history(self):
        """Test expansion with empty history."""
        shell = Shell(norc=True)
        shell.state.history_file = "/tmp/test_history_expansion_empty"
        shell.history.clear()
        
        # Should fail and return None when history is empty
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            expanded = shell.history_expander.expand_history("!!")
            assert expanded is None
            assert "event not found" in sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
    
    def test_expansion_prints_result(self, capsys):
        """Test that successful expansion prints the result in interactive mode."""
        # Need to make stdin look like a tty for the print to happen
        import os
        if not sys.stdin.isatty():
            # Skip this test in non-interactive environments
            pytest.skip("Test requires interactive terminal")
        
        expanded = self.shell.history_expander.expand_history("!!")
        captured = capsys.readouterr()
        assert "cd /tmp" in captured.out
    
    def test_word_boundary_matching(self):
        """Test that ! only triggers expansion at word boundaries."""
        # "Hello!" should not trigger expansion
        expanded = self.shell.history_expander.expand_history("echo Hello!")
        assert expanded == "echo Hello!"
        
        # "! " (! followed by space) doesn't expand - bash behavior
        result = self.shell.history_expander.expand_history("! command")
        assert result == "! command"
        
        # But "!c" should try to expand
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            result = self.shell.history_expander.expand_history("!xyz")
            # This will try to find a command starting with xyz, which fails
            assert result is None
            assert "event not found" in sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr