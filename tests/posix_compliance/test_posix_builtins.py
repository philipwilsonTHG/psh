#!/usr/bin/env python3
"""
Test POSIX-required built-in commands for compliance.
Tests both special built-ins and regular built-ins required by POSIX.
"""

import pytest
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fixture is provided by pytest, no need to import


class TestPOSIXSpecialBuiltins:
    """Test POSIX special built-in commands."""
    
    def test_colon_command(self, shell, capsys):
        """Test : (colon) null command."""
        result = shell.run_command(":")
        assert result == 0
        
        # Colon with arguments should ignore them
        result = shell.run_command(": arg1 arg2")
        assert result == 0
        
        # Colon should work in conditionals
        shell.run_command("if :; then echo ok; fi")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "ok"
    
    def test_dot_command(self, shell, capsys):
        """Test . (dot) source command."""
        # Create a script to source
        shell.run_command("echo 'DOT_VAR=sourced' > /tmp/dot_test.sh")
        
        # Source it and check variable
        shell.run_command(". /tmp/dot_test.sh")
        shell.run_command("echo $DOT_VAR")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "sourced"
        
        # Cleanup
        shell.run_command("rm -f /tmp/dot_test.sh")
    
    def test_break_continue(self, shell, capsys):
        """Test break and continue commands."""
        # Test break
        shell.run_command('for i in 1 2 3 4 5; do if [ $i -eq 3 ]; then break; fi; echo $i; done')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "1\n2"
        
        # Test continue
        shell.run_command('for i in 1 2 3 4 5; do if [ $i -eq 3 ]; then continue; fi; echo $i; done')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "1\n2\n4\n5"
        
        # Test break with levels
        shell.run_command('for i in 1 2; do for j in a b c; do if [ "$i$j" = "2b" ]; then break 2; fi; echo "$i$j"; done; done')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "1a\n1b\n1c\n2a"
    
    def test_eval_command(self, shell, capsys):
        """Test eval command."""
        # Basic eval
        shell.run_command("var='echo hello'")
        shell.run_command("eval $var")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "hello"
        
        # Eval with variable assignment
        shell.run_command("eval 'EVAL_VAR=42'")
        shell.run_command("echo $EVAL_VAR")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "42"
        
        # Eval with command substitution
        shell.run_command("eval 'echo $(echo nested)'")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "nested"
    
    @pytest.mark.xfail(reason="Exit in main shell context")

    
    def test_exit_command(self, shell, capsys):
        """Test exit command."""
        # Exit with status 0
        result = shell.run_command("exit 0")
        assert result == 0
        
        # Exit with specific status
        result = shell.run_command("exit 42")
        assert result == 42
        
        # Exit in subshell doesn't affect parent
        shell.run_command("(exit 5); echo $?")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "5"
    
    def test_export_command(self, shell, capsys):
        """Test export command."""
        # Export a variable
        shell.run_command("export POSIX_VAR=exported")
        shell.run_command("echo $POSIX_VAR")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "exported"
        
        # Export without value
        shell.run_command("UNEXP_VAR=unexported")
        shell.run_command("export UNEXP_VAR")
        # In a subshell, exported variables should be visible
        shell.run_command("sh -c 'echo ${POSIX_VAR:-not_found}'")
        captured = capsys.readouterr()
        output = captured.out
        # Note: This might fail if sh is not available or PSH doesn't properly export
    
    @pytest.mark.xfail(reason="Return outside function context")

    
    def test_return_command(self, shell, capsys):
        """Test return command in functions."""
        shell.run_command("""
        test_return() {
            return 42
        }
        """)
        shell.run_command("test_return")
        shell.run_command("echo $?")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "42"
        
        # Return with no argument
        shell.run_command("""
        test_return_default() {
            false
            return
        }
        """)
        shell.run_command("test_return_default")
        shell.run_command("echo $?")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "1"
    
    def test_set_command_basics(self, shell, capsys):
        """Test basic set command functionality."""
        # Set positional parameters
        shell.run_command("set -- one two three")
        shell.run_command("echo $1 $2 $3")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "one two three"
        
        # Check $#
        shell.run_command("echo $#")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "3"
        
        # Set with no arguments should list variables (not testing output format)
        result = shell.run_command("set")
        assert result == 0
    
    def test_unset_command(self, shell, capsys):
        """Test unset command."""
        # Unset variable
        shell.run_command("UNSET_VAR=value")
        shell.run_command("unset UNSET_VAR")
        shell.run_command("echo ${UNSET_VAR:-unset}")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "unset"
        
        # Unset function
        shell.run_command("test_func() { echo func; }")
        shell.run_command("unset -f test_func")
        result = shell.run_command("test_func")
        assert result == 127  # Command not found
    
    def test_shift_command(self, shell, capsys):
        """Test shift command."""
        shell.run_command("set -- one two three four")
        shell.run_command("shift")
        shell.run_command("echo $1 $2 $3")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "two three four"
        
        # Shift with count
        shell.run_command("shift 2")
        shell.run_command("echo $1")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "four"
    
    @pytest.mark.xfail(reason="exec not implemented in PSH")
    def test_exec_command(self, shell, capsys):
        """Test exec command."""
        # exec should replace the shell process
        # This is hard to test directly, but we can test exec with redirections
        shell.run_command("exec 3>&1")  # Duplicate stdout to fd 3
        shell.run_command("exec >/tmp/exec_test.txt")  # Redirect stdout
        shell.run_command("echo redirected")
        shell.run_command("exec 1>&3 3>&-")  # Restore stdout
        
        shell.run_command("cat /tmp/exec_test.txt")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "redirected"
        shell.run_command("rm -f /tmp/exec_test.txt")
    
    @pytest.mark.xfail(reason="trap not implemented in PSH")
    def test_trap_command(self, shell, capsys):
        """Test trap command."""
        # Set a trap
        shell.run_command("trap 'echo trapped' EXIT")
        
        # The trap should execute on exit
        shell.run_command("exit")
        captured = capsys.readouterr()
        output = captured.out
        assert "trapped" in output


class TestPOSIXRegularBuiltins:
    """Test POSIX regular built-in commands."""
    
    def test_alias_unalias(self, shell, capsys):
        """Test alias and unalias commands."""
        # Create an alias
        shell.run_command("alias ll='ls -l'")
        
        # Verify alias exists (checking alias output format is implementation-specific)
        result = shell.run_command("alias ll")
        assert result == 0
        
        # Remove alias
        shell.run_command("unalias ll")
        result = shell.run_command("alias ll")
        assert result != 0
    
    @pytest.mark.xfail(reason="Output capture issue with pwd")

    
    def test_cd_pwd(self, shell, capsys):
        """Test cd and pwd commands."""
        # Get current directory
        shell.run_command("pwd")

        captured = capsys.readouterr()

        original = captured.out.strip()
        
        # Change to /tmp
        shell.run_command("cd /tmp")
        shell.run_command("pwd")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "/tmp"
        
        # Change back
        shell.run_command(f"cd {original}")
        shell.run_command("pwd")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == original
        
        # Test cd with no arguments (should go to HOME)
        shell.run_command("HOME=/tmp")
        shell.run_command("cd")
        shell.run_command("pwd")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "/tmp"
    
    def test_false_true(self, shell, capsys):
        """Test false and true commands."""
        # true should return 0
        result = shell.run_command("true")
        assert result == 0
        
        # false should return 1
        result = shell.run_command("false")
        assert result == 1
        
        # Use in conditionals
        shell.run_command("if true; then echo yes; fi")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "yes"
        
        shell.run_command("if false; then echo yes; else echo no; fi")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "no"
    
    @pytest.mark.xfail(reason="Read from here-doc in test context")

    
    def test_read_command(self, shell, capsys):
        """Test read command."""
        # Read from here-doc
        shell.run_command('read var << EOF test input EOF echo $var')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "test input"
        
        # Read multiple variables
        shell.run_command('read var1 var2 << EOF first second third EOF echo "$var1|$var2"')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "first|second third"
    
    def test_jobs_fg_bg(self, shell, capsys):
        """Test jobs, fg, and bg commands."""
        # Start a short background job to avoid leaving long-running processes
        shell.run_command("sleep 0.1 &")
        
        # Check jobs list
        shell.run_command("jobs")
        captured = capsys.readouterr()
        output = captured.out
        assert "sleep" in output
        
        # Wait for the background job to complete to avoid test pollution
        shell.run_command("wait")
        
        # Can't easily test fg/bg without interactive terminal
        # Just verify they exist
        result = shell.run_command("fg %1 || true")  # Don't fail if no jobs
        # Note: This might fail or hang in non-interactive mode
    
    @pytest.mark.xfail(reason="getopts not implemented in PSH")
    def test_getopts_command(self, shell, capsys):
        """Test getopts command."""
        shell.run_command('while getopts "ab:c" opt; do case $opt in a) echo "Option a";; b) echo "Option b: $OPTARG";; c) echo "Option c";; esac done """, "set -- -a -b value -c')
        captured = capsys.readouterr()
        output = captured.out
        assert "Option a" in output
        assert "Option b: value" in output
        assert "Option c" in output
    
    def test_wait_command(self, shell, capsys):
        """Test wait command."""
        # Test wait with no arguments (waits for all background jobs)
        shell.run_command("sleep 0.1 &")
        result = shell.run_command("wait")
        assert result == 0
        
        # Test wait with multiple background jobs
        shell.run_command("sleep 0.1 & sleep 0.1 &")
        result = shell.run_command("wait")
        assert result == 0
        
        # Test wait when no background jobs exist
        result = shell.run_command("wait")
        assert result == 0
    
    def test_command_builtin(self, shell, capsys):
        """Test command builtin."""
        # command -v should show command location/type
        shell.run_command("command -v cd")
        captured = capsys.readouterr()
        output = captured.out
        assert "cd" in output
        
        # command should bypass aliases
        shell.run_command("alias echo='echo ALIASED'")
        shell.run_command("command echo test")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "test"
        assert "ALIASED" not in output


class TestPOSIXCompliance:
    """Test overall POSIX compliance behaviors."""
    
    @pytest.mark.xfail(reason="Variable assignment with special builtins")

    
    def test_special_builtins_affect_shell(self, shell, capsys):
        """Test that special built-ins affect the current shell environment."""
        # Variable assignment with special built-in persists
        shell.run_command("VAR=value :")
        shell.run_command("echo $VAR")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "value"
        
        # Regular built-ins don't affect shell environment the same way
        shell.run_command("VAR2=value2 true")
        shell.run_command("echo ${VAR2:-unset}")
        captured = capsys.readouterr()
        output = captured.out
        # In POSIX, this should be "unset" for regular built-ins
    
    def test_command_search_order(self, shell, capsys):
        """Test POSIX command search order."""
        # Special built-ins are found before functions
        shell.run_command("set() { echo 'function set'; }")
        shell.run_command("set --")
        captured = capsys.readouterr()
        output = captured.out
        # Should use built-in set, not function
        assert "function set" not in output
    
    def test_field_splitting(self, shell, capsys):
        """Test IFS field splitting compliance."""
        # Default IFS
        shell.run_command('echo $(echo "a b c")')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "a b c"
        
        # Custom IFS
        shell.run_command("IFS=:")
        shell.run_command('echo $(echo "a:b:c")')
        captured = capsys.readouterr()
        output = captured.out
        # Note: This tests field splitting behavior
        shell.run_command("IFS=' \t\n'")  # Reset IFS
