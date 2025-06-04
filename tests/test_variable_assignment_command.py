"""Test variable assignment before commands."""
import pytest
import sys
from io import StringIO
from psh.shell import Shell


class TestVariableAssignmentCommand:
    def setup_method(self):
        self.shell = Shell()
        # Start fresh with new shell instance
    
    def test_single_assignment_before_builtin(self):
        """Test single variable assignment before builtin command."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("hello world\n")
        
        try:
            exit_code = self.shell.run_command("IFS=_ read var")
            assert exit_code == 0
            # With IFS=_, the input should not be split on spaces
            assert self.shell.state.get_variable("var") == "hello world"
        finally:
            sys.stdin = old_stdin
    
    def test_multiple_assignments_before_command(self):
        """Test multiple variable assignments before command."""
        exit_code = self.shell.run_command("A=1 B=2 C=3 true")
        assert exit_code == 0
        # Variables should not persist after command
        assert self.shell.state.get_variable("A") == ""
        assert self.shell.state.get_variable("B") == ""
        assert self.shell.state.get_variable("C") == ""
    
    def test_assignment_with_expansion(self):
        """Test variable assignment with expansion before command."""
        self.shell.state.set_variable("BASE", "/tmp")
        old_stdin = sys.stdin
        sys.stdin = StringIO("test\n")
        
        try:
            exit_code = self.shell.run_command("PREFIX=$BASE/prefix read var")
            assert exit_code == 0
            assert self.shell.state.get_variable("var") == "test"
            # PREFIX should not persist
            assert self.shell.state.get_variable("PREFIX") == ""
        finally:
            sys.stdin = old_stdin
    
    def test_ifs_assignment_with_read(self):
        """Test IFS assignment with read command."""
        old_stdin = sys.stdin
        sys.stdin = StringIO("one:two:three\n")
        
        try:
            exit_code = self.shell.run_command("IFS=: read a b c")
            assert exit_code == 0
            assert self.shell.state.get_variable("a") == "one"
            assert self.shell.state.get_variable("b") == "two"
            assert self.shell.state.get_variable("c") == "three"
            # IFS should not persist
            assert self.shell.state.get_variable("IFS") == ""
        finally:
            sys.stdin = old_stdin
    
    def test_existing_variable_restored(self):
        """Test that existing variables are restored after command."""
        self.shell.state.set_variable("EXISTING", "original")
        old_stdin = sys.stdin
        sys.stdin = StringIO("input\n")
        
        try:
            exit_code = self.shell.run_command("EXISTING=temporary read var")
            assert exit_code == 0
            # EXISTING should be restored to original value
            assert self.shell.state.get_variable("EXISTING") == "original"
        finally:
            sys.stdin = old_stdin
    
    def test_assignment_only_no_command(self):
        """Test variable assignment without command."""
        exit_code = self.shell.run_command("VAR=value")
        assert exit_code == 0
        # Assignment without command should persist
        assert self.shell.state.get_variable("VAR") == "value"
    
    def test_multiple_assignments_only(self):
        """Test multiple variable assignments without command."""
        exit_code = self.shell.run_command("A=1 B=2 C=3")
        assert exit_code == 0
        # All assignments should persist
        assert self.shell.state.get_variable("A") == "1"
        assert self.shell.state.get_variable("B") == "2"
        assert self.shell.state.get_variable("C") == "3"
    
    def test_assignment_with_spaces_in_value(self):
        """Test assignment with spaces in quoted value."""
        # This now works with the new state machine lexer
        exit_code = self.shell.run_command('VAR="hello world"')
        assert exit_code == 0
        assert self.shell.state.get_variable("VAR") == "hello world"
        
        # Also test single quotes
        exit_code = self.shell.run_command("MSG='multiple words here'")
        assert exit_code == 0
        assert self.shell.state.get_variable("MSG") == "multiple words here"
    
    def test_assignment_before_function(self):
        """Test variable assignment before function call."""
        # Define a function
        self.shell.run_command("testfunc() { echo $VAR; }")
        
        # Call function with temporary variable
        import io
        import sys
        captured_output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            exit_code = self.shell.run_command("VAR=temporary testfunc")
            assert exit_code == 0
            
            output = captured_output.getvalue()
            assert "temporary" in output
            
            # VAR should not persist
            assert self.shell.state.get_variable("VAR") == ""
        finally:
            sys.stdout = old_stdout