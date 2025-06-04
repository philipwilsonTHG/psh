"""Test shell built-in commands."""

import os
import tempfile
import pytest
from io import StringIO
from unittest.mock import patch
from psh.shell import Shell


class TestBuiltins:
    def setup_method(self):
        self.shell = Shell()
        self.original_cwd = os.getcwd()
    
    def teardown_method(self):
        os.chdir(self.original_cwd)
    
    def test_pwd(self, capsys):
        exit_code = self.shell.run_command("pwd")
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == os.getcwd()
    
    def test_echo(self, capsys):
        # Simple echo
        self.shell.run_command("echo hello world")
        captured = capsys.readouterr()
        assert captured.out == "hello world\n"
        
        # Empty echo
        self.shell.run_command("echo")
        captured = capsys.readouterr()
        assert captured.out == "\n"
    
    def test_cd(self, capsys):
        # Change to /tmp
        exit_code = self.shell.run_command("cd /tmp")
        assert exit_code == 0
        assert os.getcwd() in ['/private/tmp', '/tmp']  # Handle macOS
        
        # Change to home
        exit_code = self.shell.run_command("cd")
        assert exit_code == 0
        assert os.getcwd() == os.path.expanduser('~')
        
        # Invalid directory
        exit_code = self.shell.run_command("cd /nonexistent/directory")
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "No such file or directory" in captured.err
    
    def test_export(self):
        # Export with value
        exit_code = self.shell.run_command("export TEST_VAR=test_value")
        assert exit_code == 0
        assert self.shell.env['TEST_VAR'] == 'test_value'
        assert self.shell.state.get_variable('TEST_VAR') == 'test_value'
        
        # Export existing variable
        self.shell.state.set_variable('EXISTING', 'existing_value')
        exit_code = self.shell.run_command("export EXISTING")
        assert exit_code == 0
        assert self.shell.env['EXISTING'] == 'existing_value'
    
    def test_unset(self):
        # Set and unset a variable
        self.shell.state.set_variable('TEST_VAR', 'test_value')
        self.shell.env['TEST_VAR'] = 'test_value'
        
        exit_code = self.shell.run_command("unset TEST_VAR")
        assert exit_code == 0
        assert not self.shell.state.scope_manager.has_variable('TEST_VAR')
        assert 'TEST_VAR' not in self.shell.env
    
    def test_env(self, capsys):
        # Set a variable and check env output
        self.shell.env['TEST_ENV'] = 'test_env_value'
        
        exit_code = self.shell.run_command("env")
        assert exit_code == 0
        captured = capsys.readouterr()
        assert 'TEST_ENV=test_env_value' in captured.out
    
    def test_source(self):
        # Create a test script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('export SOURCED_VAR=sourced_value\n')
            f.write('TEST_VAR=test_value\n')
            script_path = f.name
        
        try:
            # Source the script
            exit_code = self.shell.run_command(f"source {script_path}")
            assert exit_code == 0
            
            # Check that variables were set
            assert self.shell.env.get('SOURCED_VAR') == 'sourced_value'
            assert self.shell.state.get_variable('TEST_VAR') == 'test_value'
            
        finally:
            os.unlink(script_path)
        
        # Test source with missing file
        exit_code = self.shell.run_command("source /nonexistent/file")
        assert exit_code == 1
    
    def test_source_with_args(self):
        # Create a test script that uses positional parameters
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('ARG1=$1\n')
            f.write('ARG2=$2\n')
            f.write('echo "Args: $1 $2"\n')
            script_path = f.name
        
        try:
            # Source with arguments
            old_params = self.shell.positional_params.copy()
            exit_code = self.shell.run_command(f"source {script_path} hello world")
            assert exit_code == 0
            
            # Check that variables were set from arguments
            assert self.shell.state.get_variable('ARG1') == 'hello'
            assert self.shell.state.get_variable('ARG2') == 'world'
            
            # Positional params should be restored after source
            assert self.shell.positional_params == old_params
            
        finally:
            os.unlink(script_path)
    
    def test_source_path_search(self):
        # Create a temporary directory and add to PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a script in the temp directory
            script_name = 'test_script.sh'
            script_path = os.path.join(tmpdir, script_name)
            with open(script_path, 'w') as f:
                f.write('export PATH_SEARCHED=yes\n')
            
            # Add tmpdir to PATH
            old_path = self.shell.env.get('PATH', '')
            self.shell.env['PATH'] = f"{tmpdir}:{old_path}"
            
            try:
                # Source by name only (should search PATH)
                exit_code = self.shell.run_command(f"source {script_name}")
                assert exit_code == 0
                assert self.shell.env.get('PATH_SEARCHED') == 'yes'
            finally:
                self.shell.env['PATH'] = old_path
    
    def test_exit(self):
        # We can't actually test exit without exiting the test process
        # So we'll test that the builtin exists and can be called
        with pytest.raises(SystemExit) as exc_info:
            self.shell.run_command("exit")
        assert exc_info.value.code == 0
        
        # Test with exit code
        with pytest.raises(SystemExit) as exc_info:
            self.shell.run_command("exit 42")
        assert exc_info.value.code == 42
    
    def test_colon(self):
        # Colon command should do nothing and return 0
        exit_code = self.shell.run_command(":")
        assert exit_code == 0
        
        # With arguments (should still do nothing)
        exit_code = self.shell.run_command(": ignored arguments")
        assert exit_code == 0