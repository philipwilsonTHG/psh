"""
Interactive line editing tests using pexpect.

Tests cursor movement, history navigation, and line editing features
that require a real terminal environment.
"""

import pytest
import os
import sys
import time
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TEST_ROOT))

try:
    import pexpect
    from framework.interactive import InteractivePSHTest, InteractiveTestHelpers
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False
    pexpect = None
    InteractivePSHTest = object  # Dummy for class inheritance
    InteractiveTestHelpers = None

# Only skip if pexpect is not available
pytestmark = [
    pytest.mark.skipif(not HAS_PEXPECT, reason="pexpect not installed")
]


class TestBasicLineEditing(InteractivePSHTest):
    """Test basic line editing functionality."""
    
    # Override inherited method that has incorrect signature
    def test_interactive_sequence(self):
        """Override to prevent fixture error."""
        pytest.skip("Not applicable for line editing tests")
    
    @pytest.mark.skip(reason="PSH line editor escape sequences not working properly in PTY environment")
    def test_cursor_left_right(self):
        """Test cursor movement left and right."""
        self.spawn_shell()
        
        # Type some text
        self.send("hello world")
        
        # Move cursor to beginning
        for _ in range(11):  # Length of "hello world"
            self.send_key('left')
            
        # Insert text at beginning
        self.send("start ")
        
        # Execute
        self.send_key('enter')
        self.expect_exact("start hello world")
        self.expect_prompt()
        
    @pytest.mark.skip(reason="PSH line editor escape sequences not working properly in PTY environment")
    def test_home_end_keys(self):
        """Test Ctrl-A (home) and Ctrl-E (end) keys."""
        self.spawn_shell()
        
        # Type text
        self.send("middle")
        
        # Go to beginning with Ctrl-A
        self.send_control('a')
        self.send("start ")
        
        # Go to end with Ctrl-E
        self.send_control('e')
        self.send(" end")
        
        # Execute
        self.send_key('enter')
        self.expect_exact("start middle end")
        self.expect_prompt()
        
    @pytest.mark.skip(reason="PSH line editor escape sequences not working properly in PTY environment")
    def test_backspace_delete(self):
        """Test backspace and delete keys."""
        self.spawn_shell()
        
        # Type text with error
        self.send("hello wordl")
        
        # Backspace to fix
        self.send_key('backspace')
        self.send("ld")
        
        # Execute
        self.send_key('enter') 
        self.expect_exact("hello world")
        self.expect_prompt()
        
    def test_ctrl_u_clear_line(self):
        """Test Ctrl-U to clear line."""
        self.spawn_shell()
        
        # Type some text
        self.send("this will be cleared")
        
        # Clear with Ctrl-U
        self.send_control('u')
        
        # Type new text
        self.send("echo cleared")
        
        # Execute
        self.send_key('enter')
        self.expect_exact("cleared")
        self.expect_prompt()
        
    def test_ctrl_k_kill_to_end(self):
        """Test Ctrl-K to delete from cursor to end of line."""
        self.spawn_shell()
        
        # Type text
        self.send("keep this remove this")
        
        # Move cursor after "keep this "
        for _ in range(11):  # Length of "remove this"
            self.send_key('left')
            
        # Kill to end of line
        self.send_control('k')
        
        # Execute
        self.send_key('enter')
        self.expect_exact("keep this")
        self.expect_prompt()


class TestHistoryNavigation(InteractivePSHTest):
    """Test command history navigation."""
    
    # Override inherited method that has incorrect signature
    def test_interactive_sequence(self):
        """Override to prevent fixture error."""
        pytest.skip("Not applicable for history tests")
    
    @pytest.mark.skip(reason="PSH line editor escape sequences not working properly in PTY environment")
    def test_up_down_history(self):
        """Test navigating history with up/down arrows."""
        self.spawn_shell()
        
        # Execute some commands
        commands = ["echo first", "echo second", "echo third"]
        for cmd in commands:
            self.send_line(cmd)
            self.expect_prompt()
            
        # Press up arrow to get previous command
        self.send_key('up')
        self.send_key('enter')
        self.expect_exact("third")
        self.expect_prompt()
        
        # Press up twice to get older command
        self.send_key('up')
        self.send_key('up') 
        self.send_key('enter')
        self.expect_exact("second")
        self.expect_prompt()
        
    @pytest.mark.skip(reason="PSH line editor escape sequences not working properly in PTY environment")
    def test_history_search(self):
        """Test Ctrl-R reverse history search."""
        self.spawn_shell()
        
        # Build some history
        self.send_line("echo hello world")
        self.expect_prompt()
        self.send_line("ls -la")
        self.expect_prompt()
        self.send_line("echo goodbye")
        self.expect_prompt()
        
        # Start reverse search with Ctrl-R
        self.send_control('r')
        self.expect("(reverse-i-search)")
        
        # Search for "echo"
        self.send("echo")
        
        # Should find most recent echo command
        self.send_key('enter')
        self.expect_exact("goodbye")
        self.expect_prompt()
        
    @pytest.mark.skip(reason="PSH line editor escape sequences not working properly in PTY environment")
    def test_history_modification(self):
        """Test modifying commands from history."""
        self.spawn_shell()
        
        # Execute a command
        self.send_line("echo original")
        self.expect_prompt()
        
        # Get it from history and modify
        self.send_key('up')
        
        # Move to word and change it
        self.send_control('a')  # Beginning
        self.send_key('right')  # Past 'echo '
        self.send_key('right')
        self.send_key('right')
        self.send_key('right')
        self.send_key('right')
        
        # Delete 'original' and type 'modified'
        self.send_control('k')  # Kill to end
        self.send("modified")
        
        # Execute
        self.send_key('enter')
        self.expect_exact("modified")
        self.expect_prompt()


class TestMultilineEditing(InteractivePSHTest):
    """Test multiline command editing."""
    
    # Override inherited method that has incorrect signature
    def test_interactive_sequence(self):
        """Override to prevent fixture error."""
        pytest.skip("Not applicable for multiline tests")
    
    def test_quote_continuation(self):
        """Test editing across quote continuations."""
        self.spawn_shell()
        
        # Start a multiline string
        self.send_line('echo "first line')
        self.expect_continuation_prompt()
        
        # Add second line
        self.send_line('second line"')
        
        # Should see both lines in output
        self.expect("first line")
        self.expect("second line")
        self.expect_prompt()
        
    def test_backslash_continuation(self):
        """Test backslash line continuation."""
        self.spawn_shell()
        
        # Use backslash continuation
        self.send_line('echo one \\')
        self.expect_continuation_prompt()
        
        self.send_line('two \\')
        self.expect_continuation_prompt()
        
        self.send_line('three')
        
        # Should see all on one line
        self.expect_exact("one two three")
        self.expect_prompt()
        
    def test_cancel_multiline(self):
        """Test canceling multiline input with Ctrl-C."""
        self.spawn_shell()
        
        # Start multiline
        self.send_line('echo "incomplete')
        self.expect_continuation_prompt()
        
        # Cancel with Ctrl-C
        self.send_interrupt()
        
        # Should return to regular prompt
        self.expect_prompt()
        
        # Verify we can continue
        self.send_line("echo ok")
        self.expect_exact("ok")
        self.expect_prompt()


class TestTabCompletion(InteractivePSHTest):
    """Test tab completion functionality."""
    
    # Override inherited method that has incorrect signature
    def test_interactive_sequence(self):
        """Override to prevent fixture error."""
        pytest.skip("Not applicable for tab completion tests")
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.test_dir = os.getcwd()
        
    @pytest.mark.skip(reason="Tab completion requires raw terminal mode")
    def test_file_completion(self):
        """Test filename completion."""
        self.spawn_shell()
        
        # Create test files
        open('testfile1.txt', 'w').close()
        open('testfile2.txt', 'w').close()
        open('other.txt', 'w').close()
        
        # Type partial filename and tab
        self.send("cat test")
        self.send_key('tab')
        
        # Should show both testfile options
        self.expect("testfile1.txt")
        self.expect("testfile2.txt")
        
        # Continue typing to disambiguate
        self.send("file1")
        self.send_key('tab')
        
        # Should complete to full filename
        self.send_key('enter')
        self.expect_prompt()
        
    @pytest.mark.skip(reason="Tab completion requires raw terminal mode")
    def test_command_completion(self):
        """Test command name completion."""
        self.spawn_shell()
        
        # Test builtin completion
        self.send("ech")
        self.send_key('tab')
        
        # Should complete to echo
        self.send(" completed")
        self.send_key('enter')
        self.expect_exact("completed")
        self.expect_prompt()
        
    @pytest.mark.skip(reason="Tab completion requires raw terminal mode")
    def test_variable_completion(self):
        """Test variable name completion.""" 
        self.spawn_shell()
        
        # Set some variables
        self.send_line("MYVAR1=value1")
        self.expect_prompt()
        self.send_line("MYVAR2=value2")
        self.expect_prompt()
        
        # Test completion
        self.send("echo $MYV")
        self.send_key('tab')
        
        # Should show both options
        self.expect("MYVAR1")
        self.expect("MYVAR2")


class TestSpecialKeySequences(InteractivePSHTest):
    """Test special key sequences and combinations."""
    
    # Override inherited method that has incorrect signature
    def test_interactive_sequence(self):
        """Override to prevent fixture error."""
        pytest.skip("Not applicable for special key tests")
    
    def test_ctrl_d_eof(self):
        """Test Ctrl-D for EOF."""
        self.spawn_shell()
        
        # Ctrl-D on empty line should exit
        self.send_eof()
        self.shell.expect(pexpect.EOF)
        
    def test_ctrl_l_clear_screen(self):
        """Test Ctrl-L to clear screen."""
        self.spawn_shell()
        
        # Generate some output
        self.send_line("echo line1")
        self.expect_prompt()
        self.send_line("echo line2")
        self.expect_prompt()
        
        # Clear screen
        self.send_control('l')
        
        # Prompt should be at top (hard to test precisely)
        # Just verify shell still works
        self.send_line("echo cleared")
        self.expect_exact("cleared")
        self.expect_prompt()
        
    @pytest.mark.skip(reason="Job control tests require special terminal handling")
    def test_ctrl_z_suspend(self):
        """Test Ctrl-Z to suspend job."""
        self.spawn_shell()
        
        # Start a long-running command
        self.send_line("sleep 30")

        
        # Suspend with Ctrl-Z
        self.send_suspend()
        self.expect("Stopped")
        self.expect_prompt()
        
        # Verify job is suspended
        self.send_line("jobs")
        self.expect("[1]")
        self.expect("Stopped")
        self.expect("sleep 30")
        self.expect_prompt()