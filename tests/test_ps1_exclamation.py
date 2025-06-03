"""Test PS1 prompt variable with exclamation marks and other special characters."""
import pytest
from psh.shell import Shell


def test_ps1_with_exclamation_single_quotes():
    """Test setting PS1 with exclamation mark in single quotes."""
    shell = Shell()
    
    # Test direct assignment
    exit_code = shell.run_command("PS1='[\\!]$ '")
    assert exit_code == 0
    assert shell.state.variables['PS1'] == '[\\!]$ '
    
    # Test that prompt expands correctly (history number will vary)
    prompt_manager = shell.interactive_manager.prompt_manager
    prompt = prompt_manager.get_primary_prompt()
    # Should have format [<number>]$ 
    assert prompt.startswith('[')
    assert prompt.endswith(']$ ')
    assert prompt[1:-3].isdigit()  # The number between brackets should be digits


def test_ps1_with_exclamation_double_quotes():
    """Test setting PS1 with exclamation mark in double quotes.
    
    Note: In double quotes, some escapes are processed differently than bash.
    Use single quotes for exact prompt escape sequence preservation.
    """
    shell = Shell()
    
    # Test direct assignment with double quotes - escapes are preserved
    exit_code = shell.run_command('PS1="[\\!]$ "')
    assert exit_code == 0
    assert shell.state.variables['PS1'] == '[\\!]$ '
    
    # Test export with double quotes
    exit_code = shell.run_command('export PS1="\\u@\\h:[\\!]$ "')
    assert exit_code == 0
    assert '\\!' in shell.state.variables['PS1']


def test_ps1_with_various_escape_sequences():
    r"""Test PS1 with various escape sequences.
    
    Note: In psh, using double quotes for PS1 will cause \$ to be converted to $.
    This is a known limitation - use single quotes to preserve prompt escape sequences.
    """
    shell = Shell()
    
    # Test single quotes - these preserve all escape sequences
    single_quote_tests = [
        ("PS1='\\u@\\h:\\w\\$ '", '\\u@\\h:\\w\\$ '),
        ("PS1='[\\t] \\$ '", '[\\t] \\$ '),
        ("PS1='\\e[32m\\u\\e[0m:\\w\\$ '", '\\e[32m\\u\\e[0m:\\w\\$ '),
        ("PS1='[\\!][\\#]\\$ '", '[\\!][\\#]\\$ '),
    ]
    
    for command, expected in single_quote_tests:
        exit_code = shell.run_command(command)
        assert exit_code == 0, f"Failed to set PS1 with command: {command}"
        assert shell.state.variables['PS1'] == expected
    
    # Test double quotes - with the PS1 heuristic, prompt escapes are preserved
    # even in double quotes (different from normal variable behavior)
    exit_code = shell.run_command('PS1="\\u@\\h:\\w\\$ "')
    assert exit_code == 0
    assert shell.state.variables['PS1'] == '\\u@\\h:\\w\\$ '


def test_ps1_in_script():
    """Test setting PS1 in a script context."""
    shell = Shell()
    
    # Multiple commands including PS1 setting
    script = """
PS1='[\\!]$ '
echo "PS1 is: $PS1"
export PS2='... '
"""
    
    # Execute as a script
    from psh.input_sources import StringInput
    input_source = StringInput(script, "<test>")
    exit_code = shell.script_manager.execute_from_source(input_source, add_to_history=False)
    assert exit_code == 0
    assert shell.state.variables['PS1'] == '[\\!]$ '
    assert shell.state.variables['PS2'] == '... '


def test_ps1_heuristic_vs_normal_variables():
    """Test that PS1/PS2 heuristic doesn't affect normal variables."""
    shell = Shell()
    
    # Normal variable with \$ should have it converted to $ in assignment
    exit_code = shell.run_command('VAR="\\$"')
    assert exit_code == 0
    assert shell.state.variables['VAR'] == '$'
    
    # But PS1/PS2 preserve escape sequences
    exit_code = shell.run_command('PS1="\\$"')
    assert exit_code == 0
    assert shell.state.variables['PS1'] == '\\$'


def test_quotes_not_consumed_by_word():
    """Test that quotes are properly handled as separate tokens."""
    from psh.tokenizer import tokenize, TokenType
    
    # Test that quotes stop word reading
    tokens = tokenize("PS1='value'")
    assert len(tokens) >= 2  # Should have at least WORD and STRING tokens
    
    # First token should be PS1= (without the quotes)
    assert tokens[0].type == TokenType.WORD
    assert tokens[0].value == "PS1="
    
    # Second token should be the quoted string
    assert tokens[1].type == TokenType.STRING
    assert tokens[1].value == "value"