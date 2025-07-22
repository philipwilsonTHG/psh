"""Tests for exec command parsing in parser combinator."""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import SimpleCommand, CommandList


class TestExecCommandParsing:
    """Test exec command parsing functionality."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def get_simple_command(self, cmd_str):
        """Helper to get SimpleCommand from parsed result."""
        tokens = tokenize(cmd_str)
        result = self.parser.parse(tokens)
        
        stmt = result.statements[0]
        if hasattr(stmt, 'pipelines'):
            return stmt.pipelines[0].commands[0]
        else:
            return stmt
    
    def test_exec_with_file_descriptor_redirection(self):
        """Test: exec 3< /tmp/input.txt"""
        cmd = self.get_simple_command("exec 3< /tmp/input.txt")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec", "3"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "<"
        assert cmd.redirects[0].target == "/tmp/input.txt"
    
    def test_exec_with_stderr_redirection(self):
        """Test: exec 2> /tmp/error.log"""
        cmd = self.get_simple_command("exec 2> /tmp/error.log")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "2>"
        assert cmd.redirects[0].target == "/tmp/error.log"
    
    def test_exec_with_stdout_redirection(self):
        """Test: exec > /tmp/output.txt"""
        cmd = self.get_simple_command("exec > /tmp/output.txt")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == ">"
        assert cmd.redirects[0].target == "/tmp/output.txt"
    
    def test_exec_with_fd_duplication(self):
        """Test: exec 2>&1"""
        cmd = self.get_simple_command("exec 2>&1")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "2>&1"
    
    def test_exec_with_multiple_redirections(self):
        """Test: exec 3<&0 4>&1 (file descriptor duplication)"""
        cmd = self.get_simple_command("exec 3<&0 4>&1")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec"]
        assert len(cmd.redirects) == 2
        assert cmd.redirects[0].type == "3<&0"
        assert cmd.redirects[1].type == "4>&1"
    
    def test_exec_with_command_replacement(self):
        """Test: exec ls -la"""
        cmd = self.get_simple_command("exec ls -la")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec", "ls", "-la"]
        assert len(cmd.redirects) == 0
    
    def test_exec_with_command_and_redirection(self):
        """Test: exec cat file.txt > output.txt"""
        cmd = self.get_simple_command("exec cat file.txt > output.txt")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec", "cat", "file.txt"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == ">"
        assert cmd.redirects[0].target == "output.txt"
    
    def test_bare_exec(self):
        """Test: exec (no arguments, applies permanent redirections)"""
        cmd = self.get_simple_command("exec")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec"]
        assert len(cmd.redirects) == 0
    
    def test_exec_with_quoted_filenames(self):
        """Test: exec 3< "file with spaces.txt" """
        cmd = self.get_simple_command('exec 3< "file with spaces.txt"')
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec", "3"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "<"
        assert cmd.redirects[0].target == "file with spaces.txt"
    
    def test_exec_with_variables(self):
        """Test: exec $cmd $arg > $output"""
        cmd = self.get_simple_command("exec $cmd $arg > $output")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec", "$cmd", "$arg"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == ">"
        # Variable gets processed by lexer, removing $ prefix for plain variables
        assert cmd.redirects[0].target == "output"
    
    def test_exec_with_complex_redirections(self):
        """Test exec with heredoc and file descriptor operations."""
        # Test exec with heredoc (though unusual)
        cmd = self.get_simple_command("exec << EOF")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec"]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "<<"
        assert cmd.redirects[0].target == "EOF"
    
    def test_exec_in_pipeline_context(self):
        """Test that exec works in pipeline context (though unusual)."""
        tokens = tokenize("echo test | exec cat")
        result = self.parser.parse(tokens)
        
        # Should parse as a pipeline
        stmt = result.statements[0]
        assert hasattr(stmt, 'pipelines')
        pipeline = stmt.pipelines[0]
        assert len(pipeline.commands) == 2
        
        # Second command should be exec cat
        exec_cmd = pipeline.commands[1]
        assert exec_cmd.args == ["exec", "cat"]
    
    def test_exec_with_background(self):
        """Test: exec command &"""
        cmd = self.get_simple_command("exec sleep 10 &")
        
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["exec", "sleep", "10"]
        assert cmd.background is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])