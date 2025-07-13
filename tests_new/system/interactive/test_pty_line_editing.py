"""
PTY-based line editing tests using enhanced framework.

These tests verify line editing functionality that requires real terminal
emulation, such as cursor movement and character manipulation.
"""

import pytest
import sys
import time
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TEST_ROOT))

try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False

from framework.pty_test_framework import (
    PTYTestFramework, PTYTestConfig, PTYTest,
    interactive_shell, validate_line_editing_sequence
)

# Skip all tests if pexpect not available
pytestmark = pytest.mark.skipif(not HAS_PEXPECT, reason="pexpect not installed")


class TestPTYLineEditing(PTYTest):
    """Test line editing with real PTY."""
    
    def test_basic_text_entry(self, pty_framework):
        """Test basic text entry and execution."""
        shell = pty_framework.spawn_shell()
        
        # Use run_command for simpler interaction
        output = pty_framework.run_command("echo hello world")
        assert "hello world" in output
        
    @pytest.mark.xfail(reason="PSH line editor not handling arrow keys properly in PTY mode")
    def test_cursor_movement_left_right(self, pty_framework):
        """Test moving cursor left and right."""
        shell = pty_framework.spawn_shell()
        
        # Type text
        pty_framework.send_text("hello world")
        
        # Move cursor to beginning of "world"
        for _ in range(5):  # Move past "world"
            pty_framework.send_arrow_key('left')
            time.sleep(0.05)
        
        # Insert text
        pty_framework.send_text("brave ")
        
        # Execute
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("hello brave world")
        pty_framework._wait_for_prompt()
        
    @pytest.mark.xfail(reason="PSH line editor not handling control keys properly in PTY mode")
    def test_home_end_keys(self, pty_framework):
        """Test Ctrl-A (home) and Ctrl-E (end)."""
        shell = pty_framework.spawn_shell()
        
        # Type text
        pty_framework.send_text("middle")
        
        # Go to beginning
        pty_framework.send_ctrl('a')
        time.sleep(0.05)
        
        # Insert at beginning
        pty_framework.send_text("start ")
        
        # Go to end
        pty_framework.send_ctrl('e')
        time.sleep(0.05)
        
        # Insert at end
        pty_framework.send_text(" end")
        
        # Execute
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("start middle end")
        pty_framework._wait_for_prompt()
        
    @pytest.mark.xfail(reason="PSH line editor backspace handling issues in PTY mode")
    def test_delete_operations(self, pty_framework):
        """Test backspace and delete operations."""
        shell = pty_framework.spawn_shell()
        
        # Type text with typo
        pty_framework.send_text("hello worlld")
        
        # Backspace to remove extra 'l'
        pty_framework.send_text('\177')  # Backspace
        
        # Execute
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("hello world")
        pty_framework._wait_for_prompt()
        
    def test_ctrl_u_clear_line(self, pty_framework):
        """Test Ctrl-U to clear line."""
        shell = pty_framework.spawn_shell()
        
        # Type text
        pty_framework.send_text("this will be cleared")
        
        # Clear line
        pty_framework.send_ctrl('u')
        time.sleep(0.05)
        
        # Type new text
        pty_framework.send_text("echo cleared")
        
        # Execute
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("cleared")
        pty_framework._wait_for_prompt()
        
    def test_ctrl_k_kill_to_end(self, pty_framework):
        """Test Ctrl-K to kill to end of line."""
        shell = pty_framework.spawn_shell()
        
        # Type text
        pty_framework.send_text("echo keep this remove this")
        
        # Move cursor after "this"
        for _ in range(11):  # " remove this"
            pty_framework.send_arrow_key('left')
            time.sleep(0.05)
        
        # Kill to end
        pty_framework.send_ctrl('k')
        time.sleep(0.05)
        
        # Execute
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("keep this")
        pty_framework._wait_for_prompt()
        
    @pytest.mark.xfail(reason="PSH history navigation not working properly in PTY mode")
    def test_history_navigation(self, pty_framework):
        """Test up/down arrow history navigation."""
        shell = pty_framework.spawn_shell()
        
        # Execute some commands
        pty_framework.run_command("echo first")
        pty_framework.run_command("echo second")
        pty_framework.run_command("echo third")
        
        # Press up arrow to get previous command
        pty_framework.send_arrow_key('up')
        time.sleep(0.1)
        
        # Execute (should be "echo third")
        pty_framework.send_text('\r')
        output = pty_framework.expect_output("third")
        pty_framework._wait_for_prompt()
        
        # Press up twice to get "echo second"
        pty_framework.send_arrow_key('up')
        time.sleep(0.05)
        pty_framework.send_arrow_key('up')
        time.sleep(0.05)
        
        # Execute
        pty_framework.send_text('\r')
        output = pty_framework.expect_output("second")
        pty_framework._wait_for_prompt()
        
    def test_ctrl_w_delete_word(self, pty_framework):
        """Test Ctrl-W to delete word backward."""
        shell = pty_framework.spawn_shell()
        
        # Type text
        pty_framework.send_text("echo one two three")
        
        # Delete last word
        pty_framework.send_ctrl('w')
        time.sleep(0.05)
        
        # Execute
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("one two")
        pty_framework._wait_for_prompt()
        
    @pytest.mark.xfail(reason="PSH multiline handling in PTY mode")
    def test_multiline_editing(self, pty_framework):
        """Test editing across multiple lines."""
        shell = pty_framework.spawn_shell()
        
        # Start multiline command
        pty_framework.send_text("echo \\")
        pty_framework.send_text('\r')
        
        # Should see continuation prompt
        time.sleep(0.1)
        
        # Continue on next line
        pty_framework.send_text("  hello \\")
        pty_framework.send_text('\r')
        
        # Final line
        pty_framework.send_text("  world")
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("hello world")
        pty_framework._wait_for_prompt()
        
    def test_tab_completion_basic(self, pty_framework):
        """Test basic tab completion."""
        shell = pty_framework.spawn_shell()
        
        # Create a test file
        pty_framework.run_command("touch test_file.txt")
        
        # Start typing filename
        pty_framework.send_text("echo test_f")
        
        # Press tab
        pty_framework.send_text('\t')
        time.sleep(0.1)
        
        # Complete the command
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("test_file.txt")
        pty_framework._wait_for_prompt()
        
        # Cleanup
        pty_framework.run_command("rm test_file.txt")
        
    @pytest.mark.xfail(reason="PSH interrupt handling issues in PTY mode")
    def test_interrupt_during_editing(self, pty_framework):
        """Test Ctrl-C interrupt during line editing."""
        shell = pty_framework.spawn_shell()
        
        # Start typing a command
        pty_framework.send_text("echo this will be interrupted")
        
        # Send interrupt
        pty_framework.send_ctrl('c')
        time.sleep(0.1)
        
        # Should get new prompt, type new command
        pty_framework.send_text("echo survived")
        pty_framework.send_text('\r')
        
        # Check output
        output = pty_framework.expect_output("survived")
        pty_framework._wait_for_prompt()


class TestPTYEdgesCases(PTYTest):
    """Test edge cases in PTY line editing."""
    
    def test_very_long_line(self, pty_framework):
        """Test editing very long lines."""
        shell = pty_framework.spawn_shell()
        
        # Create a long line
        long_text = "x" * 100
        pty_framework.send_text(f"echo {long_text}")
        
        # Go to beginning
        pty_framework.send_ctrl('a')
        time.sleep(0.05)
        
        # Skip past "echo "
        for _ in range(5):
            pty_framework.send_arrow_key('right')
            time.sleep(0.02)
        
        # Insert marker
        pty_framework.send_text("START")
        
        # Execute
        pty_framework.send_text('\r')
        
        # Check output contains marker
        output = pty_framework.expect_output("START")
        pty_framework._wait_for_prompt()


if __name__ == '__main__':
    # Run with debug output if executed directly
    config = PTYTestConfig(debug=True)
    with interactive_shell(config) as framework:
        print("Interactive shell started. Testing basic command...")
        output = framework.run_command("echo test")
        print(f"Output: {output}")