"""Test command substitution with shell functions.

This test documents a known issue where command substitution doesn't work
properly with shell functions.
"""
import pytest
from psh.shell import Shell


class TestFunctionCommandSubstitution:
    """Test command substitution with functions."""
    
    @pytest.fixture
    def shell(self):
        return Shell()
    
    def test_direct_function_call(self, shell, capsys):
        """Test that functions work when called directly."""
        shell.run_command('''
        factorial() {
            n=$1
            if [ $n -le 1 ]; then
                echo 1
            else
                result=1
                i=2
                while [ $i -le $n ]; do
                    result=$((result * i))
                    i=$((i + 1))
                done
                echo $result
            fi
        }
        ''')
        
        shell.run_command('factorial 5')
        captured = capsys.readouterr()
        assert captured.out.strip() == "120"
    
    def test_function_in_command_substitution(self, shell, capsys):
        """Test that functions work in command substitution."""
        shell.run_command('''
        factorial() {
            n=$1
            if [ $n -le 1 ]; then
                echo 1
            else
                result=1
                i=2
                while [ $i -le $n ]; do
                    result=$((result * i))
                    i=$((i + 1))
                done
                echo $result
            fi
        }
        ''')
        
        shell.run_command('echo "Result: $(factorial 5)"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "Result: 120"
    
    def test_function_in_variable_assignment(self, shell, capsys):
        """Test function in command substitution for variable assignment."""
        shell.run_command('''
        double() {
            n=$1
            echo $((2 * n))
        }
        ''')
        
        shell.run_command('result=$(double 21)')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "42"
    
    def test_nested_function_calls(self, shell, capsys):
        """Test nested function calls with command substitution."""
        shell.run_command('''
        add() {
            a=$1
            b=$2
            echo $((a + b))
        }
        
        multiply() {
            a=$1
            b=$2
            echo $((a * b))
        }
        ''')
        
        # This should compute (3 + 4) * 2 = 14
        shell.run_command('result=$(multiply $(add 3 4) 2)')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "14"
    
    def test_command_substitution_with_external_commands(self, shell, capsys):
        """Test that command substitution works with external commands."""
        shell.run_command('result=$(echo "hello world")')
        shell.run_command('echo "Got: $result"')
        captured = capsys.readouterr()
        assert captured.out.strip() == 'Got: hello world'
    
    def test_function_in_arithmetic_context(self, shell, capsys):
        """Test function output used in arithmetic expansion."""
        shell.run_command('''
        get_number() {
            echo 5
        }
        ''')
        
        shell.run_command('result=$(($(get_number) * 2))')
        shell.run_command('echo $result')
        captured = capsys.readouterr()
        assert captured.out.strip() == "10"
    
    def test_function_in_for_loop(self, shell, capsys):
        """Test function in command substitution within for loop."""
        shell.run_command('''
        get_list() {
            echo "one two three"
        }
        ''')
        
        shell.run_command('''
        for item in $(get_list); do
            echo "Item: $item"
        done
        ''')
        captured = capsys.readouterr()
        assert "Item: one" in captured.out
        assert "Item: two" in captured.out
        assert "Item: three" in captured.out