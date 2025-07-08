"""
Integration tests for for loops.

Tests cover:
- Basic for loops with lists
- For loops with glob patterns
- For loops with command substitution
- C-style for loops
- Break and continue in for loops
"""

import pytest


class TestForLoops:
    """Test for loop functionality."""
    
    def test_basic_for_loop(self, shell, capsys):
        """Test basic for loop with list."""
        cmd = '''
        for item in one two three; do
            echo "item: $item"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "item: one" in captured.out
        assert "item: two" in captured.out
        assert "item: three" in captured.out
    
    def test_for_loop_with_variable(self, shell, capsys):
        """Test for loop iterating over variable."""
        cmd = '''
        LIST="apple banana cherry"
        for fruit in $LIST; do
            echo "fruit: $fruit"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "fruit: apple" in captured.out
        assert "fruit: banana" in captured.out
        assert "fruit: cherry" in captured.out
    
    def test_for_loop_with_glob(self, shell, capsys):
        """Test for loop with glob pattern."""
        cmd = '''
        touch file1.txt file2.txt file3.txt
        for f in *.txt; do
            echo "found: $f"
        done
        rm -f *.txt
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "found: file1.txt" in captured.out
        assert "found: file2.txt" in captured.out
        assert "found: file3.txt" in captured.out
    
    def test_for_loop_with_command_substitution(self, shell, capsys):
        """Test for loop with command substitution."""
        cmd = '''
        for word in $(echo "hello world test"); do
            echo "word: $word"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "word: hello" in captured.out
        assert "word: world" in captured.out
        assert "word: test" in captured.out
    
    def test_for_loop_with_break(self, shell, capsys):
        """Test for loop with break."""
        cmd = '''
        for i in 1 2 3 4 5; do
            if [ $i -eq 3 ]; then
                break
            fi
            echo "i: $i"
        done
        echo "after loop"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "i: 1" in captured.out
        assert "i: 2" in captured.out
        assert "i: 3" not in captured.out
        assert "i: 4" not in captured.out
        assert "after loop" in captured.out
    
    def test_for_loop_with_continue(self, shell, capsys):
        """Test for loop with continue."""
        cmd = '''
        for i in 1 2 3 4 5; do
            if [ $i -eq 3 ]; then
                continue
            fi
            echo "i: $i"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "i: 1" in captured.out
        assert "i: 2" in captured.out
        assert "i: 3" not in captured.out  # Skipped
        assert "i: 4" in captured.out
        assert "i: 5" in captured.out
    
    def test_nested_for_loops(self, shell, capsys):
        """Test nested for loops."""
        cmd = '''
        for i in A B; do
            for j in 1 2; do
                echo "$i$j"
            done
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "A1" in captured.out
        assert "A2" in captured.out
        assert "B1" in captured.out
        assert "B2" in captured.out
    
    @pytest.mark.xfail(reason="PSH may not support C-style for loops")
    def test_c_style_for_loop(self, shell, capsys):
        """Test C-style for loop."""
        cmd = '''
        for ((i=0; i<3; i++)); do
            echo "i: $i"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "i: 0" in captured.out
        assert "i: 1" in captured.out
        assert "i: 2" in captured.out
    
    def test_for_loop_no_list(self, shell, capsys):
        """Test for loop without list (uses positional parameters)."""
        cmd = '''
        set -- arg1 arg2 arg3
        for arg; do
            echo "arg: $arg"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "arg: arg1" in captured.out
        assert "arg: arg2" in captured.out
        assert "arg: arg3" in captured.out
    
    def test_for_loop_empty_list(self, shell, capsys):
        """Test for loop with empty list."""
        cmd = '''
        echo "before"
        for item in; do
            echo "should not print"
        done
        echo "after"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "before" in captured.out
        assert "after" in captured.out
        assert "should not print" not in captured.out
    
    def test_for_loop_with_quotes(self, shell, capsys):
        """Test for loop with quoted strings."""
        cmd = '''
        for item in "hello world" "foo bar" test; do
            echo "[$item]"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "[hello world]" in captured.out
        assert "[foo bar]" in captured.out
        assert "[test]" in captured.out
    
    def test_for_loop_with_array(self, shell, capsys):
        """Test for loop with array expansion."""
        cmd = '''
        arr=(red green blue)
        for color in "${arr[@]}"; do
            echo "color: $color"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "color: red" in captured.out
        assert "color: green" in captured.out
        assert "color: blue" in captured.out
    
    def test_for_loop_modifying_variable(self, shell, capsys):
        """Test for loop that modifies loop variable."""
        cmd = '''
        for i in 1 2 3; do
            echo "before: $i"
            i=99
            echo "after: $i"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        # Each iteration should reset i
        assert "before: 1" in captured.out
        assert "after: 99" in captured.out
        assert "before: 2" in captured.out
        assert "before: 3" in captured.out
    
    def test_for_loop_oneline(self, shell, capsys):
        """Test for loop on single line."""
        shell.run_command('for x in a b c; do echo $x; done')
        captured = capsys.readouterr()
        assert "a\nb\nc" in captured.out
    
    def test_for_loop_with_function(self, shell, capsys):
        """Test for loop calling function."""
        cmd = '''
        process() {
            echo "Processing: $1"
        }
        
        for item in file1 file2 file3; do
            process "$item"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "Processing: file1" in captured.out
        assert "Processing: file2" in captured.out
        assert "Processing: file3" in captured.out