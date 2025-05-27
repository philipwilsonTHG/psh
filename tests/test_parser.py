import pytest
from psh.tokenizer import tokenize
from psh.parser import Parser, parse, ParseError
from psh.ast_nodes import Command, Pipeline, CommandList, Redirect


class TestParser:
    def test_simple_command(self):
        tokens = tokenize("ls -la")
        ast = parse(tokens)
        
        assert isinstance(ast, CommandList)
        assert len(ast.pipelines) == 1
        
        pipeline = ast.pipelines[0]
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.commands) == 1
        
        command = pipeline.commands[0]
        assert isinstance(command, Command)
        assert command.args == ["ls", "-la"]
        assert command.redirects == []
        assert command.background is False
    
    def test_pipeline(self):
        tokens = tokenize("cat file | grep pattern | wc -l")
        ast = parse(tokens)
        
        pipeline = ast.pipelines[0]
        assert len(pipeline.commands) == 3
        
        assert pipeline.commands[0].args == ["cat", "file"]
        assert pipeline.commands[1].args == ["grep", "pattern"]
        assert pipeline.commands[2].args == ["wc", "-l"]
    
    def test_command_list(self):
        tokens = tokenize("echo first; echo second; echo third")
        ast = parse(tokens)
        
        assert len(ast.pipelines) == 3
        assert ast.pipelines[0].commands[0].args == ["echo", "first"]
        assert ast.pipelines[1].commands[0].args == ["echo", "second"]
        assert ast.pipelines[2].commands[0].args == ["echo", "third"]
    
    def test_redirections(self):
        # Input redirection
        tokens = tokenize("cat < input.txt")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert command.args == ["cat"]
        assert len(command.redirects) == 1
        assert command.redirects[0].type == "<"
        assert command.redirects[0].target == "input.txt"
        
        # Output redirection
        tokens = tokenize("echo hello > output.txt")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert command.args == ["echo", "hello"]
        assert len(command.redirects) == 1
        assert command.redirects[0].type == ">"
        assert command.redirects[0].target == "output.txt"
        
        # Multiple redirections
        tokens = tokenize("sort < input.txt > output.txt")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert command.args == ["sort"]
        assert len(command.redirects) == 2
        assert command.redirects[0].type == "<"
        assert command.redirects[0].target == "input.txt"
        assert command.redirects[1].type == ">"
        assert command.redirects[1].target == "output.txt"
    
    def test_background_command(self):
        tokens = tokenize("sleep 10 &")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert command.args == ["sleep", "10"]
        assert command.background is True
    
    def test_quoted_arguments(self):
        tokens = tokenize('echo "hello world" \'single quotes\'')
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert command.args == ["echo", "hello world", "single quotes"]
    
    def test_variables(self):
        tokens = tokenize("echo $HOME $USER")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert command.args == ["echo", "$HOME", "$USER"]
    
    def test_empty_command_list(self):
        tokens = tokenize("")
        ast = parse(tokens)
        assert isinstance(ast, CommandList)
        assert len(ast.pipelines) == 0
        
        # Multiple newlines
        tokens = tokenize("\n\n\n")
        ast = parse(tokens)
        assert len(ast.pipelines) == 0
    
    def test_trailing_semicolon(self):
        tokens = tokenize("echo hello;")
        ast = parse(tokens)
        assert len(ast.pipelines) == 1
        assert ast.pipelines[0].commands[0].args == ["echo", "hello"]
    
    def test_multiple_separators(self):
        tokens = tokenize("echo first;;; echo second")
        ast = parse(tokens)
        assert len(ast.pipelines) == 2
        assert ast.pipelines[0].commands[0].args == ["echo", "first"]
        assert ast.pipelines[1].commands[0].args == ["echo", "second"]
    
    def test_complex_command(self):
        tokens = tokenize("cat < in.txt | grep -v error | sort > out.txt; echo done &")
        ast = parse(tokens)
        
        assert len(ast.pipelines) == 2
        
        # First pipeline
        pipeline1 = ast.pipelines[0]
        assert len(pipeline1.commands) == 3
        
        # cat < in.txt
        cmd1 = pipeline1.commands[0]
        assert cmd1.args == ["cat"]
        assert len(cmd1.redirects) == 1
        assert cmd1.redirects[0].type == "<"
        assert cmd1.redirects[0].target == "in.txt"
        
        # grep -v error
        cmd2 = pipeline1.commands[1]
        assert cmd2.args == ["grep", "-v", "error"]
        
        # sort > out.txt
        cmd3 = pipeline1.commands[2]
        assert cmd3.args == ["sort"]
        assert len(cmd3.redirects) == 1
        assert cmd3.redirects[0].type == ">"
        assert cmd3.redirects[0].target == "out.txt"
        
        # Second pipeline: echo done &
        pipeline2 = ast.pipelines[1]
        cmd4 = pipeline2.commands[0]
        assert cmd4.args == ["echo", "done"]
        assert cmd4.background is True
    
    def test_parse_errors(self):
        # Missing command
        with pytest.raises(ParseError, match="Expected command"):
            parse(tokenize("|"))
        
        # Missing redirection target
        with pytest.raises(ParseError, match="Expected file name"):
            parse(tokenize("echo hello >"))
        
        # Pipe without command
        with pytest.raises(ParseError, match="Expected command"):
            parse(tokenize("echo hello; |"))