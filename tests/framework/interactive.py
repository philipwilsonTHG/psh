"""
Interactive test framework for PSH using pexpect.

Provides utilities for testing interactive shell features like:
- Line editing (cursor movement, history)
- Tab completion
- Signal handling (Ctrl-C, Ctrl-Z)
- Job control
- Multiline input
"""

import os
import signal
import sys
from pathlib import Path
from typing import List, Optional, Union

try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False
    pexpect = None

# Add PSH to path
PSH_ROOT = Path(__file__).parent.parent.parent
PSH_EXECUTABLE = [sys.executable, '-m', 'psh']


class InteractivePSHTest:
    """Base class for interactive shell tests using pexpect."""

    @classmethod
    def setup_class(cls):
        """Check for pexpect availability."""
        if not HAS_PEXPECT:
            raise ImportError("pexpect module required for interactive tests. Install with: pip install pexpect")

    def setup_method(self):
        """Set up before each test."""
        self.shell = None
        # Use flexible prompt pattern to match any prompt ending with $
        self.prompt = r'.*\$'  # Matches any prompt ending with $
        self.continuation_prompt = r'> '  # PS2 prompt pattern
        self.original_dir = os.getcwd()

    def teardown_method(self):
        """Clean up after each test."""
        self.safe_cleanup(self.shell)
        os.chdir(self.original_dir)

    def safe_cleanup(self, shell):
        """Safely clean up a pexpect shell process."""
        if shell is None:
            return

        try:
            # Check if process is still alive
            if shell.isalive():
                # Try graceful termination first
                shell.sendline('exit')
                try:
                    shell.expect(pexpect.EOF, timeout=2)
                except:
                    pass

            # If still alive, force termination
            if shell.isalive():
                shell.terminate(force=True)

            # Wait for cleanup
            try:
                shell.wait()
            except:
                pass

        except Exception:
            # If cleanup fails, try force kill
            try:
                if hasattr(shell, 'pid') and shell.pid:
                    os.kill(shell.pid, signal.SIGKILL)
            except:
                pass

    def spawn_shell(self, env=None, extra_args=None):
        """Spawn interactive PSH process with proper settings."""
        if env is None:
            env = os.environ.copy()

        # Ensure PSH can be found
        env['PYTHONPATH'] = str(PSH_ROOT)
        env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output

        args = ['-u', '-m', 'psh', '--norc', '--force-interactive']
        if extra_args:
            args.extend(extra_args)

        shell = pexpect.spawn(
            sys.executable, args,
            timeout=5,
            encoding='utf-8',
            env=env
        )

        # PSH needs a newline to show initial prompt in PTY mode
        shell.send('\r')

        # Wait for initial prompt
        index = shell.expect([self.prompt, pexpect.TIMEOUT], timeout=3)
        if index != 0:
            self.safe_cleanup(shell)
            raise RuntimeError(f"Failed to get initial prompt. Buffer: '{shell.buffer}', Before: '{shell.before}'")

        self.shell = shell
        return shell

    def send_line(self, line: str):
        """Send a line to the shell."""
        # PSH expects just \r, not \r\n
        self.shell.send(line + '\r')

    def send(self, text: str):
        """Send text without newline."""
        self.shell.send(text)

    def send_control(self, char: str):
        """Send control character (e.g., 'c' for Ctrl-C)."""
        self.shell.sendcontrol(char)

    def send_interrupt(self):
        """Send Ctrl-C to interrupt."""
        self.send_control('c')

    def send_eof(self):
        """Send Ctrl-D for EOF."""
        self.send_control('d')

    def send_suspend(self):
        """Send Ctrl-Z to suspend."""
        self.send_control('z')

    def send_key(self, key: str):
        """Send special key sequences."""
        key_map = {
            'up': '\033[A',
            'down': '\033[B',
            'right': '\033[C',
            'left': '\033[D',
            'home': '\001',  # Ctrl-A
            'end': '\005',   # Ctrl-E
            'tab': '\t',
            'enter': '\r',
            'backspace': '\177',
            'delete': '\033[3~',
        }
        if key in key_map:
            self.shell.send(key_map[key])
        else:
            raise ValueError(f"Unknown key: {key}")

    def expect_prompt(self, timeout: Optional[int] = None):
        """Wait for shell prompt."""
        return self.shell.expect(self.prompt, timeout=timeout)

    def expect_continuation_prompt(self, timeout: Optional[int] = None):
        """Wait for continuation prompt (PS2)."""
        self.shell.expect(self.continuation_prompt, timeout=timeout)

    def expect(self, pattern: Union[str, List[str]], timeout: Optional[int] = None) -> int:
        """Expect pattern(s) in output."""
        return self.shell.expect(pattern, timeout=timeout)

    def expect_exact(self, text: str, timeout: Optional[int] = None):
        """Expect exact text in output."""
        self.shell.expect_exact(text, timeout=timeout)

    def get_output(self) -> str:
        """Get all output since last expect."""
        return self.shell.before if self.shell.before else ""

    def get_output_lines(self) -> List[str]:
        """Get output as list of lines."""
        return self.get_output().strip().split('\n')

    def assert_output_contains(self, expected: str):
        """Assert output contains expected string."""
        output = self.get_output()
        assert expected in output, f"Expected '{expected}' in output:\n{output}"

    def assert_output_matches(self, pattern: str):
        """Assert output matches regex pattern."""
        import re
        output = self.get_output()
        assert re.search(pattern, output), f"Pattern '{pattern}' not found in output:\n{output}"

    def run_command(self, command: str) -> str:
        """Run a command and return output."""
        self.send_line(command)
        self.expect_prompt()
        return self.get_output().strip()


class InteractiveTestHelpers:
    """Helper methods for common interactive test patterns."""

    @staticmethod
    def test_line_editing(test: InteractivePSHTest, initial: str,
                         edits: List[tuple], expected: str):
        """Test line editing operations."""
        # Type initial text
        test.send(initial)

        # Apply edits
        for action, *args in edits:
            if action == 'move':
                test.send_key(args[0])
            elif action == 'delete':
                for _ in range(args[0] if args else 1):
                    test.send_key('backspace')
            elif action == 'insert':
                test.send(args[0])
            elif action == 'control':
                test.send_control(args[0])

        # Execute and check
        test.send_key('enter')
        test.expect_exact(expected)
        test.expect_prompt()

    @staticmethod
    def test_history_navigation(test: InteractivePSHTest,
                              commands: List[str],
                              navigate_to: int):
        """Test history navigation."""
        # Execute commands to build history
        for cmd in commands:
            test.run_command(cmd)

        # Navigate in history
        if navigate_to < 0:
            # Navigate up
            for _ in range(abs(navigate_to)):
                test.send_key('up')
        else:
            # Navigate down
            for _ in range(navigate_to):
                test.send_key('down')

        # Execute the navigated command
        test.send_key('enter')
        test.expect_prompt()
