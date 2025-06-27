"""Core test suite for array expansion and printf builtin functionality."""

import pytest
from unittest.mock import patch
from io import StringIO
from psh.shell import Shell


class TestArrayExpansionCore:
    """Test core array expansion and printf operations that are known to work."""
    
    @pytest.fixture
    def shell(self):
        """Create a shell instance for testing."""
        return Shell()
    
    # Core array expansion tests - these should all pass
    
    def test_array_expansion_in_double_quotes(self, shell, capsys):
        """Test that ${arr[@]} in double quotes expands to multiple arguments."""
        shell.run_command('arr=(one two three)')
        exit_code = shell.run_command('printf "%s\\n" "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "one\ntwo\nthree\n"
    
    def test_array_expansion_without_quotes(self, shell, capsys):
        """Test that ${arr[@]} without quotes expands to multiple arguments."""
        shell.run_command('arr=(alpha beta gamma)')
        exit_code = shell.run_command('printf "%s\\n" ${arr[@]}')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "alpha\nbeta\ngamma\n"
    
    def test_array_expansion_mixed_with_literals(self, shell, capsys):
        """Test array expansion mixed with literal arguments."""
        shell.run_command('arr=(middle)')
        exit_code = shell.run_command('printf "%s\\n" start "${arr[@]}" end')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "start\nmiddle\nend\n"
    
    def test_array_expansion_empty_array(self, shell, capsys):
        """Test array expansion with empty array."""
        shell.run_command('arr=()')
        exit_code = shell.run_command('printf "%s\\n" before "${arr[@]}" after')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "before\nafter\n"
    
    def test_array_expansion_single_element(self, shell, capsys):
        """Test array expansion with single element."""
        shell.run_command('arr=(solo)')
        exit_code = shell.run_command('printf "%s\\n" "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "solo\n"
    
    def test_array_expansion_quoted_elements(self, shell, capsys):
        """Test array expansion with quoted elements containing spaces."""
        shell.run_command('arr=("hello world" "foo bar" "test file")')
        exit_code = shell.run_command('printf "%s\\n" "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "hello world\nfoo bar\ntest file\n"
    
    def test_array_expansion_special_characters(self, shell, capsys):
        """Test array expansion with special characters."""
        shell.run_command('arr=("item!" "item@" "item#" "item$")')
        exit_code = shell.run_command('printf "%s\\n" "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "item!\nitem@\nitem#\nitem$\n"
    
    def test_array_expansion_with_variables(self, shell, capsys):
        """Test array expansion with variables in elements."""
        shell.run_command('prefix="test"')
        shell.run_command('arr=("${prefix}1" "${prefix}2" "${prefix}3")')
        exit_code = shell.run_command('printf "%s\\n" "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "test1\ntest2\ntest3\n"
    
    # Array sorting functionality - the critical feature
    
    def test_array_sort_and_reassign_complete(self, shell, capsys):
        """Test the complete array sorting pipeline that works in conformance tests."""
        shell.run_command('unsorted=("zebra" "apple" "banana" "cherry" "date")')
        # Complete sorting pipeline as used in conformance tests
        exit_code = shell.run_command('sorted_string=$(printf "%s\\n" "${unsorted[@]}" | sort | tr "\\n" " "); read -a sorted <<< "$sorted_string"; echo "Sorted: ${sorted[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Sorted: apple banana cherry date zebra" in captured.out
    
    def test_array_sort_simple_case(self, shell, capsys):
        """Test a simple case of array sorting."""
        shell.run_command('arr=("c" "a" "b")')
        exit_code = shell.run_command('sorted_string=$(printf "%s\\n" "${arr[@]}" | sort | tr "\\n" " "); read -a sorted <<< "$sorted_string"; echo "${sorted[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "a b c" in captured.out
    
    def test_array_sort_with_duplicates(self, shell, capsys):
        """Test sorting array with duplicate elements."""
        shell.run_command('arr=(banana apple banana cherry apple)')
        exit_code = shell.run_command('sorted_string=$(printf "%s\\n" "${arr[@]}" | sort | tr "\\n" " "); read -a sorted <<< "$sorted_string"; echo "${sorted[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "apple apple banana banana cherry" in captured.out
    
    # Array expansion in different contexts
    
    def test_array_expansion_in_for_loop(self, shell, capsys):
        """Test array expansion in for loop context."""
        shell.run_command('arr=(alpha beta gamma)')
        exit_code = shell.run_command('for item in "${arr[@]}"; do echo "Item: $item"; done')
        assert exit_code == 0
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        assert lines == ['Item: alpha', 'Item: beta', 'Item: gamma']
    
    def test_printf_vs_echo_with_arrays(self, shell, capsys):
        """Test printf vs echo behavior with array expansion."""
        shell.run_command('arr=(one two three)')
        
        # Printf should handle each element separately  
        exit_code = shell.run_command('printf "%s\\n" "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        printf_output = captured.out
        
        # Echo should concatenate with spaces
        exit_code = shell.run_command('echo "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        echo_output = captured.out
        
        assert printf_output == "one\ntwo\nthree\n"
        assert echo_output == "one two three\n"
    
    # Test core printf functionality
    
    def test_printf_basic_functionality(self, shell, capsys):
        """Test basic printf functionality."""
        exit_code = shell.run_command('printf "%s\\n" hello world')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "hello\nworld\n"
    
    def test_printf_with_format_specifiers(self, shell, capsys):
        """Test printf with different format specifiers."""
        exit_code = shell.run_command('printf "%s: %d\\n" test 42')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "test: 42\n"
    
    def test_printf_with_arrays_vs_single_expansion(self, shell, capsys):
        """Test that printf correctly handles array expansion as multiple arguments."""
        shell.run_command('arr=(one two)')
        
        # Test the format that we know works (%s\n)
        exit_code = shell.run_command('printf "%s\\n" "${arr[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "one\ntwo\n"
        
        # Compare with single element access
        exit_code = shell.run_command('printf "%s\\n" "${arr[0]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "one\n"
    
    # Regression tests for the specific bugs that were fixed
    
    def test_regression_array_expansion_in_string_context(self, shell, capsys):
        """Regression test: ${arr[@]} in double quotes should expand to multiple arguments."""
        # This was the bug - array expansion in STRING context with quote_type="
        # was being treated as string expansion instead of array expansion
        shell.run_command('words=("hello" "world" "test")')
        exit_code = shell.run_command('printf "%s\\n" "${words[@]}"')
        assert exit_code == 0
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        assert len(lines) == 3
        assert lines == ['hello', 'world', 'test']
    
    def test_regression_printf_format_string_escaping(self, shell, capsys):
        """Regression test: printf should handle \\n format strings correctly."""
        # This was the bug - printf wasn't recognizing '%s\\n' as equivalent to '%s\n'
        exit_code = shell.run_command('printf "%s\\n" first second')
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == "first\nsecond\n"
    
    def test_comprehensive_array_sorting_pipeline(self, shell, capsys):
        """Test the complete array sorting pipeline as used in conformance tests."""
        # This tests the exact pattern that was failing before the fix
        shell.run_command('unsorted=("zebra" "apple" "banana" "cherry" "date")')
        shell.run_command('echo "Testing array sorting concepts:"')
        shell.run_command('echo "Unsorted: ${unsorted[@]}"')
        
        # Test the sorting pipeline
        shell.run_command('sorted_string=$(printf "%s\\n" "${unsorted[@]}" | sort | tr "\\n" " ")')
        shell.run_command('read -a sorted <<< "$sorted_string"')
        exit_code = shell.run_command('echo "Sorted: ${sorted[@]}"')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        
        # Verify the sorting worked
        assert "Testing array sorting concepts:" in captured.out
        assert "Unsorted: zebra apple banana cherry date" in captured.out
        assert "Sorted: apple banana cherry date zebra" in captured.out