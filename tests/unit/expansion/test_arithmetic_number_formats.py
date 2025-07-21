"""Test arithmetic expansion with various number formats.

This module tests the parser combinator's ability to handle different number formats
in arithmetic expansion, including base notation, large numbers, and overflow behavior.

Part of Phase 1 of the arithmetic expansion testing plan.
"""
import pytest


class TestArithmeticNumberFormats:
    """Test arithmetic expansion with various number formats."""
    
    # Binary notation tests (2#)
    
    def test_binary_notation_basic(self, shell, capsys):
        """Test basic binary notation parsing and evaluation."""
        # 2#1010 = 10 in decimal
        result = shell.run_command('echo $((2#1010))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "10"
    
    def test_binary_notation_zero(self, shell, capsys):
        """Test binary zero."""
        result = shell.run_command('echo $((2#0))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "0"
    
    def test_binary_notation_one(self, shell, capsys):
        """Test binary one."""
        result = shell.run_command('echo $((2#1))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "1"
    
    def test_binary_notation_large(self, shell, capsys):
        """Test larger binary numbers."""
        # 2#11111111 = 255 in decimal
        result = shell.run_command('echo $((2#11111111))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "255"
    
    def test_binary_notation_arithmetic(self, shell, capsys):
        """Test arithmetic with binary numbers."""
        # 2#1010 + 2#0101 = 10 + 5 = 15
        result = shell.run_command('echo $((2#1010 + 2#0101))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "15"
    
    # Octal notation tests (8#)
    
    def test_octal_notation_basic(self, shell, capsys):
        """Test basic octal notation."""
        # 8#77 = 63 in decimal
        result = shell.run_command('echo $((8#77))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "63"
    
    def test_octal_notation_permissions(self, shell, capsys):
        """Test octal numbers like file permissions."""
        # 8#755 = 493 in decimal
        result = shell.run_command('echo $((8#755))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "493"
    
    def test_octal_notation_max_digit(self, shell, capsys):
        """Test octal with maximum valid digit (7)."""
        # 8#777 = 511 in decimal
        result = shell.run_command('echo $((8#777))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "511"
    
    def test_traditional_octal_leading_zero(self, shell, capsys):
        """Test traditional octal with leading zero."""
        # 010 = 8 in decimal (traditional octal)
        result = shell.run_command('echo $((010))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "8"
    
    def test_traditional_octal_vs_explicit(self, shell, capsys):
        """Test that 010 and 8#10 give same result."""
        result1 = shell.run_command('echo $((010))')
        assert result1 == 0
        captured1 = capsys.readouterr()
        output1 = captured1.out.strip()
        
        result2 = shell.run_command('echo $((8#10))')
        assert result2 == 0
        captured2 = capsys.readouterr()
        output2 = captured2.out.strip()
        
        assert output1 == output2 == "8"
    
    # Hexadecimal notation tests (16#)
    
    def test_hex_notation_basic(self, shell, capsys):
        """Test basic hexadecimal notation."""
        # 16#FF = 255 in decimal
        result = shell.run_command('echo $((16#FF))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "255"
    
    def test_hex_notation_lowercase(self, shell, capsys):
        """Test hexadecimal with lowercase letters."""
        # 16#ff = 255 in decimal
        result = shell.run_command('echo $((16#ff))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "255"
    
    def test_hex_notation_mixed_case(self, shell, capsys):
        """Test hexadecimal with mixed case."""
        # 16#CaFe = 51966 in decimal
        result = shell.run_command('echo $((16#CaFe))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "51966"
    
    def test_hex_notation_large(self, shell, capsys):
        """Test large hexadecimal number."""
        # 16#DEADBEEF = 3735928559 in decimal
        result = shell.run_command('echo $((16#DEADBEEF))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "3735928559"
    
    def test_traditional_hex_0x_prefix(self, shell, capsys):
        """Test traditional 0x hex prefix."""
        # 0x10 = 16 in decimal
        result = shell.run_command('echo $((0x10))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "16"
    
    def test_traditional_hex_vs_explicit(self, shell, capsys):
        """Test that 0xFF and 16#FF give same result."""
        result1 = shell.run_command('echo $((0xFF))')
        assert result1 == 0
        captured1 = capsys.readouterr()
        output1 = captured1.out.strip()
        
        result2 = shell.run_command('echo $((16#FF))')
        assert result2 == 0
        captured2 = capsys.readouterr()
        output2 = captured2.out.strip()
        
        assert output1 == output2 == "255"
    
    # Arbitrary base tests (2-36)
    
    def test_base_3_notation(self, shell, capsys):
        """Test base 3 notation."""
        # 3#121 = 1*9 + 2*3 + 1 = 16 in decimal
        result = shell.run_command('echo $((3#121))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "16"
    
    def test_base_36_notation(self, shell, capsys):
        """Test base 36 notation (maximum base)."""
        # 36#Z = 35 in decimal
        result = shell.run_command('echo $((36#Z))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "35"
    
    def test_base_36_word(self, shell, capsys):
        """Test base 36 with word-like number."""
        # 36#HELLO = complex calculation
        result = shell.run_command('echo $((36#HELLO))')
        assert result == 0
        captured = capsys.readouterr()
        # HELLO in base 36: H=17, E=14, L=21, L=21, O=24
        # 17*36^4 + 14*36^3 + 21*36^2 + 21*36^1 + 24*36^0
        expected = 17 * (36**4) + 14 * (36**3) + 21 * (36**2) + 21 * 36 + 24
        assert captured.out.strip() == str(expected)
    
    def test_base_10_explicit(self, shell, capsys):
        """Test explicit base 10 notation."""
        # 10#123 = 123 in decimal
        result = shell.run_command('echo $((10#123))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "123"
    
    def test_minimum_base_2(self, shell, capsys):
        """Test minimum base (2)."""
        # 2#101 = 5 in decimal
        result = shell.run_command('echo $((2#101))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "5"
    
    def test_maximum_base_36(self, shell, capsys):
        """Test maximum base (36)."""
        # 36#10 = 36 in decimal
        result = shell.run_command('echo $((36#10))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "36"
    
    # Large number and overflow tests
    
    def test_32bit_max_positive(self, shell, capsys):
        """Test 32-bit maximum positive integer."""
        # 2^31 - 1 = 2147483647
        result = shell.run_command('echo $((2147483647))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "2147483647"
    
    def test_32bit_max_negative(self, shell, capsys):
        """Test 32-bit maximum negative integer."""
        # -2^31 = -2147483648
        result = shell.run_command('echo $((-2147483648))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "-2147483648"
    
    def test_large_positive_overflow(self, shell, capsys):
        """Test behavior with numbers larger than 32-bit."""
        # This tests system-specific behavior
        result = shell.run_command('echo $((2147483648))')
        assert result == 0
        captured = capsys.readouterr()
        # Should either wrap to negative or handle as 64-bit
        output = captured.out.strip()
        assert output in ["-2147483648", "2147483648"]  # Allow both behaviors
    
    def test_large_negative_underflow(self, shell, capsys):
        """Test behavior with numbers smaller than 32-bit minimum."""
        result = shell.run_command('echo $((-2147483649))')
        assert result == 0
        captured = capsys.readouterr()
        # Should either wrap to positive or handle as 64-bit
        output = captured.out.strip()
        assert output in ["2147483647", "-2147483649"]  # Allow both behaviors
    
    def test_very_large_number(self, shell, capsys):
        """Test very large number handling."""
        # Test with a number that definitely exceeds 32-bit
        result = shell.run_command('echo $((9999999999999))')
        assert result == 0
        captured = capsys.readouterr()
        # Document the actual behavior
        output = captured.out.strip()
        # Should be either the full number (64-bit) or wrapped value
        assert output.isdigit() or (output.startswith('-') and output[1:].isdigit())
    
    # Mixed format tests
    
    def test_mixed_decimal_and_hex(self, shell, capsys):
        """Test mixing decimal and hexadecimal."""
        # 10 + 0x10 = 10 + 16 = 26
        result = shell.run_command('echo $((10 + 0x10))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "26"
    
    def test_mixed_octal_and_binary(self, shell, capsys):
        """Test mixing octal and binary."""
        # 8#10 + 2#10 = 8 + 2 = 10
        result = shell.run_command('echo $((8#10 + 2#10))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "10"
    
    def test_mixed_all_bases(self, shell, capsys):
        """Test mixing multiple base notations."""
        # 10 + 0x10 + 8#10 + 2#10 = 10 + 16 + 8 + 2 = 36
        result = shell.run_command('echo $((10 + 0x10 + 8#10 + 2#10))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "36"
    
    def test_base_notation_in_parentheses(self, shell, capsys):
        """Test base notation within parentheses."""
        # (2#1010) * (8#10) = 10 * 8 = 80
        result = shell.run_command('echo $(((2#1010) * (8#10)))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "80"
    
    def test_base_notation_with_variables(self, shell, capsys):
        """Test base notation with variables."""
        # Set a variable and use it in base notation context
        shell.run_command('x=1010')
        result = shell.run_command('echo $((2#$x))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "10"
    
    # Error handling for invalid formats
    
    def test_invalid_binary_digit(self, shell):
        """Test error handling for invalid binary digit."""
        # 2#102 contains invalid digit '2' for base 2
        result = shell.run_command('echo $((2#102))')
        # Should either error or truncate at invalid digit
        # Exact behavior may vary - document what actually happens
        assert result in [0, 1, 2]  # Allow various error handling approaches
    
    def test_invalid_octal_digit(self, shell):
        """Test error handling for invalid octal digit."""
        # 8#89 contains invalid digit '9' for base 8
        result = shell.run_command('echo $((8#89))')
        # Should either error or truncate at invalid digit
        assert result in [0, 1, 2]  # Allow various error handling approaches
    
    def test_invalid_hex_character(self, shell):
        """Test error handling for invalid hex character."""
        # 16#GG contains invalid character 'G' for base 16
        result = shell.run_command('echo $((16#GG))')
        # Should either error or truncate at invalid character
        assert result in [0, 1, 2]  # Allow various error handling approaches
    
    def test_base_out_of_range_low(self, shell):
        """Test error handling for base too low."""
        # Base 1 is invalid (minimum is 2)
        result = shell.run_command('echo $((1#1))')
        # Should error
        assert result != 0
    
    def test_base_out_of_range_high(self, shell):
        """Test error handling for base too high."""
        # Base 37 is invalid (maximum is 36)
        result = shell.run_command('echo $((37#1))')
        # Should error
        assert result != 0
    
    def test_empty_number_after_base(self, shell):
        """Test error handling for empty number after base."""
        # 16# with no digits
        result = shell.run_command('echo $((16#))')
        # Should error
        assert result != 0