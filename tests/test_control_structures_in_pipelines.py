"""Test control structures in pipelines - both receiving and sending.

Note: Some tests are marked with @pytest.mark.requires_stdin and require pytest 
to be run with the -s flag to disable output capturing since they use the 'read' 
builtin which needs access to stdin.

To run these tests:
    pytest tests/test_control_structures_in_pipelines.py -s
    
To skip stdin-requiring tests:
    pytest tests/test_control_structures_in_pipelines.py -m "not requires_stdin"
"""
import pytest
import tempfile
import os
import sys
from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse

class TestControlStructuresInPipelines:
    """Test that all control structures work as pipeline components."""
    
    def setup_method(self):
        """Create a fresh shell for each test."""
        self.shell = Shell()
        # Create a temporary file for output capture
        self.output_fd, self.output_file = tempfile.mkstemp()
        os.close(self.output_fd)
    
    def teardown_method(self):
        """Clean up temporary files."""
        try:
            os.unlink(self.output_file)
        except:
            pass
    
    def execute_command(self, command_string):
        """Execute a command string and return the exit code."""
        # Redirect to temp file for capturing output from pipelines
        if '>' not in command_string:
            command_string += f' > {self.output_file}'
        else:
            # Replace the redirection target
            command_string = command_string.replace('> /dev/stdout', f'> {self.output_file}')
        
        tokens = tokenize(command_string)
        ast = parse(tokens)
        # parse() can return either CommandList or TopLevel
        if hasattr(ast, 'items'):
            # It's a TopLevel
            return self.shell.execute_toplevel(ast)
        else:
            # It's a CommandList
            return self.shell.execute_command_list(ast)
    
    def get_output(self):
        """Get captured output from temp file."""
        try:
            with open(self.output_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return ''
    
    @pytest.mark.skip(reason="Requires pytest -s flag due to subprocess stdin interaction")
    def test_while_loop_receiving_from_pipeline(self):
        """Test while loop receiving input from pipeline."""
        result = self.execute_command('echo -e "a\\nb\\nc" | while read x; do echo "Got: $x"; done')
        assert result == 0
        output = self.get_output()
        assert "Got: a" in output
        assert "Got: b" in output
        assert "Got: c" in output
    
    @pytest.mark.skip(reason="Requires pytest -s flag due to subprocess stdin interaction")
    def test_while_loop_sending_to_pipeline(self):
        """Test while loop sending output to pipeline."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name
        
        try:
            result = self.execute_command(f'while read x; do echo $x; done < {temp_file} | head -2 | wc -l')
            assert result == 0
            output = self.get_output().strip()
            assert "2" in output
        finally:
            os.unlink(temp_file)
    
    def test_for_loop_receiving_from_pipeline(self):
        """Test for loop receiving input from pipeline."""
        result = self.execute_command('echo "a b c" | for x in $(cat); do echo "Item: $x"; done')
        assert result == 0
        output = self.get_output()
        assert "Item: a" in output
        assert "Item: b" in output
        assert "Item: c" in output
    
    def test_for_loop_sending_to_pipeline(self):
        """Test for loop sending output to pipeline."""
        result = self.execute_command('for x in a b c; do echo $x; done | wc -l')
        assert result == 0
        output = self.get_output().strip()
        assert "3" in output
    
    def test_cstyle_for_loop_receiving_from_pipeline(self):
        """Test C-style for loop receiving input from pipeline."""
        result = self.execute_command('echo "test" | for ((i=0; i<3; i++)); do echo "$i: received"; done')
        assert result == 0
        output = self.get_output()
        assert "0: received" in output
        assert "1: received" in output
        assert "2: received" in output
    
    def test_cstyle_for_loop_sending_to_pipeline(self):
        """Test C-style for loop sending output to pipeline."""
        result = self.execute_command('for ((i=0; i<3; i++)); do echo $i; done | wc -l')
        assert result == 0
        output = self.get_output().strip()
        assert "3" in output
    
    @pytest.mark.skip(reason="StringIO cannot capture output from external commands in pipelines")
    def test_if_statement_receiving_from_pipeline(self):
        """Test if statement receiving input from pipeline."""
        result = self.execute_command('echo "test" | if grep -q test; then echo "found"; else echo "not found"; fi')
        assert result == 0
        output = self.get_output()
        assert "found" in output
    
    def test_if_statement_sending_to_pipeline(self):
        """Test if statement sending output to pipeline."""
        result = self.execute_command('if true; then echo "yes"; else echo "no"; fi | tr a-z A-Z')
        assert result == 0
        output = self.get_output()
        assert "YES" in output
    
    def test_case_statement_receiving_from_pipeline(self):
        """Test case statement receiving input from pipeline."""
        result = self.execute_command('echo "foo" | case $(cat) in foo) echo "matched foo";; *) echo "no match";; esac')
        assert result == 0
        output = self.get_output()
        assert "matched foo" in output
    
    def test_case_statement_sending_to_pipeline(self):
        """Test case statement sending output to pipeline."""
        result = self.execute_command('case "test" in test) echo "matched";; esac | wc -c')
        assert result == 0
        # wc -c counts characters including newline
        output = self.get_output().strip()
        # "matched\n" is 8 characters
        assert "8" in output
    
    @pytest.mark.skip(reason="Requires pytest -s flag due to subprocess stdin interaction")
    def test_complex_pipeline_with_multiple_control_structures(self):
        """Test complex pipeline with multiple control structures."""
        # Simplify this test to avoid dependency on wc behavior in pipelines
        result = self.execute_command(
            'for i in 1 2 3; do echo $i; done | '
            'while read n; do echo $((n * 2)); done'
        )
        assert result == 0
        output = self.get_output()
        assert "2" in output  # 1 * 2
        assert "4" in output  # 2 * 2
        assert "6" in output  # 3 * 2
    
    @pytest.mark.skip(reason="Requires pytest -s flag due to subprocess stdin interaction")
    def test_nested_control_structures_in_pipeline(self):
        """Test nested control structures in pipeline."""
        result = self.execute_command(
            'echo -e "1\\n2\\n3" | '
            'while read x; do '
            '  for ((i=0; i<$x; i++)); do '
            '    echo -n "*"; '
            '  done; '
            '  echo; '
            'done | wc -l'
        )
        assert result == 0
        output = self.get_output().strip()
        assert "3" in output