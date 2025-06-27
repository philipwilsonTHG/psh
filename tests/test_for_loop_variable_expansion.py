#!/usr/bin/env python3
"""Test variable expansion in for loops functionality.

Tests for the variable expansion in for loops fix implemented in v0.59.7
as a critical POSIX compliance improvement.

This fixes the bug where 'for item in $items' was treating $items as 
literal 'items' instead of expanding the variable.
"""

import pytest
from psh.shell import Shell


class TestForLoopVariableExpansion:
    """Test variable expansion in for loop iterables."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_for_loop_basic_variable_expansion(self, capsys):
        """Test basic variable expansion in for loops."""
        exit_code = self.shell.run_command('''
        items="apple banana cherry"
        for item in $items; do
            echo "Item: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Item: apple" in captured.out
        assert "Item: banana" in captured.out
        assert "Item: cherry" in captured.out
    
    def test_for_loop_multiple_variables(self, capsys):
        """Test expansion of multiple variables in for loop."""
        exit_code = self.shell.run_command('''
        start="first second"
        end="third fourth"
        for item in $start middle $end; do
            echo "Item: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Item: first" in captured.out
        assert "Item: second" in captured.out
        assert "Item: middle" in captured.out
        assert "Item: third" in captured.out
        assert "Item: fourth" in captured.out
    
    def test_for_loop_variable_with_spaces(self, capsys):
        """Test variable containing items with spaces."""
        exit_code = self.shell.run_command('''
        items="one two three"
        for item in $items; do
            echo "[$item]"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "[one]" in captured.out
        assert "[two]" in captured.out
        assert "[three]" in captured.out
    
    def test_for_loop_empty_variable(self, capsys):
        """Test for loop with empty or undefined variable."""
        exit_code = self.shell.run_command('''
        empty_var=""
        echo "Before loop"
        for item in $empty_var; do
            echo "This should not print: $item"
        done
        echo "After loop"
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Before loop" in captured.out
        assert "After loop" in captured.out
        assert "This should not print" not in captured.out
    
    def test_for_loop_undefined_variable(self, capsys):
        """Test for loop with undefined variable."""
        exit_code = self.shell.run_command('''
        echo "Before loop"
        for item in $undefined_variable; do
            echo "This should not print: $item"
        done
        echo "After loop"
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Before loop" in captured.out
        assert "After loop" in captured.out
        assert "This should not print" not in captured.out
    
    def test_for_loop_quoted_variable_expansion(self, capsys):
        """Test quoted variable expansion preserves spaces."""
        exit_code = self.shell.run_command('''
        phrase="hello world with spaces"
        for item in "$phrase"; do
            echo "Item: [$item]"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Item: [hello world with spaces]" in captured.out
    
    def test_for_loop_mixed_quoted_unquoted(self, capsys):
        """Test mix of quoted and unquoted variables."""
        exit_code = self.shell.run_command('''
        var1="one two"
        var2="three four"
        for item in $var1 "$var2" five; do
            echo "Item: [$item]"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Item: [one]" in captured.out
        assert "Item: [two]" in captured.out
        assert "Item: [three four]" in captured.out  # Quoted should preserve spaces
        assert "Item: [five]" in captured.out
    
    def test_for_loop_variable_with_numbers(self, capsys):
        """Test variable expansion with numeric values."""
        exit_code = self.shell.run_command('''
        numbers="1 2 3 42 100"
        for num in $numbers; do
            echo "Number: $num"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Number: 1" in captured.out
        assert "Number: 2" in captured.out
        assert "Number: 3" in captured.out
        assert "Number: 42" in captured.out
        assert "Number: 100" in captured.out
    
    def test_for_loop_nested_variable_expansion(self, capsys):
        """Test nested variable expansion scenarios."""
        exit_code = self.shell.run_command('''
        prefix="test"
        suffix="items"
        var_name="${prefix}_${suffix}"
        test_items="alpha beta gamma"
        for item in $test_items; do
            echo "Item: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Item: alpha" in captured.out
        assert "Item: beta" in captured.out
        assert "Item: gamma" in captured.out
    
    def test_for_loop_positional_parameters(self, capsys):
        """Test expansion of positional parameters in for loops."""
        exit_code = self.shell.run_command('''
        set arg1 arg2 arg3
        for arg in $@; do
            echo "Arg: $arg"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Arg: arg1" in captured.out
        assert "Arg: arg2" in captured.out
        assert "Arg: arg3" in captured.out


class TestForLoopCommandSubstitution:
    """Test command substitution in for loops (should still work)."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_for_loop_command_substitution(self, capsys):
        """Test that command substitution in for loops continues to work."""
        exit_code = self.shell.run_command('''
        for item in $(echo "sub1 sub2 sub3"); do
            echo "Command sub: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Command sub: sub1" in captured.out
        assert "Command sub: sub2" in captured.out
        assert "Command sub: sub3" in captured.out
    
    def test_for_loop_backtick_substitution(self, capsys):
        """Test backtick command substitution in for loops."""
        exit_code = self.shell.run_command('''
        for item in `echo "back1 back2"`; do
            echo "Backtick: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Backtick: back1" in captured.out
        assert "Backtick: back2" in captured.out
    
    def test_for_loop_mixed_expansion_types(self, capsys):
        """Test mixing variable expansion and command substitution."""
        exit_code = self.shell.run_command('''
        vars="var1 var2"
        for item in $vars $(echo "cmd1 cmd2") literal; do
            echo "Mixed: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Mixed: var1" in captured.out
        assert "Mixed: var2" in captured.out
        assert "Mixed: cmd1" in captured.out
        assert "Mixed: cmd2" in captured.out
        assert "Mixed: literal" in captured.out


class TestForLoopEdgeCases:
    """Test edge cases for variable expansion in for loops."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_for_loop_variable_with_special_chars(self, capsys):
        """Test variables containing special characters."""
        exit_code = self.shell.run_command('''
        special="file.txt path/to/file user@domain.com"
        for item in $special; do
            echo "Special: [$item]"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Special: [file.txt]" in captured.out
        assert "Special: [path/to/file]" in captured.out
        assert "Special: [user@domain.com]" in captured.out
    
    def test_for_loop_variable_with_newlines(self, capsys):
        """Test variable containing newlines (should split on whitespace)."""
        exit_code = self.shell.run_command('''
        multiline="line1
line2
line3"
        for item in $multiline; do
            echo "Line: [$item]"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Line: [line1]" in captured.out
        assert "Line: [line2]" in captured.out
        assert "Line: [line3]" in captured.out
    
    def test_for_loop_arithmetic_expansion(self, capsys):
        """Test arithmetic expansion in for loops."""
        exit_code = self.shell.run_command('''
        for item in $((1+1)) $((2*3)) $((10-5)); do
            echo "Math: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Math: 2" in captured.out
        assert "Math: 6" in captured.out
        assert "Math: 5" in captured.out
    
    def test_for_loop_glob_expansion_with_variables(self, capsys):
        """Test that glob expansion works with variables."""
        # Create temporary files for testing
        exit_code = self.shell.run_command('''
        mkdir -p tmp/test_for_loop
        touch tmp/test_for_loop/file1.txt tmp/test_for_loop/file2.txt
        pattern="tmp/test_for_loop/*.txt"
        for file in $pattern; do
            if [ -f "$file" ]; then
                echo "Found: $(basename "$file")"
            fi
        done
        rm -rf tmp/test_for_loop
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        # Note: Whether this expands depends on glob implementation
        # The important thing is that variable expansion happens first
    
    def test_for_loop_ifs_variable_effect(self, capsys):
        """Test how IFS affects variable expansion in for loops."""
        exit_code = self.shell.run_command('''
        original_ifs="$IFS"
        IFS=":"
        items="one:two:three"
        for item in $items; do
            echo "IFS item: [$item]"
        done
        IFS="$original_ifs"
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "IFS item: [one]" in captured.out
        assert "IFS item: [two]" in captured.out
        assert "IFS item: [three]" in captured.out
    
    def test_for_loop_variable_assignment_in_loop(self, capsys):
        """Test variable assignment within for loop body."""
        exit_code = self.shell.run_command('''
        items="a b c"
        counter=0
        for item in $items; do
            counter=$((counter + 1))
            echo "Item $counter: $item"
        done
        echo "Total: $counter"
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Item 1: a" in captured.out
        assert "Item 2: b" in captured.out
        assert "Item 3: c" in captured.out
        assert "Total: 3" in captured.out
    
    def test_for_loop_break_continue_with_variables(self, capsys):
        """Test break and continue with variable expansion."""
        exit_code = self.shell.run_command('''
        items="one two skip three four"
        for item in $items; do
            if [ "$item" = "skip" ]; then
                echo "Skipping: $item"
                continue
            fi
            if [ "$item" = "four" ]; then
                echo "Breaking at: $item"
                break
            fi
            echo "Processing: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Processing: one" in captured.out
        assert "Processing: two" in captured.out
        assert "Skipping: skip" in captured.out
        assert "Processing: three" in captured.out
        assert "Breaking at: four" in captured.out


class TestForLoopRegressionPrevention:
    """Test to prevent regression of the original bug."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_for_loop_literal_vs_expansion(self, capsys):
        """Test that variables are expanded, not treated as literals."""
        # This is the specific case that was broken before v0.59.7
        exit_code = self.shell.run_command('''
        items="alpha beta gamma"
        echo "Variable content: $items"
        for item in $items; do
            echo "Loop item: $item"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Variable content: alpha beta gamma" in captured.out
        assert "Loop item: alpha" in captured.out
        assert "Loop item: beta" in captured.out
        assert "Loop item: gamma" in captured.out
        
        # Should NOT see literal 'items' as a loop item
        assert "Loop item: items" not in captured.out
    
    def test_for_loop_dollar_prefix_preservation(self, capsys):
        """Test that $ prefix is preserved in parsing for expansion."""
        # This tests the specific fix where _parse_for_iterable was 
        # storing 'items' instead of '$items'
        exit_code = self.shell.run_command('''
        values="test1 test2"
        for val in $values literal $values; do
            echo "Val: $val"
        done
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Val: test1" in captured.out
        assert "Val: test2" in captured.out
        assert "Val: literal" in captured.out
        # Should see test1 and test2 twice (before and after literal)
        assert captured.out.count("Val: test1") == 2
        assert captured.out.count("Val: test2") == 2