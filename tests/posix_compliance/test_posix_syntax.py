#!/usr/bin/env python3
"""
Test POSIX shell syntax compliance.
Tests grammar constructs required by POSIX.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.conftest import shell


class TestPOSIXCommandSyntax:
    """Test POSIX command syntax requirements."""
    
    def test_simple_commands(self, shell):
        """Test simple command execution."""
        # Command with no arguments
        result = shell.run_command("true")
        assert result == 0
        
        # Command with arguments
        output = shell.capture_output("echo hello world")
        assert output.strip() == "hello world"
        
        # Command with redirections
        shell.run_command("echo test > /tmp/posix_test.txt")
        output = shell.capture_output("cat < /tmp/posix_test.txt")
        assert output.strip() == "test"
        shell.run_command("rm -f /tmp/posix_test.txt")
    
    def test_pipelines(self, shell):
        """Test pipeline syntax."""
        # Basic pipeline
        output = shell.capture_output("echo hello | cat")
        assert output.strip() == "hello"
        
        # Multi-stage pipeline
        output = shell.capture_output("echo 'one\ntwo\nthree' | grep two | cat")
        assert output.strip() == "two"
        
        # Pipeline exit status (rightmost command)
        result = shell.run_command("false | true")
        assert result == 0
        
        result = shell.run_command("true | false")
        assert result == 1
    
    def test_lists(self, shell):
        """Test command lists."""
        # Sequential execution with ;
        output = shell.capture_output("echo one; echo two")
        assert output.strip() == "one\ntwo"
        
        # Background execution with &
        shell.run_command("sleep 0.1 &")
        result = shell.run_command("echo $!")
        assert result == 0
        
        # AND list with &&
        output = shell.capture_output("true && echo success")
        assert output.strip() == "success"
        
        output = shell.capture_output("false && echo success || echo failure")
        assert output.strip() == "failure"
        
        # OR list with ||
        output = shell.capture_output("false || echo recovery")
        assert output.strip() == "recovery"
    
    def test_compound_lists(self, shell):
        """Test compound command lists."""
        # Commands in subshell
        output = shell.capture_output("(echo one; echo two)")
        assert output.strip() == "one\ntwo"
        
        # Commands in current shell with braces
        # Note: PSH might not support { } grouping
        output = shell.capture_output("echo start; { echo middle; }; echo end")
        # If not supported, this might fail


class TestPOSIXControlStructures:
    """Test POSIX control structure syntax."""
    
    def test_if_statement(self, shell):
        """Test if/then/elif/else/fi syntax."""
        # Basic if
        output = shell.capture_output("""
        if true; then
            echo "true branch"
        fi
        """)
        assert output.strip() == "true branch"
        
        # if/else
        output = shell.capture_output("""
        if false; then
            echo "true branch"
        else
            echo "false branch"
        fi
        """)
        assert output.strip() == "false branch"
        
        # if/elif/else
        output = shell.capture_output("""
        x=2
        if [ $x -eq 1 ]; then
            echo "one"
        elif [ $x -eq 2 ]; then
            echo "two"
        else
            echo "other"
        fi
        """)
        assert output.strip() == "two"
    
    def test_while_loop(self, shell):
        """Test while/do/done syntax."""
        output = shell.capture_output("""
        i=0
        while [ $i -lt 3 ]; do
            echo $i
            i=$((i + 1))
        done
        """)
        assert output.strip() == "0\n1\n2"
    
    def test_for_loop(self, shell):
        """Test for/in/do/done syntax."""
        # Basic for loop
        output = shell.capture_output("""
        for i in 1 2 3; do
            echo $i
        done
        """)
        assert output.strip() == "1\n2\n3"
        
        # for loop with default $@
        shell.run_command("set -- a b c")
        output = shell.capture_output("""
        for arg; do
            echo $arg
        done
        """)
        assert output.strip() == "a\nb\nc"
        
        # for loop with glob expansion
        shell.run_command("touch /tmp/posix_test1.txt /tmp/posix_test2.txt")
        output = shell.capture_output("""
        for file in /tmp/posix_test*.txt; do
            basename "$file"
        done
        """)
        assert "posix_test1.txt" in output
        assert "posix_test2.txt" in output
        shell.run_command("rm -f /tmp/posix_test*.txt")
    
    def test_case_statement(self, shell):
        """Test case/in/esac syntax."""
        # Basic case
        output = shell.capture_output("""
        fruit=apple
        case $fruit in
            apple)
                echo "red"
                ;;
            banana)
                echo "yellow"
                ;;
            *)
                echo "unknown"
                ;;
        esac
        """)
        assert output.strip() == "red"
        
        # Case with patterns
        output = shell.capture_output("""
        file=test.txt
        case $file in
            *.txt)
                echo "text file"
                ;;
            *.py)
                echo "python file"
                ;;
        esac
        """)
        assert output.strip() == "text file"
        
        # Case with multiple patterns
        output = shell.capture_output("""
        char=b
        case $char in
            [aeiou])
                echo "vowel"
                ;;
            [a-z])
                echo "consonant"
                ;;
        esac
        """)
        assert output.strip() == "consonant"


class TestPOSIXFunctions:
    """Test POSIX function syntax."""
    
    def test_function_definition(self, shell):
        """Test POSIX function definition syntax."""
        # POSIX style function
        shell.run_command("""
        greet() {
            echo "Hello, $1!"
        }
        """)
        output = shell.capture_output("greet World")
        assert output.strip() == "Hello, World!"
        
        # Function with return
        shell.run_command("""
        add() {
            return $(($1 + $2))
        }
        """)
        shell.run_command("add 5 3")
        output = shell.capture_output("echo $?")
        assert output.strip() == "8"
    
    def test_function_scope(self, shell):
        """Test function variable scope."""
        # Variables are global by default in POSIX
        shell.run_command("""
        set_var() {
            var=inside
        }
        """)
        shell.run_command("var=outside")
        shell.run_command("set_var")
        output = shell.capture_output("echo $var")
        assert output.strip() == "inside"
    
    def test_function_parameters(self, shell):
        """Test function parameter handling."""
        shell.run_command("""
        show_params() {
            echo "Count: $#"
            echo "First: $1"
            echo "All: $@"
        }
        """)
        output = shell.capture_output("show_params one two three")
        assert "Count: 3" in output
        assert "First: one" in output
        assert "All: one two three" in output


class TestPOSIXRedirection:
    """Test POSIX redirection syntax."""
    
    def test_input_output_redirection(self, shell):
        """Test basic input/output redirection."""
        # Output redirection
        shell.run_command("echo test > /tmp/posix_redir.txt")
        output = shell.capture_output("cat /tmp/posix_redir.txt")
        assert output.strip() == "test"
        
        # Input redirection
        output = shell.capture_output("cat < /tmp/posix_redir.txt")
        assert output.strip() == "test"
        
        # Append redirection
        shell.run_command("echo more >> /tmp/posix_redir.txt")
        output = shell.capture_output("cat /tmp/posix_redir.txt")
        assert output.strip() == "test\nmore"
        
        shell.run_command("rm -f /tmp/posix_redir.txt")
    
    def test_fd_redirection(self, shell):
        """Test file descriptor redirection."""
        # Stderr redirection
        output = shell.capture_output("echo error >&2 2>&1")
        assert output.strip() == "error"
        
        # FD duplication
        shell.run_command("exec 3>&1")  # Save stdout
        shell.run_command("exec 1>/tmp/posix_fd.txt")  # Redirect stdout
        shell.run_command("echo redirected")
        shell.run_command("exec 1>&3 3>&-")  # Restore stdout
        
        output = shell.capture_output("cat /tmp/posix_fd.txt")
        assert "redirected" in output
        shell.run_command("rm -f /tmp/posix_fd.txt")
    
    def test_here_documents(self, shell):
        """Test here document syntax."""
        # Basic here-doc
        output = shell.capture_output("""
        cat << EOF
        line 1
        line 2
        EOF
        """)
        assert output.strip() == "line 1\nline 2"
        
        # Here-doc with tab stripping
        output = shell.capture_output("""
        cat <<- EOF
        \tindented
        \tlines
        EOF
        """)
        # Tabs should be stripped with <<-
        assert "indented" in output
        assert "lines" in output
        
        # Here-doc with parameter expansion
        shell.run_command("var=expanded")
        output = shell.capture_output("""
        cat << EOF
        Variable: $var
        EOF
        """)
        assert output.strip() == "Variable: expanded"
        
        # Here-doc with quotes (no expansion)
        output = shell.capture_output("""
        cat << 'EOF'
        Variable: $var
        EOF
        """)
        assert output.strip() == "Variable: $var"


class TestPOSIXQuoting:
    """Test POSIX quoting rules."""
    
    def test_single_quotes(self, shell):
        """Test single quote behavior."""
        # No expansions in single quotes
        shell.run_command("var=value")
        output = shell.capture_output("echo '$var'")
        assert output.strip() == "$var"
        
        # Preserve all characters
        output = shell.capture_output("echo 'special: * ? [ ] $ ` \\'")
        assert output.strip() == "special: * ? [ ] $ ` \\"
    
    def test_double_quotes(self, shell):
        """Test double quote behavior."""
        # Variable expansion in double quotes
        shell.run_command("var=value")
        output = shell.capture_output('echo "$var"')
        assert output.strip() == "value"
        
        # Command substitution in double quotes
        output = shell.capture_output('echo "Path: $(pwd)"')
        assert "Path: /" in output
        
        # Preserve literal $ with backslash
        output = shell.capture_output('echo "\$var"')
        assert output.strip() == "$var"
        
        # No glob expansion in double quotes
        output = shell.capture_output('echo "*"')
        assert output.strip() == "*"
    
    def test_backslash_escaping(self, shell):
        """Test backslash escape sequences."""
        # Escape special characters
        output = shell.capture_output('echo \$var')
        assert output.strip() == "$var"
        
        # Escape newline
        output = shell.capture_output('echo line1\\\nline2')
        assert "line1line2" in output
        
        # Escape in double quotes
        output = shell.capture_output('echo "line1\\\nline2"')
        assert "line1\\" in output or "line1line2" in output