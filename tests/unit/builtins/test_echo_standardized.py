"""
Example of standardized test pattern for builtin output testing.

This demonstrates the recommended approach for testing builtin commands
that produce output, using the captured_shell fixture instead of capsys.
"""

import pytest


class TestEchoStandardized:
    """Standardized echo builtin tests using captured_shell fixture."""
    
    def test_echo_basic(self, captured_shell):
        """Test basic echo using captured_shell fixture."""
        result = captured_shell.run_command("echo hello world")
        assert result == 0
        assert captured_shell.get_stdout() == "hello world\n"
        assert captured_shell.get_stderr() == ""
    
    def test_echo_empty(self, captured_shell):
        """Test echo with no arguments."""
        result = captured_shell.run_command("echo")
        assert result == 0
        assert captured_shell.get_stdout() == "\n"
        assert captured_shell.get_stderr() == ""
    
    def test_echo_n_flag(self, captured_shell):
        """Test -n flag suppresses newline."""
        result = captured_shell.run_command("echo -n hello")
        assert result == 0
        assert captured_shell.get_stdout() == "hello"
        assert captured_shell.get_stderr() == ""
        
        # Clear output for next test
        captured_shell.clear_output()
        
        # Test -n with multiple arguments
        result = captured_shell.run_command("echo -n hello world")
        assert result == 0
        assert captured_shell.get_stdout() == "hello world"
        assert captured_shell.get_stderr() == ""
    
    def test_echo_with_variables(self, captured_shell):
        """Test echo with variable expansion."""
        captured_shell.run_command("VAR='test value'")
        captured_shell.clear_output()  # Clear any output from assignment
        
        result = captured_shell.run_command("echo $VAR")
        assert result == 0
        assert captured_shell.get_stdout() == "test value\n"
        assert captured_shell.get_stderr() == ""
    
    def test_echo_escape_sequences(self, captured_shell):
        """Test echo with escape sequences."""
        result = captured_shell.run_command("echo -e 'hello\\nworld'")
        assert result == 0
        assert captured_shell.get_stdout() == "hello\nworld\n"
        assert captured_shell.get_stderr() == ""
        
        # Clear for next test
        captured_shell.clear_output()
        
        # Test tab escape
        result = captured_shell.run_command("echo -e 'hello\\tworld'")
        assert result == 0
        assert captured_shell.get_stdout() == "hello\tworld\n"
        assert captured_shell.get_stderr() == ""
    
    def test_echo_error_output(self, captured_shell):
        """Test capturing error output from commands."""
        # This would test stderr capture if echo produced errors
        # For now, test that echo doesn't produce stderr
        result = captured_shell.run_command("echo normal output")
        assert result == 0
        assert captured_shell.get_stdout() == "normal output\n"
        assert captured_shell.get_stderr() == ""


class TestEchoEdgeCases:
    """Edge case tests for echo using captured_shell."""
    
    def test_echo_with_quotes(self, captured_shell):
        """Test echo with various quote types."""
        # Single quotes
        result = captured_shell.run_command("echo 'single quotes'")
        assert result == 0
        assert captured_shell.get_stdout() == "single quotes\n"
        
        captured_shell.clear_output()
        
        # Double quotes
        result = captured_shell.run_command('echo "double quotes"')
        assert result == 0
        assert captured_shell.get_stdout() == "double quotes\n"
        
        captured_shell.clear_output()
        
        # Mixed quotes
        result = captured_shell.run_command('''echo "it's mixed"''')
        assert result == 0
        assert captured_shell.get_stdout() == "it's mixed\n"
    
    def test_echo_special_characters(self, captured_shell):
        """Test echo with special characters."""
        # Test with asterisk
        result = captured_shell.run_command("echo '*'")
        assert result == 0
        assert captured_shell.get_stdout() == "*\n"
        
        captured_shell.clear_output()
        
        # Test with dollar sign
        result = captured_shell.run_command("echo '\\$'")
        assert result == 0
        # PSH preserves the backslash in single quotes
        assert captured_shell.get_stdout() == "\\$\n"


# Example of when NOT to use captured_shell
class TestEchoWithFileRedirection:
    """Tests that involve file I/O should use isolated_shell_with_temp_dir."""
    
    def test_echo_to_file(self, isolated_shell_with_temp_dir):
        """Test echo with output redirection."""
        shell = isolated_shell_with_temp_dir
        
        # Redirect echo output to file
        result = shell.run_command("echo 'test content' > output.txt")
        assert result == 0
        
        # Verify file contents
        result = shell.run_command("cat output.txt")
        assert result == 0
        # Note: We can't use captured output here due to redirection
        
        # Alternative: read file directly
        import os
        with open(os.path.join(shell.state.variables['PWD'], 'output.txt')) as f:
            assert f.read() == "test content\n"
    
    def test_echo_append_to_file(self, isolated_shell_with_temp_dir):
        """Test echo with append redirection."""
        shell = isolated_shell_with_temp_dir
        
        # Create initial file
        shell.run_command("echo 'line 1' > output.txt")
        
        # Append to file
        result = shell.run_command("echo 'line 2' >> output.txt")
        assert result == 0
        
        # Verify both lines are present
        import os
        with open(os.path.join(shell.state.variables['PWD'], 'output.txt')) as f:
            content = f.read()
            assert "line 1\n" in content
            assert "line 2\n" in content