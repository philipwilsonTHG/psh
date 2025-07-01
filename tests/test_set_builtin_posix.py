"""Test POSIX set builtin options implementation."""
import pytest
import tempfile
import os
import subprocess
import sys
from psh.shell import Shell

# Mark for tests with isolation issues
skip_isolation = pytest.mark.skip(reason="Test has isolation issues - see tests/comparison/test_bash_shell_options.py")


class TestSetBuiltinPOSIX:
    """Test set builtin with POSIX options."""
    
    def test_set_short_options_mapping(self, shell):
        """Test short option to long name mapping."""
        mappings = {
            'a': 'allexport',
            'b': 'notify', 
            'C': 'noclobber',
            'e': 'errexit',
            'f': 'noglob',
            'h': 'hashcmds',
            'm': 'monitor',
            'n': 'noexec',
            'u': 'nounset',
            'v': 'verbose',
            'x': 'xtrace',
        }
        
        for short, long_name in mappings.items():
            # Skip noexec as it prevents its own unsetting
            if short == 'n':
                continue
                
            # Ensure option starts as False
            shell.run_command(f"set +{short}")
            assert shell.state.options.get(long_name, False) is False
            
            # Test setting short option
            shell.run_command(f"set -{short}")
            assert shell.state.options[long_name] is True
            
            # Test unsetting short option
            shell.run_command(f"set +{short}")
            assert shell.state.options[long_name] is False
    
    def test_noexec_special_behavior(self, shell):
        """Test noexec option's special behavior."""
        # noexec can be set
        shell.run_command("set -n")
        assert shell.state.options['noexec'] is True
        
        # But once set, it prevents its own unsetting in the same session
        shell.run_command("set +n")
        assert shell.state.options['noexec'] is True  # Still true!
        
        # This is expected behavior - noexec prevents execution of set +n
    
    def test_set_display_all_variables(self, shell, capsys):
        """Test set with no arguments displays variables."""
        # Set some variables
        shell.run_command("VAR1=value1")
        shell.run_command("VAR2=value2")
        
        # Call set with no arguments
        shell.run_command("set")
        captured = capsys.readouterr()
        
        # Should display variables
        assert "VAR1=value1" in captured.out
        assert "VAR2=value2" in captured.out
    
    def test_set_show_options(self, shell, capsys):
        """Test set -o shows all options."""
        # Set some options
        shell.run_command("set -afv")
        
        # Show options
        shell.run_command("set -o")
        captured = capsys.readouterr()
        
        # Should show option status (with new tab-separated format)
        assert "allexport      \ton" in captured.out
        assert "noglob         \ton" in captured.out
        assert "verbose        \ton" in captured.out
        assert "noclobber      \toff" in captured.out
    
    def test_set_show_as_commands(self, shell, capsys):
        """Test set +o shows options as commands."""
        # Set some options
        shell.run_command("set -aC")
        
        # Show as commands
        shell.run_command("set +o")
        captured = capsys.readouterr()
        
        # Should show as set commands
        assert "set -o allexport" in captured.out
        assert "set -o noclobber" in captured.out
        assert "set +o noglob" in captured.out
    
    def test_set_positional_params(self, shell):
        """Test set with arguments sets positional parameters."""
        shell.run_command("set arg1 arg2 arg3")
        
        # Check positional parameters
        assert shell.state.positional_params == ["arg1", "arg2", "arg3"]
        
        # Test with --
        shell.run_command("set -- new1 new2")
        assert shell.state.positional_params == ["new1", "new2"]
    
    def test_set_help_output(self, shell, capsys):
        """Test set builtin help is comprehensive."""
        from psh.builtins.environment import SetBuiltin
        
        set_builtin = SetBuiltin()
        help_text = set_builtin.help
        
        # Should document all POSIX options
        posix_options = ['allexport', 'notify', 'noclobber', 'noglob', 
                        'verbose', 'noexec', 'errexit', 'nounset', 'xtrace']
        
        for option in posix_options:
            assert option in help_text
        
        # Should document short forms
        short_forms = ['-a', '-b', '-C', '-f', '-v', '-n', '-e', '-u', '-x']
        for short in short_forms:
            assert short in help_text
    
    def test_set_invalid_option(self, shell, capsys):
        """Test invalid option handling."""
        result = shell.run_command("set -Z")
        assert result == 1
        
        captured = capsys.readouterr()
        assert "invalid option" in captured.err
    
    def test_set_combined_with_double_dash(self, shell):
        """Test combined options with positional parameters."""
        shell.run_command("set -afv -- pos1 pos2")
        
        # Options should be set
        assert shell.state.options['allexport'] is True
        assert shell.state.options['noglob'] is True
        assert shell.state.options['verbose'] is True
        
        # Positional parameters should be set
        assert shell.state.positional_params == ["pos1", "pos2"]
    
    def test_set_o_with_invalid_option(self, shell, capsys):
        """Test set -o with invalid option name."""
        result = shell.run_command("set -o invalidoption")
        assert result == 1
        
        captured = capsys.readouterr()
        assert "invalid option" in captured.err
        # Should show valid options
        assert "Valid options:" in captured.err


class TestOptionInteractions:
    """Test interactions between different options."""
    
    @skip_isolation
    def test_verbose_with_noexec(self, shell):
        """Test verbose option works with noexec."""
        script_content = '''set -nv
echo "command 1"
echo "command 2"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'psh', script_path],
                capture_output=True,
                text=True
            )
            
            # Should show verbose output but not execute
            assert 'echo "command 1"' in result.stderr
            assert 'echo "command 2"' in result.stderr
            assert "command 1" not in result.stdout
            assert "command 2" not in result.stdout
        finally:
            os.unlink(script_path)
    
    def test_allexport_with_noglob(self, shell, tmp_path):
        """Test allexport works with noglob."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            script_content = '''set -af
VAR=*.txt
python3 -c "import os; print('VAR:', os.environ.get('VAR', 'NOT_FOUND'))"
'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'psh', script_path],
                    capture_output=True,
                    text=True
                )
                
                # Variable should be exported but not expanded
                assert "VAR: *.txt" in result.stdout
            finally:
                os.unlink(script_path)
        finally:
            os.chdir(old_cwd)
    
    def test_noclobber_with_allexport(self, shell, tmp_path):
        """Test noclobber prevents overwriting exported vars."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original")
        
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            shell.run_command("set -aC")
            shell.run_command("FILENAME=existing.txt")
            
            # Try to overwrite - should fail
            result = shell.run_command("echo 'new' > existing.txt")
            assert result == 1
            
            # File should be unchanged
            assert existing_file.read_text() == "original"
        finally:
            os.chdir(old_cwd)


class TestBashCompatibility:
    """Test compatibility with bash behavior."""
    
    def test_dollar_dash_order(self, shell):
        """Test $- shows options in alphabetical order like bash."""
        # Use the same MockStdout pattern from the other test file
        result_out = []
        original_stdout = shell.stdout
        
        class MockStdout:
            def __init__(self, result_list):
                self.result_list = result_list
                self.buffer = ""
            
            def write(self, text):
                self.buffer += text
                # Immediately add any complete lines to result_list
                while '\n' in self.buffer:
                    line, self.buffer = self.buffer.split('\n', 1)
                    self.result_list.append(line + '\n')
            
            def flush(self):
                if self.buffer:
                    self.result_list.append(self.buffer)
                    self.buffer = ""
        
        shell.stdout = MockStdout(result_out)
        super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
        
        try:
            # Set options in non-alphabetical order
            shell.run_command("set -xafv")
            shell.run_command("echo $-")
            shell.stdout.flush()
            
            options = result_out[0].strip()
            
            # Should be in alphabetical order
            expected_order = "afvx"
            assert options == expected_order
        finally:
            # Restore stdout
            shell.stdout = original_stdout
            super(Shell, shell).__setattr__('stdout', sys.stdout)
    
    def test_noglob_with_quotes(self, shell, tmp_path):
        """Test noglob interaction with quoted patterns."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result_out = []
            original_stdout = shell.stdout
            
            class MockStdout:
                def __init__(self, result_list):
                    self.result_list = result_list
                    self.buffer = ""
                
                def write(self, text):
                    self.buffer += text
                    # Immediately add any complete lines to result_list
                    while '\n' in self.buffer:
                        line, self.buffer = self.buffer.split('\n', 1)
                        self.result_list.append(line + '\n')
                
                def flush(self):
                    if self.buffer:
                        self.result_list.append(self.buffer)
                        self.buffer = ""
            
            shell.stdout = MockStdout(result_out)
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            
            shell.run_command("set -f")
            
            # Quoted patterns should never expand, even without noglob
            shell.run_command('echo "*.txt"')
            shell.stdout.flush()
            assert result_out[0].strip() == "*.txt"
            
            result_out.clear()
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("echo '*.txt'")
            shell.stdout.flush()
            assert result_out[0].strip() == "*.txt"
            
            # Restore stdout
            shell.stdout = original_stdout
            super(Shell, shell).__setattr__('stdout', sys.stdout)
        finally:
            os.chdir(old_cwd)
    
    @skip_isolation
    def test_allexport_existing_vars(self, shell):
        """Test allexport affects subsequently set variables, not existing ones."""
        # Set variable before allexport
        shell.run_command("BEFORE=value")
        shell.run_command("set -a")
        shell.run_command("AFTER=value")
        
        script_content = '''python3 -c "import os; print('BEFORE:', os.environ.get('BEFORE', 'NOT_FOUND')); print('AFTER:', os.environ.get('AFTER', 'NOT_FOUND'))"'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'psh', script_path],
                capture_output=True,
                text=True,
                env=dict(os.environ, **shell.env)  # Pass shell's environment
            )
            
            # BEFORE should not be exported, AFTER should be
            assert "BEFORE: NOT_FOUND" in result.stdout
            assert "AFTER: value" in result.stdout
        finally:
            os.unlink(script_path)


if __name__ == "__main__":
    pytest.main([__file__])
