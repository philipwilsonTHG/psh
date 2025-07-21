"""Test Word AST node creation in parsers."""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.recursive_descent_adapter import RecursiveDescentAdapter
from psh.parser.config import ParserConfig
from psh.ast_nodes import (
    Word, LiteralPart, ExpansionPart,
    VariableExpansion, CommandSubstitution, ParameterExpansion,
    SimpleCommand
)


class TestRecursiveDescentWordAST:
    """Test Word AST creation in recursive descent parser."""
    
    def test_word_ast_disabled_by_default(self):
        """Test that Word AST nodes are not created by default."""
        parser = RecursiveDescentAdapter()
        tokens = tokenize("echo $USER")
        ast = parser.parse(tokens)
        
        # Get the command
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["echo", "$USER"]
        assert cmd.words is None  # No Word nodes by default
    
    def test_simple_literal_word(self):
        """Test Word AST for simple literal arguments."""
        config = ParserConfig(build_word_ast_nodes=True)
        parser = RecursiveDescentAdapter()
        parser.config = config
        
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
        config = ParserConfig(build_word_ast_nodes=True)
        parser = RecursiveDescentAdapter()
        parser.config = config
        
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
        config = ParserConfig(build_word_ast_nodes=True)
        parser = RecursiveDescentAdapter()
        parser.config = config
        
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
        config = ParserConfig(build_word_ast_nodes=True)
        parser = RecursiveDescentAdapter()
        parser.config = config
        
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
        config = ParserConfig(build_word_ast_nodes=True)
        parser = RecursiveDescentAdapter()
        parser.config = config
        
        tokens = tokenize('echo "hello world" \'single quoted\'')
        ast = parser.parse(tokens)
        
        cmd = ast.statements[0].pipelines[0].commands[0]
        assert len(cmd.words) == 3
        
        # Double quoted
        word = cmd.words[1]
        assert word.quote_type == '"'
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], LiteralPart)
        assert word.parts[0].text == "hello world"
        assert str(word) == '"hello world"'
        
        # Single quoted
        word = cmd.words[2]
        assert word.quote_type == "'"
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], LiteralPart)
        assert word.parts[0].text == "single quoted"
        assert str(word) == "'single quoted'"
    
    @pytest.mark.skip(reason="Composite word parsing not yet implemented")
    def test_composite_word(self):
        """Test Word AST for composite words with mixed content."""
        config = ParserConfig(build_word_ast_nodes=True)
        parser = RecursiveDescentAdapter()
        parser.config = config
        
        # This would require the lexer to handle composite tokens differently
        tokens = tokenize("echo prefix-$USER-suffix")
        ast = parser.parse(tokens)
        
        cmd = ast.statements[0].pipelines[0].commands[0]
        word = cmd.words[1]
        assert len(word.parts) == 3
        assert isinstance(word.parts[0], LiteralPart)
        assert word.parts[0].text == "prefix-"
        assert isinstance(word.parts[1], ExpansionPart)
        assert isinstance(word.parts[1].expansion, VariableExpansion)
        assert isinstance(word.parts[2], LiteralPart)
        assert word.parts[2].text == "-suffix"
        assert str(word) == "prefix-$USER-suffix"