"""Test that child shells inherit parser strategy from parent shell."""

import pytest
from psh.shell import Shell
from psh.parser.parser_registry import ParserRegistry


def test_child_shell_inherits_parser_strategy():
    """Test that child shells inherit parser strategy from parent."""
    # First ensure parser combinator is registered
    if not ParserRegistry.get("parser_combinator"):
        pytest.skip("Parser combinator not registered")
    
    # Create parent shell with parser combinator
    parent_shell = Shell(norc=True)
    parent_shell.parser_strategy.switch_parser("parser_combinator")
    
    # Verify parent is using parser combinator
    assert parent_shell.parser_strategy.current_parser == "parser_combinator"
    
    # Create child shell
    child_shell = Shell(parent_shell=parent_shell, norc=True)
    
    # Child should inherit parser combinator
    assert child_shell.parser_strategy.current_parser == "parser_combinator"


def test_child_shell_uses_default_without_parent():
    """Test that child shells use default parser without parent."""
    # Create shell without parent
    shell = Shell(norc=True)
    
    # Should use default parser
    assert shell.parser_strategy.current_parser == "default"


def test_command_substitution_uses_parent_parser(captured_shell):
    """Test that command substitution uses parent shell's parser."""
    shell = captured_shell
    
    # Skip if parser combinator not available
    if not ParserRegistry.get("parser_combinator"):
        pytest.skip("Parser combinator not registered")
    
    # Switch to parser combinator
    shell.run_command("parser-select parser_combinator")
    shell.clear_output()  # Clear the parser switch message
    
    # Run command with command substitution
    # The debug output should show both ASTs using parser_combinator
    shell.state.options['debug-ast'] = True
    result = shell.run_command('echo $(echo test)')
    
    # Check output was successful
    assert result == 0
    assert shell.get_stdout().strip() == "test"


def test_subshell_inherits_parser_strategy():
    """Test that subshells inherit parser strategy."""
    import subprocess
    import sys
    
    # Skip if parser combinator not available
    if not ParserRegistry.get("parser_combinator"):
        pytest.skip("Parser combinator not registered")
    
    # Use subprocess to test parser inheritance in subshell
    script = """
import sys
sys.path.insert(0, '.')
from psh.shell import Shell

shell = Shell(norc=True)
shell.run_command("parser-select parser_combinator")
shell.state.options['debug-ast'] = True

# Run in subshell - AST should show parser_combinator and SubshellGroup
result = shell.run_command('(echo subshell)')
print(f"Exit code: {result}")
"""
    
    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        cwd='/Users/pwilson/src/psh'
    )
    
    # AST output should show parser_combinator was used
    assert "parser_combinator" in result.stderr
    # And it should show SubshellGroup in the AST
    assert "SubshellGroup" in result.stderr
    # Output should be correct
    assert "subshell" in result.stdout


def test_process_substitution_inherits_parser_strategy():
    """Test that process substitution inherits parser strategy."""
    import subprocess
    import sys
    
    # Skip if parser combinator not available
    if not ParserRegistry.get("parser_combinator"):
        pytest.skip("Parser combinator not registered")
    
    # Use subprocess to test parser inheritance in process substitution
    script = """
import sys
sys.path.insert(0, '.')
from psh.shell import Shell

shell = Shell(norc=True)
shell.run_command("parser-select parser_combinator")
shell.state.options['debug-ast'] = True

# Run with process substitution - should use parser_combinator
result = shell.run_command('cat <(echo "process sub")')
print(f"Exit code: {result}")
"""
    
    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        cwd='/Users/pwilson/src/psh'
    )
    
    # AST output should show parser_combinator was used
    assert "parser_combinator" in result.stderr
    # Output should be correct
    assert "process sub" in result.stdout
    # Should show process substitution was parsed correctly
    assert "ProcessSubstitution" in result.stderr or "PROCESS_SUB" in result.stderr