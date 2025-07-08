"""
Simple command tests using subprocess instead of pexpect.

Due to buffering issues with pexpect in pytest environment, 
we use subprocess for basic command testing.
"""

import sys
import os
import subprocess
from pathlib import Path
import time


class TestSubprocessCommands:
    """Test simple PSH commands using subprocess."""
    
    def run_psh_command(self, commands, timeout=5):
        """Run PSH with given commands and return output."""
        env = os.environ.copy()
        psh_root = Path(__file__).parent.parent.parent.parent
        env['PYTHONPATH'] = str(psh_root)
        env['PYTHONUNBUFFERED'] = '1'
        
        # Join commands with newlines
        if isinstance(commands, str):
            input_text = commands + '\n'
        else:
            input_text = '\n'.join(commands) + '\n'
        
        proc = subprocess.Popen(
            [sys.executable, '-u', '-m', 'psh', '--norc'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        try:
            stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
            return {
                'stdout': stdout,
                'stderr': stderr,
                'returncode': proc.returncode
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return {
                'stdout': stdout or '',
                'stderr': stderr or '',
                'returncode': -1,
                'error': 'timeout'
            }
    
    def test_echo_command(self):
        """Test echo command."""
        result = self.run_psh_command('echo hello world')
        assert result['returncode'] == 0
        assert 'hello world' in result['stdout']
    
    def test_multiple_commands(self):
        """Test multiple commands in sequence."""
        result = self.run_psh_command(['echo first', 'echo second', 'echo third'])
        assert result['returncode'] == 0
        assert 'first' in result['stdout']
        assert 'second' in result['stdout']
        assert 'third' in result['stdout']
        # Check order
        assert result['stdout'].index('first') < result['stdout'].index('second')
        assert result['stdout'].index('second') < result['stdout'].index('third')
    
    def test_variable_assignment(self):
        """Test variable assignment and expansion."""
        result = self.run_psh_command(['X=hello', 'echo $X', 'Y=world', 'echo $X $Y'])
        assert result['returncode'] == 0
        assert 'hello' in result['stdout']
        assert 'hello world' in result['stdout']
    
    def test_command_substitution(self):
        """Test command substitution."""
        result = self.run_psh_command('echo $(echo nested)')
        assert result['returncode'] == 0
        assert 'nested' in result['stdout']
    
    def test_pipeline(self):
        """Test simple pipeline."""
        result = self.run_psh_command('echo "hello world" | grep world')
        assert result['returncode'] == 0
        assert 'hello world' in result['stdout']
    
    def test_exit_code(self):
        """Test exit code capture."""
        # Test true (exit 0)
        result = self.run_psh_command(['true', 'echo $?'])
        assert result['returncode'] == 0
        assert '0' in result['stdout']
        
        # Test false (exit 1)
        result = self.run_psh_command(['false', 'echo $?'])
        assert result['returncode'] == 0  # The shell itself exits cleanly
        assert '1' in result['stdout']
    
    def test_builtin_cd(self):
        """Test cd builtin."""
        result = self.run_psh_command(['pwd', 'cd /tmp', 'pwd'])
        assert result['returncode'] == 0
        lines = result['stdout'].strip().split('\n')
        assert len(lines) >= 2
        assert lines[-1] == '/tmp' or lines[-1].endswith('/tmp')  # Handle symlinks
    
    def test_error_handling(self):
        """Test error handling."""
        result = self.run_psh_command('nonexistent_command')
        assert result['returncode'] != 0
        assert 'nonexistent_command' in result['stderr'] or 'not found' in result['stderr']