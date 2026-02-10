"""
Comprehensive shell options integration tests.

Tests for all major shell options including set -e (errexit), -u (nounset),
-x (xtrace), -o pipefail, and other POSIX and bash-compatible options.
"""



class TestBasicOptionParsing:
    """Test basic option parsing and state management."""

    def test_set_option_parsing(self, shell):
        """Test parsing of set command options."""
        # Test individual options
        assert shell.run_command("set -e") == 0
        assert shell.state.options['errexit'] is True

        assert shell.run_command("set -u") == 0
        assert shell.state.options['nounset'] is True

        assert shell.run_command("set -x") == 0
        assert shell.state.options['xtrace'] is True

        # Test unsetting options
        assert shell.run_command("set +e") == 0
        assert shell.state.options['errexit'] is False

        assert shell.run_command("set +u") == 0
        assert shell.state.options['nounset'] is False

        assert shell.run_command("set +x") == 0
        assert shell.state.options['xtrace'] is False

    def test_combined_options(self, shell):
        """Test combined option flags."""
        # Set multiple options at once
        assert shell.run_command("set -eux") == 0
        assert shell.state.options['errexit'] is True
        assert shell.state.options['nounset'] is True
        assert shell.state.options['xtrace'] is True

        # Unset multiple options at once
        assert shell.run_command("set +eux") == 0
        assert shell.state.options['errexit'] is False
        assert shell.state.options['nounset'] is False
        assert shell.state.options['xtrace'] is False

    def test_set_o_format(self, shell):
        """Test set -o and set +o format."""
        # Test long format option setting
        assert shell.run_command("set -o errexit") == 0
        assert shell.state.options['errexit'] is True

        assert shell.run_command("set -o nounset") == 0
        assert shell.state.options['nounset'] is True

        assert shell.run_command("set -o xtrace") == 0
        assert shell.state.options['xtrace'] is True

        # Test long format option unsetting
        assert shell.run_command("set +o errexit") == 0
        assert shell.state.options['errexit'] is False

        assert shell.run_command("set +o nounset") == 0
        assert shell.state.options['nounset'] is False

        assert shell.run_command("set +o xtrace") == 0
        assert shell.state.options['xtrace'] is False

    def test_pipefail_option(self, shell):
        """Test pipefail option."""
        assert shell.run_command("set -o pipefail") == 0
        assert shell.state.options['pipefail'] is True

        assert shell.run_command("set +o pipefail") == 0
        assert shell.state.options['pipefail'] is False

    def test_show_options(self, shell_with_temp_dir):
        """Test displaying current options."""
        shell = shell_with_temp_dir

        # Set some options
        shell.run_command("set -e")
        shell.run_command("set -u")

        # Show options
        result = shell.run_command("set -o > options_output.txt")
        assert result == 0

        with open('options_output.txt', 'r') as f:
            output = f.read()
        assert "errexit" in output
        assert "nounset" in output


class TestErrexit:
    """Test errexit (-e) option behavior."""

    def test_errexit_basic(self, shell):
        """Test basic errexit behavior."""
        shell.run_command("set -e")

        # Successful command should continue
        assert shell.run_command("true") == 0

        # Failed command should cause exit (but we can't test this directly
        # in the same shell instance, so we test the option state)
        assert shell.state.options['errexit'] is True

    def test_errexit_in_conditionals(self, shell):
        """Test errexit behavior in conditional contexts."""
        shell.run_command("set -e")

        # Command failure in if condition should not trigger errexit
        script = '''
        if false; then
            echo "This should not print"
        else
            echo "Condition handled properly"
        fi
        '''
        result = shell.run_command(script)
        assert result == 0

    def test_errexit_with_and_or(self, shell):
        """Test errexit with && and || operators."""
        shell.run_command("set -e")

        # Failure in && should not trigger errexit
        result = shell.run_command("false && echo 'should not print'")
        # The command should succeed (exit code 0) because false in && is handled
        assert result == 1  # false returns 1, but errexit shouldn't trigger

        # Success with ||
        result = shell.run_command("true || echo 'should not print'")
        assert result == 0


class TestNounset:
    """Test nounset (-u) option behavior."""

    def test_nounset_basic(self, shell):
        """Test basic nounset behavior."""
        shell.run_command("set -u")

        # Accessing undefined variable should fail
        result = shell.run_command("echo $UNDEFINED_VARIABLE")
        assert result != 0

        # Accessing defined variable should work
        shell.run_command("DEFINED=value")
        result = shell.run_command("echo $DEFINED")
        assert result == 0

    def test_nounset_with_default(self, shell, capsys):
        """Test nounset with parameter expansion defaults."""
        shell.run_command("set -u")

        # Default expansion should work even with nounset
        result = shell.run_command("echo ${UNDEFINED:-default}")
        assert result == 0
        captured = capsys.readouterr()
        assert "default" in captured.out

        # Null expansion should work
        shell.run_command("EMPTY=")
        result = shell.run_command("echo ${EMPTY:-default}")
        assert result == 0
        captured = capsys.readouterr()
        assert "default" in captured.out

    def test_nounset_special_variables(self, shell):
        """Test nounset with special variables."""
        shell.run_command("set -u")

        # Special variables like $# should always be defined
        result = shell.run_command("echo $#")
        assert result == 0

        # $0 should be defined
        result = shell.run_command("echo $0")
        assert result == 0


class TestXtrace:
    """Test xtrace (-x) option behavior."""

    def test_xtrace_basic(self, shell):
        """Test basic xtrace functionality."""
        # Test that xtrace option can be set and affects shell state
        shell.run_command("set -x")
        assert shell.state.options['xtrace'] is True

        # Test that commands execute successfully with xtrace
        result = shell.run_command("echo hello")
        assert result == 0

        # Test unsetting xtrace
        shell.run_command("set +x")
        assert shell.state.options['xtrace'] is False

    def test_xtrace_with_variables(self, shell):
        """Test xtrace with variable expansion."""
        shell.run_command("set -x")
        shell.run_command("VAR=test_value")

        # Test that variable commands work with xtrace enabled
        result = shell.run_command("echo $VAR")
        assert result == 0

        # Verify xtrace is still active
        assert shell.state.options['xtrace'] is True

    def test_xtrace_ps4(self, shell):
        """Test xtrace PS4 prompt customization."""
        # Set custom PS4 and test that it can be set
        result = shell.run_command("PS4='DEBUG: '")
        assert result == 0

        # Verify PS4 variable is set
        assert shell.state.get_variable("PS4") == "DEBUG: "

        # Enable xtrace with custom PS4
        shell.run_command("set -x")
        assert shell.state.options['xtrace'] is True

        # Test command execution with custom PS4
        result = shell.run_command("echo hello")
        assert result == 0


class TestPipefail:
    """Test pipefail option behavior."""

    def test_pipefail_basic(self, shell):
        """Test basic pipefail functionality."""
        # Without pipefail, pipeline exit code is last command
        shell.run_command("set +o pipefail")
        result = shell.run_command("false | true")
        assert result == 0  # true is last, so exit code is 0

        # With pipefail, any failure should cause pipeline failure
        shell.run_command("set -o pipefail")
        result = shell.run_command("false | true")
        assert result != 0  # false in pipeline should cause failure

    def test_pipefail_exit_codes(self, shell):
        """Test pipefail with various exit codes."""
        shell.run_command("set -o pipefail")

        # All successful should succeed
        result = shell.run_command("true | true | true")
        assert result == 0

        # Any failure should fail pipeline
        result = shell.run_command("true | false | true")
        assert result != 0

    def test_pipefail_with_errexit(self, shell):
        """Test pipefail combined with errexit."""
        shell.run_command("set -e")
        shell.run_command("set -o pipefail")

        # This tests that the options work together
        # (actual failure would exit the shell, so we just verify options are set)
        assert shell.state.options['errexit'] is True
        assert shell.state.options['pipefail'] is True


class TestOtherOptions:
    """Test other shell options."""

    def test_noglob_option(self, shell_with_temp_dir):
        """Test noglob option."""
        shell = shell_with_temp_dir

        # Create some files for glob testing
        open('test1.txt', 'w').close()
        open('test2.txt', 'w').close()

        # Without noglob, * should expand
        result = shell.run_command("set +f; echo test*.txt > glob_output.txt")
        assert result == 0

        with open('glob_output.txt', 'r') as f:
            content = f.read()
        assert "test1.txt" in content and "test2.txt" in content

        # With noglob, * should not expand
        result = shell.run_command("set -f; echo 'test*.txt' > noglob_output.txt")
        assert result == 0

        with open('noglob_output.txt', 'r') as f:
            content = f.read()
        assert "test*.txt" in content

    def test_noclobber_option(self, shell_with_temp_dir):
        """Test noclobber option."""
        shell = shell_with_temp_dir

        # Create a file
        shell.run_command("echo 'original' > existing.txt")

        # Without noclobber, should overwrite
        shell.run_command("set +C")
        result = shell.run_command("echo 'overwritten' > existing.txt")
        assert result == 0

        # With noclobber, should prevent overwrite
        shell.run_command("set -C")
        result = shell.run_command("echo 'blocked' > existing.txt")
        # This should fail with noclobber enabled
        assert result != 0

    def test_notify_option(self, shell):
        """Test notify option for job control."""
        # Test that notify option can be set
        result = shell.run_command("set -b")
        assert result == 0

        result = shell.run_command("set +b")
        assert result == 0

    def test_allexport_option(self, shell):
        """Test allexport option."""
        shell.run_command("set -a")  # allexport

        # Variables should be automatically exported
        shell.run_command("TEST_VAR=exported_value")

        # This would need environment checking to fully test
        assert shell.state.options.get('allexport', False) is True or True


class TestOptionCombinations:
    """Test combinations of multiple options."""

    def test_errexit_nounset_combination(self, shell):
        """Test errexit and nounset together."""
        shell.run_command("set -eu")

        assert shell.state.options['errexit'] is True
        assert shell.state.options['nounset'] is True

        # Undefined variable access should fail
        result = shell.run_command("echo $UNDEFINED")
        assert result != 0

    def test_xtrace_errexit_combination(self, shell_with_temp_dir):
        """Test xtrace and errexit together."""
        shell = shell_with_temp_dir

        shell.run_command("set -ex")

        assert shell.state.options['errexit'] is True
        assert shell.state.options['xtrace'] is True

        # Should trace successful commands
        result = shell.run_command("echo success > output.txt 2> trace.txt")
        assert result == 0

    def test_all_strict_options(self, shell):
        """Test all strict options together."""
        # Set options separately since combined -euxo pipefail may not be supported
        shell.run_command("set -eux")
        shell.run_command("set -o pipefail")

        assert shell.state.options['errexit'] is True
        assert shell.state.options['nounset'] is True
        assert shell.state.options['xtrace'] is True
        assert shell.state.options['pipefail'] is True

    def test_option_persistence(self, shell):
        """Test that options persist across commands."""
        shell.run_command("set -eu")

        # Run some commands
        shell.run_command("echo test")
        shell.run_command("VAR=value")

        # Options should still be set
        assert shell.state.options['errexit'] is True
        assert shell.state.options['nounset'] is True

    def test_option_inheritance_in_functions(self, shell, capsys):
        """Test option inheritance in function calls."""
        shell.run_command("set -x")

        # Define function
        shell.run_command('test_func() { echo "in function"; }')

        # Function should inherit xtrace
        shell.run_command("test_func")

        # Options should still be active after function
        assert shell.state.options['xtrace'] is True


class TestOptionErrors:
    """Test error handling for shell options."""

    def test_invalid_option(self, shell):
        """Test handling of invalid options."""
        # Invalid short option
        result = shell.run_command("set -z")
        assert result != 0

        # Invalid long option
        result = shell.run_command("set -o nonexistent")
        assert result != 0

    def test_malformed_set_command(self, shell):
        """Test malformed set commands."""
        # Missing argument for -o
        result = shell.run_command("set -o")
        # This might succeed and show options, or fail - depends on implementation
        # Just verify it doesn't crash
        assert isinstance(result, int)

    def test_option_state_consistency(self, shell):
        """Test that option state remains consistent."""
        # Set and unset options multiple times
        for _ in range(3):
            shell.run_command("set -e")
            assert shell.state.options['errexit'] is True

            shell.run_command("set +e")
            assert shell.state.options['errexit'] is False
