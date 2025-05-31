import os
import tempfile
import pytest
from psh.shell import Shell


class TestRCFile:
    """Test RC file loading functionality"""
    
    def test_rc_file_not_loaded_in_script_mode(self):
        """RC file should not be loaded when running scripts"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('export TEST_RC_VAR=loaded\n')
            rc_file = f.name
        
        try:
            # Script mode should not load RC file
            shell = Shell(script_name="test.sh", rcfile=rc_file)
            assert 'TEST_RC_VAR' not in shell.env
        finally:
            os.unlink(rc_file)
    
    def test_rc_file_loaded_in_interactive_mode(self):
        """RC file should be loaded in interactive mode"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('export TEST_RC_VAR=loaded\n')
            f.write('alias test_alias="echo aliased"\n')
            rc_file = f.name
        
        try:
            # Interactive mode should load RC file
            shell = Shell(rcfile=rc_file)
            shell._force_interactive = True
            shell._load_rc_file()  # Force load since we're in test environment
            assert shell.env.get('TEST_RC_VAR') == 'loaded'
            assert 'test_alias' in shell.alias_manager.aliases
        finally:
            os.unlink(rc_file)
    
    def test_norc_flag_prevents_loading(self):
        """--norc flag should prevent RC file loading"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('export TEST_RC_VAR=loaded\n')
            rc_file = f.name
        
        try:
            # norc flag should prevent loading
            shell = Shell(rcfile=rc_file, norc=True)
            assert 'TEST_RC_VAR' not in shell.env
        finally:
            os.unlink(rc_file)
    
    def test_rc_file_syntax_error_doesnt_crash_shell(self):
        """Syntax errors in RC file should not crash the shell"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('invalid syntax {{{\n')
            rc_file = f.name
        
        try:
            # Shell should start despite RC file errors
            shell = Shell(rcfile=rc_file)
            # Shell should be created successfully
            assert shell is not None
        finally:
            os.unlink(rc_file)
    
    def test_rc_file_runtime_error_doesnt_crash_shell(self):
        """Runtime errors in RC file should not crash the shell"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('cd /nonexistent/directory\n')
            f.write('export TEST_AFTER_ERROR=yes\n')
            rc_file = f.name
        
        try:
            # Shell should continue despite runtime errors
            shell = Shell(rcfile=rc_file)
            shell._force_interactive = True
            shell._load_rc_file()  # Force load since we're in test environment
            # Commands after error should still execute
            assert shell.env.get('TEST_AFTER_ERROR') == 'yes'
        finally:
            os.unlink(rc_file)
    
    def test_rc_file_sets_variables_and_functions(self):
        """RC file should be able to set variables and define functions"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('TEST_VAR=hello_world\n')
            f.write('export ENV_VAR=exported\n')
            f.write('test_func() { echo "function works"; }\n')
            rc_file = f.name
        
        try:
            shell = Shell(rcfile=rc_file)
            shell._force_interactive = True
            shell._load_rc_file()  # Force load since we're in test environment
            # Shell variable should be set
            assert shell.variables.get('TEST_VAR') == 'hello_world'
            # Environment variable should be exported
            assert shell.env.get('ENV_VAR') == 'exported'
            # Function should be defined
            assert 'test_func' in shell.function_manager.functions
        finally:
            os.unlink(rc_file)
    
    def test_rc_file_unsafe_permissions_warning(self, capsys):
        """RC file with unsafe permissions should show warning"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('export TEST_RC_VAR=loaded\n')
            rc_file = f.name
        
        try:
            # Make file world-writable
            os.chmod(rc_file, 0o666)
            
            shell = Shell(rcfile=rc_file)
            shell._force_interactive = True
            shell._load_rc_file()  # Force load since we're in test environment
            captured = capsys.readouterr()
            
            # Should show warning
            assert "unsafe permissions" in captured.err
            # Should not load the file
            assert 'TEST_RC_VAR' not in shell.env
        finally:
            os.unlink(rc_file)
    
    def test_rc_file_preserves_dollar_zero(self):
        """RC file loading should preserve $0 after execution"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc', delete=False) as f:
            f.write('echo "Loading RC file: $0"\n')
            rc_file = f.name
        
        try:
            shell = Shell(rcfile=rc_file)
            shell._force_interactive = True
            shell._load_rc_file()  # Force load since we're in test environment
            # $0 should be restored to 'psh' after RC file execution
            assert shell.variables.get('0', shell.script_name) == 'psh'
        finally:
            os.unlink(rc_file)
    
    def test_rcfile_option_overrides_default(self):
        """--rcfile should override default ~/.pshrc location"""
        # Create two RC files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc1', delete=False) as f1:
            f1.write('export FROM_FILE1=yes\n')
            rc_file1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pshrc2', delete=False) as f2:
            f2.write('export FROM_FILE2=yes\n')
            rc_file2 = f2.name
        
        try:
            # Load with specific rcfile
            shell = Shell(rcfile=rc_file2)
            shell._force_interactive = True
            shell._load_rc_file()  # Force load since we're in test environment
            
            # Should only load the specified file
            assert 'FROM_FILE1' not in shell.env
            assert shell.env.get('FROM_FILE2') == 'yes'
        finally:
            os.unlink(rc_file1)
            os.unlink(rc_file2)
    
    def test_nonexistent_rc_file_silently_ignored(self):
        """Non-existent RC file should be silently ignored"""
        # Specify a non-existent RC file
        shell = Shell(rcfile="/tmp/nonexistent_rc_file_12345")
        
        # Shell should start normally
        assert shell is not None
        # No crash or errors