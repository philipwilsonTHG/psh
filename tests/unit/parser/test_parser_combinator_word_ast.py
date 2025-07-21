"""Test Word AST node creation in parser combinator."""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.parser.config import ParserConfig
from psh.ast_nodes import (
    Word, LiteralPart, ExpansionPart,
    VariableExpansion, CommandSubstitution, ParameterExpansion,
    SimpleCommand, CommandList
)


class TestParserCombinatorWordAST:
    """Test Word AST creation in parser combinator."""
    
    def test_word_ast_disabled_by_default(self):
        """Test that Word AST nodes are not created by default."""
        parser = ParserCombinatorShellParser()
        tokens = tokenize("echo $USER")
        ast = parser.parse(tokens)
        
        # Navigate to the command
        assert isinstance(ast, CommandList)
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["echo", "$USER"]
        assert not hasattr(cmd, 'words') or cmd.words is None  # No Word nodes by default
    
    def test_simple_literal_word(self):
        """Test Word AST for simple literal arguments."""
        parser = ParserCombinatorShellParser()
        parser.config = ParserConfig(build_word_ast_nodes=True)
        
        tokens = tokenize("echo hello world")
        ast = parser.parse(tokens)
        
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert cmd.words is not None
        assert len(cmd.words) == 3
        
        # Check each word
        for i, expected in enumerate(["echo", "hello", "world"]):
            word = cmd.words[i]
            assert isinstance(word, Word)
            assert len(word.parts) == 1
            assert isinstance(word.parts[0], LiteralPart)
            assert word.parts[0].text == expected
            assert str(word) == expected
    
    def test_variable_expansion_word(self):
        """Test Word AST for variable expansion."""
        parser = ParserCombinatorShellParser()
        parser.config = ParserConfig(build_word_ast_nodes=True)
        
        tokens = tokenize("echo $USER $HOME")
        ast = parser.parse(tokens)
        
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert cmd.words is not None
        assert len(cmd.words) == 3
        
        # First word is literal "echo"
        assert isinstance(cmd.words[0].parts[0], LiteralPart)
        
        # Second word is $USER
        word = cmd.words[1]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, VariableExpansion)
        assert word.parts[0].expansion.name == "USER"
        assert str(word) == "$USER"
        
        # Third word is $HOME
        word = cmd.words[2]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, VariableExpansion)
        assert word.parts[0].expansion.name == "HOME"
        assert str(word) == "$HOME"
    
    def test_command_substitution_word(self):
        """Test Word AST for command substitution."""
        parser = ParserCombinatorShellParser()
        parser.config = ParserConfig(build_word_ast_nodes=True)
        
        tokens = tokenize("echo $(date) `hostname`")
        ast = parser.parse(tokens)
        
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert len(cmd.words) == 3
        
        # Check $(date)
        word = cmd.words[1]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, CommandSubstitution)
        assert word.parts[0].expansion.command == "date"
        assert not word.parts[0].expansion.backtick_style
        assert str(word) == "$(date)"
        
        # Check `hostname`
        word = cmd.words[2]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, CommandSubstitution)
        assert word.parts[0].expansion.command == "hostname"
        assert word.parts[0].expansion.backtick_style
        assert str(word) == "`hostname`"
    
    def test_parameter_expansion_word(self):
        """Test Word AST for parameter expansion."""
        parser = ParserCombinatorShellParser()
        parser.config = ParserConfig(build_word_ast_nodes=True)
        
        tokens = tokenize("echo ${USER:-nobody} ${#PATH}")
        ast = parser.parse(tokens)
        
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert len(cmd.words) == 3
        
        # Check ${USER:-nobody}
        word = cmd.words[1]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ParameterExpansion)
        assert word.parts[0].expansion.parameter == "USER"
        assert word.parts[0].expansion.operator == ":-"
        assert word.parts[0].expansion.word == "nobody"
        assert str(word) == "${USER:-nobody}"
        
        # Check ${#PATH}
        word = cmd.words[2]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ParameterExpansion)
        assert word.parts[0].expansion.parameter == "PATH"
        assert word.parts[0].expansion.operator == "#"
        assert word.parts[0].expansion.word is None
        assert str(word) == "${#PATH}"
    
    def test_quoted_word(self):
        """Test Word AST for quoted strings."""
        parser = ParserCombinatorShellParser()
        parser.config = ParserConfig(build_word_ast_nodes=True)
        
        tokens = tokenize('echo "hello world" \'single quoted\'')
        ast = parser.parse(tokens)
        
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert len(cmd.words) == 3
        
        # Double quoted
        word = cmd.words[1]
        # Parser combinator doesn't have access to quote type from tokens
        # so we check the content
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], LiteralPart)
        assert word.parts[0].text == "hello world"
        
        # Single quoted
        word = cmd.words[2]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], LiteralPart)
        assert word.parts[0].text == "single quoted"
    
    def test_word_ast_in_pipeline(self):
        """Test Word AST nodes in a pipeline."""
        parser = ParserCombinatorShellParser()
        parser.config = ParserConfig(build_word_ast_nodes=True)
        
        tokens = tokenize("echo $USER | grep $HOME")
        ast = parser.parse(tokens)
        
        # First command in pipeline
        cmd1 = ast.statements[0].pipelines[0].commands[0]
        assert len(cmd1.words) == 2
        assert isinstance(cmd1.words[1].parts[0], ExpansionPart)
        assert isinstance(cmd1.words[1].parts[0].expansion, VariableExpansion)
        
        # Second command in pipeline
        cmd2 = ast.statements[0].pipelines[0].commands[1]
        assert len(cmd2.words) == 2
        assert isinstance(cmd2.words[1].parts[0], ExpansionPart)
        assert isinstance(cmd2.words[1].parts[0].expansion, VariableExpansion)