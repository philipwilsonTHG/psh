#!/usr/bin/env python3
"""
Test basic commands against bash for compatibility.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestBasicCommands:
    """Test basic command execution compatibility with bash."""
    
    def test_echo_basic(self):
        """Test basic echo commands."""
        bash_compare.assert_shells_match("echo hello")
        bash_compare.assert_shells_match("echo 'hello world'")
        bash_compare.assert_shells_match('echo "hello world"')
        bash_compare.assert_shells_match("echo")  # Empty echo
    
    def test_echo_flags(self):
        """Test echo with flags."""
        bash_compare.assert_shells_match("echo -n hello")
        bash_compare.assert_shells_match("echo -e 'hello\\nworld'")
        bash_compare.assert_shells_match("echo -E 'hello\\nworld'")
    
    def test_variable_expansion(self):
        """Test variable expansion."""
        bash_compare.assert_shells_match("VAR=test; echo $VAR")
        bash_compare.assert_shells_match("VAR=hello; echo ${VAR}")
        bash_compare.assert_shells_match("echo $USER", env={"USER": "testuser"})
    
    def test_command_substitution(self):
        """Test command substitution."""
        bash_compare.assert_shells_match("echo $(echo hello)")
        bash_compare.assert_shells_match("echo `echo world`")
        bash_compare.assert_shells_match("VAR=$(echo test); echo $VAR")
    
    def test_arithmetic_expansion(self):
        """Test arithmetic expansion."""
        bash_compare.assert_shells_match("echo $((2 + 3))")
        bash_compare.assert_shells_match("echo $((10 * 5))")
        bash_compare.assert_shells_match("x=5; echo $((x * 2))")
    
    def test_conditional_execution(self):
        """Test && and || operators."""
        bash_compare.assert_shells_match("true && echo success")
        bash_compare.assert_shells_match("false || echo fallback")
        bash_compare.assert_shells_match("true && true && echo both_true")
        bash_compare.assert_shells_match("false && echo not_printed")


class TestControlStructures:
    """Test control structures against bash."""
    
    def test_if_statements(self):
        """Test if/then/else statements."""
        bash_compare.assert_shells_match(
            "if true; then echo yes; fi"
        )
        bash_compare.assert_shells_match(
            "if false; then echo no; else echo yes; fi"
        )
        bash_compare.assert_shells_match(
            "x=5; if [ $x -gt 3 ]; then echo big; fi"
        )
    
    def test_while_loops(self):
        """Test while loops."""
        bash_compare.assert_shells_match(
            "i=1; while [ $i -le 3 ]; do echo $i; i=$((i+1)); done"
        )
        bash_compare.assert_shells_match(
            "while false; do echo never; done"
        )
    
    def test_for_loops(self):
        """Test for loops."""
        bash_compare.assert_shells_match(
            "for i in 1 2 3; do echo $i; done"
        )
        bash_compare.assert_shells_match(
            "for word in hello world; do echo $word; done"
        )
    
    def test_case_statements(self):
        """Test case statements."""
        bash_compare.assert_shells_match(
            "case test in test) echo match;; *) echo no;; esac"
        )
        bash_compare.assert_shells_match(
            "x=apple; case $x in a*) echo starts_with_a;; esac"
        )


class TestExpansions:
    """Test various shell expansions."""
    
    def test_brace_expansion(self):
        """Test brace expansion."""
        bash_compare.assert_shells_match("echo {a,b,c}")
        bash_compare.assert_shells_match("echo {1..5}")
        bash_compare.assert_shells_match("echo pre{A,B}post")
    
    def test_parameter_expansion(self):
        """Test parameter expansion."""
        bash_compare.assert_shells_match("VAR=hello; echo ${VAR:-default}")
        bash_compare.assert_shells_match("VAR=; echo ${VAR:-empty}")
        bash_compare.assert_shells_match("VAR=testing; echo ${#VAR}")
    
    def test_glob_expansion(self):
        """Test glob patterns (create temp files first)."""
        # This would need temp file setup
        pass  # TODO: Implement with temp directory
    
    def test_tilde_expansion(self):
        """Test tilde expansion."""
        bash_compare.assert_shells_match("echo ~", env={"HOME": "/home/test"})


class TestRedirection:
    """Test I/O redirection."""
    
    def test_output_redirection(self):
        """Test output redirection."""
        # These need temp files - would use tempfile
        pass  # TODO: Implement with temp files
    
    def test_input_redirection(self):
        """Test input redirection."""
        pass  # TODO: Implement with temp files
    
    def test_here_documents(self):
        """Test here documents."""
        # Here documents might not work properly in multiline strings via framework
        # This is a framework limitation, not PSH limitation
        pass  # TODO: Implement with proper multiline heredoc support


class TestBuiltins:
    """Test builtin commands."""
    
    def test_pwd(self):
        """Test pwd builtin."""
        bash_compare.assert_shells_match("pwd")
    
    def test_exit_status(self):
        """Test exit status handling."""
        bash_compare.assert_shells_match("true; echo $?")
        bash_compare.assert_shells_match("false; echo $?")
    
    def test_test_command(self):
        """Test [ command."""
        bash_compare.assert_shells_match("[ 5 -gt 3 ] && echo yes")
        bash_compare.assert_shells_match("[ hello = hello ] && echo match")
        bash_compare.assert_shells_match("[ -z '' ] && echo empty")


class TestKnownLimitations:
    """Test cases that are expected to differ - documents known issues."""
    
    def test_quote_handling_limitations(self):
        """Test quote handling - these are now FIXED!"""
        # PSH quote handling now works correctly, same as bash
        bash_compare.assert_shells_match("echo a'b'c")
        bash_compare.assert_shells_match("echo prefix'middle'suffix")
    
    def test_error_message_differences(self):
        """Test cases where error messages legitimately differ."""
        # Both shells return the same exit code for nonexistent commands
        bash_compare.assert_shells_match(
            "nonexistent_command_12345", 
            check_stderr=False  # Only compare exit codes and stdout
        )


# Parametrized test for bulk command testing
@pytest.mark.parametrize("command", [
    "echo hello",
    "echo $((1+1))",
    "VAR=test; echo $VAR",
    "true && echo success",
    "for i in 1 2; do echo $i; done",
])
def test_bulk_commands(command):
    """Test multiple commands efficiently."""
    bash_compare.assert_shells_match(command)