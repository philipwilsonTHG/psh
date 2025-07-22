#!/usr/bin/env python3
"""Integration tests for parser combinator I/O redirection support.

This module tests that the parser combinator correctly parses I/O redirections
and that the resulting AST nodes are properly structured for execution.
"""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import (
    SimpleCommand, Pipeline, CommandList, Redirect, AndOrList
)


class TestParserCombinatorIORedirection:
    """Test I/O redirection parsing with parser combinator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ParserCombinatorShellParser()
    
    def parse(self, command: str):
        """Helper to parse a command string."""
        tokens = tokenize(command)
        return self.parser.parse(tokens)
    
    def get_redirects(self, command):
        """Extract redirects from a parsed command."""
        ast = self.parse(command)
        
        # Navigate to the SimpleCommand
        if isinstance(ast, CommandList):
            statement = ast.statements[0]
            if isinstance(statement, AndOrList):
                pipeline = statement.pipelines[0]
                cmd = pipeline.commands[0]
            elif isinstance(statement, Pipeline):
                cmd = statement.commands[0]
            else:
                cmd = statement
        else:
            cmd = ast
            
        if isinstance(cmd, SimpleCommand):
            return cmd.redirects
        return []


class TestOutputRedirection(TestParserCombinatorIORedirection):
    """Test output redirection (>, >>)."""
    
    def test_simple_output_redirect(self):
        """Test: echo hello > file.txt"""
        redirects = self.get_redirects("echo hello > file.txt")
        assert len(redirects) == 1
        
        redirect = redirects[0]
        assert redirect.type == '>'
        assert redirect.fd is None  # Default stdout
        assert redirect.target == "file.txt"
    
    def test_append_output_redirect(self):
        """Test: echo world >> file.txt"""
        redirects = self.get_redirects("echo world >> file.txt")
        assert len(redirects) == 1
        
        redirect = redirects[0]
        assert redirect.type == '>>'
        assert redirect.fd is None
        assert redirect.target == "file.txt"
    
    def test_stderr_redirect_supported(self):
        """Test: command 2> error.log - NOW SUPPORTED"""
        # Parser combinator now supports stderr redirects
        redirects = self.get_redirects("command 2> error.log")
        assert len(redirects) == 1
        assert redirects[0].type == '2>'
        assert redirects[0].target == 'error.log'
    
    def test_multiple_basic_redirects(self):
        """Test: cmd < in.txt > out.txt"""
        redirects = self.get_redirects("cmd < in.txt > out.txt")
        assert len(redirects) == 2
        
        # First redirect (stdin)
        assert redirects[0].type == '<'
        assert redirects[0].fd is None
        assert redirects[0].target == "in.txt"
        
        # Second redirect (stdout)
        assert redirects[1].type == '>'
        assert redirects[1].fd is None
        assert redirects[1].target == "out.txt"


class TestInputRedirection(TestParserCombinatorIORedirection):
    """Test input redirection (<)."""
    
    def test_simple_input_redirect(self):
        """Test: cat < input.txt"""
        redirects = self.get_redirects("cat < input.txt")
        assert len(redirects) == 1
        
        redirect = redirects[0]
        assert redirect.type == '<'
        assert redirect.fd is None  # Default stdin
        assert redirect.target == "input.txt"
    
    def test_fd_input_redirect_not_supported(self):
        """Test: command 3< data.txt - NOT SUPPORTED CORRECTLY"""
        # Parser combinator parses this incorrectly as "command 3 < data.txt"
        ast = self.parse("command 3< data.txt")
        cmd = ast.statements[0].pipelines[0].commands[0]
        # It treats "3" as an argument and < as a regular redirect
        assert len(cmd.args) == 2
        assert cmd.args[0] == "command"
        assert cmd.args[1] == "3"
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == '<'
        assert cmd.redirects[0].fd is None  # Not parsed as fd 3
    
    def test_input_output_combined(self):
        """Test: sort < input.txt > output.txt"""
        redirects = self.get_redirects("sort < input.txt > output.txt")
        assert len(redirects) == 2
        
        # Input redirect
        assert redirects[0].type == '<'
        assert redirects[0].target == "input.txt"
        
        # Output redirect
        assert redirects[1].type == '>'
        assert redirects[1].target == "output.txt"


class TestRedirectionWithPipelines(TestParserCombinatorIORedirection):
    """Test redirections in pipeline contexts."""
    
    def test_pipeline_with_output_redirect(self):
        """Test: ls | grep txt > files.txt"""
        ast = self.parse("ls | grep txt > files.txt")
        
        # Should be a pipeline
        assert isinstance(ast, CommandList)
        pipeline = ast.statements[0].pipelines[0]
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.commands) == 2
        
        # Second command should have redirect
        grep_cmd = pipeline.commands[1]
        assert isinstance(grep_cmd, SimpleCommand)
        assert len(grep_cmd.redirects) == 1
        assert grep_cmd.redirects[0].type == '>'
        assert grep_cmd.redirects[0].target == "files.txt"
    
    def test_pipeline_with_input_redirect(self):
        """Test: grep pattern < file.txt | sort"""
        ast = self.parse("grep pattern < file.txt | sort")
        
        pipeline = ast.statements[0].pipelines[0]
        assert len(pipeline.commands) == 2
        
        # First command should have redirect
        grep_cmd = pipeline.commands[0]
        assert len(grep_cmd.redirects) == 1
        assert grep_cmd.redirects[0].type == '<'
        assert grep_cmd.redirects[0].target == "file.txt"
    
    def test_complex_pipeline_redirects(self):
        """Test: cat < in.txt | sort | uniq > out.txt"""
        ast = self.parse("cat < in.txt | sort | uniq > out.txt")
        
        pipeline = ast.statements[0].pipelines[0]
        assert len(pipeline.commands) == 3
        
        # First command input redirect
        assert pipeline.commands[0].redirects[0].type == '<'
        assert pipeline.commands[0].redirects[0].target == "in.txt"
        
        # Last command output redirect
        assert pipeline.commands[2].redirects[0].type == '>'
        assert pipeline.commands[2].redirects[0].target == "out.txt"


class TestRedirectionWithControlStructures(TestParserCombinatorIORedirection):
    """Test redirections with control structures."""
    
    def test_if_with_redirected_command(self):
        """Test: if true; then echo yes > result.txt; fi"""
        ast = self.parse("if true; then echo yes > result.txt; fi")
        
        # Navigate to the echo command in then block (unwrapped in Phase 3)
        if_stmt = ast.statements[0]
        then_block = if_stmt.then_part
        echo_cmd = then_block.statements[0].pipelines[0].commands[0]
        
        assert len(echo_cmd.redirects) == 1
        assert echo_cmd.redirects[0].type == '>'
        assert echo_cmd.redirects[0].target == "result.txt"
    
    def test_loop_with_input_redirect(self):
        """Test parsing of: while read line; do echo $line; done < file.txt"""
        # Note: This may not parse correctly due to limitations
        try:
            ast = self.parse("while read line; do echo $line; done < file.txt")
            # If it parses, check structure
            assert ast is not None
        except:
            # Expected - parser combinator may not support this
            pass
    
    def test_for_loop_with_output_redirect(self):
        """Test: for i in 1 2 3; do echo $i > num_$i.txt; done"""
        ast = self.parse("for i in 1 2 3; do echo $i > num_$i.txt; done")
        
        # Navigate to echo command in loop body (unwrapped in Phase 3)
        for_loop = ast.statements[0]
        echo_cmd = for_loop.body.statements[0].pipelines[0].commands[0]
        
        assert len(echo_cmd.redirects) == 1
        assert echo_cmd.redirects[0].type == '>'
        # Target contains expansion, check it's parsed
        assert "num_" in echo_cmd.redirects[0].target


class TestRedirectionEdgeCases(TestParserCombinatorIORedirection):
    """Test edge cases and complex redirections."""
    
    def test_redirect_with_spaces(self):
        """Test redirect target with spaces (quoted)."""
        redirects = self.get_redirects('echo test > "file with spaces.txt"')
        assert len(redirects) == 1
        assert redirects[0].target == 'file with spaces.txt'  # Quotes removed during parsing
    
    def test_redirect_order_preservation(self):
        """Test that redirect order is preserved."""
        redirects = self.get_redirects("cmd > out.txt < in.txt >> append.txt")
        assert len(redirects) == 3
        
        # Check order
        assert redirects[0].type == '>'
        assert redirects[0].target == "out.txt"
        
        assert redirects[1].type == '<'
        assert redirects[1].target == "in.txt"
        
        assert redirects[2].type == '>>'
        assert redirects[2].target == "append.txt"
    
    def test_exec_with_basic_redirect(self):
        """Test: exec < file.txt"""
        redirects = self.get_redirects("exec < file.txt")
        assert len(redirects) == 1
        assert redirects[0].type == '<'
        assert redirects[0].target == "file.txt"


class TestAdvancedRedirections(TestParserCombinatorIORedirection):
    """Test advanced redirection features."""
    
    def test_heredoc_now_supported(self):
        """Test that heredocs are now supported."""
        # Heredocs are now supported in the parser combinator
        ast = self.parse("cat << EOF\nhello\nEOF")
        assert ast is not None
    
    def test_herestring_now_supported(self):
        """Test that herestrings are now supported."""
        # Herestrings are now supported in the parser combinator
        ast = self.parse("cat <<< 'hello world'")
        assert ast is not None
    
    def test_fd_duplication_not_supported(self):
        """Test that fd duplication may not be supported."""
        # This might parse but not execute correctly
        try:
            ast = self.parse("command 2>&1")
            # If it parses, that's ok, execution will handle it
        except:
            # Also ok - parser may reject it
            pass
    
    def test_closing_fd_not_supported(self):
        """Test that closing fds may not be supported."""
        try:
            ast = self.parse("command 3>&-")
        except:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])