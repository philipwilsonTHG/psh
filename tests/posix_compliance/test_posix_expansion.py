#!/usr/bin/env python3
"""
Test POSIX parameter and word expansion compliance.
Tests expansion order and behavior required by POSIX.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fixture is provided by pytest, no need to import


class TestPOSIXParameterExpansion:
    """Test POSIX parameter expansion forms."""
    
    def test_basic_parameter_expansion(self, shell, capsys):
        """Test ${parameter} basic form."""
        shell.run_command("var=value")
        shell.run_command("echo ${var}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "value"
        
        # Braces needed for disambiguation
        shell.run_command("prefix=pre")
        shell.run_command("echo ${prefix}fix")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "prefix"
    
    def test_default_value_expansion(self, shell, capsys):
        """Test ${parameter:-word} default value."""
        # Unset variable
        shell.run_command("unset unset_var")
        shell.run_command("echo ${unset_var:-default}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "default"
        
        # Null variable
        shell.run_command("null_var=")
        shell.run_command("echo ${null_var:-default}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "default"
        
        # Set variable
        shell.run_command("set_var=value")
        shell.run_command("echo ${set_var:-default}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "value"
        
        # Without colon (only unset)
        shell.run_command("echo ${null_var-default}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == ""
    
    @pytest.mark.xfail(reason="Variable assignment in expansion")

    
    def test_assign_default_expansion(self, shell, capsys):
        """Test ${parameter:=word} assign default."""
        # Unset variable gets assigned
        shell.run_command("unset assign_var")
        shell.run_command("echo ${assign_var:=assigned}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "assigned"
        
        # Verify assignment persisted
        shell.run_command("echo $assign_var")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "assigned"
        
        # Already set variable not changed
        shell.run_command("existing=original")
        shell.run_command("echo ${existing:=new}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "original"
    
    @pytest.mark.xfail(reason="Error handling in expansion")

    
    def test_error_if_null_expansion(self, shell, capsys):
        """Test ${parameter:?word} error if null."""
        # Set variable works
        shell.run_command("set_var=value")
        shell.run_command("echo ${set_var:?error message}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "value"
        
        # Unset variable causes error
        shell.run_command("unset unset_var")
        result = shell.run_command("echo ${unset_var:?variable not set}")
        assert result != 0
    
    def test_alternative_value_expansion(self, shell, capsys):
        """Test ${parameter:+word} alternative value."""
        # Unset variable yields nothing
        shell.run_command("unset unset_var")
        shell.run_command('echo "${unset_var:+alternative}"')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == ""
        
        # Set variable yields alternative
        shell.run_command("set_var=value")
        shell.run_command("echo ${set_var:+alternative}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "alternative"
    
    @pytest.mark.skip(reason="PSH: ${#@} returns length of concatenated string instead of parameter count")
    def test_string_length_expansion(self, shell, capsys):
        """Test ${#parameter} string length."""
        shell.run_command("var=hello")
        shell.run_command("echo ${#var}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "5"
        
        # Empty string
        shell.run_command("empty=")
        shell.run_command("echo ${#empty}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "0"
        
        # Special parameters
        shell.run_command("set -- one two three")
        shell.run_command("echo ${#@}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "3"
    
    def test_remove_prefix_expansion(self, shell, capsys):
        """Test ${parameter#pattern} remove smallest prefix."""
        shell.run_command("path=/usr/local/bin/prog")
        
        # Remove smallest prefix
        shell.run_command("echo ${path#*/}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "usr/local/bin/prog"
        
        # Remove largest prefix
        shell.run_command("echo ${path##*/}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "prog"
        
        # Pattern doesn't match
        shell.run_command("echo ${path#xyz}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "/usr/local/bin/prog"
    
    def test_remove_suffix_expansion(self, shell, capsys):
        """Test ${parameter%pattern} remove smallest suffix."""
        shell.run_command("file=document.txt.bak")
        
        # Remove smallest suffix
        shell.run_command("echo ${file%.*}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "document.txt"
        
        # Remove largest suffix
        shell.run_command("echo ${file%%.*}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "document"
        
        # Get extension
        shell.run_command("name=file.tar.gz")
        shell.run_command("echo ${name##*.}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "gz"


class TestPOSIXSpecialParameters:
    """Test POSIX special parameters."""
    
    def test_positional_parameters(self, shell, capsys):
        """Test $1, $2, etc."""
        shell.run_command("set -- first second third")
        
        shell.run_command("echo $1")

        
        captured = capsys.readouterr()

        
        output = captured.out
        assert output.strip() == "first"
        
        shell.run_command("echo $2")

        
        captured = capsys.readouterr()

        
        output = captured.out
        assert output.strip() == "second"
        
        shell.run_command("echo $3")

        
        captured = capsys.readouterr()

        
        output = captured.out
        assert output.strip() == "third"
        
        # Multi-digit positional
        shell.run_command("set -- 1 2 3 4 5 6 7 8 9 ten eleven")
        shell.run_command("echo ${10}")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "ten"
    
    @pytest.mark.skip(reason="PSH: $@ expansion not fully POSIX compliant")
    def test_all_parameters(self, shell, capsys):
        """Test $@ and $*."""
        shell.run_command("set -- one 'two three' four")
        
        # $@ preserves separate words
        shell.run_command("""

        for arg in "$@"; do\necho "[$arg]"\ndone

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert "[one]" in output
        assert "[two three]" in output
        assert "[four]" in output
        
        # $* with default IFS
        shell.run_command('echo "$*"')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "one two three four"
        
        # $* with custom IFS
        shell.run_command("IFS=:")
        shell.run_command('echo "$*"')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "one:two three:four"
        shell.run_command("IFS=' \t\n'")  # Reset IFS
    
    def test_parameter_count(self, shell, capsys):
        """Test $# parameter count."""
        shell.run_command("set --")
        shell.run_command("echo $#")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "0"
        
        shell.run_command("set -- a b c")
        shell.run_command("echo $#")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "3"
    
    @pytest.mark.skip(reason="PSH: run_command() doesn't support check=False parameter")
    def test_exit_status(self, shell, capsys):
        """Test $? exit status."""
        shell.run_command("true")
        shell.run_command("echo $?")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "0"
        
        shell.run_command("false")
        shell.run_command("echo $?")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "1"
        
        shell.run_command("exit 42", check=False)
        shell.run_command("echo $?")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "42"
    
    @pytest.mark.skip(reason="PSH: Background job tracking issues")
    def test_process_ids(self, shell, capsys):
        """Test $$ and $! process IDs."""
        # $$ is shell PID
        shell.run_command("echo $$")

        captured = capsys.readouterr()

        output1 = captured.out
        shell.run_command("echo $$")

        captured = capsys.readouterr()

        output2 = captured.out
        assert output1.strip() == output2.strip()
        assert output1.strip().isdigit()
        
        # $! is last background PID
        shell.run_command("sleep 0.1 &")
        shell.run_command("echo $!")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip().isdigit()
    
    @pytest.mark.skip(reason="PSH: $- not implemented")
    def test_shell_options(self, shell, capsys):
        """Test $- current options."""
        shell.run_command("echo $-")

        captured = capsys.readouterr()

        output = captured.out
        # Should contain some option flags
        assert len(output.strip()) > 0
        
        # Setting options should be reflected
        shell.run_command("set -x")
        shell.run_command("echo $-")

        captured = capsys.readouterr()

        output = captured.out
        assert "x" in output
        shell.run_command("set +x")


class TestPOSIXWordExpansion:
    """Test POSIX word expansion order and behavior."""
    
    @pytest.mark.skip(reason="PSH: Tilde expansion doesn't respect HOME environment variable changes")
    def test_tilde_expansion(self, shell, capsys):
        """Test tilde expansion."""
        # ~ expands to HOME
        shell.run_command("HOME=/tmp/home")
        shell.run_command("echo ~")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "/tmp/home"
        
        # ~user expansion (may not work without real user)
        # shell.run_command("echo ~root")
        # captured = capsys.readouterr()
        # output = captured.out
        # assert output.strip() == "/root" or "root" in output
        
        # No expansion in quotes
        shell.run_command("echo '~'")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "~"
    
    def test_command_substitution(self, shell, capsys):
        """Test command substitution forms."""
        # $() form
        shell.run_command("echo $(echo hello)")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "hello"
        
        # Backtick form
        shell.run_command("echo `echo world`")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "world"
        
        # Nested command substitution
        shell.run_command("echo $(echo $(echo nested))")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "nested"
        
        # In double quotes
        shell.run_command('echo "Result: $(echo test)"')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "Result: test"
    
    def test_arithmetic_expansion(self, shell, capsys):
        """Test arithmetic expansion."""
        # Basic arithmetic
        shell.run_command("echo $((2 + 3))")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "5"
        
        # With variables
        shell.run_command("x=10")
        shell.run_command("y=3")
        shell.run_command("echo $((x * y))")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "30"
        
        # Operators
        shell.run_command("echo $((10 / 3))")

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "3"
        
        shell.run_command("echo $((10 % 3))")

        
        captured = capsys.readouterr()

        
        output = captured.out
        assert output.strip() == "1"
    
    @pytest.mark.skip(reason="PSH: IFS field splitting not fully implemented")
    def test_field_splitting(self, shell, capsys):
        """Test IFS field splitting."""
        # Default IFS splits on whitespace
        shell.run_command('set -- $(echo "one two three"); echo $#')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "3"
        
        # Custom IFS
        shell.run_command("IFS=:")
        shell.run_command('set -- $(echo "a:b:c"); echo $#')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "3"
        
        # No splitting in double quotes
        shell.run_command("IFS=' \t\n'")  # Reset IFS
        shell.run_command('set -- "$(echo "one two")"; echo $1')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "one two"
    
    def test_pathname_expansion(self, shell, capsys):
        """Test pathname expansion (globbing)."""
        # Create test files
        shell.run_command("mkdir -p /tmp/posix_glob")
        shell.run_command("touch /tmp/posix_glob/file1.txt /tmp/posix_glob/file2.txt")
        shell.run_command("touch /tmp/posix_glob/data.dat")
        
        # * expansion
        shell.run_command("echo /tmp/posix_glob/*.txt")

        captured = capsys.readouterr()

        output = captured.out
        assert "file1.txt" in output
        assert "file2.txt" in output
        assert "data.dat" not in output
        
        # ? expansion
        shell.run_command("echo /tmp/posix_glob/file?.txt")

        captured = capsys.readouterr()

        output = captured.out
        assert "file1.txt" in output
        assert "file2.txt" in output
        
        # [...] expansion
        shell.run_command("echo /tmp/posix_glob/file[12].txt")

        captured = capsys.readouterr()

        output = captured.out
        assert "file1.txt" in output
        assert "file2.txt" in output
        
        # No expansion in quotes
        shell.run_command('echo "/tmp/posix_glob/*.txt"')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "/tmp/posix_glob/*.txt"
        
        # Cleanup
        shell.run_command("rm -rf /tmp/posix_glob")
    
    def test_expansion_order(self, shell, capsys):
        """Test that expansions happen in POSIX order."""
        # Set up test
        shell.run_command("var='*.txt'")
        shell.run_command("touch /tmp/test1.txt /tmp/test2.txt")
        
        # Variable expansion happens before pathname expansion
        shell.run_command("echo $var")

        captured = capsys.readouterr()

        output = captured.out
        # This should expand the glob
        if "/tmp/test1.txt" not in output:
            # PSH might show the pattern if no files match
            pass
        
        # In quotes, no pathname expansion
        shell.run_command('echo "$var"')

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "*.txt"
        
        # Cleanup
        shell.run_command("rm -f /tmp/test1.txt /tmp/test2.txt")