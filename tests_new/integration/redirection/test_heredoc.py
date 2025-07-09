"""
Here document (heredoc) integration tests.

Tests for heredoc (<<) and here string (<<<) redirection functionality.
"""

import pytest


def test_tokenize_heredoc():
    """Test that << is tokenized correctly."""
    from psh.lexer import tokenize
    from psh.token_types import TokenType
    
    tokens = tokenize("cat << EOF")
    assert tokens[1].type == TokenType.HEREDOC
    assert tokens[1].value == "<<"
    assert tokens[2].type == TokenType.WORD
    assert tokens[2].value == "EOF"


def test_tokenize_heredoc_strip():
    """Test that <<- is tokenized correctly."""
    from psh.lexer import tokenize
    from psh.token_types import TokenType
    
    tokens = tokenize("cat <<- END")
    assert tokens[1].type == TokenType.HEREDOC_STRIP
    assert tokens[1].value == "<<-"
    assert tokens[2].type == TokenType.WORD
    assert tokens[2].value == "END"


def test_parse_heredoc():
    """Test parsing of here document."""
    from psh.lexer import tokenize
    from psh.parser import parse
    
    tokens = tokenize("cat << EOF")
    ast = parse(tokens)
    command = ast.and_or_lists[0].pipelines[0].commands[0]
    
    assert len(command.redirects) == 1
    redirect = command.redirects[0]
    assert redirect.type == "<<"
    assert redirect.target == "EOF"
    assert redirect.heredoc_content is None  # Not collected yet


def test_tokenize_here_string():
    """Test that <<< is tokenized correctly."""
    from psh.lexer import tokenize
    from psh.token_types import TokenType
    
    tokens = tokenize("cat <<< 'hello world'")
    assert tokens[1].type == TokenType.HERE_STRING
    assert tokens[1].value == "<<<"
    assert tokens[2].type == TokenType.STRING
    assert tokens[2].value == "hello world"


def test_parse_here_string():
    """Test parsing of here string."""
    from psh.lexer import tokenize
    from psh.parser import parse
    
    tokens = tokenize("cat <<< 'test string'")
    ast = parse(tokens)
    command = ast.and_or_lists[0].pipelines[0].commands[0]
    
    assert len(command.redirects) == 1
    redirect = command.redirects[0]
    assert redirect.type == "<<<"
    assert redirect.target == "test string"


def test_here_string_literal(shell_with_temp_dir):
    """Test here string with literal text."""
    output_file = "herestring_literal_test.txt"
    result = shell_with_temp_dir.run_command(f"cat <<< 'literal text' > {output_file}")
    assert result == 0
    
    with open(output_file, 'r') as f:
        content = f.read()
    assert content == "literal text\n"


def test_here_string_with_builtin(shell_with_temp_dir):
    """Test here string output to file."""
    output_file = "herestring_builtin_test.txt"
    result = shell_with_temp_dir.run_command(f"cat <<< 'from here string' > {output_file}")
    assert result == 0
    
    with open(output_file, 'r') as f:
        content = f.read()
    assert content == "from here string\n"


def test_here_string_with_quotes(shell_with_temp_dir):
    """Test here string handling quotes properly."""
    output_file = "herestring_quotes_test.txt"
    result = shell_with_temp_dir.run_command(f'cat <<< "She said \\"Hello\\"" > {output_file}')
    assert result == 0
    
    with open(output_file, 'r') as f:
        content = f.read()
    assert 'She said "Hello"' in content


def test_here_string_empty(shell_with_temp_dir):
    """Test empty here string."""
    output_file = "herestring_empty_test.txt"
    result = shell_with_temp_dir.run_command(f"cat <<< '' > {output_file}")
    assert result == 0
    
    with open(output_file, 'r') as f:
        content = f.read()
    assert content == "\n"  # Just a newline


@pytest.mark.xfail(reason="Pipeline output capture needs improvement")
def test_here_string_in_pipeline(shell_with_temp_dir):
    """Test here string in a pipeline."""
    output_file = "herestring_pipeline_test.txt"
    result = shell_with_temp_dir.run_command(f"cat <<< 'apple banana cherry' | wc -w > {output_file}")
    assert result == 0
    
    with open(output_file, 'r') as f:
        content = f.read().strip()
    assert "3" in content


@pytest.mark.xfail(reason="Variable expansion in here strings may not be implemented")
def test_here_string_with_variable(shell_with_temp_dir):
    """Test here string with variable expansion."""
    shell_with_temp_dir.state.set_variable('NAME', 'World')
    
    output_file = "herestring_var_test.txt"
    result = shell_with_temp_dir.run_command(f'cat <<< "Hello $NAME" > {output_file}')
    assert result == 0
    
    with open(output_file, 'r') as f:
        content = f.read()
    assert content == "Hello World\n"


@pytest.mark.skip(reason="Heredoc execution needs architectural updates for proper input handling")
def test_heredoc_with_builtin():
    """Test here document with cat command - skipped pending architecture updates."""
    # This test requires proper input handling for heredoc content
    # which needs updates to the PSH input processing architecture
    pass


@pytest.mark.skip(reason="Heredoc execution needs architectural updates for proper input handling")
def test_heredoc_strip_tabs():
    """Test here document with tab stripping - skipped pending architecture updates."""
    # This test requires proper tab stripping implementation
    # which is part of the heredoc processing architecture updates
    pass


@pytest.mark.skip(reason="Heredoc execution needs architectural updates for proper input handling")
def test_heredoc_empty():
    """Test empty here document - skipped pending architecture updates."""
    # This test requires proper heredoc content handling
    # which is part of the architecture updates needed
    pass


@pytest.mark.skip(reason="Heredoc execution needs architectural updates for proper input handling")
def test_heredoc_with_variable_expansion():
    """Test variable expansion in heredocs - skipped pending architecture updates."""
    # This test requires proper variable expansion in heredoc content
    # which needs architecture updates for input processing
    pass


@pytest.mark.skip(reason="External command integration with heredocs needs architecture updates")
def test_heredoc_with_external_command():
    """Test here document with external command - skipped pending architecture updates."""
    # This test requires proper integration between heredocs and external commands
    # which is part of the I/O redirection architecture that needs updates
    pass


@pytest.mark.skip(reason="Multiple redirection handling needs architecture updates")
def test_heredoc_with_output_redirect():
    """Test here document with output redirection - skipped pending architecture updates."""
    # This test requires proper handling of multiple redirections
    # which is part of the I/O redirection architecture updates needed
    pass


@pytest.mark.skip(reason="Pipeline heredoc integration needs architecture updates")
def test_heredoc_in_pipeline():
    """Test here document in pipeline - skipped pending architecture updates."""
    # This test requires proper integration of heredocs with pipelines
    # which is part of the pipeline execution architecture that needs updates
    pass


def test_heredoc_syntax_variants():
    """Test various heredoc syntax forms are parsed correctly."""
    from psh.lexer import tokenize
    from psh.parser import parse
    
    # Test different spacing patterns
    test_cases = [
        "cat <<EOF",
        "cat << EOF", 
        "cat <<-EOF",
        "cat <<- EOF"
    ]
    
    for case in test_cases:
        tokens = tokenize(case)
        ast = parse(tokens)
        command = ast.and_or_lists[0].pipelines[0].commands[0]
        assert len(command.redirects) == 1
        assert command.redirects[0].type in ["<<", "<<-"]


def test_here_string_syntax_variants():
    """Test various here string syntax forms are parsed correctly."""
    from psh.lexer import tokenize
    from psh.parser import parse
    
    # Test different quoting patterns
    test_cases = [
        "cat <<<word",
        "cat <<< word",
        "cat <<<'word'",
        "cat <<<\"word\"",
        "cat <<< 'quoted word'",
        "cat <<< \"quoted word\""
    ]
    
    for case in test_cases:
        tokens = tokenize(case)
        ast = parse(tokens)
        command = ast.and_or_lists[0].pipelines[0].commands[0]
        assert len(command.redirects) == 1
        assert command.redirects[0].type == "<<<"