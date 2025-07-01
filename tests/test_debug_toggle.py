#!/usr/bin/env python3
"""Test runtime debug toggle functionality."""

import pytest
import sys
import os
from io import StringIO

# Add psh module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from psh.shell import Shell


class TestDebugToggle:
    """Test debug option toggling at runtime."""
    
    def test_initial_debug_state(self):
        """Test that debug options are initially off."""
        shell = Shell()
        assert shell.state.debug_ast is False
        assert shell.state.debug_tokens is False
    
    def test_enable_debug_ast(self):
        """Test enabling AST debug at runtime."""
        shell = Shell()
        # Enable debug-ast
        exit_code = shell.run_command("set -o debug-ast")
        assert exit_code == 0
        assert shell.state.debug_ast is True
        assert shell.state.debug_tokens is False
    
    def test_enable_debug_tokens(self):
        """Test enabling token debug at runtime."""
        shell = Shell()
        # Enable debug-tokens
        exit_code = shell.run_command("set -o debug-tokens")
        assert exit_code == 0
        assert shell.state.debug_ast is False
        assert shell.state.debug_tokens is True
    
    def test_disable_debug_options(self):
        """Test disabling debug options."""
        shell = Shell()
        # Enable both options first
        shell.run_command("set -o debug-ast")
        shell.run_command("set -o debug-tokens")
        assert shell.state.debug_ast is True
        assert shell.state.debug_tokens is True
        
        # Disable debug-ast
        exit_code = shell.run_command("set +o debug-ast")
        assert exit_code == 0
        assert shell.state.debug_ast is False
        assert shell.state.debug_tokens is True
        
        # Disable debug-tokens
        exit_code = shell.run_command("set +o debug-tokens")
        assert exit_code == 0
        assert shell.state.debug_tokens is False
    
    def test_show_options(self):
        """Test showing current options with set -o."""
        shell = Shell()
        # Enable one option
        shell.run_command("set -o debug-ast")
        
        # Set environment variable to show all options including PSH debug options
        shell.state.env['PSH_SHOW_ALL_OPTIONS'] = '1'
        
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            exit_code = shell.run_command("set -o")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        
        assert exit_code == 0
        assert "debug-ast      \ton" in output
        assert "debug-tokens   \toff" in output
        # In new format, edit mode shows as separate emacs/vi options
        assert "emacs          \ton" in output or "vi             \ton" in output
    
    def test_show_options_as_commands(self):
        """Test showing options as set commands with set +o."""
        shell = Shell()
        # Enable debug-ast
        shell.run_command("set -o debug-ast")
        
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            exit_code = shell.run_command("set +o")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        
        assert exit_code == 0
        assert "set -o debug-ast" in output
        assert "set +o debug-tokens" in output
    
    def test_debug_output_with_ast(self):
        """Test that debug-ast actually produces output."""
        shell = Shell()
        # Enable debug-ast
        shell.run_command("set -o debug-ast")
        
        # Capture stderr (where debug output goes)
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            shell.run_command("echo hello")
            debug_output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        
        assert "=== AST Debug Output ===" in debug_output
        assert "Command:" in debug_output or "TopLevel:" in debug_output
    
    def test_debug_output_with_tokens(self):
        """Test that debug-tokens actually produces output."""
        shell = Shell()
        # Enable debug-tokens
        shell.run_command("set -o debug-tokens")
        
        # Capture stderr (where debug output goes)
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            shell.run_command("echo hello")
            debug_output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        
        assert "=== Token Debug Output ===" in debug_output
        assert "WORD" in debug_output
        assert "'echo'" in debug_output
        assert "'hello'" in debug_output
    
    def test_invalid_option(self):
        """Test error handling for invalid options."""
        shell = Shell()
        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            exit_code = shell.run_command("set -o invalid-option")
            error_output = sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr
        
        assert exit_code == 1
        assert "invalid option: invalid-option" in error_output
        assert "Valid options:" in error_output
    
    def test_underscore_vs_dash(self):
        """Test that both debug_ast and debug-ast work."""
        shell = Shell()
        # Test with underscore
        exit_code = shell.run_command("set -o debug_ast")
        assert exit_code == 0
        assert shell.state.debug_ast is True
        
        # Disable and test with dash
        shell.run_command("set +o debug-ast")
        assert shell.state.debug_ast is False
        
        exit_code = shell.run_command("set -o debug-ast")
        assert exit_code == 0
        assert shell.state.debug_ast is True
    
    def test_persistence_across_commands(self):
        """Test that debug settings persist across multiple commands."""
        shell = Shell()
        # Enable debug options
        shell.run_command("set -o debug-ast")
        shell.run_command("set -o debug-tokens")
        
        # Run several commands
        shell.run_command("echo test1")
        shell.run_command("pwd")
        shell.run_command("echo test2")
        
        # Options should still be enabled
        assert shell.state.debug_ast is True
        assert shell.state.debug_tokens is True
        
        # Disable one option
        shell.run_command("set +o debug-ast")
        
        # Run more commands
        shell.run_command("echo test3")
        
        # Check final state
        assert shell.state.debug_ast is False
        assert shell.state.debug_tokens is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])