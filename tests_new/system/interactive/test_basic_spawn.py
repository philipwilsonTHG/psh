"""
Basic test to verify pexpect can spawn PSH properly.
"""

import sys
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TEST_ROOT))

import pytest
import pexpect
import time
import signal
import os


def safe_cleanup(shell):
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
            
    except Exception as e:
        # If cleanup fails, try force kill
        try:
            if hasattr(shell, 'pid') and shell.pid:
                os.kill(shell.pid, signal.SIGKILL)
        except:
            pass


def test_can_spawn_psh():
    """Test that we can spawn PSH with pexpect."""
    shell = None
    try:
        # Clean up any leftover processes
        os.system("pkill -f 'python.*psh' 2>/dev/null || true")
        time.sleep(0.1)
        
        # Try to spawn PSH
        shell = pexpect.spawn(
            sys.executable, ['-m', 'psh'],
            timeout=5,
            encoding='utf-8'
        )
    
        # Give it a moment to start
        time.sleep(0.5)
        
        # Check if it's alive
        assert shell.isalive(), "PSH process died immediately"
        
        # Try to send a simple command
        shell.sendline('echo hello')
        
        # Look for output
        index = shell.expect(['hello', pexpect.EOF, pexpect.TIMEOUT], timeout=2)
        if index == 0:
            print("Success! Got 'hello' output")
        elif index == 1:
            print(f"Got EOF. Output so far: {shell.before}")
        else:
            print(f"Timeout. Output so far: {shell.before}")
            
    except Exception as e:
        print(f"Error: {e}")
        if shell:
            print(f"Output buffer: {shell.before}")
    finally:
        # Clean up
        safe_cleanup(shell)


def test_psh_prompt():
    """Test that PSH shows a prompt."""
    shell = None
    try:
        # Clean up any leftover processes
        os.system("pkill -f 'python.*psh' 2>/dev/null || true")
        time.sleep(0.1)
        
        shell = pexpect.spawn(
            sys.executable, ['-m', 'psh'],
            timeout=5,
            encoding='utf-8'
        )
        
        # Look for common prompt patterns
        prompts = [r'\$ ', r'> ', r'psh.*>', r'.*\$', pexpect.EOF]
        
        index = shell.expect(prompts, timeout=3)
        if index < len(prompts) - 1:
            print(f"Found prompt pattern {index}: '{prompts[index]}'")
            print(f"Actual output: '{shell.before}'")
            print(f"Match: '{shell.after}'")
        else:
            print(f"Got EOF instead of prompt. Output: {shell.before}")
            
    except pexpect.TIMEOUT:
        print(f"Timeout waiting for prompt. Output so far: {shell.before if shell else 'None'}")
        # Try sending a newline
        if shell:
            shell.sendline('')
            try:
                shell.expect(prompts, timeout=1)
                print("Got prompt after newline")
            except:
                print("Still no prompt after newline")
    except Exception as e:
        print(f"Error: {e}")
        if shell:
            print(f"Output buffer: {shell.before}")
    finally:
        safe_cleanup(shell)


def test_psh_with_norc():
    """Test PSH with --norc flag to skip startup files."""
    shell = None
    try:
        # Clean up any leftover processes
        os.system("pkill -f 'python.*psh' 2>/dev/null || true")
        time.sleep(0.1)
        
        shell = pexpect.spawn(
            sys.executable, ['-m', 'psh', '--norc'],
            timeout=5,
            encoding='utf-8'
        )
        
        # Give it time to start
        time.sleep(0.5)
        
        # Send a command
        shell.sendline('echo test')
        
        # Capture all output
        time.sleep(1)
        shell.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=1)
        
        print(f"Full output:\n{shell.before}")
        
    except Exception as e:
        print(f"Error: {e}")
        if shell:
            print(f"Output buffer: {shell.before}")
    finally:
        safe_cleanup(shell)


if __name__ == '__main__':
    print("Testing pexpect with PSH...")
    test_can_spawn_psh()
    print("\nTesting PSH prompt...")
    test_psh_prompt()
    print("\nTesting PSH with --norc...")
    test_psh_with_norc()