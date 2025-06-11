"""Test echo builtin with -n and -e flags."""

import pytest
import os
import tempfile


class TestEchoFlags:
    """Test echo builtin flag functionality."""
    
    def test_echo_basic(self, shell, capsys):
        """Test basic echo without flags."""
        result = shell.run_command("echo hello world")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello world\n"
    
    def test_echo_empty(self, shell, capsys):
        """Test echo with no arguments."""
        result = shell.run_command("echo")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "\n"
    
    def test_echo_n_flag(self, shell, capsys):
        """Test -n flag suppresses newline."""
        result = shell.run_command("echo -n hello")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello"
        
        # Test -n with multiple arguments
        result = shell.run_command("echo -n hello world")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello world"
        
        # Test -n with no other arguments
        result = shell.run_command("echo -n")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_echo_e_flag_basic(self, shell, capsys):
        """Test -e flag with basic escape sequences."""
        # Newline
        result = shell.run_command("echo -e 'hello\\nworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld\n"
        
        # Tab
        result = shell.run_command("echo -e 'hello\\tworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\tworld\n"
        
        # Multiple escapes
        result = shell.run_command("echo -e 'a\\tb\\nc'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "a\tb\nc\n"
    
    def test_echo_e_flag_all_escapes(self, shell, capsys):
        """Test -e flag with all supported escape sequences."""
        # Alert (bell)
        result = shell.run_command("echo -e '\\a'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "\a\n"
        
        # Backspace
        result = shell.run_command("echo -e 'abc\\bdef'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "abc\bdef\n"
        
        # Form feed
        result = shell.run_command("echo -e '\\f'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "\f\n"
        
        # Carriage return
        result = shell.run_command("echo -e 'hello\\rworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\rworld\n"
        
        # Vertical tab
        result = shell.run_command("echo -e '\\v'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "\v\n"
        
        # Escaped backslash
        result = shell.run_command("echo -e 'a\\\\b'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "a\\b\n"
        
        # Escape character
        result = shell.run_command("echo -e '\\e[31mRed\\e[0m'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "\x1b[31mRed\x1b[0m\n"
    
    def test_echo_e_flag_c_terminator(self, shell, capsys):
        """Test -e flag with \\c terminator."""
        # \c suppresses further output
        result = shell.run_command("echo -e 'hello\\cworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello"
        
        # \c also suppresses newline
        result = shell.run_command("echo -e 'test\\c\\nignored'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "test"
    
    def test_echo_e_flag_octal(self, shell, capsys):
        """Test -e flag with octal sequences."""
        # Octal with leading 0 (A = 0101 octal)
        result = shell.run_command("echo -e '\\0101'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "A\n"
        
        # Three digit octal (newline = 012 octal)
        result = shell.run_command("echo -e 'a\\012b'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "a\nb\n"
        
        # Another octal test (space = 040 octal)
        result = shell.run_command("echo -e 'hello\\040world'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello world\n"
        
        # Null byte test
        result = shell.run_command("echo -e 'start\\000end'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "start\0end\n"
    
    def test_echo_e_flag_hex(self, shell, capsys):
        """Test -e flag with hex sequences."""
        # Single hex digit
        result = shell.run_command("echo -e '\\x41'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "A\n"
        
        # Two hex digits
        result = shell.run_command("echo -e '\\x48\\x65\\x6c\\x6c\\x6f'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "Hello\n"
        
        # Lowercase hex
        result = shell.run_command("echo -e '\\x0a'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "\n\n"
    
    def test_echo_e_flag_unicode(self, shell, capsys):
        """Test -e flag with unicode sequences."""
        # 4-digit unicode (smiley face)
        result = shell.run_command("echo -e '\\u263A'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "☺\n"
        
        # 8-digit unicode (emoji)
        result = shell.run_command("echo -e '\\U0001F600'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "😀\n"
    
    def test_echo_combined_flags(self, shell, capsys):
        """Test combined -n and -e flags."""
        # -ne combination
        result = shell.run_command("echo -ne 'hello\\nworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld"
        
        # -en combination (same effect)
        result = shell.run_command("echo -en 'hello\\tworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\tworld"
        
        # -n -e as separate flags
        result = shell.run_command("echo -n -e 'test\\n'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "test\n"
    
    def test_echo_E_flag(self, shell, capsys):
        """Test -E flag disables escape interpretation."""
        # -E disables escapes (default behavior)
        result = shell.run_command("echo -E 'hello\\nworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\\nworld\n"
        
        # -eE means -E wins (last flag wins)
        result = shell.run_command("echo -eE 'hello\\nworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\\nworld\n"
        
        # -Ee means -e wins
        result = shell.run_command("echo -Ee 'hello\\nworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld\n"
    
    def test_echo_double_dash(self, shell, capsys):
        """Test -- stops flag parsing."""
        # -- stops flag parsing
        result = shell.run_command("echo -- -n hello")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "-n hello\n"
        
        # Flags before -- are processed
        result = shell.run_command("echo -n -- hello")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello"
        
        # -e with --
        result = shell.run_command("echo -e -- 'hello\\nworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld\n"
    
    def test_echo_invalid_flags(self, shell, capsys):
        """Test invalid flags are treated as arguments."""
        # Invalid flag treated as argument
        result = shell.run_command("echo -x hello")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "-x hello\n"
        
        # Mixed valid and invalid flags
        result = shell.run_command("echo -nx hello")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "-nx hello\n"
    
    def test_echo_with_quotes(self, shell, capsys):
        """Test echo with various quote combinations."""
        # Single quotes preserve backslashes
        result = shell.run_command("echo -e 'hello\\nworld'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld\n"
        
        # Double quotes also work
        result = shell.run_command('echo -e "hello\\nworld"')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld\n"
        
        # No quotes - need double backslash in Python string
        result = shell.run_command("echo -e hello\\\\nworld")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld\n"
    
    def test_echo_edge_cases(self, shell, capsys):
        """Test echo edge cases."""
        # Just flags, no arguments
        result = shell.run_command("echo -n -e")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        
        # Empty string argument
        result = shell.run_command("echo -e ''")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "\n"
        
        # Multiple spaces preserved
        result = shell.run_command("echo -e 'a    b'")
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == "a    b\n"
    
    def test_echo_with_redirections(self, shell):
        """Test echo with output redirections."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            # Test -n with redirection
            result = shell.run_command(f"echo -n hello > {temp_file}")
            assert result == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
            assert content == "hello"
            
            # Test -e with redirection
            result = shell.run_command(f"echo -e 'line1\\nline2' > {temp_file}")
            assert result == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
            assert content == "line1\nline2\n"
            
            # Test append with -n
            result = shell.run_command(f"echo -n test >> {temp_file}")
            assert result == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
            assert content == "line1\nline2\ntest"
            
        finally:
            os.unlink(temp_file)
    
    def test_echo_in_pipeline(self, shell):
        """Test echo in pipelines."""
        import tempfile
        import os
        
        # Create temporary file for output capture
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            temp_file = f.name
        
        try:
            # Basic pipeline with -e
            result = shell.run_command(f"echo -e 'one\\ntwo\\nthree' | wc -l > {temp_file}")
            assert result == 0
            with open(temp_file, 'r') as f:
                output = f.read().strip()
            assert output == "3"
            
            # Pipeline with -n (no final newline)
            result = shell.run_command(f"echo -n hello | wc -c > {temp_file}")
            assert result == 0
            with open(temp_file, 'r') as f:
                output = f.read().strip()
            assert output == "5"
            
            # Multiple echoes in pipeline
            result = shell.run_command(f"echo -e 'a\\nb' | grep b > {temp_file}")
            assert result == 0
            with open(temp_file, 'r') as f:
                output = f.read().strip()
            assert output == "b"
        finally:
            os.unlink(temp_file)