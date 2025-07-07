import pytest
from psh.lexer import tokenize
from psh.token_types import Token, TokenType


class TestTokenizer:
    def test_simple_command(self):
        tokens = tokenize("ls -la")
        assert len(tokens) == 3  # ls, -la, EOF
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == "ls"
        assert tokens[1].type == TokenType.WORD
        assert tokens[1].value == "-la"
        assert tokens[2].type == TokenType.EOF
    
    def test_pipe(self):
        tokens = tokenize("cat file | grep pattern")
        assert len(tokens) == 6  # cat, file, |, grep, pattern, EOF
        assert tokens[2].type == TokenType.PIPE
        assert tokens[2].value == "|"
    
    def test_redirections(self):
        # Input redirection
        tokens = tokenize("cat < input.txt")
        assert tokens[1].type == TokenType.REDIRECT_IN
        assert tokens[1].value == "<"
        
        # Output redirection
        tokens = tokenize("echo hello > output.txt")
        assert tokens[2].type == TokenType.REDIRECT_OUT
        assert tokens[2].value == ">"
        
        # Append redirection
        tokens = tokenize("echo world >> output.txt")
        assert tokens[2].type == TokenType.REDIRECT_APPEND
        assert tokens[2].value == ">>"
    
    def test_semicolon(self):
        tokens = tokenize("echo first; echo second")
        assert tokens[2].type == TokenType.SEMICOLON
        assert tokens[2].value == ";"
    
    def test_ampersand(self):
        tokens = tokenize("sleep 10 &")
        assert tokens[2].type == TokenType.AMPERSAND
        assert tokens[2].value == "&"
    
    def test_newline(self):
        tokens = tokenize("echo hello\necho world")
        assert tokens[2].type == TokenType.NEWLINE
        assert tokens[2].value == "\n"
    
    def test_quoted_strings(self):
        # Single quotes
        tokens = tokenize("echo 'hello world'")
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "hello world"
        
        # Double quotes
        tokens = tokenize('echo "hello world"')
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "hello world"
        
        # Escaped quotes
        tokens = tokenize('echo "hello \\"world\\""')
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == 'hello "world"'
    
    def test_variables(self):
        tokens = tokenize("echo $HOME $USER")
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == "HOME"
        assert tokens[2].type == TokenType.VARIABLE
        assert tokens[2].value == "USER"
    
    def test_brace_expansion_variables(self):
        # Simple brace expansion
        tokens = tokenize("echo ${HOME}")
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == "{HOME}"
        
        # Parameter expansion with default
        tokens = tokenize("echo ${FOO:-default}")
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == "{FOO:-default}"
        
        # Multiple variables
        tokens = tokenize("echo ${VAR1} ${VAR2}")
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == "{VAR1}"
        assert tokens[2].type == TokenType.VARIABLE
        assert tokens[2].value == "{VAR2}"
        
        # Concatenation (tokenizer splits this)
        tokens = tokenize("echo ${PREFIX}suffix")
        assert tokens[1].type == TokenType.VARIABLE
        assert tokens[1].value == "{PREFIX}"
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == "suffix"
    
    def test_whitespace_handling(self):
        tokens = tokenize("  echo   hello   ")
        assert len(tokens) == 3  # echo, hello, EOF
        assert tokens[0].value == "echo"
        assert tokens[1].value == "hello"
    
    def test_empty_input(self):
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF
        
        tokens = tokenize("   ")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF
    
    def test_complex_command(self):
        tokens = tokenize("cat < in.txt | grep -v error | sort > out.txt &")
        expected_types = [
            TokenType.WORD,           # cat
            TokenType.REDIRECT_IN,    # <
            TokenType.WORD,           # in.txt
            TokenType.PIPE,           # |
            TokenType.WORD,           # grep
            TokenType.WORD,           # -v
            TokenType.WORD,           # error
            TokenType.PIPE,           # |
            TokenType.WORD,           # sort
            TokenType.REDIRECT_OUT,   # >
            TokenType.WORD,           # out.txt
            TokenType.AMPERSAND,      # &
            TokenType.EOF
        ]
        
        assert len(tokens) == len(expected_types)
        for token, expected_type in zip(tokens, expected_types):
            assert token.type == expected_type
    
    def test_position_tracking(self):
        tokens = tokenize("echo hello")
        assert tokens[0].position == 0  # echo starts at 0
        assert tokens[1].position == 5  # hello starts at 5
    
    def test_unclosed_quote_error(self):
        with pytest.raises(SyntaxError, match="Unclosed"):
            tokenize('echo "hello world')
        
        with pytest.raises(SyntaxError, match="Unclosed"):
            tokenize("echo 'hello world")
    
    def test_escaped_characters_in_words(self):
        import os
        # Check if we're using ModularLexer (it's now the default unless disabled)
        use_legacy = os.environ.get('PSH_USE_LEGACY_LEXER', 'false').lower() == 'true'
        
        # Escaped spaces
        tokens = tokenize(r"echo hello\ world")
        assert len(tokens) == 3  # echo, hello world, EOF
        # ModularLexer keeps the backslash in the token value
        if not use_legacy:
            assert tokens[1].value == "hello\\ world"
        else:
            assert tokens[1].value == "hello world"
        
        # Escaped special characters
        tokens = tokenize(r"echo \$HOME")
        assert tokens[1].type == TokenType.WORD
        # ModularLexer keeps the backslash, old lexer uses NULL prefix
        if not use_legacy:
            assert tokens[1].value == "\\$HOME"
        else:
            assert tokens[1].value == "\x00$HOME"  # Escaped dollar marked with NULL prefix
        
        # Escaped glob characters
        tokens = tokenize(r"echo \*.txt")
        # ModularLexer keeps the backslash
        if not use_legacy:
            assert tokens[1].value == "\\*.txt"
        else:
            assert tokens[1].value == "*.txt"