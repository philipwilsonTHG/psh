#!/usr/bin/env python3
"""Tests for comment handling."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.tokenizer import tokenize, TokenType
from psh.parser import parse
from psh.shell import Shell


class TestComments:
    """Test comment handling in the shell."""
    
    def test_comment_at_line_start(self):
        """Test comment at the beginning of a line."""
        tokens = tokenize("# This is a comment")
        # Comments are stripped, only EOF remains
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 0
    
    def test_comment_after_command(self):
        """Test comment after a command."""
        tokens = tokenize("echo hello # this is a comment")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 2
        assert actual_tokens[0].value == "echo"
        assert actual_tokens[1].value == "hello"
    
    def test_comment_in_word(self):
        """Test # in the middle of a word is not a comment."""
        tokens = tokenize("file#name")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 1
        assert actual_tokens[0].value == "file#name"
        
        tokens = tokenize("var#iable other")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 2
        assert actual_tokens[0].value == "var#iable"
        assert actual_tokens[1].value == "other"
    
    def test_comment_in_quotes(self):
        """Test # inside quotes is not a comment."""
        tokens = tokenize('"test # not a comment"')
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 1
        assert actual_tokens[0].type == TokenType.STRING
        assert actual_tokens[0].value == "test # not a comment"
        
        tokens = tokenize("'test # not a comment'")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 1
        assert actual_tokens[0].type == TokenType.STRING
        assert actual_tokens[0].value == "test # not a comment"
    
    def test_escaped_hash(self):
        """Test escaped # is not a comment."""
        tokens = tokenize(r"echo \# not a comment")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        # The escaped \# becomes a literal # word, followed by other words
        assert len(actual_tokens) == 5
        assert actual_tokens[0].value == "echo"
        assert actual_tokens[1].value == "#"
        assert actual_tokens[2].value == "not"
        assert actual_tokens[3].value == "a"
        assert actual_tokens[4].value == "comment"
    
    def test_comment_after_semicolon(self):
        """Test comment after semicolon."""
        tokens = tokenize("echo test; # comment")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 3
        assert actual_tokens[0].value == "echo"
        assert actual_tokens[1].value == "test"
        assert actual_tokens[2].type == TokenType.SEMICOLON
    
    def test_comment_after_pipe(self):
        """Test comment after pipe."""
        tokens = tokenize("echo test | grep foo # comment")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 5
        assert actual_tokens[2].type == TokenType.PIPE
        assert actual_tokens[3].value == "grep"
        assert actual_tokens[4].value == "foo"
    
    def test_multiple_hash(self):
        """Test multiple # characters."""
        tokens = tokenize("echo test ## multiple")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 2
        assert actual_tokens[0].value == "echo"
        assert actual_tokens[1].value == "test"
        
        tokens = tokenize("test#middle#word")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 1
        assert actual_tokens[0].value == "test#middle#word"
    
    def test_comment_preserves_newline(self):
        """Test that comments don't consume the newline."""
        tokens = tokenize("echo test # comment\necho after")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        # Should have: echo, test, NEWLINE, echo, after
        assert len(actual_tokens) == 5
        assert actual_tokens[0].value == "echo"
        assert actual_tokens[1].value == "test"
        assert actual_tokens[2].type == TokenType.NEWLINE
        assert actual_tokens[3].value == "echo"
        assert actual_tokens[4].value == "after"
    
    def test_variable_assignment_with_hash(self):
        """Test variable assignment with # in value."""
        tokens = tokenize("VAR=value#notcomment")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 1
        assert actual_tokens[0].value == "VAR=value#notcomment"
        
        tokens = tokenize("VAR=value # this is comment")
        actual_tokens = [t for t in tokens if t.type != TokenType.EOF]
        assert len(actual_tokens) == 1
        assert actual_tokens[0].value == "VAR=value"
    
    def test_parser_with_comments(self):
        """Test that parser handles tokenized input with comments correctly."""
        # Parser should work normally since comments are stripped by tokenizer
        tokens = tokenize("echo hello # comment")
        ast = parse(tokens)
        assert ast is not None
        assert len(ast.pipelines) == 1
        assert len(ast.pipelines[0].commands) == 1
        assert ast.pipelines[0].commands[0].args == ["echo", "hello"]
    
    def test_shell_execution_with_comments(self):
        """Test shell execution with comments."""
        shell = Shell()
        
        # Test simple command with comment
        exit_code = shell.run_command("echo hello # this is a comment", add_to_history=False)
        assert exit_code == 0
        
        # Test that # in word is preserved
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "psh", "-c", "echo file#name"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.stdout.strip() == "file#name"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])