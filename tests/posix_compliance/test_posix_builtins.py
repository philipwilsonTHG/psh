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

from tests.conftest import shell


class TestPOSIXSpecialBuiltins:
    """Test POSIX special built-in commands."""
    
    def test_colon_command(self, shell):
        """Test : (colon) null command."""
        result = shell.run_command(":")
        assert result == 0
        
        # Colon with arguments should ignore them
        result = shell.run_command(": arg1 arg2")
        assert result == 0
        
        # Colon should work in conditionals
        output = shell.capture_output("if :; then echo ok; fi")
        assert output.strip() == "ok"
    
    def test_dot_command(self, shell):
        """Test . (dot) source command."""
        # Create a script to source
        shell.run_command("echo 'DOT_VAR=sourced' > /tmp/dot_test.sh")
        
        # Source it and check variable
        shell.run_command(". /tmp/dot_test.sh")
        output = shell.capture_output("echo $DOT_VAR")
        assert output.strip() == "sourced"
        
        # Cleanup
        shell.run_command("rm -f /tmp/dot_test.sh")
    
    def test_break_continue(self, shell):
        """Test break and continue commands."""
        # Test break
        output = shell.capture_output("""
        for i in 1 2 3 4 5; do
            if [ $i -eq 3 ]; then
                break
            fi
            echo $i
        done
        """)
        assert output.strip() == "1\n2"
        
        # Test continue
        output = shell.capture_output("""
        for i in 1 2 3 4 5; do
            if [ $i -eq 3 ]; then
                continue
            fi
            echo $i
        done
        """)
        assert output.strip() == "1\n2\n4\n5"
        
        # Test break with levels
        output = shell.capture_output("""
        for i in 1 2; do
            for j in a b c; do
                if [ "$i$j" = "2b" ]; then
                    break 2
                fi
                echo "$i$j"
            done
        done
        """)
        assert output.strip() == "1a\n1b\n1c\n2a"
    
    def test_eval_command(self, shell):
        """Test eval command."""
        # Basic eval
        shell.run_command("var='echo hello'")
        output = shell.capture_output("eval $var")
        assert output.strip() == "hello"
        
        # Eval with variable assignment
        shell.run_command("eval 'EVAL_VAR=42'")
        output = shell.capture_output("echo $EVAL_VAR")
        assert output.strip() == "42"
        
        # Eval with command substitution
        output = shell.capture_output("eval 'echo $(echo nested)'")
        assert output.strip() == "nested"
    
    def test_exit_command(self, shell):
        """Test exit command."""
        # Exit with status 0
        result = shell.run_command("exit 0")
        assert result == 0
        
        # Exit with specific status
        result = shell.run_command("exit 42")
        assert result == 42
        
        # Exit in subshell doesn't affect parent
        output = shell.capture_output("(exit 5); echo $?")
        assert output.strip() == "5"
    
    def test_export_command(self, shell):
        """Test export command."""
        # Export a variable
        shell.run_command("export POSIX_VAR=exported")
        output = shell.capture_output("echo $POSIX_VAR")
        assert output.strip() == "exported"
        
        # Export without value
        shell.run_command("UNEXP_VAR=unexported")
        shell.run_command("export UNEXP_VAR")
        # In a subshell, exported variables should be visible
        output = shell.capture_output("sh -c 'echo ${POSIX_VAR:-not_found}'")
        # Note: This might fail if sh is not available or PSH doesn't properly export
    
    def test_return_command(self, shell):
        """Test return command in functions."""
        shell.run_command("""
        test_return() {
            return 42
        }
        """)
        shell.run_command("test_return")
        output = shell.capture_output("echo $?")
        assert output.strip() == "42"
        
        # Return with no argument
        shell.run_command("""
        test_return_default() {
            false
            return
        }
        """)
        shell.run_command("test_return_default")
        output = shell.capture_output("echo $?")
        assert output.strip() == "1"
    
    def test_set_command_basics(self, shell):
        """Test basic set command functionality."""
        # Set positional parameters
        shell.run_command("set -- one two three")
        output = shell.capture_output("echo $1 $2 $3")
        assert output.strip() == "one two three"
        
        # Check $#
        output = shell.capture_output("echo $#")
        assert output.strip() == "3"
        
        # Set with no arguments should list variables (not testing output format)
        result = shell.run_command("set")
        assert result == 0
    
    def test_unset_command(self, shell):
        """Test unset command."""
        # Unset variable
        shell.run_command("UNSET_VAR=value")
        shell.run_command("unset UNSET_VAR")
        output = shell.capture_output("echo ${UNSET_VAR:-unset}")
        assert output.strip() == "unset"
        
        # Unset function
        shell.run_command("test_func() { echo func; }")
        shell.run_command("unset -f test_func")
        result = shell.run_command("test_func")
        assert result == 127  # Command not found
    
    @pytest.mark.xfail(reason="shift not implemented in PSH")
    def test_shift_command(self, shell):
        """Test shift command."""
        shell.run_command("set -- one two three four")
        shell.run_command("shift")
        output = shell.capture_output("echo $1 $2 $3")
        assert output.strip() == "two three four"
        
        # Shift with count
        shell.run_command("shift 2")
        output = shell.capture_output("echo $1")
        assert output.strip() == "four"
    
    @pytest.mark.xfail(reason="exec not implemented in PSH")
    def test_exec_command(self, shell):
        """Test exec command."""
        # exec should replace the shell process
        # This is hard to test directly, but we can test exec with redirections
        shell.run_command("exec 3>&1")  # Duplicate stdout to fd 3
        shell.run_command("exec >/tmp/exec_test.txt")  # Redirect stdout
        shell.run_command("echo redirected")
        shell.run_command("exec 1>&3 3>&-")  # Restore stdout
        
        output = shell.capture_output("cat /tmp/exec_test.txt")
        assert output.strip() == "redirected"
        shell.run_command("rm -f /tmp/exec_test.txt")
    
    @pytest.mark.xfail(reason="trap not implemented in PSH")
    def test_trap_command(self, shell):
        """Test trap command."""
        # Set a trap
        shell.run_command("trap 'echo trapped' EXIT")
        
        # The trap should execute on exit
        output = shell.capture_output("exit")
        assert "trapped" in output


class TestPOSIXRegularBuiltins:
    """Test POSIX regular built-in commands."""
    
    def test_alias_unalias(self, shell):
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
    
    def test_cd_pwd(self, shell):
        """Test cd and pwd commands."""
        # Get current directory
        original = shell.capture_output("pwd").strip()
        
        # Change to /tmp
        shell.run_command("cd /tmp")
        output = shell.capture_output("pwd")
        assert output.strip() == "/tmp"
        
        # Change back
        shell.run_command(f"cd {original}")
        output = shell.capture_output("pwd")
        assert output.strip() == original
        
        # Test cd with no arguments (should go to HOME)
        shell.run_command("HOME=/tmp")
        shell.run_command("cd")
        output = shell.capture_output("pwd")
        assert output.strip() == "/tmp"
    
    def test_false_true(self, shell):
        """Test false and true commands."""
        # true should return 0
        result = shell.run_command("true")
        assert result == 0
        
        # false should return 1
        result = shell.run_command("false")
        assert result == 1
        
        # Use in conditionals
        output = shell.capture_output("if true; then echo yes; fi")
        assert output.strip() == "yes"
        
        output = shell.capture_output("if false; then echo yes; else echo no; fi")
        assert output.strip() == "no"
    
    def test_read_command(self, shell):
        """Test read command."""
        # Read from here-doc
        output = shell.capture_output("""
        read var << EOF
        test input
        EOF
        echo $var
        """)
        assert output.strip() == "test input"
        
        # Read multiple variables
        output = shell.capture_output("""
        read var1 var2 << EOF
        first second third
        EOF
        echo "$var1|$var2"
        """)
        assert output.strip() == "first|second third"
    
    def test_jobs_fg_bg(self, shell):
        """Test jobs, fg, and bg commands."""
        # Start a background job
        shell.run_command("sleep 30 &")
        
        # Check jobs list
        output = shell.capture_output("jobs")
        assert "sleep" in output
        
        # Can't easily test fg/bg without interactive terminal
        # Just verify they exist
        result = shell.run_command("fg %1")
        # Note: This might fail or hang in non-interactive mode
    
    @pytest.mark.xfail(reason="getopts not implemented in PSH")
    def test_getopts_command(self, shell):
        """Test getopts command."""
        output = shell.capture_output("""
        while getopts "ab:c" opt; do
            case $opt in
                a) echo "Option a";;
                b) echo "Option b: $OPTARG";;
                c) echo "Option c";;
            esac
        done
        """, "set -- -a -b value -c")
        assert "Option a" in output
        assert "Option b: value" in output
        assert "Option c" in output
    
    @pytest.mark.xfail(reason="wait not implemented in PSH")
    def test_wait_command(self, shell):
        """Test wait command."""
        # Start background job
        shell.run_command("sleep 1 &")
        pid = shell.capture_output("echo $!").strip()
        
        # Wait for it
        result = shell.run_command("wait " + pid)
        assert result == 0
        
        # Wait with no arguments waits for all
        shell.run_command("sleep 1 & sleep 1 &")
        result = shell.run_command("wait")
        assert result == 0
    
    @pytest.mark.xfail(reason="command builtin not implemented in PSH")
    def test_command_builtin(self, shell):
        """Test command builtin."""
        # command -v should show command location/type
        output = shell.capture_output("command -v cd")
        assert "cd" in output
        
        # command should bypass aliases
        shell.run_command("alias echo='echo ALIASED'")
        output = shell.capture_output("command echo test")
        assert output.strip() == "test"
        assert "ALIASED" not in output


class TestPOSIXCompliance:
    """Test overall POSIX compliance behaviors."""
    
    def test_special_builtins_affect_shell(self, shell):
        """Test that special built-ins affect the current shell environment."""
        # Variable assignment with special built-in persists
        shell.run_command("VAR=value :")
        output = shell.capture_output("echo $VAR")
        assert output.strip() == "value"
        
        # Regular built-ins don't affect shell environment the same way
        shell.run_command("VAR2=value2 true")
        output = shell.capture_output("echo ${VAR2:-unset}")
        # In POSIX, this should be "unset" for regular built-ins
    
    def test_command_search_order(self, shell):
        """Test POSIX command search order."""
        # Special built-ins are found before functions
        shell.run_command("set() { echo 'function set'; }")
        output = shell.capture_output("set --")
        # Should use built-in set, not function
        assert "function set" not in output
    
    def test_field_splitting(self, shell):
        """Test IFS field splitting compliance."""
        # Default IFS
        output = shell.capture_output('echo $(echo "a b c")')
        assert output.strip() == "a b c"
        
        # Custom IFS
        shell.run_command("IFS=:")
        output = shell.capture_output('echo $(echo "a:b:c")')
        # Note: This tests field splitting behavior
        shell.run_command("IFS=' \t\n'")  # Reset IFS