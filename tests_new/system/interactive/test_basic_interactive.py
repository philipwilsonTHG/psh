"""
Basic interactive tests that work with PSH's actual behavior.
"""

import sys
import os
from pathlib import Path
import pytest
import pexpect
import time


class TestBasicInteractive:
    """Basic interactive tests without using the framework."""
    
    def spawn_psh(self):
        """Spawn PSH with proper settings."""
        # Ensure PSH can be found
        env = os.environ.copy()
        psh_root = Path(__file__).parent.parent.parent.parent
        env['PYTHONPATH'] = str(psh_root)
        env['PYTHONUNBUFFERED'] = '1'
        
        return pexpect.spawn(
            sys.executable, ['-u', '-m', 'psh', '--norc', '--force-interactive'],
            timeout=10,  # Increased timeout for slower systems
            encoding='utf-8',
            env=env
        )
    
    def test_echo_simple(self):
        """Test simple echo command."""
        shell = self.spawn_psh()
        
        # Small delay to ensure PSH is ready
        import time
        time.sleep(0.1)
        
        try:
            # Wait for initial prompt - match any prompt ending with $
            shell.expect(r'.*\$ ')
        except pexpect.TIMEOUT as e:
            # Debug output on timeout
            print(f"\nDEBUG: Failed to get initial prompt")
            print(f"Shell alive: {shell.isalive()}")
            print(f"Buffer: {repr(shell.buffer)}")
            print(f"Before: {repr(shell.before)}")
            raise
        
        # Send command - use send() with \r instead of sendline()
        shell.send('echo hello\r')
        
        try:
            # Wait for the command echo
            shell.expect('echo hello')
            # Wait for the output
            shell.expect('hello')
            # Wait for the prompt
            shell.expect(r'.*\$ ')
        except pexpect.TIMEOUT as e:
            # Debug output on timeout
            print(f"\nDEBUG: Failed to get expected output")
            print(f"Expected: 'echo hello\\r\\nhello\\r\\n.*$ '")
            print(f"Shell alive: {shell.isalive()}")
            print(f"Buffer: {repr(shell.buffer)}")
            print(f"Before: {repr(shell.before)}")
            raise
        
        # Cleanup
        shell.terminate()
        shell.wait()
    
    def test_variable_usage(self):
        """Test variable assignment and usage."""
        shell = self.spawn_psh()
        
        # Wait for prompt
        shell.expect(r'.*\$ ')
        
        # Set variable
        shell.send('X=test\r')
        shell.expect(r'.*\$ ')
        
        # Use variable
        shell.send('echo $X\r')
        shell.expect('test')
        shell.expect(r'.*\$ ')
        
        shell.terminate()
        shell.wait()
    
    def test_exit(self):
        """Test exit command."""
        shell = self.spawn_psh()
        
        # Wait for prompt
        shell.expect(r'.*\$ ')
        
        # Send exit
        shell.send('exit\r')
        
        # Should terminate
        shell.expect(pexpect.EOF)
        assert not shell.isalive()
    
    def test_multiline_string(self):
        """Test multiline string input."""
        shell = self.spawn_psh()
        
        # Wait for prompt
        shell.expect(r'.*\$ ')
        
        # Start multiline string
        shell.send('echo "first\r')
        
        # Should get continuation prompt
        shell.expect('> ')
        
        # Complete the string
        shell.send('second"\r')
        
        # Should see output with newline
        shell.expect('first')
        shell.expect('second')
        
        shell.expect(r'.*\$ ')
        
        shell.terminate()
        shell.wait()
    
    def test_pipe(self):
        """Test simple pipeline."""
        shell = self.spawn_psh()
        
        # Wait for prompt  
        shell.expect(r'.*\$ ')
        
        # Send pipeline
        shell.send('echo "hello world" | grep world\r')
        
        # Should see the filtered output
        shell.expect('hello world')
        
        shell.expect(r'.*\$ ')
        
        shell.terminate()
        shell.wait()
    
    def test_command_not_found(self):
        """Test command not found error."""
        shell = self.spawn_psh()
        
        # Wait for prompt
        shell.expect(r'.*\$ ')
        
        # Send bad command
        shell.send('nosuchcommand\r')
        
        # Should see error
        shell.expect('command not found')
        
        shell.expect(r'.*\$ ')
        
        shell.terminate()
        shell.wait()


class TestInteractiveLineEditing:
    """Test line editing features if supported."""
    
    def spawn_psh(self):
        """Spawn PSH with proper settings."""
        # Ensure PSH can be found
        env = os.environ.copy()
        psh_root = Path(__file__).parent.parent.parent.parent
        env['PYTHONPATH'] = str(psh_root)
        env['PYTHONUNBUFFERED'] = '1'
        
        return pexpect.spawn(
            sys.executable, ['-u', '-m', 'psh', '--norc', '--force-interactive'],
            timeout=10,  # Increased timeout for slower systems
            encoding='utf-8',
            env=env
        )
    
    @pytest.mark.skip(reason="Line editing may not be fully supported yet")
    def test_basic_cursor_movement(self):
        """Test basic cursor movement."""
        shell = self.spawn_psh()
        
        # Wait for prompt
        shell.expect(r'.*\$ ')
        
        # Type some text
        shell.send('hello')
        
        # Move cursor left
        shell.send('\x1b[D')  # Left arrow
        shell.send('\x1b[D')
        shell.send('\x1b[D')
        
        # Insert text
        shell.send('XXX')
        
        # Complete command
        shell.send('\r')
        
        # Should see modified output
        shell.expect('heXXXllo')
        
        shell.terminate()
        shell.wait()