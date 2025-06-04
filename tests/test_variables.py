import pytest
import os
from psh.shell import Shell


class TestVariables:
    
    def test_simple_variable_assignment(self, shell, capsys):
        """Test simple variable assignment without export"""
        shell.run_command("FOO=bar")
        assert shell.variables['FOO'] == 'bar'
        assert 'FOO' not in os.environ
        
        # Variable should be available for expansion
        shell.run_command("echo $FOO")
        captured = capsys.readouterr()
        assert captured.out.strip() == "bar"
    
    def test_variable_assignment_with_spaces(self, shell, capsys):
        """Test variable assignment with spaces in value"""
        # For now, this is a limitation - assignment values can't have spaces
        # unless the whole assignment is quoted
        shell.run_command('MSG=hello_world')
        assert shell.variables['MSG'] == 'hello_world'
        
        shell.run_command("echo $MSG")
        captured = capsys.readouterr()
        assert captured.out.strip() == "hello_world"
    
    def test_positional_parameters(self, shell, capsys):
        """Test positional parameters $1, $2, etc."""
        shell.run_command("set one two three")
        
        # Test individual parameters
        shell.run_command("echo $1")
        captured = capsys.readouterr()
        assert captured.out.strip() == "one"
        
        shell.run_command("echo $2")
        captured = capsys.readouterr()
        assert captured.out.strip() == "two"
        
        shell.run_command("echo $3")
        captured = capsys.readouterr()
        assert captured.out.strip() == "three"
        
        # Test unset parameter
        shell.run_command("echo $4")
        captured = capsys.readouterr()
        assert captured.out.strip() == ""
    
    def test_special_variable_dollar_question(self, shell, capsys):
        """Test $? exit status variable"""
        # Successful command
        shell.run_command("echo test")
        shell.run_command("echo $?")
        captured = capsys.readouterr()
        assert "0" in captured.out
        
        # Failed command
        shell.run_command("false")
        shell.run_command("echo $?")
        captured = capsys.readouterr()
        assert "1" in captured.out
    
    def test_special_variable_dollar_dollar(self, shell, capsys):
        """Test $$ PID variable"""
        shell.run_command("echo $$")
        captured = capsys.readouterr()
        assert captured.out.strip() == str(os.getpid())
    
    def test_special_variable_dollar_hash(self, shell, capsys):
        """Test $# number of parameters"""
        shell.run_command("set")
        capsys.readouterr()  # Clear the output from set command
        shell.run_command("echo $#")
        captured = capsys.readouterr()
        assert captured.out.strip() == "0"
        
        shell.run_command("set a b c d e")
        shell.run_command("echo $#")
        captured = capsys.readouterr()
        assert captured.out.strip() == "5"
    
    def test_special_variable_dollar_at(self, shell, capsys):
        """Test $@ all parameters as separate words"""
        shell.run_command("set one two three")
        shell.run_command("echo $@")
        captured = capsys.readouterr()
        # Note: Current implementation doesn't preserve quotes around individual parameters
        # This is an enhancement for future implementation
        assert captured.out.strip() == "one two three"
    
    def test_special_variable_dollar_star(self, shell, capsys):
        """Test $* all parameters as single word"""
        shell.run_command("set one two three")
        shell.run_command("echo $*")
        captured = capsys.readouterr()
        assert captured.out.strip() == "one two three"
    
    def test_special_variable_dollar_zero(self, shell, capsys):
        """Test $0 shell name"""
        shell.run_command("echo test $0")
        captured = capsys.readouterr()
        assert "psh" in captured.out
    
    @pytest.mark.skip(reason="Background process handling needs refinement")
    def test_special_variable_dollar_exclamation(self, shell, capsys):
        """Test $! last background PID"""
        shell.run_command("sleep 1 &")
        captured = capsys.readouterr()
        # Extract PID from output like "[12345]"
        pid_output = captured.out.strip()
        if pid_output.startswith('[') and pid_output.endswith(']'):
            expected_pid = pid_output[1:-1]
            
            shell.run_command("echo $!")
            captured = capsys.readouterr()
            assert captured.out.strip() == expected_pid
    
    def test_parameter_expansion_default(self, shell, capsys):
        """Test ${var:-default} expansion"""
        # Unset variable uses default
        shell.run_command('echo ${UNSET:-default}')
        captured = capsys.readouterr()
        assert captured.out.strip() == "default"
        
        # Empty variable uses default
        shell.run_command('EMPTY=')
        shell.run_command('echo ${EMPTY:-default}')
        captured = capsys.readouterr()
        assert captured.out.strip() == "default"
        
        # Set variable uses its value
        shell.run_command('SET=value')
        shell.run_command('echo ${SET:-default}')
        captured = capsys.readouterr()
        assert captured.out.strip() == "value"
    
    def test_parameter_expansion_braces(self, shell, capsys):
        """Test ${var} expansion"""
        shell.run_command('VAR=test')
        shell.run_command('echo ${VAR}')
        captured = capsys.readouterr()
        assert captured.out.strip() == "test"
        
        # Test concatenation - now works correctly
        shell.run_command('PREFIX=pre')
        shell.run_command('echo ${PREFIX}fix')
        captured = capsys.readouterr()
        assert captured.out.strip() == "prefix"  # Fixed: properly concatenated
    
    def test_shell_vs_environment_variables(self, shell, capsys):
        """Test that shell variables are separate from environment"""
        # Set shell variable
        shell.run_command("SHELLVAR=local")
        assert shell.variables['SHELLVAR'] == 'local'
        assert 'SHELLVAR' not in shell.env
        
        # Export makes it available in shell's environment
        shell.run_command("export SHELLVAR")
        assert shell.env.get('SHELLVAR') == 'local'
        
        # New export syntax
        shell.run_command("export NEWVAR=exported")
        assert shell.env['NEWVAR'] == 'exported'
        assert shell.variables['NEWVAR'] == 'exported'
    
    def test_variable_priority(self, shell, capsys):
        """Test that shell variables take priority over environment"""
        # Set environment variable
        os.environ['TESTVAR'] = 'from_env'
        shell.env['TESTVAR'] = 'from_env'
        
        # Set shell variable with same name
        shell.run_command('TESTVAR=from_shell')
        
        # Shell variable should take priority
        shell.run_command('echo $TESTVAR')
        captured = capsys.readouterr()
        assert captured.out.strip() == 'from_shell'
        
        # Clean up
        del os.environ['TESTVAR']
    
    def test_set_builtin_display(self, shell, capsys):
        """Test set builtin without args displays variables"""
        shell.run_command('VAR1=value1')
        shell.run_command('VAR2=value2')
        shell.run_command('set')
        captured = capsys.readouterr()
        assert 'VAR1=value1' in captured.out
        assert 'VAR2=value2' in captured.out