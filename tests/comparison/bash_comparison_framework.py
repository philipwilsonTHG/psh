#!/usr/bin/env python3
"""
Pytest framework for comparing PSH output with bash output.

This framework runs the same commands in both PSH and bash, then compares
their outputs to ensure compatibility and catch regressions.
"""

import subprocess
import re
import os
import tempfile
import pytest
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ShellResult:
    """Result of running a command in a shell."""
    stdout: str
    stderr: str
    returncode: int
    

class BashComparisonFramework:
    """Framework for comparing PSH and bash behavior."""
    
    def __init__(self, bash_path: str = "/opt/homebrew/bin/bash"):
        self.bash_path = bash_path
        self.psh_command = ["python3", "-m", "psh"]
        
    def run_in_shell(self, command: str, shell_command: List[str], 
                    timeout: float = 10.0, env: Optional[Dict[str, str]] = None,
                    stdin_input: Optional[str] = None) -> ShellResult:
        """Run a command in the specified shell and capture results."""
        try:
            # Prepare environment
            shell_env = os.environ.copy()
            if env:
                shell_env.update(env)
            
            # Run the command
            cmd = shell_command + ["-c", command]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=shell_env,
                input=stdin_input
            )
            
            return ShellResult(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            return ShellResult(
                stdout="",
                stderr="TIMEOUT",
                returncode=124  # Standard timeout exit code
            )
        except Exception as e:
            return ShellResult(
                stdout="",
                stderr=f"ERROR: {str(e)}",
                returncode=127
            )
    
    def normalize_output(self, output: str, shell_type: str = "both") -> str:
        """Normalize shell output to handle legitimate differences."""
        if not output:
            return output
            
        normalized = output
        
        # Remove trailing whitespace from each line but preserve structure
        lines = normalized.split('\n')
        normalized = '\n'.join(line.rstrip() for line in lines)
        
        # Normalize process IDs (bash and psh might show different PIDs)
        normalized = re.sub(r'\b\d{3,6}\b', 'PID', normalized)
        
        # Normalize job IDs in job control output
        normalized = re.sub(r'\[\d+\]', '[JOB]', normalized)
        
        # Normalize timing differences (if any timestamps appear)
        normalized = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', normalized)
        
        # Normalize temporary paths
        normalized = re.sub(r'/tmp/tmp\w+', '/tmp/TEMP', normalized)
        normalized = re.sub(r'/var/folders/[^/]+/[^/]+', '/tmp/TEMP', normalized)
        
        # Handle common path differences
        if shell_type == "psh":
            # PSH might show full paths where bash shows relative
            pass
        elif shell_type == "bash":
            # Bash might have different error message format
            pass
            
        return normalized
    
    def normalize_error_output(self, stderr: str, shell_type: str) -> str:
        """Normalize error output to handle different error message formats."""
        if not stderr:
            return stderr
            
        normalized = stderr
        
        # Both shells might have different error prefixes
        normalized = re.sub(r'^[^:]*:', 'shell:', normalized, flags=re.MULTILINE)
        
        # Normalize line numbers in error messages
        normalized = re.sub(r'line \d+:', 'line N:', normalized)
        
        # Normalize file descriptor references
        normalized = re.sub(r'file descriptor \d+', 'file descriptor N', normalized)
        
        return self.normalize_output(normalized, shell_type)
    
    def compare_results(self, psh_result: ShellResult, bash_result: ShellResult,
                       check_stderr: bool = True, 
                       normalize_errors: bool = True) -> Tuple[bool, str]:
        """
        Compare results from PSH and bash.
        
        Returns (matches, difference_description)
        """
        issues = []
        
        # Normalize outputs
        psh_stdout = self.normalize_output(psh_result.stdout, "psh")
        bash_stdout = self.normalize_output(bash_result.stdout, "bash")
        
        # Compare stdout
        if psh_stdout != bash_stdout:
            issues.append(f"STDOUT differs:")
            issues.append(f"  PSH:  '{psh_stdout}'")
            issues.append(f"  Bash: '{bash_stdout}'")
        
        # Compare stderr if requested
        if check_stderr:
            if normalize_errors:
                psh_stderr = self.normalize_error_output(psh_result.stderr, "psh")
                bash_stderr = self.normalize_error_output(bash_result.stderr, "bash")
            else:
                psh_stderr = psh_result.stderr
                bash_stderr = bash_result.stderr
                
            if psh_stderr != bash_stderr:
                issues.append(f"STDERR differs:")
                issues.append(f"  PSH:  '{psh_stderr}'")
                issues.append(f"  Bash: '{bash_stderr}'")
        
        # Compare exit codes
        if psh_result.returncode != bash_result.returncode:
            issues.append(f"Exit codes differ: PSH={psh_result.returncode}, Bash={bash_result.returncode}")
        
        return len(issues) == 0, '\n'.join(issues)
    
    def assert_shells_match(self, command: str, **kwargs):
        """Assert that PSH and bash produce the same output for a command."""
        # Extract comparison-specific kwargs
        check_stderr = kwargs.pop('check_stderr', True)
        normalize_errors = kwargs.pop('normalize_errors', True)
        
        psh_result = self.run_in_shell(command, self.psh_command, **kwargs)
        bash_result = self.run_in_shell(command, [self.bash_path], **kwargs)
        
        matches, diff = self.compare_results(
            psh_result, bash_result, 
            check_stderr=check_stderr, 
            normalize_errors=normalize_errors
        )
        
        if not matches:
            pytest.fail(f"Shell outputs differ for command: {command}\n{diff}")
        
        return psh_result, bash_result
    
    def expect_shells_differ(self, command: str, reason: str = "", **kwargs):
        """
        Expect PSH and bash to produce different output.
        Used for documenting known limitations.
        """
        # Extract comparison-specific kwargs
        check_stderr = kwargs.pop('check_stderr', True)
        normalize_errors = kwargs.pop('normalize_errors', True)
        
        psh_result = self.run_in_shell(command, self.psh_command, **kwargs)
        bash_result = self.run_in_shell(command, [self.bash_path], **kwargs)
        
        matches, diff = self.compare_results(
            psh_result, bash_result,
            check_stderr=check_stderr,
            normalize_errors=normalize_errors
        )
        
        if matches:
            pytest.fail(f"Expected shells to differ for command: {command}\n"
                       f"Reason: {reason}\n"
                       f"But outputs were identical: '{psh_result.stdout}'")
        
        return psh_result, bash_result


# Global instance for convenience
bash_compare = BashComparisonFramework()


def test_bash_compatibility(commands: List[str], **kwargs):
    """Decorator/helper for testing multiple commands against bash."""
    def decorator(test_func):
        def wrapper():
            for command in commands:
                try:
                    bash_compare.assert_shells_match(command, **kwargs)
                except Exception as e:
                    pytest.fail(f"Command '{command}' failed: {str(e)}")
            return test_func()
        return wrapper
    return decorator


class TestShellFile:
    """Helper for testing shell scripts in files."""
    
    def __init__(self, framework: BashComparisonFramework):
        self.framework = framework
    
    def test_script_file(self, script_content: str, **kwargs):
        """Test a shell script by writing it to a temp file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Test with both shells
            psh_result = self.framework.run_in_shell(f"bash {script_path}", 
                                                   self.framework.psh_command, **kwargs)
            bash_result = self.framework.run_in_shell(f"bash {script_path}",
                                                    [self.framework.bash_path], **kwargs)
            
            matches, diff = self.framework.compare_results(psh_result, bash_result)
            if not matches:
                pytest.fail(f"Script outputs differ:\n{diff}")
                
        finally:
            os.unlink(script_path)