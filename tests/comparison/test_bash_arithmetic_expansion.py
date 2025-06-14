#!/usr/bin/env python3
"""
Test arithmetic expansion against bash for compatibility.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestArithmeticExpansion:
    """Test arithmetic expansion compatibility with bash."""
    
    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        bash_compare.assert_shells_match("echo $((2 + 3))")
        bash_compare.assert_shells_match("echo $((10 - 5))")
        bash_compare.assert_shells_match("echo $((4 * 5))")
        bash_compare.assert_shells_match("echo $((20 / 4))")
        bash_compare.assert_shells_match("echo $((10 % 3))")
    
    def test_arithmetic_with_variables(self):
        """Test arithmetic with variables."""
        bash_compare.assert_shells_match("x=10; echo $((x + 5))")
        bash_compare.assert_shells_match("a=5; b=3; echo $((a * b))")
        bash_compare.assert_shells_match("x=20; y=4; echo $((x / y))")
    
    def test_arithmetic_assignment(self):
        """Test arithmetic in assignments."""
        bash_compare.assert_shells_match("result=$((5 + 3)); echo $result")
        bash_compare.assert_shells_match("x=10; result=$((x * 2)); echo $result")
    
    def test_arithmetic_precedence(self):
        """Test operator precedence."""
        bash_compare.assert_shells_match("echo $((2 + 3 * 4))")
        bash_compare.assert_shells_match("echo $(((2 + 3) * 4))")
        bash_compare.assert_shells_match("echo $((10 + 20 / 5))")
    
    def test_arithmetic_comparison(self):
        """Test comparison operators."""
        bash_compare.assert_shells_match("echo $((5 > 3))")
        bash_compare.assert_shells_match("echo $((5 < 3))")
        bash_compare.assert_shells_match("echo $((5 == 5))")
        bash_compare.assert_shells_match("echo $((5 != 3))")
    
    def test_arithmetic_logical(self):
        """Test logical operators."""
        bash_compare.assert_shells_match("echo $((1 && 1))")
        bash_compare.assert_shells_match("echo $((1 && 0))")
        bash_compare.assert_shells_match("echo $((0 || 1))")
        bash_compare.assert_shells_match("echo $((0 || 0))")
    
    def test_arithmetic_increment(self):
        """Test increment/decrement operators."""
        bash_compare.assert_shells_match("x=5; echo $((x++)); echo $x")
        bash_compare.assert_shells_match("x=5; echo $((++x)); echo $x")
        bash_compare.assert_shells_match("x=5; echo $((x--)); echo $x")
        bash_compare.assert_shells_match("x=5; echo $((--x)); echo $x")
    
    def test_arithmetic_ternary(self):
        """Test ternary operator."""
        bash_compare.assert_shells_match("echo $((5 > 3 ? 10 : 20))")
        bash_compare.assert_shells_match("echo $((5 < 3 ? 10 : 20))")
        bash_compare.assert_shells_match("x=1; echo $((x ? 100 : 200))")
    
    def test_arithmetic_bitwise(self):
        """Test bitwise operators."""
        bash_compare.assert_shells_match("echo $((5 & 3))")
        bash_compare.assert_shells_match("echo $((5 | 3))")
        bash_compare.assert_shells_match("echo $((5 ^ 3))")
        bash_compare.assert_shells_match("echo $((~5))")
        bash_compare.assert_shells_match("echo $((5 << 2))")
        bash_compare.assert_shells_match("echo $((20 >> 2))")
    
    def test_arithmetic_command_syntax(self):
        """Test arithmetic command (( )) syntax."""
        bash_compare.assert_shells_match("((x = 5)); echo $x")
        bash_compare.assert_shells_match("x=0; ((x++)); echo $x")
        bash_compare.assert_shells_match("((5 > 3)) && echo true || echo false")
        bash_compare.assert_shells_match("((5 < 3)) && echo true || echo false")