"""Test command substitution within arithmetic expressions."""
import pytest
from psh.shell import Shell


class TestArithmeticCommandSubstitution:
    """Test command substitution in arithmetic contexts."""
    
    @pytest.fixture
    def shell(self):
        # Respect PSH_USE_VISITOR_EXECUTOR env var
        import os
        use_visitor = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower() in ('1', 'true', 'yes')
        return Shell(use_visitor_executor=use_visitor)
    
    def test_simple_command_sub_in_arithmetic(self, shell, capsys):
        """Test basic command substitution in arithmetic."""
        # Disable debug for cleaner test
        exit_code = shell.run_command('result=$(($(echo 42) * 2))')
        assert exit_code == 0
        # Check the variable was set correctly
        result_value = shell.state.get_variable('result')
        assert result_value == '84', f"Expected result='84', got result='{result_value}'"
        # Test echo separately  
        exit_code2 = shell.run_command('echo $result')
        assert exit_code2 == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "84"
    
    def test_multiple_command_subs_in_arithmetic(self, shell, capsys):
        """Test multiple command substitutions in one expression."""
        # Reset stderr to avoid parse error interfering with test
        import sys
        old_stderr = sys.stderr
        try:
            shell.run_command('result=$(($(echo 10) + $(echo 20) * $(echo 2)))')
            assert shell.variables.get('result') == '50'  # 10 + (20 * 2)
        finally:
            sys.stderr = old_stderr
    
    def test_nested_command_subs_in_arithmetic(self, shell, capsys):
        """Test nested command substitutions."""
        shell.run_command('result=$(($(echo $(echo 5)) * 3))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "15"
    
    def test_command_sub_with_arithmetic_inside(self, shell, capsys):
        """Test command substitution containing arithmetic."""
        shell.run_command('result=$(($(echo $((2+3))) * 4))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "20"  # (2+3) * 4 = 5 * 4
    
    def test_non_numeric_command_output(self, shell, capsys):
        """Test non-numeric output treated as 0."""
        shell.run_command('result=$(($(echo "hello") + 5))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "5"  # "hello" treated as 0
    
    def test_empty_command_output(self, shell, capsys):
        """Test empty command output treated as 0."""
        shell.run_command('empty_func() { :; }')  # Function that outputs nothing
        shell.run_command('result=$(($(empty_func) + 10))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "10"  # Empty output treated as 0
    
    def test_command_sub_with_whitespace(self, shell, capsys):
        """Test command output with whitespace is trimmed."""
        shell.run_command('spaced() { echo "  42  "; }')
        shell.run_command('result=$(($(spaced) / 2))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "21"
    
    def test_complex_expression_with_functions(self, shell, capsys):
        """Test complex arithmetic with function calls."""
        shell.run_command('''
        add() { a=$1; b=$2; echo $((a + b)); }
        multiply() { a=$1; b=$2; echo $((a * b)); }
        ''')
        
        # Calculate: (add(3,4) * 2) + multiply(5,6)
        shell.run_command('result=$(($(add 3 4) * 2 + $(multiply 5 6)))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "44"  # (7 * 2) + 30 = 14 + 30
    
    def test_recursive_function_in_arithmetic(self, shell, capsys):
        """Test recursive function called within arithmetic."""
        shell.run_command('''
        factorial() {
            n=$1
            if [ $n -le 1 ]; then
                echo 1
            else
                prev=$(factorial $((n - 1)))
                echo $((n * prev))
            fi
        }
        ''')
        
        shell.run_command('result=$(($(factorial 5) / 10))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "12"  # 120 / 10
    
    def test_command_sub_with_error(self, shell, capsys):
        """Test command substitution that fails."""
        shell.run_command('result=$(($(false; echo $?) + 10))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "11"  # Exit code 1 + 10