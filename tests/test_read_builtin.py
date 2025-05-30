"""Test the read builtin command."""
import pytest
import sys
from io import StringIO
from psh.shell import Shell


class TestReadBuiltin:
    def setup_method(self):
        self.shell = Shell()
        # Clear any existing variables
        self.shell.variables = {}
    
    def test_basic_read(self):
        """Test basic read functionality."""
        # Simulate stdin input
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello world\n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            assert self.shell.variables.get("var") == "hello world"
        finally:
            sys.stdin = old_stdin
    
    def test_read_default_reply(self):
        """Test read with no variable names uses REPLY."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("test input\n")
        
        try:
            exit_code = self.shell.run_command("read")
            assert exit_code == 0
            assert self.shell.variables.get("REPLY") == "test input"
        finally:
            sys.stdin = old_stdin
    
    def test_read_multiple_variables(self):
        """Test read with multiple variables."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("first second third\n")
        
        try:
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.variables.get("a") == "first"
            assert self.shell.variables.get("b") == "second"
            assert self.shell.variables.get("c") == "third"
        finally:
            sys.stdin = old_stdin
    
    def test_read_more_fields_than_variables(self):
        """Test read when input has more fields than variables."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one two three four five\n")
        
        try:
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.variables.get("a") == "one"
            assert self.shell.variables.get("b") == "two"
            # Last variable gets all remaining fields
            assert self.shell.variables.get("c") == "three four five"
        finally:
            sys.stdin = old_stdin
    
    def test_read_fewer_fields_than_variables(self):
        """Test read when input has fewer fields than variables."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one two\n")
        
        try:
            exit_code = self.shell.run_command("read a b c d")
            assert exit_code == 0
            assert self.shell.variables.get("a") == "one"
            assert self.shell.variables.get("b") == "two"
            assert self.shell.variables.get("c") == ""
            assert self.shell.variables.get("d") == ""
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
            assert self.shell.variables.get("var") == "hello\\tworld\\n"
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
            assert self.shell.variables.get("var") == "hello\tworld"
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
            assert self.shell.variables.get("var") == "hello\nworld"
        finally:
            sys.stdin = old_stdin
    
    def test_read_custom_ifs(self):
        """Test read with custom IFS."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one:two:three\n")
        
        try:
            # Set IFS to colon
            self.shell.variables["IFS"] = ":"
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.variables.get("a") == "one"
            assert self.shell.variables.get("b") == "two"
            assert self.shell.variables.get("c") == "three"
        finally:
            sys.stdin = old_stdin
            # Reset IFS
            self.shell.variables.pop("IFS", None)
    
    def test_read_empty_ifs(self):
        """Test read with empty IFS (no field splitting)."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("  hello  world  \n")
        
        try:
            # Set IFS to empty string
            self.shell.variables["IFS"] = ""
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            # With empty IFS, no splitting occurs and whitespace is preserved
            assert self.shell.variables.get("var") == "  hello  world  "
        finally:
            sys.stdin = old_stdin
            # Reset IFS
            self.shell.variables.pop("IFS", None)
    
    def test_read_leading_trailing_whitespace(self):
        """Test read trims leading/trailing IFS whitespace."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("  hello  world  \n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            # Default IFS includes space, so leading/trailing spaces are trimmed
            assert self.shell.variables.get("var") == "hello  world"
        finally:
            sys.stdin = old_stdin
    
    def test_read_tab_delimiter(self):
        """Test read with tab-delimited input."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("col1\tcol2\tcol3\n")
        
        try:
            # Set IFS to tab only
            self.shell.variables["IFS"] = "\t"
            exit_code = self.shell.run_command("read a b c")
            assert exit_code == 0
            assert self.shell.variables.get("a") == "col1"
            assert self.shell.variables.get("b") == "col2"
            assert self.shell.variables.get("c") == "col3"
        finally:
            sys.stdin = old_stdin
            self.shell.variables.pop("IFS", None)
    
    def test_read_mixed_ifs_characters(self):
        """Test read with IFS containing both whitespace and non-whitespace."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one:two three:four\n")
        
        try:
            # Set IFS to colon and space
            self.shell.variables["IFS"] = ": "
            exit_code = self.shell.run_command("read a b c d")
            assert exit_code == 0
            assert self.shell.variables.get("a") == "one"
            assert self.shell.variables.get("b") == "two"
            assert self.shell.variables.get("c") == "three"
            assert self.shell.variables.get("d") == "four"
        finally:
            sys.stdin = old_stdin
            self.shell.variables.pop("IFS", None)
    
    def test_read_empty_input(self):
        """Test read with empty line (just newline)."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("\n")
        
        try:
            exit_code = self.shell.run_command("read var")
            assert exit_code == 0
            assert self.shell.variables.get("var") == ""
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
            assert self.shell.variables.get("var") == "hello"
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
                assert self.shell.variables.get("var") == expected
        finally:
            sys.stdin = old_stdin