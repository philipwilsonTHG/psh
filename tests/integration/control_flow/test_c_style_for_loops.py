"""
C-style for loop tests.

Comprehensive test suite for C-style for loops: for ((init; condition; update))
Tests cover initialization, condition evaluation, update expressions, and edge cases.
"""

import pytest
import tempfile
import os


class TestCStyleForBasic:
    """Basic C-style for loop functionality tests."""
    
    def test_basic_counter(self, isolated_shell_with_temp_dir):
        """Test basic C-style for loop with counter."""
        shell = isolated_shell_with_temp_dir
        result = shell.run_command('for ((i=0; i<3; i++)); do echo $i; done > result.txt')
        assert result == 0
        
        # Verify the counter worked correctly
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n"
    
    def test_increment_by_two(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with increment by 2."""
        shell = isolated_shell_with_temp_dir
        shell.run_command('for ((i=0; i<10; i+=2)); do echo $i; done > result.txt')
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n2\n4\n6\n8\n"
    
    def test_decrement(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with decrement."""
        shell = isolated_shell_with_temp_dir
        shell.run_command('for ((i=5; i>0; i--)); do echo $i; done > result.txt')
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "5\n4\n3\n2\n1\n"
    
    def test_multiplication_update(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with multiplication in update."""
        shell = isolated_shell_with_temp_dir
        shell.run_command('for ((i=1; i<=100; i*=2)); do echo $i; done > result.txt')
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "1\n2\n4\n8\n16\n32\n64\n"


class TestCStyleForEmpty:
    """Test C-style for loops with empty sections."""
    
    def test_empty_init(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with empty initialization."""
        shell = isolated_shell_with_temp_dir
        shell.run_command('i=0; for ((; i<3; i++)); do echo $i; done > result.txt')
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n"
    
    def test_empty_condition_with_break(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with empty condition (infinite loop with break)."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; ; i++)); do 
            echo $i >> result.txt
            if ((i >= 3)); then break; fi
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n3\n"
    
    def test_empty_update(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with empty update."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; i<3; )); do 
            echo $i >> result.txt
            ((i++))
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n"
    
    def test_all_empty_sections(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with all sections empty."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        i=0
        for ((;;)); do 
            echo $i >> result.txt
            ((i++))
            if ((i >= 3)); then break; fi
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n"


class TestCStyleForMultipleVariables:
    """Test C-style for loops with multiple variables."""
    
    def test_multiple_variables(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with multiple variables."""
        shell = isolated_shell_with_temp_dir
        shell.run_command('for ((i=0, j=10; i<5; i++, j--)); do echo "$i $j"; done > result.txt')
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0 10\n1 9\n2 8\n3 7\n4 6\n"
    
    def test_with_existing_variables(self, isolated_shell_with_temp_dir):
        """Test C-style for loop using existing variables."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        start=5
        end=8
        for ((i=start; i<=end; i++)); do 
            echo $i >> result.txt
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "5\n6\n7\n8\n"


class TestCStyleForNested:
    """Test nested C-style for loops."""
    
    def test_nested_c_style_for(self, isolated_shell_with_temp_dir):
        """Test nested C-style for loops."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; i<3; i++)); do 
            for ((j=0; j<2; j++)); do 
                echo "$i,$j" >> result.txt
            done
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0,0\n0,1\n1,0\n1,1\n2,0\n2,1\n"
    
    def test_c_style_mixed_with_regular_for(self, isolated_shell_with_temp_dir):
        """Test C-style for loop nested with regular for loop."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=1; i<=2; i++)); do
            for item in a b; do
                echo "$i-$item" >> result.txt
            done
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "1-a\n1-b\n2-a\n2-b\n"


class TestCStyleForControlFlow:
    """Test break and continue in C-style for loops."""
    
    def test_break_in_c_style_for(self, isolated_shell_with_temp_dir):
        """Test break statement in C-style for loop."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; i<10; i++)); do 
            if ((i == 5)); then break; fi
            echo $i >> result.txt
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n3\n4\n"
    
    def test_continue_in_c_style_for(self, isolated_shell_with_temp_dir):
        """Test continue statement in C-style for loop."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; i<5; i++)); do 
            if ((i == 2)); then continue; fi
            echo $i >> result.txt
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n3\n4\n"
    
    def test_nested_break_continue(self, isolated_shell_with_temp_dir):
        """Test break and continue in nested C-style loops."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; i<3; i++)); do
            for ((j=0; j<4; j++)); do
                if ((j == 2)); then continue; fi
                if ((j == 3)); then break; fi
                echo "$i,$j" >> result.txt
            done
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'result.txt')) as f:
            content = f.read()
            assert content == "0,0\n0,1\n1,0\n1,1\n2,0\n2,1\n"


class TestCStyleForIORedirection:
    """Test C-style for loops with I/O redirection."""
    
    def test_c_style_with_output_redirection(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with output redirection."""
        shell = isolated_shell_with_temp_dir
        result = shell.run_command('for ((i=0; i<3; i++)); do echo $i; done > numbers.txt')
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'numbers.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n"
    
    def test_c_style_with_append_redirection(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with append redirection."""
        shell = isolated_shell_with_temp_dir
        shell.run_command('echo "start" > log.txt')
        shell.run_command('for ((i=1; i<=2; i++)); do echo "line $i"; done >> log.txt')
        
        with open(os.path.join(shell.state.variables['PWD'], 'log.txt')) as f:
            content = f.read()
            assert content == "start\nline 1\nline 2\n"
    
    def test_c_style_with_input_redirection(self, isolated_shell_with_temp_dir):
        """Test C-style for loop reading from file."""
        shell = isolated_shell_with_temp_dir
        
        # Create input file
        shell.run_command('echo -e "apple\\nbanana\\ncherry" > fruits.txt')
        
        # Use for loop to process file line by line
        cmd = '''
        counter=0
        while read line; do
            ((counter++))
            for ((i=1; i<=counter; i++)); do
                echo "$i: $line" >> processed.txt
            done
        done < fruits.txt
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'processed.txt')) as f:
            content = f.read()
            assert content == "1: apple\n1: banana\n2: banana\n1: cherry\n2: cherry\n3: cherry\n"


class TestCStyleForFunctions:
    """Test C-style for loops in functions."""
    
    def test_c_style_in_function(self, isolated_shell_with_temp_dir):
        """Test C-style for loop inside a function."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        count_to() {
            local n=$1
            for ((i=1; i<=n; i++)); do
                echo $i >> count_result.txt
            done
        }
        count_to 4
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'count_result.txt')) as f:
            content = f.read()
            assert content == "1\n2\n3\n4\n"
    
    def test_c_style_with_local_variables(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with local variables in function."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        test_locals() {
            local start=$1
            local end=$2
            for ((i=start; i<=end; i++)); do
                echo "local: $i" >> locals_result.txt
            done
        }
        test_locals 2 5
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'locals_result.txt')) as f:
            content = f.read()
            assert content == "local: 2\nlocal: 3\nlocal: 4\nlocal: 5\n"


class TestCStyleForArithmetic:
    """Test C-style for loops with complex arithmetic."""
    
    def test_c_style_with_complex_arithmetic(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with complex arithmetic expressions."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        x=2
        for ((i=x*2; i<x*5; i+=x)); do
            echo $i >> arithmetic_result.txt
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'arithmetic_result.txt')) as f:
            content = f.read()
            assert content == "4\n6\n8\n"
    
    def test_modulo_operations(self, isolated_shell_with_temp_dir):
        """Test C-style for loop with modulo operations."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=1; i<=10; i++)); do
            if ((i % 2 == 0)); then
                echo $i >> evens.txt
            fi
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'evens.txt')) as f:
            content = f.read()
            assert content == "2\n4\n6\n8\n10\n"


class TestCStyleForVariableScope:
    """Test variable scope and preservation in C-style for loops."""
    
    def test_variable_preservation_after_loop(self, isolated_shell_with_temp_dir):
        """Test that loop variable is preserved after loop."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; i<3; i++)); do
            :  # No-op command
        done
        echo "final value: $i" > final_result.txt
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'final_result.txt')) as f:
            content = f.read()
            assert content == "final value: 3\n"
    
    def test_variable_scope_in_subshell(self, isolated_shell_with_temp_dir):
        """Test C-style for loop variable scope in subshells."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        i=100
        (
            for ((i=0; i<3; i++)); do
                echo "subshell: $i" >> subshell_result.txt
            done
            echo "subshell final: $i" >> subshell_result.txt
        )
        echo "parent: $i" >> subshell_result.txt
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'subshell_result.txt')) as f:
            content = f.read()
            lines = content.strip().split('\n')
            assert "subshell: 0" in lines
            assert "subshell: 1" in lines
            assert "subshell: 2" in lines
            assert "subshell final: 3" in lines
            assert "parent: 100" in lines


class TestCStyleForComparators:
    """Test various comparison operators in C-style for loops."""
    
    def test_comparison_operators(self, isolated_shell_with_temp_dir):
        """Test various comparison operators in condition."""
        shell = isolated_shell_with_temp_dir
        
        # Less than or equal
        shell.run_command('for ((i=1; i<=3; i++)); do echo $i; done > le_result.txt')
        with open(os.path.join(shell.state.variables['PWD'], 'le_result.txt')) as f:
            assert f.read() == "1\n2\n3\n"
        
        # Greater than
        shell.run_command('for ((i=3; i>0; i--)); do echo $i; done > gt_result.txt')
        with open(os.path.join(shell.state.variables['PWD'], 'gt_result.txt')) as f:
            assert f.read() == "3\n2\n1\n"
        
        # Not equal
        shell.run_command('for ((i=0; i!=3; i++)); do echo $i; done > ne_result.txt')
        with open(os.path.join(shell.state.variables['PWD'], 'ne_result.txt')) as f:
            assert f.read() == "0\n1\n2\n"
        
        # Greater than or equal
        shell.run_command('for ((i=5; i>=3; i--)); do echo $i; done > ge_result.txt')
        with open(os.path.join(shell.state.variables['PWD'], 'ge_result.txt')) as f:
            assert f.read() == "5\n4\n3\n"


class TestCStyleForSyntaxVariations:
    """Test syntax variations and edge cases."""
    
    def test_c_style_without_do_keyword(self, isolated_shell_with_temp_dir):
        """Test C-style for loop without optional 'do' keyword."""
        shell = isolated_shell_with_temp_dir
        result = shell.run_command('for ((i=0; i<3; i++)) echo $i >> no_do_result.txt; done')
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'no_do_result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n"
    
    def test_whitespace_handling(self, isolated_shell_with_temp_dir):
        """Test handling of various whitespace patterns."""
        shell = isolated_shell_with_temp_dir
        
        # Test with extra spaces
        result = shell.run_command('for (( i = 0 ; i < 3 ; i++ )); do echo $i; done > space_result.txt')
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'space_result.txt')) as f:
            content = f.read()
            assert content == "0\n1\n2\n"
    
    def test_complex_expressions_in_sections(self, isolated_shell_with_temp_dir):
        """Test complex expressions in all three sections."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        base=2
        for ((i=base*base; i<(base+3)*base; i+=(base/2))); do
            echo $i >> complex_result.txt
        done
        '''
        result = shell.run_command(cmd)
        assert result == 0
        
        with open(os.path.join(shell.state.variables['PWD'], 'complex_result.txt')) as f:
            content = f.read()
            # base=2: init=4, condition=i<10, increment=1
            assert content == "4\n5\n6\n7\n8\n9\n"


class TestCStyleForErrorCases:
    """Test error handling and edge cases."""
    
    def test_division_by_zero_handling(self, isolated_shell_with_temp_dir):
        """Test arithmetic error handling in loop expressions."""
        shell = isolated_shell_with_temp_dir
        
        # Test division by zero in condition - should handle gracefully
        cmd = '''
        for ((i=0; i<5; i++)); do
            if ((i == 2)); then
                # This should not cause the loop to crash
                echo "before division" >> div_test.txt
                ((x = 5 / 0)) || echo "division error handled" >> div_test.txt
                echo "after division" >> div_test.txt
            else
                echo $i >> div_test.txt
            fi
        done
        '''
        result = shell.run_command(cmd)
        # Should complete successfully even with division error
        
        with open(os.path.join(shell.state.variables['PWD'], 'div_test.txt')) as f:
            content = f.read()
            assert "0\n" in content
            assert "1\n" in content
            # Should have error handling for division by zero
            assert "before division" in content
    
    def test_variable_unset_in_condition(self, isolated_shell_with_temp_dir):
        """Test handling of unset variables in loop condition."""
        shell = isolated_shell_with_temp_dir
        cmd = '''
        for ((i=0; i<unset_var; i++)); do
            echo $i >> unset_test.txt
        done 2>/dev/null || echo "handled unset variable" >> unset_test.txt
        '''
        result = shell.run_command(cmd)
        
        # Should handle unset variables gracefully
        # Unset variables typically evaluate to 0 in arithmetic context
        with open(os.path.join(shell.state.variables['PWD'], 'unset_test.txt')) as f:
            content = f.read()
            # Loop should not execute since i<0 is false from start
            assert content == "" or "handled" in content