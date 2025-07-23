"""Tests for arithmetic bit-shift assignment operations.

This test module specifically tests the fix for bit-shift operators
being mistaken for heredoc operators in arithmetic expressions.
"""

import pytest
from psh.shell import Shell


class TestArithmeticBitShiftAssignment:
    """Test arithmetic bit-shift assignment operations."""
    
    def test_left_shift_assignment(self, shell):
        """Test left shift assignment: ((x=x<<2))"""
        shell.run_command('x=5')
        exit_code = shell.run_command('((x=x<<2))')
        assert exit_code == 0
        result = shell.state.get_variable('x')
        assert result == '20'  # 5 << 2 = 5 * 4 = 20
    
    def test_right_shift_assignment(self, shell):
        """Test right shift assignment: ((x=x>>2))"""
        shell.run_command('x=20')
        exit_code = shell.run_command('((x=x>>2))')
        assert exit_code == 0
        result = shell.state.get_variable('x')
        assert result == '5'  # 20 >> 2 = 20 / 4 = 5
    
    def test_multiple_arithmetic_operations(self, shell):
        """Test mixed arithmetic operations including bit-shift."""
        shell.run_command('x=5')
        exit_code = shell.run_command('((x=x<<2)); ((x=x+3)); ((x=x>>1))')
        assert exit_code == 0
        result = shell.state.get_variable('x')
        assert result == '11'  # (5 << 2) + 3 >> 1 = 20 + 3 >> 1 = 23 >> 1 = 11
    
    def test_bitshift_in_compound_command(self, shell):
        """Test bit-shift in compound command with semicolon."""
        exit_code = shell.run_command('x=5; ((x=x<<2)); echo $x')
        assert exit_code == 0
        result = shell.state.get_variable('x')
        assert result == '20'
    
    def test_bitshift_with_output(self, shell, capsys):
        """Test bit-shift with echo output."""
        shell.run_command('x=5; ((x=x<<2)); echo $x')
        captured = capsys.readouterr()
        assert captured.out.strip() == '20'
    
    def test_bitshift_vs_heredoc(self, isolated_shell_with_temp_dir):
        """Test that bit-shift is not confused with heredoc."""
        shell = isolated_shell_with_temp_dir
        
        # This should NOT wait for heredoc input
        exit_code = shell.run_command('((x=8<<2))')
        assert exit_code == 0
        result = shell.state.get_variable('x')
        assert result == '32'
        
        # But this SHOULD be a heredoc
        import os
        temp_dir = shell.state.variables['PWD']
        shell.run_command('cat <<EOF > test.txt\nhello\nEOF')
        test_file = os.path.join(temp_dir, 'test.txt')
        assert os.path.exists(test_file)
        with open(test_file) as f:
            assert f.read().strip() == 'hello'
    
    def test_bitshift_in_arithmetic_expansion(self, shell, capsys):
        """Test bit-shift in arithmetic expansion $((expression))."""
        shell.run_command('echo $((5<<2))')
        captured = capsys.readouterr()
        assert captured.out.strip() == '20'
        
        # Also test with variable
        shell.run_command('x=5; echo $((x<<2))')
        captured = capsys.readouterr()
        assert captured.out.strip() == '20'
    
    def test_bitshift_compound_assignment(self, shell):
        """Test compound assignment with bit-shift."""
        # Note: PSH may not support <<= and >>= operators yet
        # Use the expanded form instead
        shell.run_command('x=5')
        exit_code = shell.run_command('((x=x<<2))')  # equivalent to x <<= 2
        assert exit_code == 0
        result = shell.state.get_variable('x')
        assert result == '20'
        
        shell.run_command('y=20')
        exit_code = shell.run_command('((y=y>>2))')  # equivalent to y >>= 2
        assert exit_code == 0
        result = shell.state.get_variable('y')
        assert result == '5'
    
    def test_bitshift_in_conditional(self, shell):
        """Test bit-shift in conditional arithmetic expression."""
        exit_code = shell.run_command('if ((5<<2 == 20)); then x=pass; else x=fail; fi')
        assert exit_code == 0
        result = shell.state.get_variable('x')
        assert result == 'pass'
    
    def test_complex_expression_with_bitshift(self, shell):
        """Test complex arithmetic expression with bit-shift."""
        shell.run_command('a=3; b=2')
        exit_code = shell.run_command('((result = (a<<b) + (a>>1) * 2))')
        assert exit_code == 0
        result = shell.state.get_variable('result')
        # (3<<2) + (3>>1) * 2 = 12 + 1 * 2 = 14
        assert result == '14'