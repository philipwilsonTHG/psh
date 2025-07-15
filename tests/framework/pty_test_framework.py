"""
Enhanced PTY test framework for PSH interactive testing.

This framework provides improved PTY handling for testing interactive features
that require real terminal emulation, including:
- Line editing with cursor movement
- History navigation
- Tab completion
- Signal handling
- Job control

Key improvements over basic pexpect approach:
- Better escape sequence handling
- More reliable prompt detection
- Improved buffering control
- Debug output capabilities
"""

import os
import sys
import time
import re
import signal
from pathlib import Path
from typing import Optional, List, Union, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

try:
    import pexpect
    import ptyprocess
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False
    pexpect = None
    ptyprocess = None

import pytest

# Add PSH to path
PSH_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PSH_ROOT))


@dataclass
class PTYTestConfig:
    """Configuration for PTY tests."""
    timeout: int = 5
    prompt_pattern: str = r'\$ '  # More specific prompt pattern
    continuation_pattern: str = r'> '
    debug: bool = False
    encoding: str = 'utf-8'
    columns: int = 80
    rows: int = 24
    env: Optional[dict] = None
    extra_args: Optional[List[str]] = None


class PTYTestFramework:
    """Enhanced framework for PTY-based interactive testing."""
    
    def __init__(self, config: Optional[PTYTestConfig] = None):
        """Initialize framework with configuration."""
        if not HAS_PEXPECT:
            raise ImportError("pexpect required for PTY tests. Install with: pip install pexpect")
        
        self.config = config or PTYTestConfig()
        self.shell = None
        self.logfile = None
        self._output_buffer = []
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        
    def cleanup(self):
        """Clean up shell process and resources."""
        if self.shell:
            try:
                if self.shell.isalive():
                    # Try graceful exit
                    self.shell.sendline('exit')
                    self.shell.expect(pexpect.EOF, timeout=1)
            except:
                pass
            
            try:
                if self.shell.isalive():
                    self.shell.terminate(force=True)
                self.shell.wait()
            except:
                pass
            
            self.shell = None
            
        if self.logfile:
            try:
                self.logfile.close()
            except:
                pass
            self.logfile = None
    
    def spawn_shell(self) -> pexpect.spawn:
        """Spawn PSH with proper PTY settings."""
        # Set up environment
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)
        
        # Force unbuffered I/O
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONPATH'] = str(PSH_ROOT)
        
        # Disable readline if it causes issues
        env['INPUTRC'] = '/dev/null'
        
        # Build command
        cmd = [sys.executable, '-u', '-m', 'psh', '--norc', '--force-interactive']
        if self.config.extra_args:
            cmd.extend(self.config.extra_args)
        
        # Enable debug logging if requested
        if self.config.debug:
            self.logfile = sys.stdout
        
        # Spawn with specific terminal dimensions
        self.shell = pexpect.spawn(
            cmd[0], cmd[1:],
            timeout=self.config.timeout,
            encoding=self.config.encoding,
            dimensions=(self.config.rows, self.config.columns),
            env=env,
            logfile=self.logfile
        )
        
        # Set more aggressive buffering options
        self.shell.setecho(False)  # Don't echo input
        self.shell.delaybeforesend = 0.05  # Small delay between sends
        
        # Wait for initial prompt with retries
        self._wait_for_prompt(initial=True)
        
        return self.shell
    
    def _wait_for_prompt(self, initial: bool = False, timeout: Optional[int] = None):
        """Wait for prompt with better error handling."""
        timeout = timeout or self.config.timeout
        
        if initial:
            # For initial prompt, PSH might need a nudge
            time.sleep(0.1)
            self.shell.send('\r')
        
        try:
            index = self.shell.expect([
                self.config.prompt_pattern,
                self.config.continuation_pattern,
                pexpect.TIMEOUT,
                pexpect.EOF
            ], timeout=timeout)
            
            if index == 2:  # TIMEOUT
                raise TimeoutError(f"Prompt timeout. Buffer: {self.shell.buffer}")
            elif index == 3:  # EOF
                raise EOFError("Shell terminated unexpectedly")
                
            return index == 0  # True if normal prompt, False if continuation
            
        except Exception as e:
            if self.config.debug:
                print(f"Prompt wait failed: {e}")
                print(f"Buffer: {repr(self.shell.buffer)}")
                print(f"Before: {repr(self.shell.before)}")
            raise
    
    def send_line(self, line: str):
        """Send a line with proper line ending."""
        self.shell.send(line + '\r')
        
    def send_text(self, text: str):
        """Send text without line ending."""
        self.shell.send(text)
        
    def send_key_sequence(self, sequence: str):
        """Send raw escape sequence."""
        self.shell.send(sequence)
        
    def send_arrow_key(self, direction: str):
        """Send arrow key escape sequence."""
        sequences = {
            'up': '\033[A',
            'down': '\033[B',
            'right': '\033[C',
            'left': '\033[D'
        }
        if direction not in sequences:
            raise ValueError(f"Unknown arrow direction: {direction}")
        self.shell.send(sequences[direction])
        
    def send_ctrl(self, char: str):
        """Send control character."""
        if len(char) != 1:
            raise ValueError("Control character must be single character")
        # Convert to control code
        ctrl_code = ord(char.upper()) - ord('A') + 1
        self.shell.send(chr(ctrl_code))
        
    def expect_output(self, pattern: Union[str, re.Pattern], timeout: Optional[int] = None) -> str:
        """Expect pattern and return matched output."""
        timeout = timeout or self.config.timeout
        
        if isinstance(pattern, str):
            # For exact string match, look for it anywhere in the output
            index = self.shell.expect([re.escape(pattern)], timeout=timeout)
        else:
            index = self.shell.expect([pattern], timeout=timeout)
            
        # Return everything before the match plus the match itself
        return self.shell.before + (self.shell.match.group(0) if self.shell.match else "")
        
    def run_command(self, cmd: str) -> str:
        """Run command and return output."""
        self.send_line(cmd)
        self._wait_for_prompt()
        
        # Get output and clean it up
        output = self.shell.before
        if output:
            # Remove the echoed command if present
            lines = output.strip().split('\n')
            # If first line contains the command, remove it
            if lines and cmd in lines[0]:
                lines = lines[1:]
            return '\n'.join(lines).strip()
        return ""
        
    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position using ANSI escape sequence."""
        # Send cursor position request
        self.shell.send('\033[6n')
        
        # Expect response in format ESC[row;colR
        try:
            self.shell.expect(r'\033\[(\d+);(\d+)R', timeout=1)
            match = self.shell.match
            if match:
                row = int(match.group(1))
                col = int(match.group(2))
                return (row, col)
        except:
            pass
            
        return (-1, -1)
        
    def assert_cursor_at_column(self, expected_col: int):
        """Assert cursor is at expected column."""
        _, col = self.get_cursor_position()
        assert col == expected_col, f"Expected cursor at column {expected_col}, got {col}"
        
    def capture_screen_content(self) -> str:
        """Capture current screen content."""
        # This is a simplified version - real implementation would need
        # to track all output and cursor movements
        return self.shell.before or ""


class PTYTest:
    """Base class for PTY-based tests."""
    
    @pytest.fixture
    def pty_framework(self):
        """Provide PTY test framework."""
        config = PTYTestConfig(debug=False)  # Set True for debugging
        framework = PTYTestFramework(config)
        yield framework
        framework.cleanup()
        
    @pytest.fixture
    def shell(self, pty_framework):
        """Provide spawned shell."""
        return pty_framework.spawn_shell()


# Helper functions for common test patterns

@contextmanager
def interactive_shell(config: Optional[PTYTestConfig] = None):
    """Context manager for interactive shell testing."""
    framework = PTYTestFramework(config)
    try:
        shell = framework.spawn_shell()
        yield framework
    finally:
        framework.cleanup()


def validate_line_editing_sequence(framework: PTYTestFramework, 
                              initial_text: str,
                              edit_sequence: List[Tuple[str, str]],
                              expected_result: str):
    """Test a sequence of line editing operations.
    
    Args:
        framework: PTY test framework
        initial_text: Initial text to type
        edit_sequence: List of (action, argument) tuples
        expected_result: Expected final result
    """
    # Type initial text
    framework.send_text(initial_text)
    
    # Apply edit sequence
    for action, arg in edit_sequence:
        if action == 'left':
            for _ in range(int(arg)):
                framework.send_arrow_key('left')
        elif action == 'right':
            for _ in range(int(arg)):
                framework.send_arrow_key('right')
        elif action == 'home':
            framework.send_ctrl('a')
        elif action == 'end':
            framework.send_ctrl('e')
        elif action == 'insert':
            framework.send_text(arg)
        elif action == 'delete':
            framework.send_key_sequence('\033[3~')
        elif action == 'backspace':
            framework.send_text('\177')
        time.sleep(0.05)  # Small delay between operations
    
    # Execute and check result
    framework.send_text('\r')
    output = framework.expect_output(expected_result)
    framework._wait_for_prompt()
    
    return output