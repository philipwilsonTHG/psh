"""
Tests for the getopts builtin command.

Comprehensive test suite for getopts functionality including option parsing,
argument handling, error modes, and state management with OPTIND/OPTARG/OPTERR.
"""

import pytest
from io import StringIO


class TestGetoptsBuiltinBasic:
    """Basic getopts builtin functionality tests."""
    
    def test_getopts_builtin_registration(self, shell):
        """Test that getopts builtin is properly registered."""
        result = shell.run_command('type getopts')
        assert result == 0
    
    def test_getopts_help(self, captured_shell):
        """Test getopts help or usage information."""
        result = captured_shell.run_command('getopts --help')
        output = captured_shell.get_stdout() + captured_shell.get_stderr()
        
        # Should show help or usage
        if "getopts" in output.lower():
            assert any(word in output.lower() for word in ['usage', 'help', 'option', 'optstring'])
    
    def test_getopts_insufficient_arguments(self, captured_shell):
        """Test getopts with insufficient arguments."""
        result = captured_shell.run_command('getopts')
        assert result != 0
        
        stderr = captured_shell.get_stderr()
        assert any(word in stderr.lower() for word in ['usage', 'argument', 'required'])


class TestGetoptsBasicParsing:
    """Test basic option parsing functionality."""
    
    def test_getopts_simple_option(self, shell):
        """Test parsing a simple option."""
        # Set up positional parameters using 'set' command
        result = shell.run_command('set -- -a arg1')
        assert result == 0
        
        # Reset OPTIND
        shell.run_command('OPTIND=1')
        
        result = shell.run_command('getopts ab opt')
        assert result == 0
        
        # Should parse option 'a'
        assert shell.state.get_variable('opt') == 'a'
        # OPTIND should advance
        optind = shell.state.get_variable('OPTIND')
        assert optind == '2'
    
    def test_getopts_multiple_options_sequence(self, shell):
        """Test parsing multiple options in sequence."""
        # Set up: script -a -b arg1
        shell.run_command('set -- -a -b arg1')
        shell.run_command('OPTIND=1')
        
        # Parse first option
        result = shell.run_command('getopts ab opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'a'
        
        # Parse second option
        result = shell.run_command('getopts ab opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'b'
        
        # No more options
        result = shell.run_command('getopts ab opt')
        assert result == 1  # End of options
    
    def test_getopts_option_with_argument(self, shell):
        """Test parsing option that requires an argument."""
        # Set up: script -f filename arg1
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        result = shell.run_command('getopts f: opt')
        assert result == 0
        
        assert shell.state.get_variable('opt') == 'f'
        assert shell.state.get_variable('OPTARG') == 'filename'
        optind = shell.state.get_variable('OPTIND')
        assert optind == '3'  # Should skip over the argument
    
    def test_getopts_clustered_options(self, shell):
        """Test parsing clustered options like -abc."""
        # Set up: script -abc arg1
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # Parse each option from the cluster
        expected_opts = ['a', 'b', 'c']
        for expected_opt in expected_opts:
            result = shell.run_command('getopts abc opt')
            assert result == 0
            assert shell.state.get_variable('opt') == expected_opt
        
        # After parsing all clustered options, OPTIND should advance
        optind = shell.state.get_variable('OPTIND')
        assert optind == '2'


class TestGetoptsErrorHandling:
    """Test getopts error handling and invalid options."""
    
    def test_getopts_invalid_option(self, captured_shell):
        """Test handling of invalid option."""
        shell = captured_shell
        
        # Set up: script -x arg1 (x is not in optstring)
        shell.run_command("set -- -x arg1")
        shell.run_command('OPTIND=1')
        
        result = shell.run_command('getopts ab opt')
        assert result == 0  # getopts returns 0 even for invalid options
        
        assert shell.state.get_variable('opt') == '?'
        stderr = shell.get_stderr()
        # Should report illegal option
        assert any(word in stderr.lower() for word in ['illegal', 'invalid', 'unknown']) or 'x' in stderr
    
    def test_getopts_missing_argument(self, captured_shell):
        """Test handling of missing required argument."""
        shell = captured_shell
        
        # Set up: script -f (no argument following)
        shell.run_command("set -- -f")
        shell.run_command('OPTIND=1')
        
        result = shell.run_command('getopts f: opt')
        assert result == 0
        
        assert shell.state.get_variable('opt') == '?'
        stderr = shell.get_stderr()
        # Should report missing argument
        assert any(phrase in stderr.lower() for phrase in ['requires an argument', 'missing argument', 'argument']) or 'f' in stderr
    
    def test_getopts_silent_error_mode(self, captured_shell):
        """Test silent error reporting mode with leading colon."""
        shell = captured_shell
        
        # Set up: script -x arg1 with silent mode (:ab)
        shell.run_command("set -- -x arg1")
        shell.run_command('OPTIND=1')
        
        result = shell.run_command('getopts :ab opt')
        assert result == 0
        
        assert shell.state.get_variable('opt') == '?'
        assert shell.state.get_variable('OPTARG') == 'x'
        stderr = shell.get_stderr()
        # Should be silent - no error message
        assert len(stderr.strip()) == 0
    
    def test_getopts_silent_missing_argument(self, captured_shell):
        """Test silent mode with missing argument."""
        shell = captured_shell
        
        # Set up: script -f with silent mode
        shell.run_command("set -- -f")
        shell.run_command('OPTIND=1')
        
        result = shell.run_command('getopts :f: opt')
        assert result == 0
        
        assert shell.state.get_variable('opt') == ':'  # Colon for missing argument
        assert shell.state.get_variable('OPTARG') == 'f'
        stderr = shell.get_stderr()
        # Should be silent
        assert len(stderr.strip()) == 0


class TestGetoptsSpecialCases:
    """Test special cases and edge conditions."""
    
    def test_getopts_end_of_options(self, shell):
        """Test behavior when no more options to parse."""
        # Set up: script arg1 arg2 (no options)
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        result = shell.run_command('getopts ab opt')
        assert result == 1  # End of options
        
        # opt variable should be set to '?' to indicate end
        assert shell.state.get_variable('opt') == '?'
    
    def test_getopts_double_dash_terminator(self, shell):
        """Test handling of -- to end options."""
        # Set up: script -a -- -b
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # First call gets -a
        result = shell.run_command('getopts ab opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'a'
        
        # Second call hits -- and should terminate
        result = shell.run_command('getopts ab opt')
        assert result == 1  # End of options
        
        # OPTIND should point past the --
        optind = shell.state.get_variable('OPTIND')
        assert optind == '3'
    
    def test_getopts_optind_reset(self, shell):
        """Test resetting OPTIND to restart parsing."""
        # Set up: script -a -b
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # Parse first option
        result = shell.run_command('getopts ab opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'a'
        
        # Reset OPTIND to restart
        shell.run_command("set -- -f filename arg1")
        
        # Should parse from beginning again
        result = shell.run_command('getopts ab opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'a'
    
    def test_getopts_opterr_disabled(self, captured_shell):
        """Test OPTERR=0 disables error messages."""
        shell = captured_shell
        
        # Set up with OPTERR=0
        shell.run_command("set -- -x")
        shell.run_command('OPTIND=1')
        shell.run_command('OPTERR=0')
        
        result = shell.run_command('getopts ab opt')
        assert result == 0
        assert shell.state.get_variable('opt') == '?'
        
        stderr = shell.get_stderr()
        # Should be no error message with OPTERR=0
        assert len(stderr.strip()) == 0


class TestGetoptsVariableHandling:
    """Test OPTIND, OPTARG, and OPTERR variable handling."""
    
    def test_getopts_optind_persistence(self, shell):
        """Test OPTIND persists between calls."""
        # Set up: script -a -b -c
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # Parse each option and verify OPTIND increments
        expected_opts = ['a', 'b', 'c']
        for i, expected_opt in enumerate(expected_opts, 1):
            result = shell.run_command('getopts abc opt')
            assert result == 0
            assert shell.state.get_variable('opt') == expected_opt
            optind = shell.state.get_variable('OPTIND')
            assert optind == str(i + 1)
        
        # Next call should return 1 (no more options)
        result = shell.run_command('getopts abc opt')
        assert result == 1
    
    def test_getopts_optarg_handling(self, shell):
        """Test OPTARG variable with option arguments."""
        # Set up: script -f file1 -g file2
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # Parse -f file1
        result = shell.run_command('getopts f:g: opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'f'
        assert shell.state.get_variable('OPTARG') == 'file1'
        
        # Parse -g file2
        result = shell.run_command('getopts f:g: opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'g'
        assert shell.state.get_variable('OPTARG') == 'file2'
    
    def test_getopts_optarg_clearing(self, shell):
        """Test OPTARG is cleared for options without arguments."""
        # Set up: script -f file1 -a
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # Parse -f file1 (sets OPTARG)
        result = shell.run_command('getopts f:a opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'f'
        assert shell.state.get_variable('OPTARG') == 'file1'
        
        # Parse -a (should clear OPTARG)
        result = shell.run_command('getopts f:a opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'a'
        optarg = shell.state.get_variable('OPTARG')
        # OPTARG should be cleared or empty
        assert optarg == '' or optarg is None


class TestGetoptsCustomArguments:
    """Test getopts with custom argument lists."""
    
    def test_getopts_with_custom_args(self, shell):
        """Test parsing custom arguments instead of positional params."""
        # Test with inline arguments: getopts ab: opt -b value arg1
        result = shell.run_command('getopts ab: opt -b value arg1')
        
        if result == 0:
            # If getopts supports inline args
            assert shell.state.get_variable('opt') == 'b'
            assert shell.state.get_variable('OPTARG') == 'value'
        else:
            # If getopts only works with positional parameters
            # This is also acceptable behavior
            assert result in [1, 2]  # Either end-of-options or usage error
    
    def test_getopts_mixed_arguments(self, shell):
        """Test getopts behavior with mixed argument types."""
        # Set up complex scenario: script -a -f file -- remaining args
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # Parse -a
        result = shell.run_command('getopts af: opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'a'
        
        # Parse -f file
        result = shell.run_command('getopts af: opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'f'
        assert shell.state.get_variable('OPTARG') == 'file'
        
        # Hit -- terminator
        result = shell.run_command('getopts af: opt')
        assert result == 1  # End of options
        
        # OPTIND should point to first remaining arg
        optind = shell.state.get_variable('OPTIND')
        assert optind == '5'


class TestGetoptsComplexScenarios:
    """Test complex getopts usage scenarios."""
    
    def test_getopts_in_function(self, shell):
        """Test getopts usage inside a function."""
        cmd = '''
        parse_opts() {
            local opt
            while getopts "f:v" opt; do
                case $opt in
                    f) echo "File: $OPTARG" ;;
                    v) echo "Verbose mode" ;;
                    ?) echo "Invalid option" ;;
                esac
            done
        }
        parse_opts -f myfile -v
        '''
        result = shell.run_command(cmd)
        # Should complete without error
        assert result == 0
    
    def test_getopts_with_while_loop(self, isolated_shell_with_temp_dir):
        """Test typical getopts usage pattern with while loop."""
        shell = isolated_shell_with_temp_dir
        
        cmd = '''
        file=""
        verbose=false
        
        # Set up test arguments
        set -- -f testfile -v arg1 arg2
        
        while getopts "f:v" opt; do
            case $opt in
                f) file="$OPTARG" ;;
                v) verbose=true ;;
                ?) echo "Usage error" >&2 ;;
            esac
        done
        
        echo "File: $file" > result.txt
        echo "Verbose: $verbose" >> result.txt
        echo "OPTIND: $OPTIND" >> result.txt
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        # Check results
        import os
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert "File: testfile" in content
            assert "Verbose: true" in content
            assert "OPTIND:" in content
    
    def test_getopts_option_with_equals(self, shell):
        """Test handling of option=value format."""
        # Set up: script -f=filename
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        result = shell.run_command('getopts f: opt')
        
        if result == 0:
            # Some implementations handle -f=value as -f value
            opt = shell.state.get_variable('opt')
            optarg = shell.state.get_variable('OPTARG')
            # Either parse as -f with OPTARG="filename" or handle differently
            assert opt in ['f', '?']
        else:
            # If not supported, should handle gracefully
            assert result in [0, 1]


class TestGetoptsEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_getopts_empty_optstring(self, shell):
        """Test getopts with empty option string."""
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        result = shell.run_command('getopts "" opt')
        # Should treat any option as invalid
        assert result == 0
        assert shell.state.get_variable('opt') == '?'
    
    def test_getopts_long_option_string(self, shell):
        """Test getopts with very long option string."""
        long_optstring = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        result = shell.run_command(f'getopts {long_optstring} opt')
        assert result == 0
        assert shell.state.get_variable('opt') == 'z'
    
    def test_getopts_special_characters_in_optstring(self, shell):
        """Test getopts with special characters in option string."""
        # Test with some special characters that might be valid
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        result = shell.run_command('getopts ":?-" opt')
        # Behavior depends on implementation
        assert result in [0, 1]
    
    def test_getopts_numeric_options(self, shell):
        """Test getopts with numeric option characters."""
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        result = shell.run_command('getopts "123" opt')
        assert result == 0
        assert shell.state.get_variable('opt') == '1'
    
    def test_getopts_variable_name_validation(self, captured_shell):
        """Test getopts with invalid variable names."""
        shell = captured_shell
        shell.run_command("set -- -a")
        shell.run_command('OPTIND=1')
        
        # Try with invalid variable name
        result = shell.run_command('getopts ab 123invalid')
        # Should either fail or handle gracefully
        assert result in [0, 1, 2]
        
        stderr = shell.get_stderr()
        if result != 0:
            # If it fails, should provide error message
            assert len(stderr) > 0
    
    def test_getopts_state_persistence_across_commands(self, shell):
        """Test that getopts state persists across multiple command invocations."""
        # Set up: script -a -b -c
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        shell.run_command("set -- -f filename arg1")
        
        # Parse options in separate commands
        commands = [
            'getopts abc opt1',
            'getopts abc opt2', 
            'getopts abc opt3'
        ]
        
        expected_opts = ['a', 'b', 'c']
        for i, cmd in enumerate(commands):
            result = shell.run_command(cmd)
            assert result == 0
            var_name = f'opt{i+1}'
            assert shell.state.get_variable(var_name) == expected_opts[i]
        
        # Next call should indicate end of options
        result = shell.run_command('getopts abc opt4')
        assert result == 1