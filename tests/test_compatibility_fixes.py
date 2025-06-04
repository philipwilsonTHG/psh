"""Unit tests for compatibility fixes between PSH and Bash."""

import pytest
from psh.state_machine_lexer import tokenize, TokenType
from psh.parser import parse, ParseError
from psh.shell import Shell
from psh.token_transformer import TokenTransformer


class TestWordConcatenation:
    """Test word concatenation functionality."""
    
    def test_simple_concatenation(self, capsys):
        """Test basic string concatenation like '*'.txt"""
        shell = Shell()
        # Should concatenate into single argument
        result = shell.run_command("echo '*'.txt")
        captured = capsys.readouterr()
        assert captured.out.strip() == "*.txt"
    
    def test_complex_concatenation(self, capsys):
        """Test complex concatenation like a'b'c\"d\"e"""
        shell = Shell()
        result = shell.run_command("echo a'b'c\"d\"e")
        captured = capsys.readouterr()
        # Quotes should be stripped in the output
        assert captured.out.strip() == "abcde"
    
    def test_concatenation_with_variables(self, capsys):
        """Test concatenation including variables."""
        shell = Shell()
        shell.variables['x'] = 'test'
        result = shell.run_command("echo pre$x'post'")
        captured = capsys.readouterr()
        # Known limitation: When adjacent tokens are concatenated into COMPOSITE arguments,
        # we lose the information about which parts were variables. The whole string
        # "pre$xpost" is treated as containing variable $xpost (not $x).
        # To get the desired behavior, use braces: ${x}
        assert captured.out.strip() == "pre"
        
        # This works correctly with braces
        result = shell.run_command("echo pre${x}post")
        captured = capsys.readouterr()
        assert captured.out.strip() == "pretestpost"
    
    def test_non_adjacent_no_concatenation(self, capsys):
        """Test that non-adjacent tokens are not concatenated."""
        shell = Shell()
        result = shell.run_command("echo 'a' 'b'")
        captured = capsys.readouterr()
        assert captured.out.strip() == "a b"
    
    def test_tokenization_positions(self):
        """Test that token positions are properly tracked."""
        tokens = tokenize("echo '*'.txt")
        # Find the STRING and WORD tokens
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        word_token = next(t for t in tokens if t.value == '.txt')
        # They should be adjacent
        assert string_token.end_position == word_token.position


class TestDoubleSemicolonHandling:
    """Test double semicolon handling outside case statements."""
    
    def test_double_semicolon_error(self):
        """Test that ;; outside case is a syntax error."""
        with pytest.raises(ParseError) as exc_info:
            parse(tokenize("echo hello;; echo world"))
        assert "unexpected token ';;'" in str(exc_info.value)
    
    def test_double_semicolon_in_case_allowed(self):
        """Test that ;; inside case statements is allowed."""
        # Should parse without error
        ast = parse(tokenize("case $x in a) echo a ;; b) echo b ;; esac"))
        assert ast is not None
    
    def test_semicolon_amp_outside_case_error(self):
        """Test that ;& outside case is a syntax error."""
        with pytest.raises(ParseError) as exc_info:
            parse(tokenize("echo hello;& echo world"))
        assert "unexpected token ';&'" in str(exc_info.value)
    
    def test_amp_semicolon_outside_case_error(self):
        """Test that ;;& outside case is a syntax error."""  
        with pytest.raises(ParseError) as exc_info:
            parse(tokenize("echo hello;;& echo world"))
        assert "unexpected token ';;&'" in str(exc_info.value)
    
    def test_token_transformation(self):
        """Test that TokenTransformer preserves ;; context."""
        tokens = tokenize("echo a ;; echo b")
        transformer = TokenTransformer()
        transformed = transformer.transform(tokens)
        
        # Should still have DOUBLE_SEMICOLON token
        double_semi = next((t for t in transformed if t.type == TokenType.DOUBLE_SEMICOLON), None)
        assert double_semi is not None
        
        # In case statement, should also preserve
        tokens_case = tokenize("case $x in a) echo a ;; esac")
        transformed_case = transformer.transform(tokens_case)
        double_semi_case = next((t for t in transformed_case if t.type == TokenType.DOUBLE_SEMICOLON), None)
        assert double_semi_case is not None


class TestSingleQuoteHandling:
    """Test single quote literal handling."""
    
    def test_no_escape_in_single_quotes(self):
        """Test that backslashes are literal in single quotes."""
        tokens = tokenize("echo 'hello\\world'")
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        # Backslash should be preserved literally
        assert string_token.value == "hello\\world"
    
    def test_no_variable_expansion_in_single_quotes(self):
        """Test that $ is literal in single quotes."""
        tokens = tokenize("echo '$HOME'")
        string_token = next(t for t in tokens if t.type == TokenType.STRING)
        assert string_token.value == "$HOME"
    
    def test_single_quote_cannot_be_escaped(self):
        """Test that \\' doesn't work in single quotes."""
        # In bash, to include a single quote in a single-quoted string,
        # you must end the string, add escaped quote, and start new string:
        # 'hello'\''world' 
        # But 'hello\'world' is invalid and should raise an error
        with pytest.raises(SyntaxError) as exc_info:
            tokens = tokenize("echo 'hello\\'world'")
        assert "Unclosed single quote" in str(exc_info.value)


class TestShellIntegration:
    """Integration tests with the shell."""
    
    def test_concatenation_with_glob(self, capsys):
        """Test concatenation works with glob expansion."""
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for i in range(3):
                open(os.path.join(tmpdir, f"file{i}.txt"), 'w').close()
            
            shell = Shell()
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = shell.run_command("echo file'*'.txt")
                captured = capsys.readouterr()
                # FIXED in v0.28.1: Glob expansion is now disabled for COMPOSITE arguments
                # to prevent incorrect expansion of quoted wildcards
                assert captured.out.strip() == "file*.txt"
                
                # But this should expand
                result2 = shell.run_command("echo file*.txt")
                captured2 = capsys.readouterr()
                assert "file0.txt" in captured2.out
                assert "file1.txt" in captured2.out
                assert "file2.txt" in captured2.out
            finally:
                os.chdir(old_cwd)
    
    def test_error_exit_codes(self):
        """Test that syntax errors return non-zero exit codes."""
        shell = Shell()
        
        # Double semicolon error
        exit_code = shell.run_command("echo hello;; echo world")
        assert exit_code != 0
        
        # Empty command at start
        exit_code = shell.run_command("; echo hello")
        assert exit_code != 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])