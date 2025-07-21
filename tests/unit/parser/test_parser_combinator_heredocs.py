"""Test heredoc support in parser combinator implementation.

This module tests the heredoc functionality added to the parser combinator,
including basic heredocs, tab-stripping heredocs, here strings, and content
population.
"""

import pytest
from psh.lexer import tokenize_with_heredocs
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import SimpleCommand, Redirect, CommandList


class TestParserCombinatorHeredocs:
    """Test heredoc parsing in parser combinator."""
    
    def test_simple_heredoc_parsing(self):
        """Test basic heredoc parsing without content."""
        cmd = "cat <<EOF"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        assert isinstance(ast, CommandList)
        assert len(ast.statements) == 1
        
        # Parser combinator wraps commands in AndOrList -> Pipeline -> SimpleCommand
        statement = ast.statements[0]
        from psh.ast_nodes import AndOrList, Pipeline
        assert isinstance(statement, AndOrList)
        assert len(statement.pipelines) == 1
        
        pipeline = statement.pipelines[0]
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.commands) == 1
        
        command = pipeline.commands[0]
        assert isinstance(command, SimpleCommand)
        assert command.args == ["cat"]
        assert len(command.redirects) == 1
        
        redirect = command.redirects[0]
        assert redirect.type == "<<"
        assert redirect.target == "EOF"
        assert redirect.heredoc_quoted == False
    
    def test_quoted_delimiter_heredoc(self):
        """Test heredoc with quoted delimiter."""
        cmd = "cat <<'EOF'"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        # Extract command from AST structure
        command = ast.statements[0].pipelines[0].commands[0]
        redirect = command.redirects[0]
        assert redirect.type == "<<"
        assert redirect.target == "EOF"  # Quotes should be stripped
        assert redirect.heredoc_quoted == True  # Should detect quoted delimiter
    
    def test_heredoc_strip_parsing(self):
        """Test <<- tab-stripping heredoc parsing."""
        cmd = "cat <<-EOF"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        command = ast.statements[0].pipelines[0].commands[0]
        redirect = command.redirects[0]
        assert redirect.type == "<<-"
        assert redirect.target == "EOF"
        assert redirect.heredoc_quoted == False
    
    def test_here_string_parsing(self):
        """Test here string (<<<) parsing."""
        cmd = "cat <<<'hello world'"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        command = ast.statements[0].pipelines[0].commands[0]
        redirect = command.redirects[0]
        assert redirect.type == "<<<"
        assert redirect.target == "hello world"  # Quotes are stripped from target
        assert redirect.heredoc_content == "hello world"
        assert redirect.heredoc_quoted == True  # Here strings disable expansion
    
    def test_heredoc_with_content_population(self):
        """Test heredoc content population via two-pass parsing."""
        cmd = "cat <<EOF"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        # Simulate heredoc content collection
        heredoc_contents = {"heredoc_0_EOF": "line1\nline2\n"}
        
        parser = ParserCombinatorShellParser()
        
        # Use two-pass parsing
        ast = parser.parse_with_heredocs(tokens, heredoc_contents)
        
        command = ast.statements[0].pipelines[0].commands[0]
        redirect = command.redirects[0]
        assert redirect.type == "<<"
        assert redirect.target == "EOF"
        # Note: Content population requires the lexer to provide heredoc_key
        # which is not available in this test setup
    
    def test_multiple_heredocs(self):
        """Test multiple heredocs in one command."""
        cmd = "cat <<EOF1 <<EOF2"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        command = ast.statements[0].pipelines[0].commands[0]
        assert len(command.redirects) == 2
        
        redirect1 = command.redirects[0]
        assert redirect1.type == "<<"
        assert redirect1.target == "EOF1"
        
        redirect2 = command.redirects[1]
        assert redirect2.type == "<<"
        assert redirect2.target == "EOF2"
    
    def test_heredoc_with_other_redirections(self):
        """Test heredoc combined with other redirections."""
        cmd = "cat <<EOF >output.txt"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        command = ast.statements[0].pipelines[0].commands[0]
        assert len(command.redirects) == 2
        
        # Find heredoc and output redirection
        heredoc = None
        output_redirect = None
        for redirect in command.redirects:
            if redirect.type == "<<":
                heredoc = redirect
            elif redirect.type == ">":
                output_redirect = redirect
        
        assert heredoc is not None
        assert heredoc.target == "EOF"
        
        assert output_redirect is not None
        assert output_redirect.target == "output.txt"


class TestHeredocErrorCases:
    """Test error cases in heredoc parsing."""
    
    def test_heredoc_missing_delimiter(self):
        """Test error when heredoc delimiter is missing."""
        cmd = "cat <<"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        
        with pytest.raises(Exception):  # Should fail to parse
            parser.parse(tokens)
    
    def test_here_string_missing_content(self):
        """Test error when here string content is missing."""
        cmd = "cat <<<"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        
        with pytest.raises(Exception):  # Should fail to parse
            parser.parse(tokens)


class TestHeredocIntegration:
    """Test heredoc integration with other features."""
    
    def test_heredoc_in_if_statement(self):
        """Test heredoc inside if statement."""
        cmd = """if true; then
    cat <<EOF
EOF
fi"""
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        # Should parse without error
        assert ast is not None
        # Note: Full structure validation would require more complex setup
    
    def test_heredoc_in_pipeline(self):
        """Test heredoc in pipeline."""
        cmd = "cat <<EOF | grep test"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        # Should parse as pipeline with heredoc in first command
        from psh.ast_nodes import Pipeline
        and_or_list = ast.statements[0]
        pipeline = and_or_list.pipelines[0]
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.commands) == 2
        
        cat_cmd = pipeline.commands[0]
        assert len(cat_cmd.redirects) == 1
        assert cat_cmd.redirects[0].type == "<<"


class TestHeredocCompatibility:
    """Test compatibility with existing parser combinator features."""
    
    def test_heredoc_does_not_break_existing_redirections(self):
        """Ensure heredoc support doesn't break existing redirection parsing."""
        cmd = "cat >output.txt <input.txt 2>error.log"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        command = ast.statements[0].pipelines[0].commands[0]
        assert len(command.redirects) == 3
        
        # Verify all redirections are parsed correctly
        redirect_types = [r.type for r in command.redirects]
        assert ">" in redirect_types
        assert "<" in redirect_types
        assert "2>" in redirect_types
    
    def test_heredoc_with_background_process(self):
        """Test heredoc with background process."""
        cmd = "cat <<EOF &"
        tokens, heredoc_contents = tokenize_with_heredocs(cmd)
        
        parser = ParserCombinatorShellParser()
        ast = parser.parse(tokens)
        
        command = ast.statements[0].pipelines[0].commands[0]
        assert command.background == True
        assert len(command.redirects) == 1
        assert command.redirects[0].type == "<<"