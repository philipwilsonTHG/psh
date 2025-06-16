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

# Fixture is provided by pytest, no need to import


class TestPOSIXCommandSyntax:
    """Test POSIX command syntax requirements."""
    
    @pytest.mark.skip(reason="PSH: Output capture issues with file redirection")
    def test_simple_commands(self, shell, capsys):
        """Test simple command execution."""
        # Command with no arguments
        result = shell.run_command("true")
        assert result == 0
        
        # Command with arguments
        shell.run_command("echo hello world")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "hello world"
        
        # Command with redirections
        shell.run_command("echo test > /tmp/posix_test.txt")
        shell.run_command("cat < /tmp/posix_test.txt")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "test"
        shell.run_command("rm -f /tmp/posix_test.txt")
    
    @pytest.mark.skip(reason="PSH: Output capture issues with pipelines")
    def test_pipelines(self, shell, capsys):
        """Test pipeline syntax."""
        # Basic pipeline
        shell.run_command("echo hello | cat")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "hello"
        
        # Multi-stage pipeline
        shell.run_command("echo 'one\ntwo\nthree' | grep two | cat")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "two"
        
        # Pipeline exit status (rightmost command)
        result = shell.run_command("false | true")
        assert result == 0
        
        result = shell.run_command("true | false")
        assert result == 1
    
    @pytest.mark.skip(reason="PSH: Multi-line output capture issues")
    def test_lists(self, shell, capsys):
        """Test command lists."""
        # Sequential execution with ;
        shell.run_command("echo one; echo two")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "one\ntwo"
        
        # Background execution with &
        shell.run_command("sleep 0.1 &")
        result = shell.run_command("echo $!")
        assert result == 0
        
        # AND list with &&
        shell.run_command("true && echo success")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "success"
        
        shell.run_command("false && echo success || echo failure")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "failure"
        
        # OR list with ||
        shell.run_command("false || echo recovery")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "recovery"
    
    @pytest.mark.skip(reason="PSH: Subshell () and brace grouping {} not implemented")
    def test_compound_lists(self, shell, capsys):
        """Test compound command lists."""
        # Commands in subshell
        shell.run_command("(echo one; echo two)")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "one\ntwo"
        
        # Commands in current shell with braces
        # Note: PSH might not support { } grouping
        shell.run_command("echo start; { echo middle; }; echo end")
        captured = capsys.readouterr()
        output = captured.out
        # If not supported, this might fail


class TestPOSIXControlStructures:
    """Test POSIX control structure syntax."""
    
    def test_if_statement(self, shell, capsys):
        """Test if/then/elif/else/fi syntax."""
        # Basic if
        shell.run_command("""

        if true; then\necho "true branch"\nfi

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "true branch"
        
        # if/else
        shell.run_command("""

        if false; then\necho "true branch"\nelse\necho "false branch"\nfi

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "false branch"
        
        # if/elif/else
        shell.run_command("""

        x=2\nif [ $x -eq 1 ]; then\necho "one"\nelif [ $x -eq 2 ]; then\necho "two"\nelse\necho "other"\nfi

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "two"
    
    def test_while_loop(self, shell, capsys):
        """Test while/do/done syntax."""
        shell.run_command("""

        i=0\nwhile [ $i -lt 3 ]; do\necho $i\ni=$((i + 1))\ndone

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "0\n1\n2"
    
    @pytest.mark.skip(reason="PSH: for loop without 'in' keyword not supported")
    def test_for_loop(self, shell, capsys):
        """Test for/in/do/done syntax."""
        # Basic for loop
        shell.run_command("""

        for i in 1 2 3; do\necho $i\ndone

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "1\n2\n3"
        
        # for loop with default $@
        shell.run_command("set -- a b c")
        shell.run_command("""

        for arg; do\necho $arg\ndone

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "a\nb\nc"
        
        # for loop with glob expansion
        shell.run_command("touch /tmp/posix_test1.txt /tmp/posix_test2.txt")
        shell.run_command("""

        for file in /tmp/posix_test*.txt; do\nbasename "$file"\ndone

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert "posix_test1.txt" in output
        assert "posix_test2.txt" in output
        shell.run_command("rm -f /tmp/posix_test*.txt")
    
    def test_case_statement(self, shell, capsys):
        """Test case/in/esac syntax."""
        # Basic case
        shell.run_command("""

        fruit=apple\ncase $fruit in\napple)\necho "red"\n;;\nbanana)\necho "yellow"\n;;\n*)\necho "unknown"\n;;\nesac

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "red"
        
        # Case with patterns
        shell.run_command("""

        file=test.txt\ncase $file in\n*.txt)\necho "text file"\n;;\n*.py)\necho "python file"\n;;\nesac

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "text file"
        
        # Case with multiple patterns
        shell.run_command("""

        char=b\ncase $char in\n[aeiou])\necho "vowel"\n;;\n[a-z])\necho "consonant"\n;;\nesac

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "consonant"


class TestPOSIXFunctions:
    """Test POSIX function syntax."""
    
    def test_function_definition(self, shell, capsys):
        """Test POSIX function definition syntax."""
        # POSIX style function
        shell.run_command("""
        greet() {
            echo "Hello, $1!"
        }
        """)
        shell.run_command("greet World")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "Hello, World!"
        
        # Function with return
        shell.run_command("""
        add() {
            return $(($1 + $2))
        }
        """)
        shell.run_command("add 5 3")
        shell.run_command("echo $?")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "8"
    
    def test_function_scope(self, shell, capsys):
        """Test function variable scope."""
        # Variables are global by default in POSIX
        shell.run_command("""
        set_var() {
            var=inside
        }
        """)
        shell.run_command("var=outside")
        shell.run_command("set_var")
        shell.run_command("echo $var")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "inside"
    
    def test_function_parameters(self, shell, capsys):
        """Test function parameter handling."""
        shell.run_command("""
        show_params() {
            echo "Count: $#"
            echo "First: $1"
            echo "All: $@"
        }
        """)
        shell.run_command("show_params one two three")
        captured = capsys.readouterr()
        output = captured.out
        assert "Count: 3" in output
        assert "First: one" in output
        assert "All: one two three" in output


class TestPOSIXRedirection:
    """Test POSIX redirection syntax."""
    
    @pytest.mark.skip(reason="PSH: Output capture issues with file redirection")
    def test_input_output_redirection(self, shell, capsys):
        """Test basic input/output redirection."""
        # Output redirection
        shell.run_command("echo test > /tmp/posix_redir.txt")
        shell.run_command("cat /tmp/posix_redir.txt")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "test"
        
        # Input redirection
        shell.run_command("cat < /tmp/posix_redir.txt")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "test"
        
        # Append redirection
        shell.run_command("echo more >> /tmp/posix_redir.txt")
        shell.run_command("cat /tmp/posix_redir.txt")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "test\nmore"
        
        shell.run_command("rm -f /tmp/posix_redir.txt")
    
    @pytest.mark.skip(reason="exec builtin not implemented - corrupts test environment")
    def test_fd_redirection(self, shell, capsys):
        """Test file descriptor redirection."""
        # Stderr redirection
        shell.run_command("echo error >&2 2>&1")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "error"
        
        # FD duplication
        shell.run_command("exec 3>&1")  # Save stdout
        shell.run_command("exec 1>/tmp/posix_fd.txt")  # Redirect stdout
        shell.run_command("echo redirected")
        shell.run_command("exec 1>&3 3>&-")  # Restore stdout
        
        shell.run_command("cat /tmp/posix_fd.txt")
        captured = capsys.readouterr()
        output = captured.out
        assert "redirected" in output
        shell.run_command("rm -f /tmp/posix_fd.txt")
    
    @pytest.mark.skip(reason="PSH: Multi-line command handling issues")
    def test_here_documents(self, shell, capsys):
        """Test here document syntax."""
        # Basic here-doc
        shell.run_command("""

        cat << EOF\nline 1\nline 2\nEOF

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "line 1\nline 2"
        
        # Here-doc with tab stripping
        shell.run_command("""

        cat <<- EOF\n\tindented\n\tlines\nEOF

        """)

        captured = capsys.readouterr()

        output = captured.out
        # Tabs should be stripped with <<-
        assert "indented" in output
        assert "lines" in output
        
        # Here-doc with parameter expansion
        shell.run_command("var=expanded")
        shell.run_command("""

        cat << EOF\nVariable: $var\nEOF

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "Variable: expanded"
        
        # Here-doc with quotes (no expansion)
        shell.run_command("""

        cat << 'EOF'\nVariable: $var\nEOF

        """)

        captured = capsys.readouterr()

        output = captured.out
        assert output.strip() == "Variable: $var"


class TestPOSIXQuoting:
    """Test POSIX quoting rules."""
    
    def test_single_quotes(self, shell, capsys):
        """Test single quote behavior."""
        # No expansions in single quotes
        shell.run_command("var=value")
        shell.run_command("echo '$var'")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "$var"
        
        # Preserve all characters
        shell.run_command("echo 'special: * ? [ ] $ ` \\'")
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "special: * ? [ ] $ ` \\"
    
    @pytest.mark.skip(reason="PSH: Backslash handling in double quotes not correct")
    def test_double_quotes(self, shell, capsys):
        """Test double quote behavior."""
        # Variable expansion in double quotes
        shell.run_command("var=value")
        shell.run_command('echo "$var"')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "value"
        
        # Command substitution in double quotes
        shell.run_command('echo "Path: $(pwd)"')
        captured = capsys.readouterr()
        output = captured.out
        assert "Path: /" in output
        
        # Preserve literal $ with backslash
        shell.run_command('echo "$var"')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "$var"
        
        # No glob expansion in double quotes
        shell.run_command('echo "*"')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "*"
    
    def test_backslash_escaping(self, shell, capsys):
        """Test backslash escape sequences."""
        # Escape special characters
        shell.run_command(r'echo \$var')
        captured = capsys.readouterr()
        output = captured.out
        assert output.strip() == "$var"
        
        # Escape newline
        shell.run_command('echo line1\\\nline2')
        captured = capsys.readouterr()
        output = captured.out
        assert "line1line2" in output
        
        # Escape in double quotes
        shell.run_command('echo "line1\\\nline2"')
        captured = capsys.readouterr()
        output = captured.out
        assert "line1\\" in output or "line1line2" in output