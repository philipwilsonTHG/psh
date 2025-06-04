"""Test the read builtin command."""
import pytest
import sys
from io import StringIO
from psh.shell import Shell


class TestReadBuiltin:
    def setup_method(self):
        self.shell = Shell()
        # Clear any existing variables - start fresh with new shell instance
        # (each Shell instance starts with a clean scope)
    
    def test_basic_read(self):
        """Test basic read functionality."""
        # Simulate stdin input
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello world\n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            assert self.shell.state.get_variable("var") == "hello world"
        finally:
            sys.stdin = old_stdin
    
    def test_read_default_reply(self):
        """Test read with no variable names uses REPLY."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("test input\n")
        
        try:
            exit_code = self.shell.run_command("read")
            assert exit_code == 0
            assert self.shell.state.get_variable("REPLY") == "test input"
        finally:
            sys.stdin = old_stdin
    
    def test_read_multiple_variables(self):
        """Test read with multiple variables."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("first second third\n")
        
        try:
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "first"
            assert self.shell.state.get_variable("b") == "second"
            assert self.shell.state.get_variable("c") == "third"
        finally:
            sys.stdin = old_stdin
    
    def test_read_more_fields_than_variables(self):
        """Test read when input has more fields than variables."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one two three four five\n")
        
        try:
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "one"
            assert self.shell.state.get_variable("b") == "two"
            # Last variable gets all remaining fields
            assert self.shell.state.get_variable("c") == "three four five"
        finally:
            sys.stdin = old_stdin
    
    def test_read_fewer_fields_than_variables(self):
        """Test read when input has fewer fields than variables."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one two\n")
        
        try:
            exit_code = self.shell.run_command("read a b c d")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "one"
            assert self.shell.state.get_variable("b") == "two"
            assert self.shell.state.get_variable("c") == ""
            assert self.shell.state.get_variable("d") == ""
        finally:
            sys.stdin = old_stdin
    
    def test_read_eof(self):
        """Test read returns 1 on EOF."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("")  # Empty input (EOF)
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 1
        finally:
            sys.stdin = old_stdin
    
    def test_read_raw_mode(self):
        """Test read -r (raw mode) preserves backslashes."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello\\tworld\\n\n")
        
        try:
            exit_code = self.shell.run_command("read -r var")
            assert exit_code == 0
            # In raw mode, backslashes are preserved
            assert self.shell.state.get_variable("var") == "hello\\tworld\\n"
        finally:
            sys.stdin = old_stdin
    
    def test_read_escape_processing(self):
        """Test read processes escape sequences without -r."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello\\tworld\\n\n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            # Without -r, escape sequences are processed
            # Note: trailing newline is trimmed as it's IFS whitespace
            assert self.shell.state.get_variable("var") == "hello\tworld"
        finally:
            sys.stdin = old_stdin
    
    def test_read_embedded_newline(self):
        """Test read preserves embedded newlines."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello\\nworld\n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            # Embedded newline is preserved
            assert self.shell.state.get_variable("var") == "hello\nworld"
        finally:
            sys.stdin = old_stdin
    
    def test_read_custom_ifs(self):
        """Test read with custom IFS."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one:two:three\n")
        
        try:
            # Set IFS to colon
            self.shell.state.set_variable("IFS", ":")
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "one"
            assert self.shell.state.get_variable("b") == "two"
            assert self.shell.state.get_variable("c") == "three"
        finally:
            sys.stdin = old_stdin
            # Reset IFS
            self.shell.state.scope_manager.unset_variable("IFS")
    
    def test_read_empty_ifs(self):
        """Test read with empty IFS (no field splitting)."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("  hello  world  \n")
        
        try:
            # Set IFS to empty string
            self.shell.state.set_variable("IFS", "")
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            # With empty IFS, no splitting occurs and whitespace is preserved
            assert self.shell.state.get_variable("var") == "  hello  world  "
        finally:
            sys.stdin = old_stdin
            # Reset IFS
            self.shell.state.scope_manager.unset_variable("IFS")
    
    def test_read_leading_trailing_whitespace(self):
        """Test read trims leading/trailing IFS whitespace."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("  hello  world  \n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            # Default IFS includes space, so leading/trailing spaces are trimmed
            assert self.shell.state.get_variable("var") == "hello  world"
        finally:
            sys.stdin = old_stdin
    
    def test_read_tab_delimiter(self):
        """Test read with tab-delimited input."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("col1\tcol2\tcol3\n")
        
        try:
            # Set IFS to tab only
            self.shell.state.set_variable("IFS", "\t")
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "col1"
            assert self.shell.state.get_variable("b") == "col2"
            assert self.shell.state.get_variable("c") == "col3"
        finally:
            sys.stdin = old_stdin
            self.shell.state.scope_manager.unset_variable("IFS")
    
    def test_read_mixed_ifs_characters(self):
        """Test read with IFS containing both whitespace and non-whitespace."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one:two three:four\n")
        
        try:
            # Set IFS to colon and space
            self.shell.state.set_variable("IFS", ": ")
            exit_code = self.shell.run_command("read a b c d")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "one"
            assert self.shell.state.get_variable("b") == "two"
            assert self.shell.state.get_variable("c") == "three"
            assert self.shell.state.get_variable("d") == "four"
        finally:
            sys.stdin = old_stdin
            self.shell.state.scope_manager.unset_variable("IFS")
    
    def test_read_empty_input(self):
        """Test read with empty line (just newline)."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("\n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            assert self.shell.state.get_variable("var") == ""
        finally:
            sys.stdin = old_stdin
    
    def test_read_backslash_at_end(self):
        """Test read handles backslash at end of input."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello\\\n")
        
        try:
            # Without -r, backslash-newline is line continuation
            # This should remove both the backslash and newline
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            assert self.shell.state.get_variable("var") == "hello"
        finally:
            sys.stdin = old_stdin
    
    def test_read_backslash_escapes(self):
        """Test various backslash escape sequences."""
        old_stdin = sys.stdin
        test_cases = [
            ("\\\\", "\\"),           # \\ -> \
            ("foo\\nbar", "foo\nbar"),  # \n -> newline (preserved when embedded)
            ("foo\\tbar", "foo\tbar"),  # \t -> tab (preserved when embedded)
            ("foo\\rbar", "foo\rbar"),  # \r -> carriage return
            ("foo\\ bar", "foo bar"),   # \space -> space (preserved)
            ("\\a", "a"),               # \other -> other
        ]
        
        try:
            for input_str, expected in test_cases:
                sys.stdin = StringIO(input_str + "\n")
                exit_code = self.shell.run_command("read var")
                assert exit_code == 0
                assert self.shell.state.get_variable("var") == expected
        finally:
            sys.stdin = old_stdin