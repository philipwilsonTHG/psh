"""
Base test framework for PSH testing.

Provides common utilities and base classes for all test types.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import subprocess

# Add PSH to path
PSH_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PSH_ROOT))


@dataclass
class CommandResult:
    """Result from running a command."""
    stdout: str
    stderr: str
    exit_code: int
    
    def assert_success(self):
        """Assert command succeeded."""
        assert self.exit_code == 0, f"Command failed with exit code {self.exit_code}\nstderr: {self.stderr}"
        
    def assert_exit_code(self, expected: int):
        """Assert specific exit code."""
        assert self.exit_code == expected, f"Expected exit code {expected}, got {self.exit_code}"
        
    def assert_stdout(self, expected: str):
        """Assert stdout matches exactly."""
        assert self.stdout == expected, f"Expected stdout:\n{expected}\nGot:\n{self.stdout}"
        
    def assert_stderr(self, expected: str):
        """Assert stderr matches exactly."""
        assert self.stderr == expected, f"Expected stderr:\n{expected}\nGot:\n{self.stderr}"
        
    def assert_stdout_contains(self, substring: str):
        """Assert stdout contains substring."""
        assert substring in self.stdout, f"Expected '{substring}' in stdout:\n{self.stdout}"
        
    def assert_stderr_contains(self, substring: str):
        """Assert stderr contains substring."""
        assert substring in self.stderr, f"Expected '{substring}' in stderr:\n{self.stderr}"


class PSHTestCase:
    """Base class for all PSH tests with common utilities."""
    
    @classmethod
    def setup_class(cls):
        """Set up class-level test fixtures."""
        pass
        
    @classmethod
    def teardown_class(cls):
        """Tear down class-level test fixtures."""
        pass
        
    def setup_method(self):
        """Set up test fixtures before each test."""
        self.original_dir = os.getcwd()
        self.temp_dir = tempfile.mkdtemp(prefix='psh_test_')
        os.chdir(self.temp_dir)
        
    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_shell(self, **options) -> 'Shell':
        """Create a configured shell instance."""
        from psh.shell import Shell
        
        # Default options for testing
        test_options = {
            'norc': True,  # Don't load .pshrc
            'debug_ast': options.get('debug_ast', False),
            'debug_tokens': options.get('debug_tokens', False),
        }
        test_options.update(options)
        
        return Shell(**test_options)
        
    def run_command(self, cmd: str, shell=None, input: Optional[str] = None,
                   env: Optional[Dict[str, str]] = None) -> CommandResult:
        """Run command and return structured result."""
        if shell is None:
            shell = self.create_shell()
            
        # Set up environment
        if env:
            old_env = dict(shell.state.env)
            shell.state.env.update(env)
            
        # Capture output
        from io import StringIO
        old_stdout = shell.stdout
        old_stderr = shell.stderr
        old_stdin = shell.stdin
        
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        stdin_input = StringIO(input) if input else StringIO()
        
        shell.stdout = stdout_capture
        shell.stderr = stderr_capture  
        shell.stdin = stdin_input
        
        try:
            # Run command
            exit_code = shell.run_command(cmd)
            if exit_code is None:
                exit_code = 0
            
            # Get output
            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()
            
            return CommandResult(stdout=stdout, stderr=stderr, exit_code=exit_code)
            
        finally:
            # Restore streams
            shell.stdout = old_stdout
            shell.stderr = old_stderr
            shell.stdin = old_stdin
            
            # Restore environment
            if env:
                shell.state.env.clear()
                shell.state.env.update(old_env)
                
    def run_script(self, script_content: str, args: Optional[List[str]] = None) -> CommandResult:
        """Run a script file."""
        script_path = self.create_file('test_script.sh', script_content)
        shell = self.create_shell()
        
        # Set positional parameters
        if args:
            shell.set_positional_params(args)
            
        exit_code = shell.run_script(script_path)
        
        # Capture any output (would need to enhance this)
        return CommandResult(stdout='', stderr='', exit_code=exit_code)
        
    def create_file(self, name: str, content: str = '') -> str:
        """Create a file in the test directory."""
        path = os.path.join(self.temp_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        return path
        
    def create_directory(self, name: str) -> str:
        """Create a directory in the test directory."""
        path = os.path.join(self.temp_dir, name)
        os.makedirs(path, exist_ok=True)
        return path
        
    def assert_file_exists(self, path: str):
        """Assert a file exists."""
        assert os.path.exists(path), f"File does not exist: {path}"
        
    def assert_file_content(self, path: str, expected: str):
        """Assert file has expected content."""
        self.assert_file_exists(path)
        with open(path, 'r') as f:
            content = f.read()
        assert content == expected, f"File content mismatch.\nExpected:\n{expected}\nGot:\n{content}"
        
    @contextmanager
    def environment(self, **env_vars):
        """Context manager to temporarily set environment variables."""
        old_env = dict(os.environ)
        os.environ.update(env_vars)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(old_env)
            
    def assert_output(self, result: CommandResult, stdout: Optional[str] = None,
                     stderr: Optional[str] = None, exit_code: int = 0):
        """Assert command output matches expectations."""
        if exit_code is not None:
            result.assert_exit_code(exit_code)
        if stdout is not None:
            result.assert_stdout(stdout)
        if stderr is not None:
            result.assert_stderr(stderr)