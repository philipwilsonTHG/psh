"""
Working interactive tests based on actual PSH behavior.
"""

import os
import sys
from pathlib import Path

import pexpect


class TestWorkingInteractive:
    """Interactive tests that work with PSH's actual behavior."""

    def spawn_psh(self):
        """Spawn PSH with proper settings."""
        env = os.environ.copy()
        psh_root = Path(__file__).parent.parent.parent.parent
        env['PYTHONPATH'] = str(psh_root)
        # Force unbuffered output
        env['PYTHONUNBUFFERED'] = '1'

        shell = pexpect.spawn(
            sys.executable, ['-u', '-m', 'psh', '--norc', '--force-interactive'],
            timeout=5,
            encoding='utf-8',
            env=env
        )

        # PSH needs a newline to show initial prompt in PTY mode
        shell.send('\r')

        return shell

    def test_echo_output(self):
        """Test that echo produces output."""
        shell = self.spawn_psh()

        # Enable logging for debugging
        shell.logfile_read = sys.stdout

        # Wait for initial prompt - PSH shows it after the initial newline
        index = shell.expect([r'.*\$', pexpect.TIMEOUT], timeout=3)
        assert index == 0, f"Did not find initial prompt. Buffer: '{shell.buffer}', Before: '{shell.before}'"

        # Send echo command
        shell.send('echo hello world\r')

        # The output appears between the command echo and the next prompt
        # We need to look for the output text
        index = shell.expect(['hello world', pexpect.TIMEOUT])
        assert index == 0, "Did not find expected output"

        # Now wait for the next prompt
        shell.expect(r'.*\$')

        # Clean up
        shell.send('exit\r')
        shell.expect(pexpect.EOF)

    def test_multiple_commands(self):
        """Test executing multiple commands."""
        shell = self.spawn_psh()

        # Wait for prompt
        shell.expect(r'.*\$')

        # First command
        shell.send('echo first\r')
        shell.expect('first')
        shell.expect(r'.*\$')

        # Second command
        shell.send('echo second\r')
        shell.expect('second')
        shell.expect(r'.*\$')

        # Exit
        shell.send('exit\r')
        shell.expect(pexpect.EOF)

    def test_variable(self):
        """Test variable assignment and usage."""
        shell = self.spawn_psh()

        # Wait for prompt
        shell.expect(r'.*\$')

        # Set variable
        shell.send('X=hello\r')
        shell.expect(r'.*\$')

        # Use variable
        shell.send('echo $X\r')
        shell.expect('hello')
        shell.expect(r'.*\$')

        # Exit
        shell.send('exit\r')
        shell.expect(pexpect.EOF)

    def test_exit_code(self):
        """Test exit code reporting."""
        shell = self.spawn_psh()

        # Wait for prompt
        shell.expect(r'.*\$')

        # Run true
        shell.send('true\r')
        shell.expect(r'.*\$')

        # Check exit code
        shell.send('echo $?\r')
        shell.expect('0')
        shell.expect(r'.*\$')

        # Run false
        shell.send('false\r')
        shell.expect(r'.*\$')

        # Check exit code
        shell.send('echo $?\r')
        shell.expect('1')
        shell.expect(r'.*\$')

        # Exit
        shell.send('exit\r')
        shell.expect(pexpect.EOF)

    def test_pipeline(self):
        """Test simple pipeline."""
        shell = self.spawn_psh()

        # Wait for prompt
        shell.expect(r'.*\$')

        # Run pipeline
        shell.send('echo "hello world" | grep world\r')
        shell.expect('hello world')
        shell.expect(r'.*\$')

        # Exit
        shell.send('exit\r')
        shell.expect(pexpect.EOF)

    def test_multiline_input(self):
        """Test multiline string input."""
        shell = self.spawn_psh()

        # Wait for prompt
        shell.expect(r'.*\$')

        # Start multiline string
        shell.send('echo "line1\r')

        # Should get continuation prompt
        shell.expect('> ')

        # Continue string
        shell.send('line2"\r')

        # Should see output with newline
        shell.expect('line1')
        shell.expect('line2')
        shell.expect(r'.*\$')

        # Exit
        shell.send('exit\r')
        shell.expect(pexpect.EOF)
