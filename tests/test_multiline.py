"""Test multi-line command input and prompt expansion."""

import pytest
from psh.multiline_handler import MultiLineInputHandler
from psh.prompt import PromptExpander
from psh.shell import Shell
from psh.line_editor import LineEditor
from unittest.mock import Mock, patch
import os
import pwd
import socket
from datetime import datetime


class TestMultiLineHandler:
    """Test multi-line command detection and handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.shell = Shell()
        self.line_editor = Mock(spec=LineEditor)
        self.handler = MultiLineInputHandler(self.line_editor, self.shell)
    
    def test_is_complete_simple_command(self):
        """Test detection of complete simple commands."""
        assert self.handler._is_complete_command("echo hello")
        assert self.handler._is_complete_command("ls -la")
        assert self.handler._is_complete_command("")
        assert self.handler._is_complete_command("   ")
    
    def test_is_complete_with_line_continuation(self):
        """Test detection of line continuation with backslash."""
        assert not self.handler._is_complete_command("echo hello \\")
        assert not self.handler._is_complete_command("echo \\\n")
        assert self.handler._is_complete_command("echo hello \\\\")  # Escaped backslash
        assert self.handler._is_complete_command("echo hello")
    
    def test_is_complete_unclosed_quotes(self):
        """Test detection of unclosed quotes."""
        assert not self.handler._is_complete_command('echo "hello')
        assert not self.handler._is_complete_command("echo 'hello")
        assert self.handler._is_complete_command('echo "hello"')
        assert self.handler._is_complete_command("echo 'hello'")
    
    def test_is_complete_if_statement(self):
        """Test detection of incomplete if statements."""
        assert not self.handler._is_complete_command("if true")
        assert not self.handler._is_complete_command("if true; then")
        assert not self.handler._is_complete_command("if true; then\necho hello")
        assert self.handler._is_complete_command("if true; then echo hello; fi")
        assert self.handler._is_complete_command("if true; then\necho hello\nfi")
    
    def test_is_complete_while_loop(self):
        """Test detection of incomplete while loops."""
        assert not self.handler._is_complete_command("while true")
        assert not self.handler._is_complete_command("while true; do")
        assert not self.handler._is_complete_command("while true; do\necho hello")
        assert self.handler._is_complete_command("while true; do echo hello; done")
        assert self.handler._is_complete_command("while true; do\necho hello\ndone")
    
    def test_is_complete_for_loop(self):
        """Test detection of incomplete for loops."""
        assert not self.handler._is_complete_command("for i in 1 2 3")
        assert not self.handler._is_complete_command("for i in 1 2 3; do")
        assert not self.handler._is_complete_command("for i in 1 2 3; do\necho $i")
        assert self.handler._is_complete_command("for i in 1 2 3; do echo $i; done")
        assert self.handler._is_complete_command("for i in 1 2 3; do\necho $i\ndone")
    
    def test_is_complete_case_statement(self):
        """Test detection of incomplete case statements."""
        assert not self.handler._is_complete_command("case $x in")
        assert not self.handler._is_complete_command("case $x in\n1)")
        assert not self.handler._is_complete_command("case $x in\n1) echo one;;")
        assert self.handler._is_complete_command("case $x in\n1) echo one;;\nesac")
    
    def test_is_complete_function_definition(self):
        """Test detection of incomplete function definitions."""
        assert not self.handler._is_complete_command("hello() {")
        assert not self.handler._is_complete_command("hello() {\necho hello")
        assert self.handler._is_complete_command("hello() { echo hello; }")
        assert self.handler._is_complete_command("hello() {\necho hello\n}")
    
    def test_is_complete_heredoc(self):
        """Test detection of incomplete heredocs."""
        # Basic heredoc
        assert not self.handler._is_complete_command("cat <<EOF")
        assert not self.handler._is_complete_command("cat <<EOF\nline1")
        assert not self.handler._is_complete_command("cat <<EOF\nline1\nline2")
        assert self.handler._is_complete_command("cat <<EOF\nline1\nEOF")
        
        # Heredoc with dash (tab stripping)
        assert not self.handler._is_complete_command("cat <<-EOF")
        assert not self.handler._is_complete_command("cat <<-EOF\n\tline1")
        assert self.handler._is_complete_command("cat <<-EOF\n\tline1\nEOF")
        assert self.handler._is_complete_command("cat <<-EOF\n\tline1\n\tEOF")
        
        # Heredoc with quotes
        assert not self.handler._is_complete_command("cat <<'EOF'")
        assert self.handler._is_complete_command("cat <<'EOF'\nline\nEOF")
        assert not self.handler._is_complete_command('cat <<"EOF"')
        assert self.handler._is_complete_command('cat <<"EOF"\nline\nEOF')
        
        # Multiple heredocs
        assert not self.handler._is_complete_command("cat <<EOF1 && cat <<EOF2")
        assert not self.handler._is_complete_command("cat <<EOF1 && cat <<EOF2\nline1\nEOF1")
        assert self.handler._is_complete_command("cat <<EOF1 && cat <<EOF2\nline1\nEOF1\nline2\nEOF2")
    
    def test_read_command_simple(self):
        """Test reading a simple single-line command."""
        self.line_editor.read_line.return_value = "echo hello"
        
        result = self.handler.read_command()
        
        assert result == "echo hello"
        assert self.line_editor.read_line.call_count == 1
    
    def test_read_command_multiline(self):
        """Test reading a multi-line command."""
        # Mock multiple line inputs
        self.line_editor.read_line.side_effect = [
            "if true; then",
            "  echo hello",
            "fi"
        ]
        
        result = self.handler.read_command()
        
        assert result == "if true; then\n  echo hello\nfi"
        assert self.line_editor.read_line.call_count == 3
    
    def test_read_command_eof(self):
        """Test handling EOF during input."""
        self.line_editor.read_line.return_value = None
        
        result = self.handler.read_command()
        
        assert result is None
    
    def test_read_command_eof_in_multiline(self):
        """Test handling EOF in middle of multi-line input."""
        self.line_editor.read_line.side_effect = [
            "if true; then",
            None  # EOF
        ]
        
        with patch('builtins.print') as mock_print:
            result = self.handler.read_command()
        
        assert result is None
        mock_print.assert_called_with("\npsh: syntax error: unexpected end of file")
    
    def test_get_prompt_ps1(self):
        """Test getting primary prompt (PS1)."""
        self.shell.variables['PS1'] = 'test$ '
        prompt = self.handler._get_prompt()
        assert 'test$' in prompt  # May be expanded
    
    def test_get_prompt_ps2(self):
        """Test getting continuation prompt (PS2)."""
        self.shell.variables['PS2'] = '... '
        self.handler.buffer = ['if true; then']  # Non-empty buffer
        prompt = self.handler._get_prompt()
        assert prompt == '... '


class TestPromptExpander:
    """Test prompt expansion functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.shell = Shell()
        self.expander = PromptExpander(self.shell)
    
    def test_expand_literal_text(self):
        """Test that literal text is preserved."""
        assert self.expander.expand_prompt("hello world") == "hello world"
        assert self.expander.expand_prompt("$") == "$"
        assert self.expander.expand_prompt("test>") == "test>"
    
    def test_expand_backslash(self):
        """Test expansion of backslash escape."""
        assert self.expander.expand_prompt("\\\\") == "\\"
        assert self.expander.expand_prompt("foo\\\\bar") == "foo\\bar"
    
    def test_expand_newline_and_carriage_return(self):
        """Test expansion of newline and carriage return."""
        assert self.expander.expand_prompt("\\n") == "\n"
        assert self.expander.expand_prompt("\\r") == "\r"
        assert self.expander.expand_prompt("line1\\nline2") == "line1\nline2"
    
    def test_expand_bell_and_escape(self):
        """Test expansion of bell and escape characters."""
        assert self.expander.expand_prompt("\\a") == "\a"
        assert self.expander.expand_prompt("\\e") == "\033"
    
    def test_expand_shell_name(self):
        """Test expansion of shell name."""
        assert self.expander.expand_prompt("\\s") == "psh"
        assert self.expander.expand_prompt("Shell: \\s") == "Shell: psh"
    
    def test_expand_hostname(self):
        """Test expansion of hostname."""
        with patch('socket.gethostname', return_value='myhost.example.com'):
            expander = PromptExpander(self.shell)
            assert expander.expand_prompt("\\h") == "myhost"
            assert expander.expand_prompt("\\H") == "myhost.example.com"
    
    def test_expand_username(self):
        """Test expansion of username."""
        with patch('pwd.getpwuid') as mock_pwd:
            mock_pwd.return_value.pw_name = 'testuser'
            expander = PromptExpander(self.shell)
            assert expander.expand_prompt("\\u") == "testuser"
    
    def test_expand_working_directory(self):
        """Test expansion of working directory."""
        with patch('os.getcwd', return_value='/home/user/projects'):
            with patch('os.path.expanduser', return_value='/home/user'):
                assert self.expander.expand_prompt("\\w") == "~/projects"
                assert self.expander.expand_prompt("\\W") == "projects"
        
        with patch('os.getcwd', return_value='/'):
            assert self.expander.expand_prompt("\\W") == "/"
    
    def test_expand_dollar_hash(self):
        """Test expansion of $ or # based on uid."""
        with patch('os.geteuid', return_value=0):
            assert self.expander.expand_prompt("\\$") == "#"
        
        with patch('os.geteuid', return_value=1000):
            assert self.expander.expand_prompt("\\$") == "$"
    
    def test_expand_time_formats(self):
        """Test expansion of time formats."""
        test_time = datetime(2024, 1, 15, 14, 30, 45)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_time
            
            assert self.expander.expand_prompt("\\t") == "14:30:45"
            assert self.expander.expand_prompt("\\T") == "02:30:45"
            assert self.expander.expand_prompt("\\@") == "02:30 PM"
            assert self.expander.expand_prompt("\\A") == "14:30"
    
    def test_expand_date(self):
        """Test expansion of date."""
        test_date = datetime(2024, 1, 15)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_date
            
            assert self.expander.expand_prompt("\\d") == "Mon Jan 15"
    
    def test_expand_version(self):
        """Test expansion of version."""
        with patch('psh.version.__version__', '1.2.3'):
            assert self.expander.expand_prompt("\\v") == "1.2"
            assert self.expander.expand_prompt("\\V") == "1.2.3"
    
    def test_expand_octal_sequence(self):
        """Test expansion of octal sequences."""
        assert self.expander.expand_prompt("\\033") == "\033"  # ESC
        assert self.expander.expand_prompt("\\007") == "\007"  # Bell
        assert self.expander.expand_prompt("\\101") == "A"      # 101 octal = 65 decimal = 'A'
    
    def test_expand_non_printing_markers(self):
        """Test expansion of non-printing sequence markers."""
        assert self.expander.expand_prompt("\\[") == "\001"
        assert self.expander.expand_prompt("\\]") == "\002"
    
    def test_complex_prompt(self):
        """Test expansion of complex prompt with multiple escapes."""
        with patch('socket.gethostname', return_value='myhost'):
            with patch('pwd.getpwuid') as mock_pwd:
                mock_pwd.return_value.pw_name = 'user'
                with patch('os.getcwd', return_value='/home/user'):
                    with patch('os.path.expanduser', return_value='/home/user'):
                        expander = PromptExpander(self.shell)
                        
                        # Basic prompt
                        result = expander.expand_prompt("\\u@\\h:\\w\\$ ")
                        assert result == "user@myhost:~$ "
                        
                        # Colored prompt
                        result = expander.expand_prompt("\\[\\e[32m\\]\\u@\\h\\[\\e[0m\\]:\\w\\$ ")
                        assert result == "\001\033[32m\002user@myhost\001\033[0m\002:~$ "
    
    def test_invalid_escape_preserved(self):
        """Test that invalid escape sequences are preserved."""
        assert self.expander.expand_prompt("\\x") == "\\x"
        assert self.expander.expand_prompt("\\9") == "\\9"
        assert self.expander.expand_prompt("\\invalid") == "\\invalid"
    
    def test_expand_history_number(self):
        """Test expansion of history number."""
        # Set up shell with some history
        self.shell.history = ['echo 1', 'echo 2', 'echo 3']
        result = self.expander.expand_prompt("\\!")
        assert result == "4"  # Next history number
        
        # Empty history
        self.shell.history = []
        result = self.expander.expand_prompt("\\!")
        assert result == "1"
    
    def test_expand_command_number(self):
        """Test expansion of command number."""
        # Set up shell with command count
        self.shell.command_number = 5
        result = self.expander.expand_prompt("\\#")
        assert result == "6"  # Next command number
        
        # Fresh shell
        self.shell.command_number = 0
        result = self.expander.expand_prompt("\\#")
        assert result == "1"
    
    def test_complex_prompt_with_counters(self):
        """Test complex prompt with history and command numbers."""
        self.shell.history = ['cmd1', 'cmd2']
        self.shell.command_number = 10
        result = self.expander.expand_prompt("[\\!:\\#] \\$ ")
        assert result == "[3:11] $ "


class TestMultiLineEdgeCases:
    """Test edge cases for multi-line detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.shell = Shell()
        self.line_editor = Mock(spec=LineEditor)
        self.handler = MultiLineInputHandler(self.line_editor, self.shell)
    
    def test_operators_at_end_of_line(self):
        """Test that operators at end of line require continuation."""
        assert not self.handler._is_complete_command("echo hello |")
        assert not self.handler._is_complete_command("echo hello &&")
        assert not self.handler._is_complete_command("echo hello ||")
        assert self.handler._is_complete_command("echo hello | grep")
        assert self.handler._is_complete_command("true && echo success")
    
    def test_unclosed_expansions(self):
        """Test detection of unclosed expansions."""
        # Command substitution
        assert not self.handler._is_complete_command("echo $(")
        assert not self.handler._is_complete_command("echo $(echo hello")
        assert not self.handler._is_complete_command("echo `echo hello")
        assert self.handler._is_complete_command("echo $(echo hello)")
        assert self.handler._is_complete_command("echo `echo hello`")
    
    def test_escaped_heredoc_delimiter(self):
        """Test heredoc with escaped delimiter."""
        assert not self.handler._is_complete_command("cat << \\EOF")
        assert not self.handler._is_complete_command("cat << \\EOF\nline1")
        assert self.handler._is_complete_command("cat << \\EOF\nline1\nEOF")
    
    def test_multiline_with_trailing_spaces(self):
        """Test multi-line detection with trailing spaces."""
        assert not self.handler._is_complete_command("echo hello | ")
        assert not self.handler._is_complete_command("echo hello && ")
        assert not self.handler._is_complete_command("if true; then ")
    
    def test_nested_incomplete_structures(self):
        """Test nested incomplete control structures."""
        assert not self.handler._is_complete_command("if true; then\n  if false; then")
        assert not self.handler._is_complete_command("while true; do\n  for i in 1 2 3; do")
        assert self.handler._is_complete_command("if true; then\n  if false; then\n    echo nested\n  fi\nfi")


class TestMultiLineIntegration:
    """Integration tests for multi-line functionality."""
    
    def test_multiline_if_statement(self):
        """Test multi-line if statement execution."""
        shell = Shell()
        command = """if [ 1 -eq 1 ]; then
    echo "success"
fi"""
        exit_code = shell.run_command(command)
        assert exit_code == 0
    
    def test_multiline_for_loop(self):
        """Test multi-line for loop execution."""
        shell = Shell()
        command = """for i in 1 2 3; do
    echo $i
done"""
        exit_code = shell.run_command(command)
        assert exit_code == 0
    
    def test_multiline_function_definition(self):
        """Test multi-line function definition."""
        shell = Shell()
        command = """greet() {
    echo "Hello, $1!"
}
greet World"""
        exit_code = shell.run_command(command)
        assert exit_code == 0
    
    def test_nested_multiline_structures(self):
        """Test nested multi-line control structures."""
        shell = Shell()
        command = """for i in 1 2; do
    if [ $i -eq 1 ]; then
        echo "First"
    else
        echo "Second"
    fi
done"""
        exit_code = shell.run_command(command)
        assert exit_code == 0