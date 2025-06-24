import pytest
import os
from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.token_types import TokenType
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
    
    def test_heredoc_with_external_command(self, shell, monkeypatch):
        """Test here document with external command"""
        import tempfile
        
        # Mock input
        input_lines = ["Line 1", "Line 2", "EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        # Create temporary file for output capture
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            temp_file = f.name
        
        try:
            # Use wc -l to count lines
            result = shell.run_command(f"wc -l << EOF > {temp_file}")
            assert result == 0
            
            with open(temp_file, 'r') as f:
                output = f.read().strip()
            assert "2" in output
        finally:
            os.unlink(temp_file)
    
    # @pytest.mark.skip(reason="Multiple redirections need special handling")
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
    
    def test_heredoc_in_pipeline(self, shell, monkeypatch):
        """Test here document in a pipeline"""
        import tempfile
        
        # Mock input
        input_lines = ["apple", "banana", "cherry", "EOF"]
        input_iter = iter(input_lines)
        monkeypatch.setattr('builtins.input', lambda: next(input_iter))
        
        # Create temporary file for output capture
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            temp_file = f.name
        
        try:
            result = shell.run_command(f"cat << EOF | wc -l > {temp_file}")
            assert result == 0
            
            with open(temp_file, 'r') as f:
                output = f.read().strip()
            assert "3" in output
        finally:
            os.unlink(temp_file)


class TestHereString:
    """Tests for here strings (<<<)"""
    
    @pytest.fixture
    def shell(self):
        return Shell()
    def test_tokenize_here_string(self):
        """Test that <<< is tokenized correctly"""
        tokens = tokenize("cat <<< 'hello world'")
        assert tokens[1].type == TokenType.HERE_STRING
        assert tokens[1].value == "<<<"
        assert tokens[2].type == TokenType.STRING
        assert tokens[2].value == "hello world"
    
    def test_parse_here_string(self):
        """Test parsing of here string"""
        tokens = tokenize("cat <<< 'test string'")
        ast = parse(tokens)
        command = ast.and_or_lists[0].pipelines[0].commands[0]
        
        assert len(command.redirects) == 1
        redirect = command.redirects[0]
        assert redirect.type == "<<<"
        assert redirect.target == "test string"
    
    def test_here_string_with_variable(self, shell, capsys):
        """Test here string with variable expansion"""
        shell.state.set_variable('NAME', 'World')
        
        output_file = "/tmp/herestring_var_test.txt"
        shell.run_command(f"cat <<< \"Hello $NAME\" > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert content == "Hello World\n"
        os.unlink(output_file)
    
    def test_here_string_literal(self, shell, capsys):
        """Test here string with literal text"""
        output_file = "/tmp/herestring_literal_test.txt"
        shell.run_command(f"cat <<< 'literal text' > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert content == "literal text\n"
        os.unlink(output_file)
    
    def test_here_string_with_builtin(self, shell, capsys):
        """Test here string output to file"""
        output_file = "/tmp/herestring_builtin_test.txt"
        shell.run_command(f"cat <<< 'from here string' > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert content == "from here string\n"
        os.unlink(output_file)
    
    def test_here_string_in_pipeline(self, shell, capsys):
        """Test here string in a pipeline"""
        output_file = "/tmp/herestring_pipeline_test.txt"
        shell.run_command(f"cat <<< 'apple banana cherry' | wc -w > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read().strip()
        assert "3" in content
        os.unlink(output_file)
    
    def test_here_string_with_quotes(self, shell, capsys):
        """Test here string handling quotes properly"""
        output_file = "/tmp/herestring_quotes_test.txt"
        shell.run_command(f'cat <<< "She said \\"Hello\\"" > {output_file}')
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert content == 'She said "Hello"\n'
        os.unlink(output_file)
    
    def test_here_string_empty(self, shell, capsys):
        """Test empty here string"""
        output_file = "/tmp/herestring_empty_test.txt"
        shell.run_command(f"cat <<< '' > {output_file}")
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert content == "\n"  # Just a newline
        os.unlink(output_file)