import pytest
from psh.shell import Shell
from psh.parser import parse
from psh.lexer import tokenize


class TestBreakContinueSimple:
    """Test break and continue statements with simple cases."""
    
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
        from psh.ast_nodes import BreakStatement, StatementList
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], BreakStatement)
        
        ast = parse(tokenize("continue"))
        from psh.ast_nodes import ContinueStatement
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 1
        assert isinstance(ast.statements[0], ContinueStatement)
    
    def test_break_in_for_loop(self):
        """Test break statement in for loop."""
        shell = Shell()
        # Test by executing step by step using the shell's execution methods
        from psh.lexer import tokenize
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
        from psh.lexer import tokenize
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
        shell.state.set_variable('done', 'false')
        
        # Use a single-line command to avoid parsing issues
        code = 'while [ "$done" = "false" ]; do echo "looping"; break; echo "after break"; done'
        
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            result = shell.run_command(code)
        
        output = f.getvalue().strip()
        assert output == "looping"  # Should only see this once
        assert result == 0
    
    def test_continue_in_for_loop_simple(self):
        """Test continue in a simple for loop.""" 
        shell = Shell()
        # Test by manually testing continue that we know works
        from psh.lexer import tokenize
        from psh.parser import parse
        
        # Create a simpler test that uses continue in its basic form
        code = "for i in 1 2 3; do continue; echo $i; done"
        tokens = tokenize(code)
        ast = parse(tokens)
        
        import io
        import sys
        
        saved_stdout = sys.stdout
        test_output = io.StringIO()
        sys.stdout = test_output
        
        try:
            if hasattr(ast, 'items'):
                result = shell.execute_toplevel(ast)
            else:
                result = shell.execute_command_list(ast)
        finally:
            sys.stdout = saved_stdout
        
        output = test_output.getvalue().strip()
        # With continue at the start, nothing should be printed
        assert output == ""
        assert result == 0
    
    def test_basic_break_continue_behavior(self):
        """Test basic break and continue behavior works correctly."""
        shell = Shell()
        # Test that break actually stops the loop 
        from psh.lexer import tokenize
        from psh.parser import parse
        
        # Simple break test
        code = "for i in 1 2 3 4; do echo $i; break; done"
        tokens = tokenize(code)
        ast = parse(tokens)
        
        import io
        import sys
        
        saved_stdout = sys.stdout
        test_output = io.StringIO()
        sys.stdout = test_output
        
        try:
            if hasattr(ast, 'items'):
                result = shell.execute_toplevel(ast)
            else:
                result = shell.execute_command_list(ast)
        finally:
            sys.stdout = saved_stdout
        
        output = test_output.getvalue().strip()
        # Should only see "1" since break happens after first echo
        assert output == "1"
        assert result == 0