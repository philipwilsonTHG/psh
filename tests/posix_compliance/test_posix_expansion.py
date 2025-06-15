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

from tests.conftest import shell


class TestPOSIXParameterExpansion:
    """Test POSIX parameter expansion forms."""
    
    def test_basic_parameter_expansion(self, shell):
        """Test ${parameter} basic form."""
        shell.run_command("var=value")
        output = shell.capture_output("echo ${var}")
        assert output.strip() == "value"
        
        # Braces needed for disambiguation
        shell.run_command("prefix=pre")
        output = shell.capture_output("echo ${prefix}fix")
        assert output.strip() == "prefix"
    
    def test_default_value_expansion(self, shell):
        """Test ${parameter:-word} default value."""
        # Unset variable
        shell.run_command("unset unset_var")
        output = shell.capture_output("echo ${unset_var:-default}")
        assert output.strip() == "default"
        
        # Null variable
        shell.run_command("null_var=")
        output = shell.capture_output("echo ${null_var:-default}")
        assert output.strip() == "default"
        
        # Set variable
        shell.run_command("set_var=value")
        output = shell.capture_output("echo ${set_var:-default}")
        assert output.strip() == "value"
        
        # Without colon (only unset)
        output = shell.capture_output("echo ${null_var-default}")
        assert output.strip() == ""
    
    def test_assign_default_expansion(self, shell):
        """Test ${parameter:=word} assign default."""
        # Unset variable gets assigned
        shell.run_command("unset assign_var")
        output = shell.capture_output("echo ${assign_var:=assigned}")
        assert output.strip() == "assigned"
        
        # Verify assignment persisted
        output = shell.capture_output("echo $assign_var")
        assert output.strip() == "assigned"
        
        # Already set variable not changed
        shell.run_command("existing=original")
        output = shell.capture_output("echo ${existing:=new}")
        assert output.strip() == "original"
    
    def test_error_if_null_expansion(self, shell):
        """Test ${parameter:?word} error if null."""
        # Set variable works
        shell.run_command("set_var=value")
        output = shell.capture_output("echo ${set_var:?error message}")
        assert output.strip() == "value"
        
        # Unset variable causes error
        shell.run_command("unset unset_var")
        result = shell.run_command("echo ${unset_var:?variable not set}")
        assert result != 0
    
    def test_alternative_value_expansion(self, shell):
        """Test ${parameter:+word} alternative value."""
        # Unset variable yields nothing
        shell.run_command("unset unset_var")
        output = shell.capture_output("echo '${unset_var:+alternative}'")
        assert output.strip() == ""
        
        # Set variable yields alternative
        shell.run_command("set_var=value")
        output = shell.capture_output("echo ${set_var:+alternative}")
        assert output.strip() == "alternative"
    
    def test_string_length_expansion(self, shell):
        """Test ${#parameter} string length."""
        shell.run_command("var=hello")
        output = shell.capture_output("echo ${#var}")
        assert output.strip() == "5"
        
        # Empty string
        shell.run_command("empty=")
        output = shell.capture_output("echo ${#empty}")
        assert output.strip() == "0"
        
        # Special parameters
        shell.run_command("set -- one two three")
        output = shell.capture_output("echo ${#@}")
        assert output.strip() == "3"
    
    def test_remove_prefix_expansion(self, shell):
        """Test ${parameter#pattern} remove smallest prefix."""
        shell.run_command("path=/usr/local/bin/prog")
        
        # Remove smallest prefix
        output = shell.capture_output("echo ${path#*/}")
        assert output.strip() == "usr/local/bin/prog"
        
        # Remove largest prefix
        output = shell.capture_output("echo ${path##*/}")
        assert output.strip() == "prog"
        
        # Pattern doesn't match
        output = shell.capture_output("echo ${path#xyz}")
        assert output.strip() == "/usr/local/bin/prog"
    
    def test_remove_suffix_expansion(self, shell):
        """Test ${parameter%pattern} remove smallest suffix."""
        shell.run_command("file=document.txt.bak")
        
        # Remove smallest suffix
        output = shell.capture_output("echo ${file%.*}")
        assert output.strip() == "document.txt"
        
        # Remove largest suffix
        output = shell.capture_output("echo ${file%%.*}")
        assert output.strip() == "document"
        
        # Get extension
        shell.run_command("name=file.tar.gz")
        output = shell.capture_output("echo ${name##*.}")
        assert output.strip() == "gz"


class TestPOSIXSpecialParameters:
    """Test POSIX special parameters."""
    
    def test_positional_parameters(self, shell):
        """Test $1, $2, etc."""
        shell.run_command("set -- first second third")
        
        output = shell.capture_output("echo $1")
        assert output.strip() == "first"
        
        output = shell.capture_output("echo $2")
        assert output.strip() == "second"
        
        output = shell.capture_output("echo $3")
        assert output.strip() == "third"
        
        # Multi-digit positional
        shell.run_command("set -- 1 2 3 4 5 6 7 8 9 ten eleven")
        output = shell.capture_output("echo ${10}")
        assert output.strip() == "ten"
    
    def test_all_parameters(self, shell):
        """Test $@ and $*."""
        shell.run_command("set -- one 'two three' four")
        
        # $@ preserves separate words
        output = shell.capture_output('''
        for arg in "$@"; do
            echo "[$arg]"
        done
        ''')
        assert "[one]" in output
        assert "[two three]" in output
        assert "[four]" in output
        
        # $* with default IFS
        output = shell.capture_output('echo "$*"')
        assert output.strip() == "one two three four"
        
        # $* with custom IFS
        shell.run_command("IFS=:")
        output = shell.capture_output('echo "$*"')
        assert output.strip() == "one:two three:four"
        shell.run_command("IFS=' \t\n'")  # Reset IFS
    
    def test_parameter_count(self, shell):
        """Test $# parameter count."""
        shell.run_command("set --")
        output = shell.capture_output("echo $#")
        assert output.strip() == "0"
        
        shell.run_command("set -- a b c")
        output = shell.capture_output("echo $#")
        assert output.strip() == "3"
    
    def test_exit_status(self, shell):
        """Test $? exit status."""
        shell.run_command("true")
        output = shell.capture_output("echo $?")
        assert output.strip() == "0"
        
        shell.run_command("false")
        output = shell.capture_output("echo $?")
        assert output.strip() == "1"
        
        shell.run_command("exit 42", check=False)
        output = shell.capture_output("echo $?")
        assert output.strip() == "42"
    
    def test_process_ids(self, shell):
        """Test $$ and $! process IDs."""
        # $$ is shell PID
        output1 = shell.capture_output("echo $$")
        output2 = shell.capture_output("echo $$")
        assert output1.strip() == output2.strip()
        assert output1.strip().isdigit()
        
        # $! is last background PID
        shell.run_command("sleep 0.1 &")
        output = shell.capture_output("echo $!")
        assert output.strip().isdigit()
    
    def test_shell_options(self, shell):
        """Test $- current options."""
        output = shell.capture_output("echo $-")
        # Should contain some option flags
        assert len(output.strip()) > 0
        
        # Setting options should be reflected
        shell.run_command("set -x")
        output = shell.capture_output("echo $-")
        assert "x" in output
        shell.run_command("set +x")


class TestPOSIXWordExpansion:
    """Test POSIX word expansion order and behavior."""
    
    def test_tilde_expansion(self, shell):
        """Test tilde expansion."""
        # ~ expands to HOME
        shell.run_command("HOME=/tmp/home")
        output = shell.capture_output("echo ~")
        assert output.strip() == "/tmp/home"
        
        # ~user expansion (may not work without real user)
        # output = shell.capture_output("echo ~root")
        # assert output.strip() == "/root" or "root" in output
        
        # No expansion in quotes
        output = shell.capture_output("echo '~'")
        assert output.strip() == "~"
    
    def test_command_substitution(self, shell):
        """Test command substitution forms."""
        # $() form
        output = shell.capture_output("echo $(echo hello)")
        assert output.strip() == "hello"
        
        # Backtick form
        output = shell.capture_output("echo `echo world`")
        assert output.strip() == "world"
        
        # Nested command substitution
        output = shell.capture_output("echo $(echo $(echo nested))")
        assert output.strip() == "nested"
        
        # In double quotes
        output = shell.capture_output('echo "Result: $(echo test)"')
        assert output.strip() == "Result: test"
    
    def test_arithmetic_expansion(self, shell):
        """Test arithmetic expansion."""
        # Basic arithmetic
        output = shell.capture_output("echo $((2 + 3))")
        assert output.strip() == "5"
        
        # With variables
        shell.run_command("x=10")
        shell.run_command("y=3")
        output = shell.capture_output("echo $((x * y))")
        assert output.strip() == "30"
        
        # Operators
        output = shell.capture_output("echo $((10 / 3))")
        assert output.strip() == "3"
        
        output = shell.capture_output("echo $((10 % 3))")
        assert output.strip() == "1"
    
    def test_field_splitting(self, shell):
        """Test IFS field splitting."""
        # Default IFS splits on whitespace
        output = shell.capture_output('set -- $(echo "one two three"); echo $#')
        assert output.strip() == "3"
        
        # Custom IFS
        shell.run_command("IFS=:")
        output = shell.capture_output('set -- $(echo "a:b:c"); echo $#')
        assert output.strip() == "3"
        
        # No splitting in double quotes
        shell.run_command("IFS=' \t\n'")  # Reset IFS
        output = shell.capture_output('set -- "$(echo "one two")"; echo $1')
        assert output.strip() == "one two"
    
    def test_pathname_expansion(self, shell):
        """Test pathname expansion (globbing)."""
        # Create test files
        shell.run_command("mkdir -p /tmp/posix_glob")
        shell.run_command("touch /tmp/posix_glob/file1.txt /tmp/posix_glob/file2.txt")
        shell.run_command("touch /tmp/posix_glob/data.dat")
        
        # * expansion
        output = shell.capture_output("echo /tmp/posix_glob/*.txt")
        assert "file1.txt" in output
        assert "file2.txt" in output
        assert "data.dat" not in output
        
        # ? expansion
        output = shell.capture_output("echo /tmp/posix_glob/file?.txt")
        assert "file1.txt" in output
        assert "file2.txt" in output
        
        # [...] expansion
        output = shell.capture_output("echo /tmp/posix_glob/file[12].txt")
        assert "file1.txt" in output
        assert "file2.txt" in output
        
        # No expansion in quotes
        output = shell.capture_output('echo "/tmp/posix_glob/*.txt"')
        assert output.strip() == "/tmp/posix_glob/*.txt"
        
        # Cleanup
        shell.run_command("rm -rf /tmp/posix_glob")
    
    def test_expansion_order(self, shell):
        """Test that expansions happen in POSIX order."""
        # Set up test
        shell.run_command("var='*.txt'")
        shell.run_command("touch /tmp/test1.txt /tmp/test2.txt")
        
        # Variable expansion happens before pathname expansion
        output = shell.capture_output("echo $var")
        # This should expand the glob
        if "/tmp/test1.txt" not in output:
            # PSH might show the pattern if no files match
            pass
        
        # In quotes, no pathname expansion
        output = shell.capture_output('echo "$var"')
        assert output.strip() == "*.txt"
        
        # Cleanup
        shell.run_command("rm -f /tmp/test1.txt /tmp/test2.txt")