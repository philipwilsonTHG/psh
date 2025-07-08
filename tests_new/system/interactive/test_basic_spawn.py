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


def test_can_spawn_psh():
    """Test that we can spawn PSH with pexpect."""
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
    try:
        index = shell.expect(['hello', pexpect.EOF, pexpect.TIMEOUT], timeout=2)
        if index == 0:
            print("Success! Got 'hello' output")
        elif index == 1:
            print(f"Got EOF. Output so far: {shell.before}")
        else:
            print(f"Timeout. Output so far: {shell.before}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Output buffer: {shell.before}")
    
    # Clean up
    shell.terminate()
    shell.wait()


def test_psh_prompt():
    """Test that PSH shows a prompt."""
    shell = pexpect.spawn(
        sys.executable, ['-m', 'psh'],
        timeout=5,
        encoding='utf-8'
    )
    
    # Look for common prompt patterns
    prompts = [r'\$ ', r'> ', r'psh.*>', r'.*\$', pexpect.EOF]
    
    try:
        index = shell.expect(prompts, timeout=3)
        if index < len(prompts) - 1:
            print(f"Found prompt pattern {index}: '{prompts[index]}'")
            print(f"Actual output: '{shell.before}'")
            print(f"Match: '{shell.after}'")
        else:
            print(f"Got EOF instead of prompt. Output: {shell.before}")
    except pexpect.TIMEOUT:
        print(f"Timeout waiting for prompt. Output so far: {shell.before}")
        # Try sending a newline
        shell.sendline('')
        try:
            shell.expect(prompts, timeout=1)
            print("Got prompt after newline")
        except:
            print("Still no prompt after newline")
    
    shell.terminate()
    shell.wait()


def test_psh_with_norc():
    """Test PSH with --norc flag to skip startup files."""
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
    
    shell.terminate()
    shell.wait()


if __name__ == '__main__':
    print("Testing pexpect with PSH...")
    test_can_spawn_psh()
    print("\nTesting PSH prompt...")
    test_psh_prompt()
    print("\nTesting PSH with --norc...")
    test_psh_with_norc()