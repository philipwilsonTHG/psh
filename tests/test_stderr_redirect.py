import pytest
import tempfile
import os
import sys
from psh.state_machine_lexer import tokenize, TokenType
from psh.parser import parse
from psh.shell import Shell


class TestStderrRedirection:
    def test_tokenize_stderr_redirect(self):
        """Test tokenization of stderr redirection operators"""
        # Test 2>
        tokens = tokenize("ls 2> errors.txt")
        assert len(tokens) == 4  # ls, 2>, errors.txt, EOF
        assert tokens[0].type == TokenType.WORD and tokens[0].value == "ls"
        assert tokens[1].type == TokenType.REDIRECT_ERR and tokens[1].value == "2>"
        assert tokens[2].type == TokenType.WORD and tokens[2].value == "errors.txt"
        
        # Test 2>>
        tokens = tokenize("grep foo 2>> errors.log")
        assert len(tokens) == 5  # grep, foo, 2>>, errors.log, EOF
        assert tokens[2].type == TokenType.REDIRECT_ERR_APPEND and tokens[2].value == "2>>"
        
        # Test 2>&1
        tokens = tokenize("command 2>&1")
        assert len(tokens) == 3  # command, 2>&1, EOF
        assert tokens[1].type == TokenType.REDIRECT_DUP and tokens[1].value == "2>&1"
        
        # Test combined stdout and stderr
        tokens = tokenize("ls > output.txt 2>&1")
        assert len(tokens) == 5  # ls, >, output.txt, 2>&1, EOF
        assert tokens[1].type == TokenType.REDIRECT_OUT
        assert tokens[3].type == TokenType.REDIRECT_DUP
    
    def test_parse_stderr_redirect(self):
        """Test parsing of stderr redirection"""
        # Test 2>
        tokens = tokenize("ls 2> errors.txt")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert len(command.redirects) == 1
        redirect = command.redirects[0]
        assert redirect.type == '>'
        assert redirect.fd == 2
        assert redirect.target == 'errors.txt'
        
        # Test 2>>
        tokens = tokenize("grep foo 2>> errors.log")
        ast = parse(tokens)
        redirect = ast.pipelines[0].commands[0].redirects[0]
        assert redirect.type == '>>'
        assert redirect.fd == 2
        assert redirect.target == 'errors.log'
        
        # Test 2>&1
        tokens = tokenize("command 2>&1")
        ast = parse(tokens)
        redirect = ast.pipelines[0].commands[0].redirects[0]
        assert redirect.type == '>&'
        assert redirect.fd == 2
        assert redirect.dup_fd == 1
        
        # Test combined redirections
        tokens = tokenize("ls > output.txt 2>&1")
        ast = parse(tokens)
        redirects = ast.pipelines[0].commands[0].redirects
        assert len(redirects) == 2
        assert redirects[0].type == '>'
        assert redirects[0].fd is None  # stdout
        assert redirects[1].type == '>&'
        assert redirects[1].fd == 2
        assert redirects[1].dup_fd == 1
    
    @pytest.mark.skipif(os.getenv('GITHUB_ACTIONS') == 'true', 
                        reason="Shell execution tests can be flaky in CI")
    def test_stderr_redirect_execution(self):
        """Test actual execution of stderr redirection"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            error_file = os.path.join(tmpdir, "errors.txt")
            
            # Test redirecting stderr to a file
            # Using a command that will definitely produce stderr
            shell.run_command(f"ls /nonexistent/path 2> {error_file}")
            
            # Check that error was written to file
            with open(error_file, 'r') as f:
                content = f.read()
                assert "No such file or directory" in content or "cannot access" in content
            
            # Test appending to stderr file
            shell.run_command(f"ls /another/bad/path 2>> {error_file}")
            
            with open(error_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) >= 2  # Should have at least 2 error messages
    
    @pytest.mark.skipif(os.getenv('GITHUB_ACTIONS') == 'true', 
                        reason="Shell execution tests can be flaky in CI")
    def test_stderr_stdout_combined(self):
        """Test combining stderr and stdout"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "combined.txt")
            
            # Create a test script that outputs to both stdout and stderr
            test_script = os.path.join(tmpdir, "test.py")
            with open(test_script, 'w') as f:
                f.write('''import sys
print("This is stdout")
print("This is stderr", file=sys.stderr)
''')
            
            # Redirect both stdout and stderr to the same file
            shell.run_command(f"python3 {test_script} > {output_file} 2>&1")
            
            # Check that both outputs are in the file
            with open(output_file, 'r') as f:
                content = f.read()
                assert "This is stdout" in content
                assert "This is stderr" in content
    
    @pytest.mark.visitor_xfail(reason="Visitor executor needs proper stderr redirection for builtins")
    def test_stderr_redirect_with_builtin(self):
        """Test stderr redirection with built-in commands"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            error_file = os.path.join(tmpdir, "errors.txt")
            
            # cd to non-existent directory should produce stderr
            shell.run_command(f"cd /nonexistent/directory 2> {error_file}")
            
            # Check that error was written to file
            with open(error_file, 'r') as f:
                content = f.read()
                assert "No such file or directory" in content or "cd:" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])