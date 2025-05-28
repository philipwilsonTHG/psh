import pytest
from psh.shell import Shell
from psh.parser import parse
from psh.tokenizer import tokenize


class TestBreakContinueSimple:
    """Test break and continue statements with simple cases."""
    
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
        assert hasattr(ast, 'and_or_lists')
        assert len(ast.and_or_lists) == 1
        from psh.ast_nodes import BreakStatement
        assert isinstance(ast.and_or_lists[0], BreakStatement)
        
        ast = parse(tokenize("continue"))
        assert hasattr(ast, 'and_or_lists')
        assert len(ast.and_or_lists) == 1
        from psh.ast_nodes import ContinueStatement
        assert isinstance(ast.and_or_lists[0], ContinueStatement)
    
    def test_break_in_for_loop(self):
        """Test break statement in for loop."""
        shell = Shell()
        
        # Test by executing step by step using the shell's execution methods
        from psh.tokenizer import tokenize
        from psh.parser import parse
        
        # Create a for loop with break inside
        code = "for i in 1 2 3; do echo $i; break; done"
        tokens = tokenize(code)
        ast = parse(tokens)
        
        import io
        from contextlib import redirect_stdout
        import sys
        
        # Use the same approach as the other for loop tests
        saved_stdout = sys.stdout
        test_output = io.StringIO()
        sys.stdout = test_output
        
        try:
            if hasattr(ast, 'items'):
                # It's a TopLevel
                result = shell.execute_toplevel(ast)
            else:
                # It's a CommandList
                result = shell.execute_command_list(ast)
        finally:
            sys.stdout = saved_stdout
        
        output = test_output.getvalue()
        assert "1" in output
        # Should not contain 2 or 3 because break happens after first echo
        assert "2" not in output
        assert "3" not in output
        assert result == 0
    
    def test_continue_in_for_loop(self):
        """Test continue statement in for loop."""
        shell = Shell()
        
        # Test continue using direct execution method
        from psh.tokenizer import tokenize
        from psh.parser import parse
        
        # Create a for loop with continue inside  
        code = "for i in 1 2 3; do continue; echo $i; done"
        tokens = tokenize(code)
        ast = parse(tokens)
        
        import io
        import sys
        
        # Use the same approach as the other for loop tests
        saved_stdout = sys.stdout
        test_output = io.StringIO()
        sys.stdout = test_output
        
        try:
            if hasattr(ast, 'items'):
                # It's a TopLevel
                result = shell.execute_toplevel(ast)
            else:
                # It's a CommandList
                result = shell.execute_command_list(ast)
        finally:
            sys.stdout = saved_stdout
        
        output = test_output.getvalue()
        # Should not contain any numbers because continue skips echo  
        assert "1" not in output
        assert "2" not in output
        assert "3" not in output
        assert result == 0
    
    def test_break_in_while_loop_simple(self):
        """Test break in a simple while loop."""
        shell = Shell()
        shell.variables['done'] = 'false'
        
        code = '''
        while [ "$done" = "false" ]; do
            echo "looping"
            break
            echo "after break"
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        assert output == "looping"  # Should only see this once
        assert result == 0
    
    def test_continue_in_while_loop_simple(self):
        """Test continue in a simple while loop with counter."""
        shell = Shell()
        
        code = '''
        count=0
        for i in 1 2 3; do
            if [ "$i" = "2" ]; then
                continue
            fi
            echo "processing $i"
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        assert "processing 1" in output
        assert "processing 2" not in output  # Skipped
        assert "processing 3" in output
        assert result == 0
    
    def test_nested_loops_break_inner(self):
        """Test break in nested loops affecting only inner loop."""
        shell = Shell()
        
        code = '''
        for outer in a b; do
            echo "outer: $outer"
            for inner in 1 2 3; do
                echo "inner: $inner"
                if [ "$inner" = "2" ]; then
                    break
                fi
            done
            echo "back in outer"
        done
        '''
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        # Should see both outer loops complete
        assert "outer: a" in output
        assert "outer: b" in output
        # Should see inner break working
        assert "inner: 1" in output
        assert "inner: 2" in output
        assert "inner: 3" not in output  # Broken before this
        # Should see outer continuing
        assert output.count("back in outer") == 2
        assert result == 0