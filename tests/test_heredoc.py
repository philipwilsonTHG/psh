import pytest
import os
from psh.shell import Shell
from psh.tokenizer import tokenize, TokenType
from psh.parser import parse


class TestHereDoc:
    
    @pytest.fixture
    def shell(self):
        return Shell()
    
    def test_tokenize_heredoc(self):
        """Test that << is tokenized correctly"""
        tokens = tokenize("cat << EOF")
        assert tokens[1].type == TokenType.HEREDOC
        assert tokens[1].value == "<<"
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == "EOF"
    
    def test_tokenize_heredoc_strip(self):
        """Test that <<- is tokenized correctly"""
        tokens = tokenize("cat <<- END")
        assert tokens[1].type == TokenType.HEREDOC_STRIP
        assert tokens[1].value == "<<-"
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == "END"
    
    def test_parse_heredoc(self):
        """Test parsing of here document"""
        tokens = tokenize("cat << EOF")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        
        assert len(command.redirects) == 1
        redirect = command.redirects[0]
        assert redirect.type == "<<"
        assert redirect.target == "EOF"
        assert redirect.heredoc_content is None  # Not collected yet
    
    def test_heredoc_with_builtin(self, shell, capsys, monkeypatch):
        """Test here document with cat command"""
        # Mock input to provide heredoc content
        input_lines = ["Hello", "World", "EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        output_file = "/tmp/heredoc_test.txt"
        shell.run_command(f"cat << EOF > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert "Hello\nWorld\n" in content
        os.unlink(output_file)
    
    def test_heredoc_strip_tabs(self, shell, capsys, monkeypatch):
        """Test here document with tab stripping"""
        # Mock input with tabs
        input_lines = ["\tLine with tab", "\t\tDouble tab", "END"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        output_file = "/tmp/heredoc_strip_test.txt"
        shell.run_command(f"cat <<- END > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert "Line with tab\nDouble tab\n" in content
        assert "\t" not in content
        os.unlink(output_file)
    
    def test_heredoc_empty(self, shell, capsys, monkeypatch):
        """Test empty here document"""
        # Mock input with just delimiter
        input_lines = ["EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        output_file = "/tmp/heredoc_empty_test.txt"
        shell.run_command(f"cat << EOF > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert content == ""
        os.unlink(output_file)
    
    def test_heredoc_with_variable_expansion(self, shell, capsys, monkeypatch):
        """Test that variables in heredocs are not expanded (for now)"""
        shell.variables['VAR'] = 'value'
        
        input_lines = ["Hello $VAR", "EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        output_file = "/tmp/heredoc_var_test.txt"
        shell.run_command(f"cat << EOF > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        # Variables are not expanded in heredocs (this is a simplification)
        assert "Hello $VAR\n" in content
        os.unlink(output_file)
    
    @pytest.mark.skip(reason="Pytest capture doesn't work well with external commands")
    def test_heredoc_with_external_command(self, shell, capsys, monkeypatch):
        """Test here document with external command"""
        # Mock input
        input_lines = ["Line 1", "Line 2", "EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        # Use wc -l to count lines
        shell.run_command("wc -l << EOF")
        captured = capsys.readouterr()
        assert "2" in captured.out
    
    @pytest.mark.skip(reason="Multiple redirections need special handling")
    def test_heredoc_with_output_redirect(self, shell, monkeypatch, tmp_path):
        """Test here document combined with output redirection"""
        # Create temp file
        output_file = tmp_path / "output.txt"
        
        # Mock input
        input_lines = ["Test content", "EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        shell.run_command(f"cat << EOF > {output_file}")
        
        assert output_file.read_text() == "Test content\n"
    
    @pytest.mark.skip(reason="Pytest capture doesn't work well with pipelines")
    def test_heredoc_in_pipeline(self, shell, capsys, monkeypatch):
        """Test here document in a pipeline"""
        # Mock input
        input_lines = ["apple", "banana", "cherry", "EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        shell.run_command("cat << EOF | wc -l")
        captured = capsys.readouterr()
        assert "3" in captured.out