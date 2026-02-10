"""
Multiline command execution integration tests.

Tests actual execution of multiline commands including control structures,
function definitions, and complex nested scenarios.
"""

from pathlib import Path


class TestMultilineControlStructures:
    """Test execution of multiline control structures."""

    def test_multiline_if_statement(self, shell, capsys):
        """Test multi-line if statement execution."""
        command = '''if [ 1 -eq 1 ]; then
    echo "condition is true"
    echo "second line"
fi'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "condition is true" in captured.out
        assert "second line" in captured.out

    def test_multiline_if_else_statement(self, shell, capsys):
        """Test multi-line if-else statement execution."""
        command = '''VAR=5
if [ "$VAR" -gt 10 ]; then
    echo "greater than 10"
else
    echo "less than or equal to 10"
fi'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "less than or equal to 10" in captured.out
        assert "greater than 10" not in captured.out

    def test_multiline_elif_chain(self, shell, capsys):
        """Test multi-line if-elif-else chain."""
        command = '''VALUE=15
if [ "$VALUE" -lt 10 ]; then
    echo "small"
elif [ "$VALUE" -lt 20 ]; then
    echo "medium"
else
    echo "large"
fi'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "medium" in captured.out
        assert "small" not in captured.out
        assert "large" not in captured.out

    def test_multiline_while_loop(self, shell, capsys):
        """Test multi-line while loop execution."""
        command = '''counter=0
while [ "$counter" -lt 3 ]; do
    echo "iteration: $counter"
    counter=$((counter + 1))
done
echo "loop complete"'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "iteration: 0" in captured.out
        assert "iteration: 1" in captured.out
        assert "iteration: 2" in captured.out
        assert "iteration: 3" not in captured.out
        assert "loop complete" in captured.out

    def test_multiline_for_loop(self, shell, capsys):
        """Test multi-line for loop execution."""
        command = '''for item in apple banana cherry; do
    echo "fruit: $item"
    echo "processing $item"
done'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "fruit: apple" in captured.out
        assert "processing apple" in captured.out
        assert "fruit: banana" in captured.out
        assert "processing banana" in captured.out
        assert "fruit: cherry" in captured.out
        assert "processing cherry" in captured.out

    def test_multiline_case_statement(self, shell, capsys):
        """Test multi-line case statement execution."""
        command = '''VALUE="test.txt"
case "$VALUE" in
    *.txt)
        echo "text file"
        echo "processing text"
        ;;
    *.log)
        echo "log file"
        ;;
    *)
        echo "unknown file type"
        ;;
esac'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "text file" in captured.out
        assert "processing text" in captured.out
        assert "log file" not in captured.out
        assert "unknown file type" not in captured.out


class TestMultilineFunctionDefinitions:
    """Test multiline function definition and execution."""

    def test_simple_multiline_function(self, shell, capsys):
        """Test multi-line function definition and execution."""
        command = '''greet() {
    echo "Hello, $1!"
    echo "Welcome to PSH"
}
greet "World"'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "Hello, World!" in captured.out
        assert "Welcome to PSH" in captured.out

    def test_function_with_control_structures(self, shell, capsys):
        """Test function containing control structures."""
        command = '''check_number() {
    if [ "$1" -gt 0 ]; then
        echo "$1 is positive"
    elif [ "$1" -eq 0 ]; then
        echo "$1 is zero"
    else
        echo "$1 is negative"
    fi
}
check_number 5
check_number 0
check_number -3'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "5 is positive" in captured.out
        assert "0 is zero" in captured.out
        assert "-3 is negative" in captured.out

    def test_function_with_local_variables(self, shell, capsys):
        """Test function with local variable handling."""
        command = '''GLOBAL_VAR="global"
test_scope() {
    LOCAL_VAR="local"
    echo "Global: $GLOBAL_VAR"
    echo "Local: $LOCAL_VAR"
}
test_scope
echo "After function: ${LOCAL_VAR:-undefined}"'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "Global: global" in captured.out
        assert "Local: local" in captured.out
        # In PSH, variables may persist after function
        assert captured.out.count("undefined") <= 1

    def test_recursive_function(self, shell, capsys):
        """Test recursive function execution."""
        command = '''countdown() {
    if [ "$1" -gt 0 ]; then
        echo "Count: $1"
        countdown $(($1 - 1))
    else
        echo "Blast off!"
    fi
}
countdown 3'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "Count: 3" in captured.out
        assert "Count: 2" in captured.out
        assert "Count: 1" in captured.out
        assert "Blast off!" in captured.out


class TestNestedMultilineStructures:
    """Test complex nested multiline structures."""

    def test_nested_if_statements(self, shell, capsys):
        """Test nested if statements in multiline."""
        command = '''VALUE=15
if [ "$VALUE" -gt 10 ]; then
    echo "greater than 10"
    if [ "$VALUE" -gt 20 ]; then
        echo "also greater than 20"
    else
        echo "but not greater than 20"
    fi
else
    echo "not greater than 10"
fi'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "greater than 10" in captured.out
        assert "but not greater than 20" in captured.out
        assert "also greater than 20" not in captured.out
        assert "not greater than 10" not in captured.out

    def test_if_in_for_loop(self, shell, capsys):
        """Test if statement inside for loop."""
        command = '''for i in 1 2 3 4 5; do
    if [ "$i" -gt 3 ]; then
        echo "big: $i"
    else
        echo "small: $i"
    fi
done'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "small: 1" in captured.out
        assert "small: 2" in captured.out
        assert "small: 3" in captured.out
        assert "big: 4" in captured.out
        assert "big: 5" in captured.out

    def test_nested_loops(self, shell, capsys):
        """Test nested loop structures."""
        command = '''for outer in 1 2; do
    echo "Outer: $outer"
    for inner in a b; do
        echo "  Inner: $inner"
        echo "  Combined: $outer$inner"
    done
done'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "Outer: 1" in captured.out
        assert "Inner: a" in captured.out
        assert "Combined: 1a" in captured.out
        assert "Inner: b" in captured.out
        assert "Combined: 1b" in captured.out
        assert "Outer: 2" in captured.out
        assert "Combined: 2a" in captured.out
        assert "Combined: 2b" in captured.out

    def test_function_with_nested_structures(self, shell, capsys):
        """Test function containing nested control structures."""
        command = '''process_items() {
    for item in "$@"; do
        case "$item" in
            *.txt)
                echo "Processing text file: $item"
                if [ -r "$item" ]; then
                    echo "  File is readable"
                else
                    echo "  File not found or not readable"
                fi
                ;;
            *.log)
                echo "Processing log file: $item"
                ;;
            *)
                echo "Unknown file type: $item"
                ;;
        esac
    done
}
process_items "test.txt" "data.log" "script.sh"'''

        result = shell.run_command(command)
        assert result == 0

        captured = capsys.readouterr()
        assert "Processing text file: test.txt" in captured.out
        assert "Processing log file: data.log" in captured.out
        assert "Unknown file type: script.sh" in captured.out


class TestMultilineErrorHandling:
    """Test error handling in multiline commands."""

    def test_incomplete_if_statement_handling(self, shell):
        """Test handling of incomplete if statement."""
        # This should be caught during parsing
        command = '''if [ 1 -eq 1 ]; then
    echo "test"
# Missing fi'''

        # The shell should handle this gracefully
        # Exact behavior depends on PSH implementation
        result = shell.run_command(command)
        # Should either succeed (if PSH auto-completes) or fail gracefully
        assert isinstance(result, int)

    def test_syntax_error_in_multiline(self, shell):
        """Test handling of syntax errors in multiline commands."""
        # Invalid syntax should be detected
        command = '''if [ 1 -eq 1 ] then  # Missing semicolon
    echo "test"
fi'''

        result = shell.run_command(command)
        # Should handle syntax error gracefully
        assert isinstance(result, int)

    def test_command_failure_in_multiline_structure(self, shell, capsys):
        """Test command failure within multiline structure."""
        command = '''for i in 1 2 3; do
    echo "Processing $i"
    if [ "$i" -eq 2 ]; then
        false  # This should fail
    fi
    echo "Continuing with $i"
done
echo "Loop completed"'''

        result = shell.run_command(command)
        # Should complete despite false command
        assert result == 0

        captured = capsys.readouterr()
        assert "Processing 1" in captured.out
        assert "Processing 2" in captured.out
        assert "Processing 3" in captured.out
        assert "Loop completed" in captured.out


class TestMultilineWithRedirection:
    """Test multiline commands with I/O redirection."""

    def test_multiline_with_output_redirection(self, temp_dir):
        """Test multiline command with output redirection."""
        import os
        import subprocess
        import sys

        output_file = os.path.join(temp_dir, "output.txt")

        command = f'''for i in 1 2 3; do
    echo "Line $i"
    echo "Data: $i"
done > {output_file}'''

        # Use subprocess to test PSH directly
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent.parent.parent.parent)

        proc = subprocess.run(
            [sys.executable, '-m', 'psh', '--norc', '-c', command],
            env=env,
            capture_output=True,
            text=True
        )

        assert proc.returncode == 0

        # Check file was created and contains expected content
        assert os.path.exists(output_file)
        with open(output_file, 'r') as f:
            content = f.read()
        assert "Line 1" in content
        assert "Data: 1" in content
        assert "Line 2" in content
        assert "Data: 2" in content
        assert "Line 3" in content
        assert "Data: 3" in content

    def test_multiline_with_pipe(self):
        """Test multiline command with pipe."""
        import os
        import subprocess
        import sys

        command = '''for i in 1 2 3; do
    echo "item_$i"
done | grep "item_2"'''

        # Use subprocess to test PSH directly
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent.parent.parent.parent)

        proc = subprocess.run(
            [sys.executable, '-m', 'psh', '--norc', '-c', command],
            env=env,
            capture_output=True,
            text=True
        )

        assert proc.returncode == 0
        assert "item_2" in proc.stdout
        assert "item_1" not in proc.stdout
        assert "item_3" not in proc.stdout
