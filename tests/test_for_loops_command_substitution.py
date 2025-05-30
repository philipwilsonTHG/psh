"""Test command substitution in for loops."""

import pytest
from psh.shell import Shell

def test_command_substitution_in_for_loop(capsys):
    """Test basic command substitution in for loop."""
    shell = Shell()
    shell.run_command('for i in $(echo 1 2 3); do echo "num:$i"; done')
    captured = capsys.readouterr()
    assert captured.out == "num:1\nnum:2\nnum:3\n"

def test_backtick_substitution_in_for_loop(capsys):
    """Test backtick command substitution in for loop."""
    shell = Shell()
    shell.run_command('for c in `echo a b c`; do echo "char:$c"; done')
    captured = capsys.readouterr()
    assert captured.out == "char:a\nchar:b\nchar:c\n"

def test_mixed_for_loop_items(capsys):
    """Test for loop with mixed literal and command substitution."""
    shell = Shell()
    shell.run_command('for x in start $(echo mid1 mid2) end; do echo "$x"; done')
    captured = capsys.readouterr()
    assert captured.out == "start\nmid1\nmid2\nend\n"

def test_command_substitution_with_variables(capsys):
    """Test command substitution that uses variables."""
    shell = Shell()
    # Set variable directly in shell
    shell.variables['x'] = "1 2"
    shell.run_command('for i in $(echo $x 3); do echo "$i"; done')
    captured = capsys.readouterr()
    assert captured.out == "1\n2\n3\n"

def test_empty_command_substitution():
    """Test for loop with empty command substitution."""
    shell = Shell()
    # Empty command substitution should result in no iterations
    exit_code = shell.run_command('for i in $(echo -n); do echo "should not print"; done')
    assert exit_code == 0

def test_nested_command_substitution_in_for(capsys):
    """Test nested structures with command substitution in for loop."""
    shell = Shell()
    script = '''
    for n in $(echo 1 2); do
        if [ "$n" = "1" ]; then
            echo "first"
        else
            echo "second"
        fi
    done
    '''
    shell.run_command(script)
    captured = capsys.readouterr()
    assert captured.out == "first\nsecond\n"

def test_command_substitution_with_glob_patterns(capsys):
    """Test command substitution that outputs glob patterns."""
    shell = Shell()
    # Create test files
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        for i in [1, 2, 3]:
            open(os.path.join(tmpdir, f"test{i}.txt"), 'w').close()
        
        # Change to temp directory and test
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Command substitution outputs a glob pattern
            shell.run_command('for f in $(echo "test*.txt"); do echo "Found: $f"; done')
            captured = capsys.readouterr()
            # Glob should NOT expand because it came from command substitution
            assert captured.out == "Found: test*.txt\n"
        finally:
            os.chdir(old_cwd)

def test_multiline_command_substitution_in_for(capsys):
    """Test command substitution that outputs multiple lines."""
    shell = Shell()
    # Use printf to generate multi-line output
    shell.run_command('for line in $(printf "line1\\nline2\\nline3"); do echo "Got: $line"; done')
    captured = capsys.readouterr()
    # Word splitting should split on all whitespace including newlines
    assert captured.out == "Got: line1\nGot: line2\nGot: line3\n"