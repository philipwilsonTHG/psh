"""Tests for parser integration with CompositeTokenProcessor."""

import pytest
from psh.state_machine_lexer import tokenize
from psh.parser import Parser
from psh.ast_nodes import SimpleCommand, Pipeline


class TestParserCompositeIntegration:
    """Test parser behavior with and without composite processor."""
    
    def parse_command(self, input_str: str, use_composite_processor: bool = False):
        """Helper to parse a command with optional composite processing."""
        tokens = tokenize(input_str)
        parser = Parser(tokens, use_composite_processor=use_composite_processor)
        return parser.parse()
    
    def test_simple_composite_without_processor(self):
        """Test that parser handles composites correctly without processor."""
        # Use a case where lexer produces separate tokens
        ast = self.parse_command('echo "hello"world', use_composite_processor=False)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'echo'
        assert cmd.arg_types[0] == 'WORD'
        assert cmd.args[1] == 'helloworld'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_simple_composite_with_processor(self):
        """Test that parser handles pre-processed composites."""
        # Use a case where lexer produces separate tokens
        ast = self.parse_command('echo "hello"world', use_composite_processor=True)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'echo'
        assert cmd.arg_types[0] == 'WORD'
        assert cmd.args[1] == 'helloworld'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_complex_composite_without_processor(self):
        """Test complex composite without processor."""
        # Test with multiple adjacent strings
        ast = self.parse_command('cat "part1""part2""part3"', use_composite_processor=False)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'cat'
        assert cmd.args[1] == 'part1part2part3'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_complex_composite_with_processor(self):
        """Test complex composite with processor."""
        # Test with multiple adjacent strings
        ast = self.parse_command('cat "part1""part2""part3"', use_composite_processor=True)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'cat'
        assert cmd.args[1] == 'part1part2part3'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_quoted_composite_without_processor(self):
        """Test quoted composite without processor."""
        ast = self.parse_command('echo "hello"world', use_composite_processor=False)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[1] == 'helloworld'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_quoted_composite_with_processor(self):
        """Test quoted composite with processor."""
        ast = self.parse_command('echo "hello"world', use_composite_processor=True)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[1] == 'helloworld'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_multiple_arguments_with_composites(self):
        """Test multiple arguments, some composite."""
        ast = self.parse_command('cp "file"name "dest"dir/', use_composite_processor=True)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 3
        assert cmd.args[0] == 'cp'
        assert cmd.args[1] == 'filename'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
        assert cmd.args[2] == 'destdir/'
        assert cmd.arg_types[2] == 'COMPOSITE_QUOTED'
    
    def test_pipeline_with_composites(self):
        """Test pipeline commands with composites."""
        ast = self.parse_command('cat "file"name | grep "pattern"text', use_composite_processor=True)
        
        assert len(ast.and_or_lists[0].pipelines[0].commands) == 2
        
        cmd1 = ast.and_or_lists[0].pipelines[0].commands[0]
        assert cmd1.args[1] == 'filename'
        assert cmd1.arg_types[1] == 'COMPOSITE_QUOTED'
        
        cmd2 = ast.and_or_lists[0].pipelines[0].commands[1]
        assert cmd2.args[1] == 'patterntext'
        assert cmd2.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_redirect_with_composite(self):
        """Test redirection to composite filename."""
        ast = self.parse_command('echo test > "output"file.txt', use_composite_processor=True)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.redirects) == 1
        redirect = cmd.redirects[0]
        assert redirect.target == 'outputfile.txt'
    
    def test_array_element_composite(self):
        """Test array element access as composite."""
        # Test a case that the lexer actually tokenizes separately
        ast = self.parse_command('echo "prefix"suffix', use_composite_processor=True)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[1] == 'prefixsuffix'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'