import pytest
import tempfile
import os
import sys
from psh.state_machine_lexer import tokenize, TokenType
from psh.parser import parse
from psh.shell import Shell


class TestCommandSubstitution:
    def test_tokenize_command_substitution(self):
        """Test tokenization of command substitution"""
        # Test $()
        tokens = tokenize("echo $(date)")
        assert len(tokens) == 3  # echo, $(date), EOF
        assert tokens[0].type == TokenType.WORD and tokens[0].value == "echo"
        assert tokens[1].type == TokenType.COMMAND_SUB and tokens[1].value == "$(date)"
        
        # Test backticks
        tokens = tokenize("echo `whoami`")
        assert len(tokens) == 3
        assert tokens[1].type == TokenType.COMMAND_SUB_BACKTICK and tokens[1].value == "`whoami`"
        
        # Test nested $()
        tokens = tokenize("echo $(echo $(date))")
        assert tokens[1].type == TokenType.COMMAND_SUB
        assert tokens[1].value == "$(echo $(date))"
        
        # Test multiple substitutions
        tokens = tokenize("echo $(date) $(whoami)")
        assert len(tokens) == 4  # echo, $(date), $(whoami), EOF
        assert tokens[1].type == TokenType.COMMAND_SUB
        assert tokens[2].type == TokenType.COMMAND_SUB
    
    def test_parse_command_substitution(self):
        """Test parsing of command substitution"""
        # Test $()
        tokens = tokenize("echo $(date)")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert len(command.args) == 2
        assert command.args[0] == "echo"
        assert command.args[1] == "$(date)"
        assert command.arg_types[1] == 'COMMAND_SUB'
        
        # Test backticks
        tokens = tokenize("echo `whoami`")
        ast = parse(tokens)
        command = ast.pipelines[0].commands[0]
        assert command.args[1] == "`whoami`"
        assert command.arg_types[1] == 'COMMAND_SUB_BACKTICK'
    
    @pytest.mark.visitor_xfail(reason="Visitor executor doesn't support command substitution expansion in forked processes")
    def test_command_substitution_execution(self):
        """Test execution of command substitution"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("hello world\n")
            
            # Test basic command substitution
            output_file = os.path.join(tmpdir, "output.txt")
            shell.run_command(f"echo $(cat {test_file}) > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                assert content.strip() == "hello world"
            
            # Test backtick substitution
            shell.run_command(f"echo `cat {test_file}` > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                assert content.strip() == "hello world"
    
    @pytest.mark.visitor_xfail(reason="Visitor executor doesn't handle word splitting of command substitution output")
    def test_command_substitution_word_splitting(self):
        """Test that command substitution results are word-split"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with multiple words
            test_file = os.path.join(tmpdir, "words.txt")
            with open(test_file, 'w') as f:
                f.write("one two three\n")
            
            output_file = os.path.join(tmpdir, "output.txt")
            
            # The echo command should see three separate arguments
            shell.run_command(f"echo $(cat {test_file}) > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                assert content.strip() == "one two three"
    
    @pytest.mark.visitor_xfail(reason="Visitor executor doesn't properly propagate exit status from command substitutions")
    def test_command_substitution_exit_status(self):
        """Test that command substitution sets exit status"""
        shell = Shell()
        
        # Successful command
        shell.run_command("echo $(echo test)")
        assert shell.last_exit_code == 0
        
        # The exit status should be from the main command (echo), not the substitution
        # This is POSIX behavior
        shell.run_command("echo $(python3 -c 'import sys; sys.exit(42)')")
        assert shell.last_exit_code == 0  # echo succeeds
        
        # Command substitution that produces a command to execute
        shell.run_command("$(echo false)")
        assert shell.last_exit_code == 1  # false returns 1
    
    @pytest.mark.visitor_xfail(reason="Visitor executor doesn't handle empty command substitution output correctly")
    def test_command_substitution_empty_output(self):
        """Test command substitution with empty output"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "output.txt")
            
            # Command that produces no output
            shell.run_command(f"echo before $(true) after > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                # Empty substitution should not add any args
                assert content.strip() == "before after"
    
    @pytest.mark.visitor_xfail(reason="Visitor executor doesn't expand variables within command substitution contexts")
    def test_command_substitution_with_variables(self):
        """Test command substitution containing variables"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "output.txt")
            
            # Set a variable
            shell.run_command("TEST_VAR=hello")
            
            # Use variable inside command substitution
            shell.run_command(f"echo $(echo $TEST_VAR world) > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                assert content.strip() == "hello world"
    
    @pytest.mark.visitor_xfail(reason="Visitor executor doesn't support nested command substitution processing")
    def test_nested_command_substitution(self):
        """Test nested command substitution"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "output.txt")
            
            # Nested substitution
            shell.run_command(f"echo $(echo $(echo nested)) > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                assert content.strip() == "nested"
    
    @pytest.mark.skip("Backtick escape handling needs more work")
    def test_backtick_escape_sequences(self):
        """Test escape sequences in backticks"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "output.txt")
            
            # Test escaping dollar sign
            # Use a non-existent variable to make the test clearer
            shell.run_command(f"echo `echo \\$NONEXISTENT` > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                assert content.strip() == "$NONEXISTENT"
            
            # Test escaping backtick (this is tricky to test)
            # Skip for now as it requires more complex parsing
    
    @pytest.mark.visitor_xfail(reason="Visitor executor doesn't handle command substitution in pipeline contexts")
    @pytest.mark.skipif(os.getenv('GITHUB_ACTIONS') == 'true', 
                        reason="Pipeline tests can be flaky in CI")
    def test_command_substitution_in_pipeline(self):
        """Test command substitution in pipeline"""
        shell = Shell()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.txt")
            with open(file1, 'w') as f:
                f.write("file1\n")
            with open(file2, 'w') as f:
                f.write("file2\n")
            
            output_file = os.path.join(tmpdir, "output.txt")
            
            # Use command substitution in pipeline
            shell.run_command(f"cat $(echo {file1}) | grep file > {output_file}")
            
            with open(output_file, 'r') as f:
                content = f.read()
                assert "file1" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])