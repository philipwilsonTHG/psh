"""Test file descriptor duplication (>&2, 2>&1)."""

import pytest
from psh.shell import Shell
import sys
from io import StringIO


class TestFDDuplication:
    """Test file descriptor duplication redirections."""
    
    def test_stdout_to_stderr(self, capsys):
        """Test >&2 redirection (stdout to stderr)."""
        shell = Shell()
        
        # Run command that redirects stdout to stderr
        shell.run_command('echo "hello" >&2')
        
        # Check that output went to stderr, not stdout
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "hello\n"
    
    def test_stderr_to_stdout(self, capsys):
        """Test 2>&1 redirection (stderr to stdout)."""
        shell = Shell()
        
        # Run command that would normally output to stderr
        # but redirect it to stdout
        shell.run_command('python -c "import sys; print(\"error\", file=sys.stderr)" 2>&1')
        
        # Check that error went to stdout, not stderr
        captured = capsys.readouterr()
        assert "error" in captured.out
        assert captured.err == ""
    
    def test_multiple_redirections(self, capsys, tmp_path):
        """Test combining file and fd redirections."""
        shell = Shell()
        outfile = tmp_path / "output.txt"
        
        # Redirect stdout to file, then stderr to stdout (which goes to file)
        shell.run_command(f'echo "stdout"; echo "stderr" >&2 > {outfile} 2>&1')
        
        # Both should be in the file
        content = outfile.read_text()
        assert "stdout" in content
        assert "stderr" in content
        
        # Nothing should be on console
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
    
    def test_partial_form_parsing(self):
        """Test that >&2 is parsed correctly (not as >& followed by 2)."""
        from psh.state_machine_lexer import tokenize
        from psh.parser import parse
        
        # Parse the command
        tokens = tokenize('echo test >&2')
        ast = parse(tokens)
        
        # Get the command
        cmd = ast.statements[0].pipelines[0].commands[0]
        
        # Check arguments - should not include '2'
        assert cmd.args == ['echo', 'test']
        
        # Check redirections
        assert len(cmd.redirects) == 1
        redir = cmd.redirects[0]
        assert redir.type == '>&'
        assert redir.fd == 1
        assert redir.dup_fd == 2
    
    def test_builtin_with_fd_dup(self, capsys):
        """Test builtin commands with fd duplication."""
        shell = Shell()
        
        # Echo is a builtin that should respect >&2
        shell.run_command('echo "to stderr" >&2')
        
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "to stderr\n"
    
    def test_fd_dup_in_pipeline(self, capsys):
        """Test fd duplication in a pipeline."""
        shell = Shell()
        
        # In a pipeline, the redirection applies to the specific command
        shell.run_command('echo "test" >&2 | cat')
        
        captured = capsys.readouterr()
        assert captured.out == ""  # cat receives nothing on stdin
        assert captured.err == "test\n"  # echo outputs to stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])