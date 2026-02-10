"""
Simple test using the existing test pattern.
"""



def test_simple_variable(shell, capsys):
    """Test basic $var expansion."""
    shell.run_command('VAR=hello')
    shell.run_command('echo $VAR')
    captured = capsys.readouterr()
    assert captured.out.strip() == "hello"


def test_braced_variable(shell, capsys):
    """Test ${var} expansion."""
    shell.run_command('VAR=world')
    shell.run_command('echo ${VAR}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "world"


def test_undefined_variable(shell, capsys):
    """Test expansion of undefined variable."""
    shell.run_command('unset UNDEFINED')
    shell.run_command('echo "$UNDEFINED"')
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_variable_in_string(shell, capsys):
    """Test variable expansion within double quotes."""
    shell.run_command('NAME=John')
    shell.run_command('echo "Hello, $NAME!"')
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello, John!"


def test_no_expansion_in_single_quotes(shell, capsys):
    """Test that variables don't expand in single quotes."""
    shell.run_command("VAR=test")
    shell.run_command("echo '$VAR'")
    captured = capsys.readouterr()
    assert captured.out.strip() == "$VAR"
