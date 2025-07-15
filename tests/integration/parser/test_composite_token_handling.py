"""
Integration tests for parser handling of composite tokens.

These tests verify that the parser correctly handles composite tokens
(adjacent strings that should be concatenated) with and without the
composite token processor.
"""

import sys
from pathlib import Path

# Add PSH to path
PSH_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PSH_ROOT))

import pytest
from psh.lexer import tokenize
from psh.parser import Parser
from psh.ast_nodes import SimpleCommand, Pipeline


class TestCompositeTokenParsing:
    """Test parser behavior with composite tokens."""
    
    def parse_command(self, input_str: str, use_composite_processor: bool = False):
        """Helper to parse a command with optional composite processing."""
        tokens = tokenize(input_str)
        parser = Parser(tokens, use_composite_processor=use_composite_processor)
        return parser.parse()
    
    def get_simple_command(self, input_str: str, use_composite_processor: bool = False):
        """Helper to get the first simple command from parsed input."""
        ast = self.parse_command(input_str, use_composite_processor)
        return ast.and_or_lists[0].pipelines[0].commands[0]
    
    def test_simple_quoted_composite(self):
        """Test parsing of simple quoted string followed by unquoted text."""
        # Test without processor
        cmd = self.get_simple_command('echo "hello"world', use_composite_processor=False)
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'echo'
        assert cmd.args[1] == 'helloworld'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
        
        # Test with processor - should behave the same
        cmd = self.get_simple_command('echo "hello"world', use_composite_processor=True)
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'echo'
        assert cmd.args[1] == 'helloworld'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_multiple_adjacent_strings(self):
        """Test parsing of multiple adjacent quoted strings."""
        input_cmd = 'cat "part1""part2""part3"'
        
        # Without processor
        cmd = self.get_simple_command(input_cmd, use_composite_processor=False)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'cat'
        assert cmd.args[1] == 'part1part2part3'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
        
        # With processor
        cmd = self.get_simple_command(input_cmd, use_composite_processor=True)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'cat'
        assert cmd.args[1] == 'part1part2part3'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_mixed_quote_types(self):
        """Test parsing of mixed single and double quotes."""
        input_cmd = '''echo "double"'single'"mixed"'''
        
        cmd = self.get_simple_command(input_cmd, use_composite_processor=True)
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'echo'
        assert cmd.args[1] == 'doublesinglemixed'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_composite_with_spaces(self):
        """Test that spaces break composite tokens."""
        input_cmd = 'echo "hello" world'
        
        cmd = self.get_simple_command(input_cmd, use_composite_processor=True)
        assert len(cmd.args) == 3  # echo, hello, world (separate args)
        assert cmd.args[0] == 'echo'
        assert cmd.args[1] == 'hello'
        assert cmd.args[2] == 'world'
        # These should not be composite
        assert cmd.arg_types[1] != 'COMPOSITE_QUOTED'
        assert cmd.arg_types[2] != 'COMPOSITE_QUOTED'


class TestCompositeTokensInComplexStructures:
    """Test composite tokens in various shell structures."""
    
    def parse_command(self, input_str: str, use_composite_processor: bool = True):
        """Helper to parse with composite processor enabled by default."""
        tokens = tokenize(input_str)
        parser = Parser(tokens, use_composite_processor=use_composite_processor)
        return parser.parse()
    
    def test_multiple_composite_arguments(self):
        """Test command with multiple composite arguments."""
        ast = self.parse_command('cp "file"name "dest"dir/')
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert isinstance(cmd, SimpleCommand)
        assert len(cmd.args) == 3
        assert cmd.args[0] == 'cp'
        assert cmd.args[1] == 'filename'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
        assert cmd.args[2] == 'destdir/'
        assert cmd.arg_types[2] == 'COMPOSITE_QUOTED'
    
    def test_composite_in_pipeline(self):
        """Test composite tokens in pipeline commands."""
        ast = self.parse_command('cat "file"name | grep "pattern"text')
        
        # Check we have a pipeline with 2 commands
        pipeline = ast.and_or_lists[0].pipelines[0]
        assert len(pipeline.commands) == 2
        
        # First command: cat
        cmd1 = pipeline.commands[0]
        assert cmd1.args[0] == 'cat'
        assert cmd1.args[1] == 'filename'
        assert cmd1.arg_types[1] == 'COMPOSITE_QUOTED'
        
        # Second command: grep
        cmd2 = pipeline.commands[1]
        assert cmd2.args[0] == 'grep'
        assert cmd2.args[1] == 'patterntext'
        assert cmd2.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_composite_in_redirection(self):
        """Test composite tokens in file redirection."""
        ast = self.parse_command('echo test > "output"file.txt')
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        # Check the command
        assert cmd.args[0] == 'echo'
        assert cmd.args[1] == 'test'
        
        # Check the redirection
        assert len(cmd.redirects) == 1
        redirect = cmd.redirects[0]
        assert redirect.type == '>'
        assert redirect.target == 'outputfile.txt'
    
    def test_composite_with_variables(self):
        """Test composite tokens containing variables."""
        # Note: The actual variable expansion happens later, not in parsing
        ast = self.parse_command('echo "$HOME"/.bashrc')
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'echo'
        # The composite should preserve the variable
        assert '$HOME' in cmd.args[1]
        assert '/.bashrc' in cmd.args[1]
    
    def test_composite_in_subshell(self):
        """Test composite tokens within subshell."""
        ast = self.parse_command('(echo "sub"shell)')
        
        # Navigate to the subshell command
        subshell = ast.and_or_lists[0].pipelines[0].commands[0]
        # The subshell contains statements
        inner_cmd = subshell.statements.and_or_lists[0].pipelines[0].commands[0]
        
        assert inner_cmd.args[0] == 'echo'
        assert inner_cmd.args[1] == 'subshell'
        assert inner_cmd.arg_types[1] == 'COMPOSITE_QUOTED'


class TestCompositeEdgeCases:
    """Test edge cases in composite token handling."""
    
    def parse_command(self, input_str: str):
        """Helper to parse with composite processor enabled."""
        tokens = tokenize(input_str)
        parser = Parser(tokens, use_composite_processor=True)
        return parser.parse()
    
    def test_empty_quotes_composite(self):
        """Test composite with empty quoted strings."""
        ast = self.parse_command('echo ""hello')
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[1] == 'hello'  # Empty string concatenated
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_escaped_quotes_in_composite(self):
        """Test composite with escaped quotes."""
        # This tests how escaped quotes interact with composite tokens
        ast = self.parse_command(r'echo "part\"one"two')
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[0] == 'echo'
        # The exact result depends on how the lexer handles escapes
        assert 'part' in cmd.args[1]
        assert 'two' in cmd.args[1]
    
    def test_numeric_composite(self):
        """Test composite with numeric strings."""
        ast = self.parse_command('echo "123"456')
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[1] == '123456'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_special_chars_composite(self):
        """Test composite with special characters."""
        ast = self.parse_command('echo "hello-"world')
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[1] == 'hello-world'
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'
    
    def test_long_composite_chain(self):
        """Test very long chain of composite tokens."""
        # Create a long chain of adjacent strings
        parts = [f'"part{i}"' for i in range(10)]
        input_cmd = f'echo {"".join(parts)}'
        
        ast = self.parse_command(input_cmd)
        cmd = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        expected = ''.join(f'part{i}' for i in range(10))
        assert cmd.args[1] == expected
        assert cmd.arg_types[1] == 'COMPOSITE_QUOTED'