"""Test shell options functionality."""
import pytest
import sys
import io
from contextlib import redirect_stderr
from psh.shell import Shell

class TestShellOptions:
    """Test shell options (-e, -u, -x, -o pipefail)."""
    
    def test_xtrace_basic(self):
        """Test basic xtrace functionality."""
        shell = Shell()
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            # Enable xtrace
            shell.run_command("set -x")
            # Execute a simple command
            shell.run_command("echo hello")
            # Disable xtrace
            shell.run_command("set +x")
            # This should not be traced
            shell.run_command("echo world")
        
        stderr_output = stderr_capture.getvalue()
        
        # Check that echo hello was traced
        assert "+ echo hello" in stderr_output
        # Check that echo world was not traced after +x
        assert "+ echo world" not in stderr_output
    
    def test_xtrace_with_variables(self):
        """Test xtrace with variable expansion."""
        shell = Shell()
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            shell.run_command("x=hello")
            shell.run_command("set -x")
            shell.run_command("echo $x world")
        
        stderr_output = stderr_capture.getvalue()
        # Should show expanded command
        assert "+ echo hello world" in stderr_output
    
    def test_xtrace_control_structures(self):
        """Test xtrace with control structures."""
        shell = Shell()
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            shell.run_command("set -x")
            shell.run_command("if true; then echo yes; fi")
        
        stderr_output = stderr_capture.getvalue()
        # Should show control structure traces
        assert "+ if" in stderr_output
        assert "+ true" in stderr_output
        assert "+ echo yes" in stderr_output
    
    def test_xtrace_for_loop(self):
        """Test xtrace with for loops."""
        shell = Shell()
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            shell.run_command("set -x")
            shell.run_command("for i in 1 2; do echo $i; done")
        
        stderr_output = stderr_capture.getvalue()
        # Should show for loop traces
        assert "+ for i in" in stderr_output
        assert "+ echo 1" in stderr_output
        assert "+ echo 2" in stderr_output
    
    def test_xtrace_while_loop(self):
        """Test xtrace with while loops."""
        shell = Shell()
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            shell.run_command("set -x")
            shell.run_command("i=0; while [ $i -lt 2 ]; do echo $i; i=$((i+1)); done")
        
        stderr_output = stderr_capture.getvalue()
        # Should show while loop traces
        assert "+ while" in stderr_output
        assert "+ [ 0 -lt 2 ]" in stderr_output
        assert "+ echo 0" in stderr_output
    
    @pytest.mark.xfail(reason="stderr capture doesn't work properly with forked processes in pipelines")
    def test_xtrace_pipeline(self):
        """Test xtrace with pipelines."""
        shell = Shell()
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            shell.run_command("set -x")
            shell.run_command("echo hello | cat")
        
        stderr_output = stderr_capture.getvalue()
        # Should show both commands in pipeline
        # Note: This works in actual shell usage but fails in test due to
        # pytest's stderr capture not working with forked processes
        assert "+ echo hello" in stderr_output
        assert "+ cat" in stderr_output
    
    def test_xtrace_combined_options(self):
        """Test xtrace combined with other options."""
        shell = Shell()
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            # Set multiple options at once
            shell.run_command("set -eux")
            shell.run_command("echo test")
            # Check options are set
            result = shell.run_command("set -o | grep -E 'xtrace|errexit|nounset'")
        
        stderr_output = stderr_capture.getvalue()
        assert "+ echo test" in stderr_output
    
    def test_set_option_display(self):
        """Test displaying shell options."""
        shell = Shell()
        
        # Capture output of set -o
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "psh", "-c", "set -o"],
            capture_output=True,
            text=True
        )
        
        output = result.stdout
        # Check that all options are displayed
        assert "errexit" in output
        assert "nounset" in output
        assert "xtrace" in output
        assert "pipefail" in output
        assert "debug-ast" in output
        assert "debug-tokens" in output
        assert "debug-scopes" in output
    
    def test_short_option_syntax(self):
        """Test short option syntax (-e, -u, -x)."""
        shell = Shell()
        
        # Test setting options
        shell.run_command("set -e")
        assert shell.state.options['errexit'] is True
        
        shell.run_command("set -u")
        assert shell.state.options['nounset'] is True
        
        shell.run_command("set -x")
        assert shell.state.options['xtrace'] is True
        
        # Test unsetting options
        shell.run_command("set +e")
        assert shell.state.options['errexit'] is False
        
        shell.run_command("set +u")
        assert shell.state.options['nounset'] is False
        
        shell.run_command("set +x")
        assert shell.state.options['xtrace'] is False
    
    def test_long_option_syntax(self):
        """Test long option syntax (-o option)."""
        shell = Shell()
        
        # Test setting options
        shell.run_command("set -o errexit")
        assert shell.state.options['errexit'] is True
        
        shell.run_command("set -o nounset")
        assert shell.state.options['nounset'] is True
        
        shell.run_command("set -o xtrace")
        assert shell.state.options['xtrace'] is True
        
        shell.run_command("set -o pipefail")
        assert shell.state.options['pipefail'] is True
        
        # Test unsetting options
        shell.run_command("set +o errexit")
        assert shell.state.options['errexit'] is False
        
        shell.run_command("set +o pipefail")
        assert shell.state.options['pipefail'] is False
    
    def test_combined_short_options(self):
        """Test combined short options (-eux)."""
        shell = Shell()
        
        # Set multiple options at once
        shell.run_command("set -eux")
        assert shell.state.options['errexit'] is True
        assert shell.state.options['nounset'] is True
        assert shell.state.options['xtrace'] is True
        
        # Unset multiple options at once
        shell.run_command("set +eux")
        assert shell.state.options['errexit'] is False
        assert shell.state.options['nounset'] is False
        assert shell.state.options['xtrace'] is False
    
    def test_invalid_option_error(self):
        """Test error handling for invalid options."""
        shell = Shell()
        
        # Test invalid short option
        result = shell.run_command("set -z")
        assert result != 0  # Should return error
        
        # Test invalid long option
        result = shell.run_command("set -o invalid")
        assert result != 0  # Should return error