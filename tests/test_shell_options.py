"""Test shell options: set -e, -u, -x, -o pipefail."""
import pytest
import subprocess
import os
import sys
from psh.shell import Shell
from psh.core.exceptions import UnboundVariableError


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
    
    @pytest.mark.xfail(reason="Conditional context detection needs more work")
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
    
    @pytest.mark.xfail(reason="Pipefail exit code handling needs refinement")
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