"""Test advanced read builtin options."""
import pytest
import sys
import subprocess
import time
from io import StringIO
from psh.shell import Shell


class TestReadAdvanced:
    def setup_method(self):
        self.shell = Shell()
    
    def test_read_prompt_option(self):
        """Test read -p prompt option."""
        # Since prompt goes to stderr, we need to test with subprocess
        proc = subprocess.Popen(
            [sys.executable, '-m', 'psh', '-c', 'read -p "Name: " name; echo "Hello, $name"'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(input="Alice\n")
        assert stderr == "Name: "
        assert stdout == "Hello, Alice\n"
        assert proc.returncode == 0
    
    def test_read_silent_option(self):
        """Test read -s silent option."""
        # Silent mode requires terminal, test that it parses correctly
        old_stdin = sys.stdin
        sys.stdin = StringIO("secret\n")
        
        try:
            exit_code = self.shell.run_command("read -s password")
            assert exit_code == 0
            assert self.shell.state.get_variable("password") == "secret"
        finally:
            sys.stdin = old_stdin
    
    def test_read_n_chars_option(self):
        """Test read -n chars option."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("1234567890\n")
        
        try:
            exit_code = self.shell.run_command("read -n 4 pin")
            assert exit_code == 0
            assert self.shell.state.get_variable("pin") == "1234"
        finally:
            sys.stdin = old_stdin
    
    def test_read_d_delimiter_option(self):
        """Test read -d delimiter option."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello:world\n")
        
        try:
            exit_code = self.shell.run_command("read -d : data")
            assert exit_code == 0
            assert self.shell.state.get_variable("data") == "hello"
        finally:
            sys.stdin = old_stdin
    
    def test_read_null_delimiter(self):
        """Test read -d '' for null delimiter."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello\0world")
        
        try:
            exit_code = self.shell.run_command('read -d "" data')
            assert exit_code == 0
            assert self.shell.state.get_variable("data") == "hello"
        finally:
            sys.stdin = old_stdin
    
    def test_read_timeout_option(self):
        """Test read -t timeout option."""
        # Test timeout with subprocess
        proc = subprocess.Popen(
            [sys.executable, '-m', 'psh', '-c', 'read -t 0.1 data; echo "Exit: $?"'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate()
        assert "Exit: 142" in stdout
        assert proc.returncode == 0
    
    def test_read_combined_options(self):
        """Test combining multiple read options."""
        # Test -p with -n
        proc = subprocess.Popen(
            [sys.executable, '-m', 'psh', '-c', 'read -p "Enter 4-digit PIN: " -n 4 pin; echo; echo "PIN: $pin"'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(input="1234567")
        assert stderr == "Enter 4-digit PIN: "
        assert "PIN: 1234" in stdout
    
    def test_read_invalid_options(self):
        """Test invalid option handling."""
        # Invalid timeout - just check that error is printed
        proc = subprocess.Popen(
            [sys.executable, '-m', 'psh', '-c', 'read -t abc data'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate()
        assert "invalid timeout specification" in stderr
        
        # Invalid char count
        proc = subprocess.Popen(
            [sys.executable, '-m', 'psh', '-c', 'read -n -5 data'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate()
        assert "invalid number" in stderr
        
        # Test that valid negative timeout is rejected
        proc = subprocess.Popen(
            [sys.executable, '-m', 'psh', '-c', 'read -t -1 data'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate()
        assert "invalid timeout specification" in stderr
    
    def test_read_with_ifs(self):
        """Test read with IFS and new options."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one,two,three")
        
        try:
            self.shell.state.set_variable("IFS", ",")
            exit_code = self.shell.run_command("read -d '' a b c")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "one"
            assert self.shell.state.get_variable("b") == "two"
            assert self.shell.state.get_variable("c") == "three"
        finally:
            sys.stdin = old_stdin
            self.shell.state.scope_manager.unset_variable("IFS")
    
    def test_read_raw_mode_with_options(self):
        """Test -r raw mode with other options."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello\\tworld")
        
        try:
            exit_code = self.shell.run_command("read -r -d d data")
            assert exit_code == 0
            # In raw mode, backslash is preserved
            assert self.shell.state.get_variable("data") == "hello\\tworl"
        finally:
            sys.stdin = old_stdin
    
    def test_read_eof_with_options(self):
        """Test EOF handling with various options."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("")  # Empty input (EOF)
        
        try:
            exit_code = self.shell.run_command("read -n 5 data")
            assert exit_code == 1  # EOF should return 1
        finally:
            sys.stdin = old_stdin
    
    def test_read_multiline_delimiter(self):
        """Test reading multiple lines with custom delimiter."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("line1\nline2\nline3#end")
        
        try:
            exit_code = self.shell.run_command('read -d "#" data')
            assert exit_code == 0
            assert self.shell.state.get_variable("data") == "line1\nline2\nline3"
        finally:
            sys.stdin = old_stdin