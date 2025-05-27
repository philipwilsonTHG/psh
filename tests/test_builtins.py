import pytest
import os
import tempfile
from io import StringIO
from unittest.mock import patch
from psh.shell import Shell


class TestBuiltins:
    def setup_method(self):
        self.shell = Shell()
        self.original_cwd = os.getcwd()
    
    def teardown_method(self):
        os.chdir(self.original_cwd)
    
    def test_pwd(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell._builtin_pwd(['pwd'])
            assert exit_code == 0
            assert mock_stdout.getvalue().strip() == os.getcwd()
    
    def test_echo(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            # Simple echo
            self.shell._builtin_echo(['echo', 'hello', 'world'])
            assert mock_stdout.getvalue() == "hello world\n"
            
            # Empty echo
            mock_stdout.truncate(0)
            mock_stdout.seek(0)
            self.shell._builtin_echo(['echo'])
            assert mock_stdout.getvalue() == "\n"
    
    def test_cd(self):
        # Change to /tmp
        exit_code = self.shell._builtin_cd(['cd', '/tmp'])
        assert exit_code == 0
        assert os.getcwd() == '/private/tmp' or os.getcwd() == '/tmp'
        
        # Change to home
        exit_code = self.shell._builtin_cd(['cd'])
        assert exit_code == 0
        assert os.getcwd() == os.path.expanduser('~')
        
        # Invalid directory
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            exit_code = self.shell._builtin_cd(['cd', '/nonexistent/directory'])
            assert exit_code == 1
            assert "No such file or directory" in mock_stderr.getvalue()
    
    def test_export(self):
        # Export variable
        exit_code = self.shell._builtin_export(['export', 'TEST_VAR=test_value'])
        assert exit_code == 0
        assert self.shell.env['TEST_VAR'] == 'test_value'
        # Note: export only modifies shell.env, not os.environ
        
        # Export without value (should do nothing but not error)
        exit_code = self.shell._builtin_export(['export', 'NOVALUE'])
        assert exit_code == 0
    
    def test_unset(self):
        # Set up a variable
        self.shell.env['TEST_VAR'] = 'value'
        # Note: unset only removes from shell.env, not os.environ
        
        # Unset it
        exit_code = self.shell._builtin_unset(['unset', 'TEST_VAR'])
        assert exit_code == 0
        assert 'TEST_VAR' not in self.shell.env
        
        # Unset non-existent variable (should not error)
        exit_code = self.shell._builtin_unset(['unset', 'NONEXISTENT'])
        assert exit_code == 0
    
    def test_env(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            # Set some test variables
            self.shell.env['AAA_TEST'] = 'first'
            self.shell.env['ZZZ_TEST'] = 'last'
            
            exit_code = self.shell._builtin_env(['env'])
            assert exit_code == 0
            
            output = mock_stdout.getvalue()
            lines = output.strip().split('\n')
            
            # Check that variables are sorted
            aaa_index = None
            zzz_index = None
            for i, line in enumerate(lines):
                if line.startswith('AAA_TEST='):
                    aaa_index = i
                if line.startswith('ZZZ_TEST='):
                    zzz_index = i
            
            assert aaa_index is not None
            assert zzz_index is not None
            assert aaa_index < zzz_index
    
    def test_source(self):
        # Create a temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.psh', delete=False) as f:
            f.write("export SOURCE_TEST=sourced\n")
            f.write("export ANOTHER_VAR=value\n")
            script_path = f.name
        
        try:
            # Source the file
            exit_code = self.shell._builtin_source(['source', script_path])
            assert exit_code == 0
            assert self.shell.env['SOURCE_TEST'] == 'sourced'
            assert self.shell.env['ANOTHER_VAR'] == 'value'
            
            # Test with . command
            with tempfile.NamedTemporaryFile(mode='w', suffix='.psh', delete=False) as f:
                f.write("export DOT_TEST=dotted\n")
                dot_script = f.name
            
            exit_code = self.shell._builtin_source(['.', dot_script])
            assert exit_code == 0
            assert self.shell.env['DOT_TEST'] == 'dotted'
            
            os.unlink(dot_script)
        finally:
            os.unlink(script_path)
        
        # Test missing file
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            exit_code = self.shell._builtin_source(['source', '/nonexistent/file'])
            assert exit_code == 1
            assert "No such file or directory" in mock_stderr.getvalue()
        
        # Test missing argument
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            exit_code = self.shell._builtin_source(['source'])
            assert exit_code == 1
            assert "filename argument required" in mock_stderr.getvalue()
    
    def test_exit(self):
        # Test exit without code
        with pytest.raises(SystemExit) as exc_info:
            self.shell._builtin_exit(['exit'])
        assert exc_info.value.code == 0
        
        # Test exit with code
        with pytest.raises(SystemExit) as exc_info:
            self.shell._builtin_exit(['exit', '42'])
        assert exc_info.value.code == 42