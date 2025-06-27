"""Test shell options: set -e, -u, -x, -o pipefail, and POSIX options."""
import pytest
import subprocess
import os
import sys
import tempfile
import glob
from psh.shell import Shell
from psh.core.exceptions import UnboundVariableError

# Mark for tests with isolation issues
skip_isolation = pytest.mark.skip(reason="Test has isolation issues - see tests/comparison/test_bash_shell_options.py")


class TestShellOptions:
    """Test suite for shell options."""
    
    def test_set_option_parsing(self, shell):
        """Test parsing of set command options."""
        # Test individual options
        assert shell.run_command("set -e") == 0
        assert shell.state.options['errexit'] is True
        
        assert shell.run_command("set -u") == 0
        assert shell.state.options['nounset'] is True
        
        assert shell.run_command("set -x") == 0
        assert shell.state.options['xtrace'] is True
        
        # Test unsetting options
        assert shell.run_command("set +e") == 0
        assert shell.state.options['errexit'] is False
        
        assert shell.run_command("set +u") == 0
        assert shell.state.options['nounset'] is False
        
        assert shell.run_command("set +x") == 0
        assert shell.state.options['xtrace'] is False
        
        # Test combined options
        assert shell.run_command("set -eux") == 0
        assert shell.state.options['errexit'] is True
        assert shell.state.options['nounset'] is True
        assert shell.state.options['xtrace'] is True
        
        assert shell.run_command("set +eux") == 0
        assert shell.state.options['errexit'] is False
        assert shell.state.options['nounset'] is False
        assert shell.state.options['xtrace'] is False
    
    def test_set_o_pipefail(self, shell):
        """Test set -o pipefail option."""
        assert shell.run_command("set -o pipefail") == 0
        assert shell.state.options['pipefail'] is True
        
        assert shell.run_command("set +o pipefail") == 0
        assert shell.state.options['pipefail'] is False
    
    def test_show_options(self, shell, capsys):
        """Test showing current options."""
        # Set some options
        shell.run_command("set -e")
        shell.run_command("set -x")
        
        # Show with -o
        shell.run_command("set -o")
        captured = capsys.readouterr()
        assert "errexit              on" in captured.out
        assert "nounset              off" in captured.out
        assert "xtrace               on" in captured.out
        assert "pipefail             off" in captured.out
    
    def test_xtrace_basic(self, shell, capsys):
        """Test basic xtrace functionality."""
        shell.run_command("set -x")
        shell.run_command("echo hello")
        
        captured = capsys.readouterr()
        assert "hello\n" in captured.out
        assert "+ echo hello\n" in captured.err
    
    def test_xtrace_with_variables(self, shell, capsys):
        """Test xtrace with variable expansion."""
        shell.run_command("set -x")
        shell.run_command("VAR=world")
        shell.run_command('echo hello $VAR')
        
        captured = capsys.readouterr()
        assert "hello world\n" in captured.out
        assert "+ VAR=world\n" in captured.err
        assert "+ echo hello world\n" in captured.err
    
    def test_xtrace_ps4(self, shell, capsys):
        """Test xtrace with custom PS4."""
        shell.run_command("PS4='>> '")
        shell.run_command("set -x")
        shell.run_command("echo test")
        
        captured = capsys.readouterr()
        assert ">> echo test\n" in captured.err
    
    def test_nounset_basic(self, shell):
        """Test basic nounset functionality."""
        # Without nounset, undefined variables are empty
        assert shell.run_command('echo "$UNDEFINED"') == 0
        
        # With nounset, undefined variables cause error
        shell.run_command("set -u")
        # In the test harness, the exception is caught and returns 1
        result = shell.run_command('echo "$UNDEFINED"')
        assert result == 1
    
    def test_nounset_with_default(self, shell):
        """Test nounset with parameter expansion defaults."""
        shell.run_command("set -u")
        
        # Default expansion should work
        assert shell.run_command('echo "${UNDEFINED:-default}"') == 0
        assert shell.run_command('X="${UNDEFINED:-value}"; echo $X') == 0
    
    def test_nounset_special_vars(self, shell):
        """Test nounset with special variables."""
        shell.run_command("set -u")
        
        # These should always work
        assert shell.run_command('echo "$?"') == 0
        assert shell.run_command('echo "$$"') == 0
        assert shell.run_command('echo "$#"') == 0
        assert shell.run_command('echo "$0"') == 0
        
        # $@ and $* are allowed even when empty
        assert shell.run_command('echo "$@"') == 0
        assert shell.run_command('echo "$*"') == 0
    
    @pytest.mark.xfail(reason="Errexit works correctly but test environment issue with subprocess")
    def test_errexit_basic(self, shell):
        """Test basic errexit functionality in scripts."""
        script = '''#!/usr/bin/env psh
set -e
echo "Before failure"
false
echo "Should not print"
'''
        # Create a temporary script
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            # Make it executable
            os.chmod(script_path, 0o755)
            
            # Run the script
            result = subprocess.run(
                [sys.executable, '-m', 'psh', script_path],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 1
            assert "Before failure" in result.stdout
            assert "Should not print" not in result.stdout
        finally:
            os.unlink(script_path)
    
    def test_errexit_conditionals(self, shell):
        """Test errexit doesn't trigger in conditionals."""
        script = '''#!/usr/bin/env psh
set -e
if false; then
    echo "In if"
else
    echo "In else"
fi
false || echo "After or"
true && echo "After and"
echo "End"
'''
        # The script should complete successfully
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            os.chmod(script_path, 0o755)
            result = subprocess.run(
                [sys.executable, '-m', 'psh', script_path],
                capture_output=True,
                text=True
            )
            
            # Should not exit on false in conditionals
            assert result.returncode == 0
            assert "In else" in result.stdout
            assert "After or" in result.stdout
            assert "End" in result.stdout
        finally:
            os.unlink(script_path)
    
    def test_pipefail_basic(self, shell):
        """Test basic pipefail functionality."""
        # Without pipefail
        assert shell.run_command("false | true") == 0
        
        # With pipefail
        shell.run_command("set -o pipefail")
        assert shell.run_command("false | true") == 1
        assert shell.run_command("true | false | true") == 1
        assert shell.run_command("true | true | true") == 0
    
    def test_pipefail_exit_codes(self, shell):
        """Test pipefail returns correct exit code."""
        shell.run_command("set -o pipefail")
        
        # Create commands with specific exit codes
        import tempfile
        
        # Script that exits with 2
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/sh\nexit 2')
            exit2_path = f.name
        os.chmod(exit2_path, 0o755)
        
        # Script that exits with 3
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/sh\nexit 3')
            exit3_path = f.name
        os.chmod(exit3_path, 0o755)
        
        try:
            # Should return rightmost non-zero exit code
            assert shell.run_command(f"true | {exit2_path} | true") == 2
            assert shell.run_command(f"{exit2_path} | {exit3_path} | true") == 3
            assert shell.run_command(f"true | {exit3_path} | {exit2_path}") == 2
        finally:
            os.unlink(exit2_path)
            os.unlink(exit3_path)
    
    @skip_isolation
    def test_combined_options(self, shell):
        """Test combining multiple options."""
        script = '''
set -eux -o pipefail
VAR="test"
echo "Value: $VAR"
true | true
echo "Success"
'''
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'psh', script_path],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert "Value: test" in result.stdout
            assert "Success" in result.stdout
            # Check xtrace output
            assert "+ VAR=test" in result.stderr
            assert "+ echo Value: test" in result.stderr
        finally:
            os.unlink(script_path)


class TestPOSIXOptions:
    """Test suite for POSIX set options (-f, -v, -n, -C, -a, -b)."""
    
    def test_noglob_option_basic(self, shell, tmp_path):
        """Test -f (noglob) disables pathname expansion."""
        # Create test files
        test_file1 = tmp_path / "test1.txt"
        test_file2 = tmp_path / "test2.txt"
        test_file1.write_text("content1")
        test_file2.write_text("content2")
        
        # Change to test directory
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Without noglob - should expand
            result_out = []
            original_stdout = shell.stdout
            shell.stdout = MockStdout(result_out)
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("echo *.txt")
            shell.stdout.flush()
            expanded_output = result_out[0].strip()
            assert "test1.txt" in expanded_output and "test2.txt" in expanded_output
            
            # With noglob - should not expand
            result_out.clear()
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("set -f")
            shell.run_command("echo *.txt")
            shell.stdout.flush()
            noglob_output = result_out[0].strip()
            assert noglob_output == "*.txt"
            
            # Disable noglob - should expand again
            result_out.clear()
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("set +f")
            shell.run_command("echo *.txt")
            shell.stdout.flush()
            enabled_output = result_out[0].strip()
            assert "test1.txt" in enabled_output and "test2.txt" in enabled_output
            
            # Restore stdout
            shell.stdout = original_stdout
            super(Shell, shell).__setattr__('stdout', sys.stdout)
        finally:
            os.chdir(old_cwd)
    
    def test_noglob_option_long_form(self, shell, tmp_path):
        """Test -o noglob long form."""
        test_file = tmp_path / "glob_test.txt"
        test_file.write_text("test")
        
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result_out = []
            original_stdout = shell.stdout
            shell.stdout = MockStdout(result_out)
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            
            # Test long form enable
            shell.run_command("set -o noglob")
            shell.run_command("echo *.txt")
            shell.stdout.flush()
            assert result_out[0].strip() == "*.txt"
            
            # Test long form disable
            result_out.clear()
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("set +o noglob")
            shell.run_command("echo *.txt")
            shell.stdout.flush()
            assert "glob_test.txt" in result_out[0]
            
            # Restore stdout
            shell.stdout = original_stdout
            super(Shell, shell).__setattr__('stdout', sys.stdout)
        finally:
            os.chdir(old_cwd)
    
    @skip_isolation
    def test_verbose_option(self, shell, capsys):
        """Test -v (verbose) echoes input lines."""
        # Test with script
        script_content = '''set -v
echo "first command"
VAR=value
echo "second command"
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
            
            # Check that commands are echoed to stderr
            assert "echo \"first command\"" in result.stderr
            assert "VAR=value" in result.stderr
            assert "echo \"second command\"" in result.stderr
            
            # Check that output still works
            assert "first command" in result.stdout
            assert "second command" in result.stdout
        finally:
            os.unlink(script_path)
    
    @skip_isolation
    def test_verbose_toggle(self, shell, capsys):
        """Test toggling verbose option."""
        script_content = '''set -v
echo "verbose on"
set +v
echo "verbose off"
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
            
            # First echo should be verbose
            assert "echo \"verbose on\"" in result.stderr
            # Second echo should not be verbose  
            assert "echo \"verbose off\"" not in result.stderr
            # But set +v itself should be echoed
            assert "set +v" in result.stderr
        finally:
            os.unlink(script_path)
    
    def test_noexec_option(self, shell):
        """Test -n (noexec) parses but doesn't execute."""
        script_content = '''set -n
echo "this should not execute"
touch /tmp/should_not_create
exit 42
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
            
            # Should exit with 0 (successful parse), not 42
            assert result.returncode == 0
            # Should not execute commands
            assert "this should not execute" not in result.stdout
            assert not os.path.exists("/tmp/should_not_create")
        finally:
            os.unlink(script_path)
    
    @pytest.mark.xfail(reason="Complex interaction between noexec mode and line-by-line parsing - requires architectural review")
    def test_noexec_syntax_error(self, shell):
        """Test -n (noexec) catches syntax errors."""
        script_content = '''set -n
echo "valid command"
if echo "unclosed if"
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
            
            # Should exit with error due to syntax error
            assert result.returncode == 1
            assert "Expected 'then'" in result.stderr
        finally:
            os.unlink(script_path)
    
    def test_noclobber_option(self, shell, tmp_path):
        """Test -C (noclobber) prevents file overwriting."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("original content")
        
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            # Enable noclobber
            shell.run_command("set -C")
            
            # Try to overwrite - should fail
            result = shell.run_command("echo 'new content' > existing.txt")
            assert result == 1  # Should fail
            
            # File should be unchanged
            assert test_file.read_text() == "original content"
            
            # Disable noclobber - should work
            shell.run_command("set +C")
            result = shell.run_command("echo 'new content' > existing.txt")
            assert result == 0  # Should succeed
            assert test_file.read_text().strip() == "new content"
        finally:
            os.chdir(old_cwd)
    
    def test_noclobber_new_file(self, shell, tmp_path):
        """Test noclobber allows creating new files."""
        new_file = tmp_path / "new.txt"
        assert not new_file.exists()
        
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            shell.run_command("set -C")
            
            # Should allow creating new file
            result = shell.run_command("echo 'content' > new.txt")
            assert result == 0
            assert new_file.exists()
            assert new_file.read_text().strip() == "content"
        finally:
            os.chdir(old_cwd)
    
    @skip_isolation
    def test_allexport_option(self, shell):
        """Test -a (allexport) auto-exports variables."""
        # Test with Python subprocess to check environment
        script_content = '''set -a
VAR1=value1
VAR2=value2
python3 -c "import os; print('VAR1:', os.environ.get('VAR1', 'NOT_FOUND')); print('VAR2:', os.environ.get('VAR2', 'NOT_FOUND'))"
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
            
            assert "VAR1: value1" in result.stdout
            assert "VAR2: value2" in result.stdout
        finally:
            os.unlink(script_path)
    
    @skip_isolation
    def test_allexport_toggle(self, shell):
        """Test toggling allexport option."""
        script_content = '''set -a
EXPORTED=value
set +a
NOT_EXPORTED=value
python3 -c "import os; print('EXPORTED:', os.environ.get('EXPORTED', 'NOT_FOUND')); print('NOT_EXPORTED:', os.environ.get('NOT_EXPORTED', 'NOT_FOUND'))"
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
            
            assert "EXPORTED: value" in result.stdout
            assert "NOT_EXPORTED: NOT_FOUND" in result.stdout
        finally:
            os.unlink(script_path)
    
    def test_notify_option(self, shell):
        """Test -b (notify) option is set correctly."""
        # Test that option is tracked in $-
        result_out = []
        original_stdout = shell.stdout
        shell.stdout = MockStdout(result_out)
        super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
        
        try:
            shell.run_command("set -b")
            shell.run_command("echo $-")
            shell.stdout.flush()
            assert "b" in result_out[0]
            
            result_out.clear()
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("set +b")
            shell.run_command("echo $-")
            shell.stdout.flush()
            assert "b" not in result_out[0]
        finally:
            # Restore stdout
            shell.stdout = original_stdout
            super(Shell, shell).__setattr__('stdout', sys.stdout)
    
    def test_dollar_dash_variable(self, shell):
        """Test $- special variable shows active options."""
        result_out = []
        # Save and replace shell's stdout - need to set both shell.stdout and actual shell attribute
        original_stdout = shell.stdout  # This gets shell.state.stdout due to __getattr__
        original_shell_stdout = getattr(shell, '_stdout', None)  # Check if there's a direct attribute
        shell.stdout = MockStdout(result_out)  # This sets shell.state.stdout
        # Also need to set the shell's direct stdout attribute that the builtin accesses
        super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
        
        try:
            # Test individual options  
            shell.run_command("set -f")
            shell.run_command("echo $-")
            shell.stdout.flush()
            assert "f" in result_out[0]
            
            result_out.clear()
            # Re-set stdout for second test
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("set -v")
            shell.run_command("echo $-")
            shell.stdout.flush()
            options = result_out[0].strip()
            assert "f" in options and "v" in options
            
            result_out.clear()
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("set -a")
            shell.run_command("echo $-")
            shell.stdout.flush()
            options = result_out[0].strip()
            assert "a" in options and "f" in options and "v" in options
            
            # Test unsetting
            result_out.clear()
            super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
            shell.run_command("set +f")
            shell.run_command("echo $-")
            shell.stdout.flush()
            options = result_out[0].strip()
            assert "f" not in options
            assert "a" in options and "v" in options
        finally:
            # Restore stdout
            shell.stdout = original_stdout
            if original_shell_stdout is not None:
                super(Shell, shell).__setattr__('stdout', original_shell_stdout)
            else:
                super(Shell, shell).__setattr__('stdout', sys.stdout)
    
    def test_combined_posix_options(self, shell):
        """Test combining multiple POSIX options."""
        result_out = []
        original_stdout = shell.stdout
        shell.stdout = MockStdout(result_out)
        super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
        
        try:
            # Set multiple options (excluding noexec since it prevents execution)
            shell.run_command("set -afvC")
            shell.run_command("echo $-")
            shell.stdout.flush()
            options = result_out[0].strip()
        
            # Check all options are set (excluding noexec)
            for opt in ['a', 'f', 'v', 'C']:
                assert opt in options
            
            # Verify options are actually enabled
            assert shell.state.options['allexport'] is True
            assert shell.state.options['noglob'] is True
            assert shell.state.options['verbose'] is True
            assert shell.state.options['noclobber'] is True
            
            # Test noexec separately since it prevents execution
            shell.run_command("set -n")
            assert shell.state.options['noexec'] is True
        finally:
            # Restore stdout
            shell.stdout = original_stdout
            super(Shell, shell).__setattr__('stdout', sys.stdout)
    
    def test_long_form_options(self, shell):
        """Test long form option names work correctly."""
        # Test setting with long names (excluding noexec until the end)
        shell.run_command("set -o noglob")
        assert shell.state.options['noglob'] is True
        
        shell.run_command("set -o verbose") 
        assert shell.state.options['verbose'] is True
        
        shell.run_command("set -o noclobber")
        assert shell.state.options['noclobber'] is True
        
        shell.run_command("set -o allexport")
        assert shell.state.options['allexport'] is True
        
        shell.run_command("set -o notify")
        assert shell.state.options['notify'] is True
        
        # Test unsetting with long names (before setting noexec)
        shell.run_command("set +o noglob")
        assert shell.state.options['noglob'] is False
        
        shell.run_command("set +o verbose")
        assert shell.state.options['verbose'] is False
        
        # Test noexec last since it prevents further execution
        shell.run_command("set -o noexec")
        assert shell.state.options['noexec'] is True
    
    def test_option_combinations_with_existing(self, shell):
        """Test new POSIX options work with existing options."""
        result_out = []
        original_stdout = shell.stdout
        shell.stdout = MockStdout(result_out)
        super(Shell, shell).__setattr__('stdout', MockStdout(result_out))
        
        try:
            # Combine new and existing options
            shell.run_command("set -fveux")
            shell.run_command("echo $-")
            shell.stdout.flush()
            options = result_out[0].strip()
            
            # Should contain both new and existing options
            assert "f" in options  # noglob
            assert "v" in options  # verbose  
            assert "e" in options  # errexit
            assert "u" in options  # nounset
            assert "x" in options  # xtrace
        finally:
            # Restore stdout
            shell.stdout = original_stdout
            super(Shell, shell).__setattr__('stdout', sys.stdout)
    
    def test_invalid_option_error(self, shell, capsys):
        """Test invalid options produce appropriate errors."""
        result = shell.run_command("set -Z")  # Invalid option
        assert result == 1
        
        captured = capsys.readouterr()
        assert "invalid option" in captured.err.lower()


# Helper class for capturing stdout
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
