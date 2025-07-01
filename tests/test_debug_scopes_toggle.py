import pytest
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from psh.shell import Shell


class TestDebugScopesToggle:
    """Test runtime toggling of debug-scopes option."""
    
    def test_debug_scopes_off_by_default(self, shell):
        """Test that debug-scopes is off by default."""
        assert shell.state.debug_scopes is False
        assert shell.state.scope_manager._debug is False
    
    def test_enable_debug_scopes(self, shell):
        """Test enabling debug-scopes with set -o."""
        result = shell.run_command("set -o debug-scopes")
        assert result == 0
        assert shell.state.debug_scopes is True
        assert shell.state.scope_manager._debug is True
    
    def test_disable_debug_scopes(self, shell):
        """Test disabling debug-scopes with set +o."""
        # First enable it
        shell.run_command("set -o debug-scopes")
        assert shell.state.debug_scopes is True
        
        # Then disable it
        result = shell.run_command("set +o debug-scopes")
        assert result == 0
        assert shell.state.debug_scopes is False
        assert shell.state.scope_manager._debug is False
    
    def test_debug_scopes_output(self, shell):
        """Test that debug-scopes produces output when enabled."""
        # Enable debug-scopes
        shell.run_command("set -o debug-scopes")
        
        # Run a command that sets a variable and capture stderr
        f = StringIO()
        with redirect_stderr(f):
            shell.run_command("test_var=42")
        
        output = f.getvalue()
        assert "[SCOPE]" in output
        assert "test_var = 42" in output
    
    def test_debug_scopes_no_output_when_disabled(self, shell):
        """Test that debug-scopes produces no output when disabled."""
        # Make sure it's disabled
        shell.run_command("set +o debug-scopes")
        
        # Run a command that sets a variable and capture stderr
        f = StringIO()
        with redirect_stderr(f):
            shell.run_command("test_var=42")
        
        output = f.getvalue()
        assert "[SCOPE]" not in output
    
    def test_debug_scopes_with_functions(self, shell):
        """Test debug-scopes output with function calls."""
        # Enable debug-scopes
        shell.run_command("set -o debug-scopes")
        
        # Define a function
        shell.run_command("""
        test_func() {
            local x=10
            y=20
        }
        """)
        
        # Call the function and capture stderr
        f = StringIO()
        with redirect_stderr(f):
            shell.run_command("test_func")
        
        output = f.getvalue()
        # Should see scope push/pop and local variable creation
        assert "Pushing scope for function: test_func" in output
        assert "Creating local variable: x = 10" in output
        assert "Setting variable in scope 'global': y = 20" in output
        assert "Popping scope: test_func" in output
    
    def test_set_o_shows_debug_scopes(self, shell):
        """Test that 'set -o' shows debug-scopes status."""
        # Set environment variable to show all options including PSH debug options
        shell.state.env['PSH_SHOW_ALL_OPTIONS'] = '1'
        
        # Test when off
        f = StringIO()
        with redirect_stdout(f):
            shell.run_command("set -o")
        output = f.getvalue()
        assert "debug-scopes   \toff" in output
        
        # Enable and test again
        shell.run_command("set -o debug-scopes")
        f = StringIO()
        with redirect_stdout(f):
            shell.run_command("set -o")
        output = f.getvalue()
        assert "debug-scopes   \ton" in output
    
    def test_set_plus_o_shows_debug_scopes(self, shell):
        """Test that 'set +o' shows debug-scopes as set commands."""
        # Test when off
        f = StringIO()
        with redirect_stdout(f):
            shell.run_command("set +o")
        output = f.getvalue()
        assert "set +o debug-scopes" in output
        
        # Enable and test again
        shell.run_command("set -o debug-scopes")
        f = StringIO()
        with redirect_stdout(f):
            shell.run_command("set +o")
        output = f.getvalue()
        assert "set -o debug-scopes" in output
    
    def test_debug_scopes_shows_function_scope_operations(self, shell):
        """Test debug-scopes shows function scope operations."""
        # Enable debug-scopes
        shell.run_command("set -o debug-scopes")
        
        # Define and call a simple function
        shell.run_command("""
        simple_func() {
            echo "in function"
        }
        """)
        
        # Call the function and capture stderr
        f = StringIO()
        with redirect_stderr(f):
            shell.run_command("simple_func")
        
        output = f.getvalue()
        # Should see scope push/pop
        assert "[SCOPE]" in output
        assert "Pushing scope for function: simple_func" in output
        assert "Popping scope: simple_func" in output
    
    def test_debug_scopes_persists_across_commands(self, shell):
        """Test that debug-scopes setting persists across commands."""
        # Enable debug-scopes
        shell.run_command("set -o debug-scopes")
        
        # Run multiple commands
        f = StringIO()
        with redirect_stderr(f):
            shell.run_command("a=1")
            shell.run_command("b=2")
            shell.run_command("c=$a$b")
        
        output = f.getvalue()
        # Should see debug output for all three commands
        assert output.count("[SCOPE]") >= 3
        assert "a = 1" in output
        assert "b = 2" in output