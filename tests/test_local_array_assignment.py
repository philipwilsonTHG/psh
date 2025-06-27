#!/usr/bin/env python3
"""Test local builtin array assignment functionality.

Tests for the local builtin's ability to handle array assignment syntax
like: local arr=("a" "b" "c")

This was implemented in v0.59.9 to fix POSIX compliance issues where
the local builtin was treating array syntax as literal strings.
"""

import pytest
from psh.shell import Shell


class TestLocalArrayAssignment:
    """Test local builtin array assignment capabilities."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_local_array_basic_assignment(self, capsys):
        """Test basic local array assignment with parentheses syntax."""
        # Define a function that creates a local array
        exit_code = self.shell.run_command('''
        test_func() {
            local arr=("apple" "banana" "cherry")
            echo "${arr[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "apple banana cherry" in captured.out
    
    def test_local_array_vs_global_isolation(self, capsys):
        """Test that local arrays don't affect global variables."""
        exit_code = self.shell.run_command('''
        global_arr=("global1" "global2")
        test_func() {
            local global_arr=("local1" "local2" "local3")
            echo "In function: ${global_arr[@]}"
        }
        echo "Before: ${global_arr[@]}"
        test_func
        echo "After: ${global_arr[@]}"
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Before: global1 global2" in captured.out
        assert "In function: local1 local2 local3" in captured.out
        assert "After: global1 global2" in captured.out
    
    def test_local_array_with_variable_expansion(self, capsys):
        """Test local array assignment with variable expansion in elements."""
        exit_code = self.shell.run_command('''
        prefix="item"
        suffix="value"
        test_func() {
            local arr=("${prefix}_1" "${prefix}_2" "literal" "$suffix")
            echo "${arr[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "item_1 item_2 literal value" in captured.out
    
    def test_local_array_with_quoted_elements(self, capsys):
        """Test local array assignment with quoted elements containing spaces."""
        exit_code = self.shell.run_command('''
        test_func() {
            local arr=("hello world" "with spaces" "normal")
            echo "Count: ${#arr[@]}"
            echo "First: ${arr[0]}"
            echo "Second: ${arr[1]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Count: 3" in captured.out
        assert "First: hello world" in captured.out
        assert "Second: with spaces" in captured.out
    
    def test_local_array_empty_assignment(self, capsys):
        """Test local array assignment with empty parentheses."""
        exit_code = self.shell.run_command('''
        test_func() {
            local arr=()
            echo "Length: ${#arr[@]}"
            echo "Elements: ${arr[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Length: 0" in captured.out
        assert "Elements:" in captured.out
    
    def test_local_array_single_element(self, capsys):
        """Test local array assignment with single element."""
        exit_code = self.shell.run_command('''
        test_func() {
            local arr=("single")
            echo "Length: ${#arr[@]}"
            echo "Element: ${arr[0]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Length: 1" in captured.out
        assert "Element: single" in captured.out
    
    def test_local_array_numeric_elements(self, capsys):
        """Test local array assignment with numeric elements."""
        exit_code = self.shell.run_command('''
        test_func() {
            local numbers=(1 2 3 42 100)
            echo "${numbers[@]}"
            echo "Third: ${numbers[2]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "1 2 3 42 100" in captured.out
        assert "Third: 3" in captured.out
    
    def test_local_array_mixed_quotes(self, capsys):
        """Test local array with mixed quoted and unquoted elements."""
        exit_code = self.shell.run_command('''
        test_func() {
            local mixed=(unquoted "double quoted" 'single quoted' bare)
            echo "Count: ${#mixed[@]}"
            echo "All: ${mixed[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Count: 4" in captured.out
        assert "All: unquoted double quoted single quoted bare" in captured.out
    
    def test_local_array_vs_regular_assignment(self, capsys):
        """Test that regular local assignments still work alongside array assignments."""
        exit_code = self.shell.run_command('''
        test_func() {
            local regular_var="simple value"
            local arr=("array" "elements")
            echo "Regular: $regular_var"
            echo "Array: ${arr[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Regular: simple value" in captured.out
        assert "Array: array elements" in captured.out
    
    def test_local_array_multiple_declarations(self, capsys):
        """Test multiple local array declarations in same function."""
        exit_code = self.shell.run_command('''
        test_func() {
            local arr1=("first" "array")
            local arr2=("second" "array" "more")
            echo "Arr1: ${arr1[@]}"
            echo "Arr2: ${arr2[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Arr1: first array" in captured.out
        assert "Arr2: second array more" in captured.out
    
    def test_local_array_indices_access(self, capsys):
        """Test accessing array indices with local arrays."""
        exit_code = self.shell.run_command('''
        test_func() {
            local colors=("red" "green" "blue" "yellow")
            echo "Indices: ${!colors[@]}"
            echo "Length: ${#colors[@]}"
            echo "Second: ${colors[1]}"
            echo "Last: ${colors[3]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Indices: 0 1 2 3" in captured.out
        assert "Length: 4" in captured.out
        assert "Second: green" in captured.out
        assert "Last: yellow" in captured.out
    
    def test_local_array_modification_in_function(self, capsys):
        """Test modifying local array elements within function."""
        exit_code = self.shell.run_command('''
        test_func() {
            local fruits=("apple" "banana" "cherry")
            echo "Original: ${fruits[@]}"
            fruits[1]="orange"
            fruits[3]="grape"
            echo "Modified: ${fruits[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Original: apple banana cherry" in captured.out
        assert "Modified: apple orange cherry grape" in captured.out
    
    def test_local_array_error_outside_function(self, capsys):
        """Test that local arrays fail outside functions (same as regular local)."""
        # Capture stderr for error output
        exit_code = self.shell.run_command('local arr=("should" "fail")')
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "can only be used in a function" in captured.err
    
    def test_local_array_inheritance_to_nested_functions(self, capsys):
        """Test that local arrays are visible to nested function calls."""
        exit_code = self.shell.run_command('''
        inner_func() {
            echo "Inner sees: ${outer_arr[@]}"
        }
        outer_func() {
            local outer_arr=("outer1" "outer2")
            inner_func
        }
        outer_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Inner sees: outer1 outer2" in captured.out
    
    def test_local_array_with_special_characters(self, capsys):
        """Test local array with special characters in elements."""
        exit_code = self.shell.run_command('''
        test_func() {
            local special=("hello!" "@#$%" "path/to/file" "var=value")
            echo "${special[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "hello! @#$% path/to/file var=value" in captured.out
    
    def test_local_array_display_format(self, capsys):
        """Test that local arrays display in proper format (not with parentheses)."""
        # This is the specific bug that was fixed in v0.59.9
        exit_code = self.shell.run_command('''
        test_func() {
            local test_arr=("func1" "func2" "func3")
            echo "Local array: ${test_arr[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        # Should show "func1 func2 func3" not "(func1 func2 func3)"
        assert "Local array: func1 func2 func3" in captured.out
        assert "(func1 func2 func3)" not in captured.out


class TestLocalArrayEdgeCases:
    """Test edge cases and error conditions for local array assignment."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_local_array_malformed_syntax(self, capsys):
        """Test local array with malformed syntax falls back gracefully."""
        exit_code = self.shell.run_command('''
        test_func() {
            # Missing closing parenthesis - should be treated as literal string
            local bad_arr="(unclosed array"
            echo "Bad: $bad_arr"
        }
        test_func
        ''')
        
        # Should still work, treating as literal string assignment
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Bad: (unclosed array" in captured.out
    
    def test_local_array_with_command_substitution(self, capsys):
        """Test local array with command substitution in elements."""
        exit_code = self.shell.run_command('''
        test_func() {
            local cmd_arr=("literal" "$(echo substituted)" "another")
            echo "${cmd_arr[@]}"
        }
        test_func
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "literal substituted another" in captured.out
    
    def test_local_array_recursive_function(self, capsys):
        """Test local arrays in recursive functions."""
        exit_code = self.shell.run_command('''
        recursive_func() {
            local level=$1
            local arr=("level_$level" "data")
            echo "Level $level: ${arr[@]}"
            if [ $level -lt 3 ]; then
                recursive_func $((level + 1))
            fi
        }
        recursive_func 1
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Level 1: level_1 data" in captured.out
        assert "Level 2: level_2 data" in captured.out
        assert "Level 3: level_3 data" in captured.out