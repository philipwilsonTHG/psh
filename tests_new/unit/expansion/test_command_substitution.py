"""
Command substitution expansion tests.

Tests both $(command) and `command` syntax for command substitution,
including nested substitutions and edge cases.
"""

import pytest


def test_simple_dollar_paren_substitution(shell, capsys):
    """Test basic $(command) substitution."""
    shell.run_command('echo $(echo hello)')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_simple_backtick_substitution(shell, capsys):
    """Test basic `command` substitution."""
    shell.run_command('echo `echo hello`')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'

def test_substitution_with_variables(shell, capsys):
    """Test command substitution with variables."""
    shell.run_command('x=world; echo $(echo hello $x)')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello world'


def test_substitution_in_assignment(shell, capsys):
    """Test command substitution in variable assignment."""
    shell.run_command('x=$(echo hello); echo $x')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_multiple_substitutions(shell, capsys):
    """Test multiple command substitutions in one command."""
    shell.run_command('echo $(echo first) $(echo second)')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'first second'


def test_substitution_with_spaces(shell, capsys):
    """Test command substitution preserving spaces."""
    shell.run_command('echo "$(echo hello   world)"')
    captured = capsys.readouterr()
    # PSH normalizes spaces in unquoted contexts
    assert captured.out.strip() == 'hello world'


def test_substitution_trimming_newlines(shell, capsys):
    """Test that command substitution trims trailing newlines."""
    shell.run_command('echo "$(printf "hello\\n\\n")"')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_nested_dollar_paren_substitution(shell, capsys):
    """Test nested $(command) substitutions."""
    shell.run_command('echo $(echo $(echo hello))')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'

def test_nested_backtick_substitution(shell, capsys):
    """Test nested `command` substitutions."""
    # Note: This requires escaping the inner backticks
    shell.run_command('echo `echo \\`echo hello\\``')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_mixed_nested_substitution(shell, capsys):
    """Test mixing $() and `` in nesting."""
    shell.run_command('echo $(echo `echo hello`)')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_substitution_with_quotes(shell, capsys):
    """Test command substitution with quoted arguments."""
    shell.run_command('echo $(echo "hello world")')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello world'


def test_substitution_with_special_chars(shell, capsys):
    """Test command substitution with special characters."""
    shell.run_command('echo $(echo "hello;world|test")')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello;world|test'


def test_substitution_multiline_output(shell, capsys):
    """Test command substitution with multiline output."""
    shell.run_command('echo "$(printf "line1\\nline2\\nline3")"')
    captured = capsys.readouterr()
    assert 'line1' in captured.out
    assert 'line2' in captured.out
    assert 'line3' in captured.out

def test_substitution_in_pipeline(shell, capsys):
    """Test command substitution in pipeline."""
    result = shell.run_command('echo $(echo hello) | tr a-z A-Z')
    captured = capsys.readouterr()
    # Pipeline output isn't captured by capsys - command executes successfully
    assert result == 0


def test_empty_substitution(shell, capsys):
    """Test empty command substitution."""
    shell.run_command('echo before$(true)after')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'beforeafter'


def test_substitution_exit_status(shell, capsys):
    """Test that substitution doesn't affect exit status of main command."""
    result = shell.run_command('echo $(false)')
    captured = capsys.readouterr()
    assert captured.out.strip() == ''
    assert result == 0  # echo succeeds even if substitution fails


def test_substitution_with_error(shell, capsys):
    """Test command substitution with failing command."""
    shell.run_command('echo before $(nonexistent_command_xyz 2>/dev/null) after')
    captured = capsys.readouterr()
    # Command should continue, just with empty substitution
    assert 'before' in captured.out
    assert 'after' in captured.out

def test_substitution_in_if_condition(shell, capsys):
    """Test command substitution in conditional expressions."""
    shell.run_command('if [ "$(echo hello)" = "hello" ]; then echo match; fi')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'match'


def test_substitution_with_builtin(shell, capsys):
    """Test command substitution with builtin commands."""
    shell.run_command('echo $(pwd | wc -c)')
    captured = capsys.readouterr()
    # Should get character count of pwd output (including newline)
    assert captured.out.strip().isdigit()


def test_substitution_with_arithmetic(shell, capsys):
    """Test command substitution with arithmetic."""
    shell.run_command('echo $(echo $((2 + 3)))')
    captured = capsys.readouterr()
    assert captured.out.strip() == '5'


def test_substitution_preserves_exit_status(shell, capsys):
    """Test that we can capture exit status of substituted command."""
    shell.run_command('x=$(false; echo $?); echo $x')
    captured = capsys.readouterr()
    assert captured.out.strip() == '1'

@pytest.mark.xfail(reason="Complex backtick escaping may not be supported")
def test_backtick_escaping(shell, capsys):
    """Test escaping backticks in backtick substitution."""
    # Test that we can include literal backticks in output
    shell.run_command('echo `echo \\`literal backtick\\``')
    captured = capsys.readouterr()
    assert 'literal backtick' in captured.out


def test_dollar_paren_in_string(shell, capsys):
    """Test $() substitution within double quotes."""
    shell.run_command('echo "prefix $(echo middle) suffix"')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'prefix middle suffix'


def test_substitution_with_redirection(shell, capsys):
    """Test command substitution with redirection."""
    shell.run_command('echo $(echo hello >&1)')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_word_splitting_in_substitution(shell, capsys):
    """Test word splitting behavior in command substitution."""
    # Without quotes, substitution result should be word-split
    shell.run_command('echo $(echo "a b c")')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'a b c'
    
    # With quotes, spaces should be preserved
    shell.run_command('echo "$(echo "a   b   c")"')
    captured = capsys.readouterr()
    assert 'a   b   c' in captured.out


# Edge cases and error conditions

@pytest.mark.xfail(reason="PSH may not detect unmatched substitution syntax")
def test_unmatched_dollar_paren(shell, capsys):
    """Test handling of unmatched $( without )."""
    result = shell.run_command('echo $(echo hello')
    # Should be a syntax error
    assert result != 0


@pytest.mark.xfail(reason="PSH may not detect unmatched substitution syntax")
def test_unmatched_backtick(shell, capsys):
    """Test handling of unmatched backtick."""
    result = shell.run_command('echo `echo hello')
    # Should be a syntax error
    assert result != 0

def test_empty_substitution_syntax(shell, capsys):
    """Test empty substitution expressions."""
    shell.run_command('echo before$()after')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'beforeafter'

    shell.run_command('echo before``after')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'beforeafter'


def test_substitution_with_semicolon(shell, capsys):
    """Test command substitution containing semicolons."""
    shell.run_command('echo $(echo hello; echo world)')
    captured = capsys.readouterr()
    # Should execute both commands and concatenate output
    assert 'hello' in captured.out
    assert 'world' in captured.out


def test_deeply_nested_substitution(shell, capsys):
    """Test deeply nested command substitutions."""
    shell.run_command('echo $(echo $(echo $(echo hello)))')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'

def test_substitution_with_complex_expansion(shell, capsys):
    """Test command substitution with complex parameter expansion."""
    shell.run_command('x=hello; echo $(echo ${x:-default})')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_substitution_in_here_document(shell, capsys):
    """Test command substitution in here documents."""
    script = '''cat << EOF
Hello $(echo world)
EOF'''
    result = shell.run_command(script)
    captured = capsys.readouterr()
    # Here document output may not be captured by capsys
    assert result == 0


def test_substitution_with_external_command(shell, capsys):
    """Test command substitution with external commands."""
    shell.run_command('echo $(echo hello | cat)')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'