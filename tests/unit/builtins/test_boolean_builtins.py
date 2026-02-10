"""
Unit tests for boolean builtins (true, false).

Tests cover:
- Exit codes
- No side effects
- Usage in conditions
"""



class TestBooleanBuiltins:
    """Test true and false builtins."""

    def test_true_exit_code(self, shell, capsys):
        """Test true returns exit code 0."""
        exit_code = shell.run_command('true')
        assert exit_code == 0

    def test_false_exit_code(self, shell, capsys):
        """Test false returns exit code 1."""
        exit_code = shell.run_command('false')
        assert exit_code == 1

    def test_true_no_output(self, shell, capsys):
        """Test true produces no output."""
        shell.run_command('true')
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_false_no_output(self, shell, capsys):
        """Test false produces no output."""
        shell.run_command('false')
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_true_ignores_arguments(self, shell, capsys):
        """Test true ignores any arguments."""
        exit_code = shell.run_command('true arg1 arg2 arg3')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_false_ignores_arguments(self, shell, capsys):
        """Test false ignores any arguments."""
        exit_code = shell.run_command('false arg1 arg2 arg3')
        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_true_in_if_condition(self, shell, capsys):
        """Test true in if statement."""
        shell.run_command('if true; then echo "yes"; else echo "no"; fi')
        captured = capsys.readouterr()
        assert captured.out.strip() == "yes"

    def test_false_in_if_condition(self, shell, capsys):
        """Test false in if statement."""
        shell.run_command('if false; then echo "yes"; else echo "no"; fi')
        captured = capsys.readouterr()
        assert captured.out.strip() == "no"

    def test_true_in_and_chain(self, shell, capsys):
        """Test true in && chain."""
        shell.run_command('true && echo "success"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "success"

    def test_false_in_and_chain(self, shell, capsys):
        """Test false in && chain."""
        shell.run_command('false && echo "success"')
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_true_in_or_chain(self, shell, capsys):
        """Test true in || chain."""
        shell.run_command('true || echo "failure"')
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_false_in_or_chain(self, shell, capsys):
        """Test false in || chain."""
        shell.run_command('false || echo "failure"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "failure"

    def test_true_in_while_loop(self, shell, capsys):
        """Test true in while loop (with break to avoid infinite loop)."""
        cmd = '''
        count=0
        while true; do
            count=$((count + 1))
            if [ $count -eq 3 ]; then
                break
            fi
            echo $count
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "1\n2" in captured.out

    def test_false_in_until_loop(self, shell, capsys):
        """Test false in until loop (with break to avoid infinite loop)."""
        cmd = '''
        count=0
        until false; do
            count=$((count + 1))
            if [ $count -eq 3 ]; then
                break
            fi
            echo $count
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "1\n2" in captured.out
