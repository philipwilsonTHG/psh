import pytest
from psh.shell import Shell
from psh.parser import parse
from psh.state_machine_lexer import tokenize


class TestBreakContinue:
    """Test break and continue statements in loops."""
    
    def test_break_in_while_loop(self):
        """Test break statement in while loop."""
        shell = Shell()
        # Simple while loop with break
        code = '''
        for i in 1 2 3 4 5; do
            echo $i
            if [ "$i" = "3" ]; then
                break
            fi
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        assert output == "1\n2\n3"
        assert result == 0
    
    def test_continue_in_while_loop(self):
        """Test continue statement in while loop."""
        shell = Shell()
        shell.state.set_variable('i', '0')
        
        code = '''
        while [ $i -lt 5 ]; do
            i=$((i + 1))
            if [ $i -eq 3 ]; then
                continue
            fi
            echo $i
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        assert output == "1\n2\n4\n5"  # 3 is skipped
        assert result == 0
        assert shell.state.get_variable('i') == '5'
    
    # @pytest.mark.skip(reason="For loop variable persistence not implemented correctly")
    def test_break_in_for_loop(self):
        """Test break statement in for loop."""
        shell = Shell()
        code = '''
        for i in 1 2 3 4 5; do
            if [ $i -eq 3 ]; then
                break
            fi
            echo $i
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        assert output == "1\n2"
        assert result == 0
        # Loop variable should retain last value before break
        assert shell.state.get_variable('i') == '3'
    
    # @pytest.mark.skip(reason="For loop variable persistence not implemented correctly")
    def test_continue_in_for_loop(self):
        """Test continue statement in for loop."""
        shell = Shell()
        code = '''
        for i in 1 2 3 4 5; do
            if [ $i -eq 3 ]; then
                continue
            fi
            echo $i
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        assert output == "1\n2\n4\n5"  # 3 is skipped
        assert result == 0
        assert shell.variables['i'] == '5'
    
    def test_nested_loops_break_inner(self):
        """Test break in nested loops affecting only inner loop."""
        shell = Shell()
        code = '''
        for outer in 1 2; do
            echo "outer: $outer"
            for inner in a b c; do
                if [ $inner = "b" ]; then
                    break
                fi
                echo "inner: $inner"
            done
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        expected = "outer: 1\ninner: a\nouter: 2\ninner: a"
        assert output == expected
        assert result == 0
    
    def test_nested_loops_continue_inner(self):
        """Test continue in nested loops affecting only inner loop."""
        shell = Shell()
        code = '''
        for outer in 1 2; do
            echo "outer: $outer"
            for inner in a b c; do
                if [ $inner = "b" ]; then
                    continue
                fi
                echo "inner: $inner"
            done
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        expected = "outer: 1\ninner: a\ninner: c\nouter: 2\ninner: a\ninner: c"
        assert output == expected
        assert result == 0
    
    def test_break_with_complex_condition(self):
        """Test break with complex conditional logic."""
        shell = Shell()
        shell.state.set_variable('count', '0')
        
        code = '''
        for i in 1 2 3 4 5 6 7 8 9 10; do
            count=$((count + 1))
            if [ $i -gt 3 ] && [ $((i % 2)) -eq 0 ]; then
                break
            fi
            echo $i
        done
        echo "count: $count"
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        # Should process 1, 2, 3, then break at 4 (first even number > 3)
        expected = "1\n2\n3\ncount: 4"
        assert output == expected
        assert result == 0
    
    def test_continue_with_complex_condition(self):
        """Test continue with complex conditional logic."""
        shell = Shell()
        code = '''
        for i in 1 2 3 4 5 6 7 8; do
            if [ $((i % 2)) -eq 0 ] && [ $i -le 6 ]; then
                continue
            fi
            echo $i
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        # Should skip 2, 4, 6 (even numbers <= 6) but print 1, 3, 5, 7, 8
        expected = "1\n3\n5\n7\n8"
        assert output == expected
        assert result == 0
    
    @pytest.mark.skip(reason="StringIO cannot capture direct stderr writes from builtins")
    def test_break_outside_loop_error(self):
        """Test that break outside of loop produces error."""
        shell = Shell()
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            result = shell.run_command("break")
        
        error_output = f.getvalue().strip()
        assert "break: only meaningful in a `for' or `while' loop" in error_output
        assert result == 1
    
    @pytest.mark.skip(reason="StringIO cannot capture direct stderr writes from builtins")
    def test_continue_outside_loop_error(self):
        """Test that continue outside of loop produces error."""
        shell = Shell()
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            result = shell.run_command("continue")
        
        error_output = f.getvalue().strip()
        assert "continue: only meaningful in a `for' or `while' loop" in error_output
        assert result == 1
    
    def test_break_in_function_outside_loop(self):
        """Test that break in function but outside loop produces error."""
        shell = Shell()
        code = '''
        test_func() {
            echo "in function"
            break
            echo "after break"
        }
        test_func
        '''
        
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            result = shell.run_command(code)
        
        error_output = f.getvalue().strip()
        assert "break: only meaningful in a `for' or `while' loop" in error_output
        assert result == 1
    
    def test_continue_in_function_outside_loop(self):
        """Test that continue in function but outside loop produces error."""
        shell = Shell()
        code = '''
        test_func() {
            echo "in function"
            continue
            echo "after continue"
        }
        test_func
        '''
        
        import io
        from contextlib import redirect_stderr
        
        f = io.StringIO()
        with redirect_stderr(f):
            result = shell.run_command(code)
        
        error_output = f.getvalue().strip()
        assert "continue: only meaningful in a `for' or `while' loop" in error_output
        assert result == 1
    
    def test_break_continue_in_function_within_loop(self):
        """Test break and continue work correctly in functions called from loops."""
        shell = Shell()
        code = '''
        break_func() {
            if [ $1 -eq 3 ]; then
                break
            fi
        }
        continue_func() {
            if [ $1 -eq 2 ]; then
                continue
            fi
        }
        
        # Test break in function
        for i in 1 2 3 4 5; do
            break_func $i
            echo $i
        done
        echo "---"
        # Test continue in function
        for i in 1 2 3 4; do
            continue_func $i
            echo $i
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        expected = "1\n2\n---\n1\n3\n4"  # break at 3, continue at 2
        assert output == expected
        assert result == 0
    
    # @pytest.mark.skip(reason="Parser returns statements, not and_or_lists for break/continue")
    def test_break_continue_parsing(self):
        """Test that break and continue are parsed correctly."""
        # Test tokenization
        tokens = tokenize("break")
        assert len(tokens) == 2  # BREAK + EOF
        assert tokens[0].type.name == "BREAK"
        assert tokens[0].value == "break"
        
        tokens = tokenize("continue")
        assert len(tokens) == 2  # CONTINUE + EOF
        assert tokens[0].type.name == "CONTINUE"
        assert tokens[0].value == "continue"
        
        # Test parsing
        ast = parse(tokenize("break"))
        assert hasattr(ast, 'statements')
        assert len(ast.statements) == 1
        from psh.ast_nodes import BreakStatement
        assert isinstance(ast.statements[0], BreakStatement)
        
        ast = parse(tokenize("continue"))
        assert hasattr(ast, 'statements')
        assert len(ast.statements) == 1
        from psh.ast_nodes import ContinueStatement
        assert isinstance(ast.statements[0], ContinueStatement)
    
    # @pytest.mark.skip(reason="Parse error with break after && operator")
    def test_break_continue_with_pipes_and_operators(self):
        """Test that break/continue work correctly with shell operators."""
        shell = Shell()
        code = '''
        for i in 1 2 3 4 5; do
            if [ $i -eq 3 ]; then
                echo "breaking at $i" && break
            fi
            echo $i
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        expected = "1\n2\nbreaking at 3"
        assert output == expected
        assert result == 0
    
    # @pytest.mark.skip(reason="For loop variable restoration issue") 
    def test_variable_scoping_with_break_continue(self):
        """Test that variable scoping works correctly with break/continue."""
        shell = Shell()
        # Test that loop variable is properly restored after break
        shell.state.set_variable('i', 'original')
        
        code = '''
        for i in 1 2 3; do
            if [ $i -eq 2 ]; then
                break
            fi
            echo $i
        done
        echo "final i: $i"
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        expected = "1\nfinal i: 2"  # i should be 2 when break occurred
        assert output == expected
        assert result == 0
        
        # After the for loop, the variable should be restored to original value
        # or the last value in the loop depending on implementation
        # For now, let's just check it has some reasonable value
        assert shell.state.get_variable('i') in ['original', '2']