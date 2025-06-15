#!/usr/bin/env python3
"""
Framework for comparing PSH behavior with POSIX-compliant shells.
This framework runs commands in both PSH and a reference POSIX shell (like dash or sh)
to verify POSIX compliance.
"""

import subprocess
import os
import sys
import tempfile
import shutil
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ShellResult:
    """Result from executing a command in a shell."""
    stdout: str
    stderr: str
    returncode: int
    shell: str


class POSIXComparisonFramework:
    """Framework for comparing PSH with POSIX shells."""
    
    def __init__(self, posix_shell: Optional[str] = None):
        """Initialize with a POSIX reference shell.
        
        Args:
            posix_shell: Path to POSIX shell. If None, will try to find one.
        """
        self.psh_command = [sys.executable, "-m", "psh"]
        self.posix_shell = self._find_posix_shell(posix_shell)
        self.temp_dir = None
    
    def _find_posix_shell(self, preferred: Optional[str] = None) -> List[str]:
        """Find a POSIX-compliant shell for comparison.
        
        Args:
            preferred: Preferred shell path
            
        Returns:
            Command to run POSIX shell
        """
        if preferred and shutil.which(preferred):
            return [preferred]
        
        # Try to find a POSIX shell in order of preference
        candidates = [
            "dash",      # Debian Almquist Shell - very POSIX compliant
            "ash",       # Almquist Shell
            "ksh",       # Korn Shell - POSIX compliant
            "/bin/sh",   # System shell (might be POSIX)
            "sh",        # Generic shell
        ]
        
        for shell in candidates:
            if shutil.which(shell):
                # If it's bash, run in POSIX mode
                if "bash" in os.path.realpath(shutil.which(shell)):
                    return ["bash", "--posix"]
                return [shell]
        
        # Fallback to bash in POSIX mode if available
        if shutil.which("bash"):
            return ["bash", "--posix"]
        
        raise RuntimeError("No POSIX shell found for comparison")
    
    def setup(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="psh_posix_test_")
    
    def teardown(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def run_in_shell(self, command: str, shell_cmd: List[str], 
                     env: Optional[Dict[str, str]] = None,
                     stdin: Optional[str] = None,
                     timeout: float = 10.0) -> ShellResult:
        """Run a command in a specific shell.
        
        Args:
            command: Shell command to execute
            shell_cmd: Shell command list (e.g., ["dash"])
            env: Environment variables
            stdin: Input to provide to the command
            timeout: Command timeout in seconds
            
        Returns:
            ShellResult with output and exit code
        """
        # Prepare environment
        shell_env = os.environ.copy()
        if env:
            shell_env.update(env)
        
        # Set a consistent environment for comparison
        shell_env["LC_ALL"] = "C"
        shell_env["PS1"] = "$ "
        shell_env["PS2"] = "> "
        
        # Use temp directory as working directory for consistency
        if self.temp_dir:
            shell_env["PWD"] = self.temp_dir
        
        try:
            # Run command
            process = subprocess.run(
                shell_cmd + ["-c", command],
                capture_output=True,
                text=True,
                input=stdin,
                timeout=timeout,
                env=shell_env,
                cwd=self.temp_dir
            )
            
            return ShellResult(
                stdout=process.stdout,
                stderr=process.stderr,
                returncode=process.returncode,
                shell=shell_cmd[0]
            )
        except subprocess.TimeoutExpired:
            return ShellResult(
                stdout="",
                stderr="Command timed out",
                returncode=-1,
                shell=shell_cmd[0]
            )
        except Exception as e:
            return ShellResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                shell=shell_cmd[0]
            )
    
    def compare_command(self, command: str, 
                       env: Optional[Dict[str, str]] = None,
                       stdin: Optional[str] = None,
                       normalize_output: bool = True) -> Tuple[ShellResult, ShellResult]:
        """Run command in both PSH and POSIX shell and compare.
        
        Args:
            command: Command to test
            env: Environment variables
            stdin: Input to provide
            normalize_output: Whether to normalize output for comparison
            
        Returns:
            Tuple of (psh_result, posix_result)
        """
        # Run in PSH
        psh_result = self.run_in_shell(command, self.psh_command, env, stdin)
        
        # Run in POSIX shell
        posix_result = self.run_in_shell(command, self.posix_shell, env, stdin)
        
        if normalize_output:
            # Normalize results for comparison
            psh_result = self._normalize_result(psh_result)
            posix_result = self._normalize_result(posix_result)
        
        return psh_result, posix_result
    
    def _normalize_result(self, result: ShellResult) -> ShellResult:
        """Normalize shell output for comparison.
        
        Args:
            result: Original result
            
        Returns:
            Normalized result
        """
        # Normalize stdout
        stdout = result.stdout
        # Remove trailing whitespace
        stdout = stdout.rstrip()
        # Normalize line endings
        stdout = stdout.replace('\r\n', '\n')
        
        # Normalize stderr
        stderr = result.stderr
        # Remove shell-specific error prefixes
        stderr = self._normalize_error_messages(stderr)
        
        return ShellResult(
            stdout=stdout,
            stderr=stderr,
            returncode=result.returncode,
            shell=result.shell
        )
    
    def _normalize_error_messages(self, stderr: str) -> str:
        """Normalize error messages for comparison.
        
        Args:
            stderr: Original stderr
            
        Returns:
            Normalized stderr
        """
        # Remove shell name from error messages
        lines = []
        for line in stderr.split('\n'):
            # Remove common shell prefixes
            for prefix in ["psh:", "sh:", "dash:", "bash:", "-bash:"]:
                if line.startswith(prefix):
                    line = line[len(prefix):].lstrip()
            # Remove line numbers
            line = line.strip()
            if line:
                lines.append(line)
        
        return '\n'.join(lines)
    
    def assert_results_match(self, psh_result: ShellResult, posix_result: ShellResult,
                           check_stdout: bool = True,
                           check_stderr: bool = False,
                           check_returncode: bool = True):
        """Assert that PSH and POSIX results match.
        
        Args:
            psh_result: Result from PSH
            posix_result: Result from POSIX shell
            check_stdout: Whether to compare stdout
            check_stderr: Whether to compare stderr
            check_returncode: Whether to compare return codes
            
        Raises:
            AssertionError: If results don't match
        """
        errors = []
        
        if check_stdout and psh_result.stdout != posix_result.stdout:
            errors.append(
                f"stdout mismatch:\n"
                f"PSH:   '{psh_result.stdout}'\n"
                f"POSIX: '{posix_result.stdout}'"
            )
        
        if check_stderr and psh_result.stderr != posix_result.stderr:
            errors.append(
                f"stderr mismatch:\n"
                f"PSH:   '{psh_result.stderr}'\n"
                f"POSIX: '{posix_result.stderr}'"
            )
        
        if check_returncode and psh_result.returncode != posix_result.returncode:
            errors.append(
                f"return code mismatch:\n"
                f"PSH:   {psh_result.returncode}\n"
                f"POSIX: {posix_result.returncode}"
            )
        
        if errors:
            raise AssertionError("\n".join(errors))
    
    def run_compliance_test(self, command: str,
                           expected_stdout: Optional[str] = None,
                           expected_returncode: Optional[int] = None,
                           **kwargs) -> bool:
        """Run a POSIX compliance test.
        
        Args:
            command: Command to test
            expected_stdout: Expected output (if None, compare with POSIX shell)
            expected_returncode: Expected return code (if None, compare with POSIX shell)
            **kwargs: Additional arguments for compare_command
            
        Returns:
            True if test passes
        """
        psh_result, posix_result = self.compare_command(command, **kwargs)
        
        if expected_stdout is not None:
            # Compare against expected
            if psh_result.stdout != expected_stdout:
                print(f"PSH output mismatch: expected '{expected_stdout}', got '{psh_result.stdout}'")
                return False
        else:
            # Compare against POSIX shell
            if psh_result.stdout != posix_result.stdout:
                print(f"Output mismatch: PSH='{psh_result.stdout}', POSIX='{posix_result.stdout}'")
                return False
        
        if expected_returncode is not None:
            # Compare against expected
            if psh_result.returncode != expected_returncode:
                print(f"PSH return code mismatch: expected {expected_returncode}, got {psh_result.returncode}")
                return False
        else:
            # Compare against POSIX shell
            if psh_result.returncode != posix_result.returncode:
                print(f"Return code mismatch: PSH={psh_result.returncode}, POSIX={posix_result.returncode}")
                return False
        
        return True


# Convenience instance for tests
posix_compare = POSIXComparisonFramework()