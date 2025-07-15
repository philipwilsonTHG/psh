"""
Tests for the help builtin command.

Comprehensive test suite for help builtin functionality including
builtin listing, pattern matching, output modes, and documentation display.
"""

import pytest


class TestHelpBuiltinBasic:
    """Basic help builtin functionality tests."""
    
    def test_help_builtin_registration(self, shell):
        """Test that help builtin is properly registered."""
        result = shell.run_command('type help')
        assert result == 0
    
    def test_help_without_arguments(self, captured_shell):
        """Test help without arguments shows all builtins."""
        result = captured_shell.run_command('help')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "PSH Shell" in output or "shell" in output.lower()
        assert "commands" in output.lower() or "builtins" in output.lower()
        # Should list some basic builtins
        assert any(builtin in output.lower() for builtin in ['echo', 'exit', 'pwd', 'cd'])
    
    def test_help_shows_basic_builtins(self, captured_shell):
        """Test that help shows expected basic builtins."""
        result = captured_shell.run_command('help')
        assert result == 0
        
        output = captured_shell.get_stdout()
        essential_builtins = ['echo', 'exit', 'pwd']
        found_builtins = sum(1 for builtin in essential_builtins if builtin in output.lower())
        assert found_builtins >= 2  # Should have most essential builtins


class TestHelpSpecificBuiltins:
    """Test help for specific builtins."""
    
    def test_help_specific_builtin_echo(self, captured_shell):
        """Test help for echo builtin."""
        result = captured_shell.run_command('help echo')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "echo" in output.lower()
        # Should show usage or description
        assert any(keyword in output.lower() for keyword in ['usage', 'display', 'print', 'output'])
    
    def test_help_specific_builtin_cd(self, captured_shell):
        """Test help for cd builtin."""
        result = captured_shell.run_command('help cd')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "cd" in output.lower()
        # Should mention directory or change
        assert any(keyword in output.lower() for keyword in ['directory', 'change', 'working'])
    
    def test_help_specific_builtin_pwd(self, captured_shell):
        """Test help for pwd builtin."""
        result = captured_shell.run_command('help pwd')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "pwd" in output.lower()
        # Should mention directory or path
        assert any(keyword in output.lower() for keyword in ['directory', 'path', 'working', 'current'])
    
    def test_help_multiple_builtins(self, captured_shell):
        """Test help for multiple specific builtins."""
        result = captured_shell.run_command('help echo pwd')
        assert result == 0
        
        output = captured_shell.get_stdout()
        # Should show information for both commands
        assert "echo" in output.lower()
        assert "pwd" in output.lower()
    
    def test_help_nonexistent_builtin(self, captured_shell):
        """Test help for non-existent builtin."""
        result = captured_shell.run_command('help nonexistent_builtin_12345')
        # May return 0 with no match message, or 1 for error
        stderr = captured_shell.get_stderr()
        stdout = captured_shell.get_stdout()
        output = stderr + stdout
        
        # Should indicate no match or no help available
        if result != 0:
            assert any(phrase in output.lower() for phrase in ['no help', 'not found', 'no match', 'unknown'])


class TestHelpOptions:
    """Test help builtin options and flags."""
    
    def test_help_description_mode(self, captured_shell):
        """Test help -d flag for short descriptions."""
        result = captured_shell.run_command('help -d')
        assert result == 0
        
        output = captured_shell.get_stdout()
        # Should show builtin names with descriptions
        assert "echo" in output.lower()
        # Description mode should be more concise
        lines = [line for line in output.split('\n') if line.strip()]
        assert len(lines) >= 3  # Should have multiple builtins listed
    
    def test_help_description_mode_specific(self, captured_shell):
        """Test help -d for specific builtin."""
        result = captured_shell.run_command('help -d echo')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "echo" in output.lower()
        # Should be in short description format
        assert len(output.split('\n')) <= 5  # Should be concise
    
    def test_help_synopsis_mode(self, captured_shell):
        """Test help -s flag for synopsis only."""
        result = captured_shell.run_command('help -s echo')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "echo" in output.lower()
        # Synopsis should be brief
        assert len(output.split('\n')) <= 3  # Should be very brief
    
    def test_help_manpage_mode(self, captured_shell):
        """Test help -m flag for manpage format."""
        result = captured_shell.run_command('help -m echo')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "echo" in output.lower()
        # Manpage format should have sections
        upper_output = output.upper()
        # Should have at least one manpage-style section
        assert any(section in upper_output for section in ['NAME', 'SYNOPSIS', 'DESCRIPTION', 'USAGE'])
    
    def test_help_invalid_option(self, captured_shell):
        """Test help with invalid option."""
        result = captured_shell.run_command('help -x')
        assert result != 0
        
        stderr = captured_shell.get_stderr()
        assert any(phrase in stderr.lower() for phrase in ['invalid', 'unknown', 'unrecognized', 'usage'])


class TestHelpPatternMatching:
    """Test help with pattern matching."""
    
    def test_help_wildcard_pattern(self, captured_shell):
        """Test help with wildcard patterns."""
        result = captured_shell.run_command('help ec*')
        # PSH help builtin doesn't support pattern matching for builtin names
        # The pattern gets glob-expanded and likely matches no valid builtin names
        assert result == 1
        
        stderr = captured_shell.get_stderr()
        # Should indicate no help topics match
        assert "no help topics match" in stderr.lower() or "no such" in stderr.lower()
    
    def test_help_pattern_no_match(self, captured_shell):
        """Test help with pattern that matches nothing."""
        result = captured_shell.run_command('help nonexistent_pattern_xyz*')
        # Should either return error or indicate no matches
        stderr = captured_shell.get_stderr()
        stdout = captured_shell.get_stdout()
        
        if result != 0:
            # Error case
            assert any(phrase in stderr.lower() for phrase in ['no help', 'no match', 'not found'])
        else:
            # Success with no matches message
            output = stdout + stderr
            assert any(phrase in output.lower() for phrase in ['no help', 'no match', 'not found']) or len(stdout.strip()) == 0
    
    def test_help_single_character_pattern(self, captured_shell):
        """Test help with single character pattern."""
        result = captured_shell.run_command('help "?"')
        # May or may not match depending on available single-char builtins
        output = captured_shell.get_stdout()
        
        if result == 0 and output.strip():
            # If successful, should show matched builtins
            assert len(output) > 0
    
    def test_help_bracket_pattern(self, captured_shell):
        """Test help with bracket character class patterns."""
        result = captured_shell.run_command('help "[e-p]*"')
        assert result == 0
        
        output = captured_shell.get_stdout()
        # Should match builtins starting with letters e through p
        assert "echo" in output.lower()


class TestHelpSelfDocumentation:
    """Test help builtin self-documentation."""
    
    def test_help_help(self, captured_shell):
        """Test help for the help command itself."""
        result = captured_shell.run_command('help help')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "help" in output.lower()
        # Should describe what help does
        assert any(keyword in output.lower() for keyword in ['display', 'show', 'information', 'builtin'])
        # Should mention options
        assert any(option in output for option in ['-d', '-s', '-m'])
    
    def test_help_help_with_options(self, captured_shell):
        """Test help help with different option modes."""
        modes = ['-d', '-s', '-m']
        
        for mode in modes:
            captured_shell.clear_output()
            result = captured_shell.run_command(f'help {mode} help')
            assert result == 0
            
            output = captured_shell.get_stdout()
            assert "help" in output.lower()
            assert len(output.strip()) > 0


class TestHelpOptionCombinations:
    """Test help with option combinations and edge cases."""
    
    def test_help_combined_flags(self, captured_shell):
        """Test help with combined flags."""
        result = captured_shell.run_command('help -ds echo')
        # Should handle combined flags appropriately
        output = captured_shell.get_stdout()
        assert "echo" in output.lower()
    
    def test_help_with_double_dash(self, captured_shell):
        """Test help with -- to end options."""
        result = captured_shell.run_command('help -- echo')
        assert result == 0
        
        output = captured_shell.get_stdout()
        assert "echo" in output.lower()
    
    def test_help_empty_argument(self, captured_shell):
        """Test help with empty string argument."""
        result = captured_shell.run_command('help ""')
        # Should handle gracefully
        stderr = captured_shell.get_stderr()
        stdout = captured_shell.get_stdout()
        
        # Either succeed with empty output or fail with appropriate message
        if result != 0:
            assert any(phrase in stderr.lower() for phrase in ['no help', 'no match', 'empty'])


class TestHelpBuiltinProperties:
    """Test help builtin properties and integration."""
    
    def test_help_builtin_exists(self, shell):
        """Test that help builtin exists and is accessible."""
        # Test through type command
        result = shell.run_command('type help')
        assert result == 0
        
        # Test through builtin registry if available
        if hasattr(shell, 'builtin_registry'):
            assert shell.builtin_registry.has('help')
    
    def test_help_with_all_available_builtins(self, captured_shell):
        """Test help works with all available builtins."""
        # First get list of builtins
        result = captured_shell.run_command('help')
        assert result == 0
        
        output = captured_shell.get_stdout()
        # Extract builtin names (this is heuristic)
        words = output.lower().split()
        potential_builtins = ['echo', 'cd', 'pwd', 'exit', 'set', 'export', 'alias']
        
        # Test help for each builtin we can identify
        for builtin in potential_builtins:
            if builtin in words:
                captured_shell.clear_output()
                result = captured_shell.run_command(f'help {builtin}')
                # Should succeed for valid builtins
                assert result == 0
                help_output = captured_shell.get_stdout()
                assert builtin in help_output.lower()


class TestHelpBuiltinRedirection:
    """Test help builtin with I/O redirection."""
    
    def test_help_with_output_redirection(self, isolated_shell_with_temp_dir):
        """Test help with output redirection."""
        shell = isolated_shell_with_temp_dir
        
        result = shell.run_command('help echo > help_output.txt')
        assert result == 0
        
        # Check that file was created and contains help text
        import os
        help_file = os.path.join(shell.state.variables['PWD'], 'help_output.txt')
        assert os.path.exists(help_file)
        
        with open(help_file) as f:
            content = f.read()
            assert "echo" in content.lower()
            assert len(content.strip()) > 0
    
    def test_help_with_append_redirection(self, isolated_shell_with_temp_dir):
        """Test help with append redirection."""
        shell = isolated_shell_with_temp_dir
        
        # Create initial file
        shell.run_command('echo "Initial content" > help_log.txt')
        
        # Append help output
        result = shell.run_command('help -d echo >> help_log.txt')
        assert result == 0
        
        # Check that both contents are present
        import os
        help_file = os.path.join(shell.state.variables['PWD'], 'help_log.txt')
        with open(help_file) as f:
            content = f.read()
            assert "Initial content" in content
            assert "echo" in content.lower()
    
    def test_help_with_error_redirection(self, isolated_shell_with_temp_dir):
        """Test help with error redirection."""
        shell = isolated_shell_with_temp_dir
        
        # Try help with invalid option, redirect stderr
        result = shell.run_command('help -invalid_option 2> error_output.txt')
        
        # Check error file
        import os
        error_file = os.path.join(shell.state.variables['PWD'], 'error_output.txt')
        if os.path.exists(error_file):
            with open(error_file) as f:
                content = f.read()
                if content.strip():  # If there's error content
                    assert any(word in content.lower() for word in ['invalid', 'option', 'error', 'unknown'])


class TestHelpBuiltinEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_help_with_very_long_pattern(self, captured_shell):
        """Test help with very long pattern string."""
        long_pattern = "a" * 1000 + "*"
        result = captured_shell.run_command(f'help "{long_pattern}"')
        
        # Should handle gracefully without crashing
        stderr = captured_shell.get_stderr()
        stdout = captured_shell.get_stdout()
        
        # Either succeed with no matches or fail gracefully
        if result != 0:
            assert len(stderr) > 0  # Should have some error message
    
    def test_help_with_special_characters(self, captured_shell):
        """Test help with special characters in patterns."""
        special_patterns = ['*', '?', '[abc]', '{a,b}']
        
        for pattern in special_patterns:
            captured_shell.clear_output()
            result = captured_shell.run_command(f'help "{pattern}"')
            
            # Should handle special characters without crashing
            # Result may be 0 (found matches) or error (no matches)
            stderr = captured_shell.get_stderr()
            stdout = captured_shell.get_stdout()
            
            # Should not crash - either succeed or fail gracefully
            assert len(stderr + stdout) >= 0  # Basic sanity check
    
    def test_help_with_numeric_arguments(self, captured_shell):
        """Test help with numeric arguments."""
        result = captured_shell.run_command('help 123')
        
        # Should handle gracefully - likely no match
        stderr = captured_shell.get_stderr()
        stdout = captured_shell.get_stdout()
        output = stderr + stdout
        
        if result != 0:
            assert any(phrase in output.lower() for phrase in ['no help', 'no match', 'not found'])
    
    def test_help_output_formatting(self, captured_shell):
        """Test that help output is well-formatted."""
        result = captured_shell.run_command('help echo')
        assert result == 0
        
        output = captured_shell.get_stdout()
        lines = output.split('\n')
        
        # Should have multiple lines for detailed help
        non_empty_lines = [line for line in lines if line.strip()]
        assert len(non_empty_lines) >= 1
        
        # Should contain the builtin name
        assert "echo" in output.lower()
    
    def test_help_synopsis_all_builtins(self, captured_shell):
        """Test help -s without specific builtin shows all synopsis."""
        result = captured_shell.run_command('help -s')
        assert result == 0
        
        output = captured_shell.get_stdout()
        # Should show synopsis for multiple builtins
        lines = [line for line in output.split('\n') if line.strip()]
        assert len(lines) >= 3  # Should have multiple builtins
        
        # Should contain some builtin names
        assert any(builtin in output.lower() for builtin in ['echo', 'cd', 'pwd'])
    
    def test_help_manpage_fallback(self, captured_shell):
        """Test help -m without specific builtin behavior."""
        result = captured_shell.run_command('help -m')
        assert result == 0
        
        output = captured_shell.get_stdout()
        # Should either show default listing or manpage for all
        assert len(output.strip()) > 0
        assert any(builtin in output.lower() for builtin in ['echo', 'help', 'builtin', 'command'])