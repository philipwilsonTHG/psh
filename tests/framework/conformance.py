"""
Conformance test framework for comparing PSH behavior with bash.

Provides utilities for:
- Running commands in both PSH and bash
- Comparing outputs
- Handling documented differences
- POSIX compliance verification
"""

import subprocess
import os
import sys
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from enum import Enum

from .base import CommandResult, PSHTestCase


class DifferenceType(Enum):
    """Types of documented differences between PSH and bash."""
    IDENTICAL = "identical"  # Must match exactly
    DOCUMENTED = "documented"  # Known, documented difference
    OUTPUT_FORMAT = "output_format"  # Different formatting, same info
    ERROR_MESSAGE = "error_message"  # Different error text, same meaning
    FEATURE_MISSING = "feature_missing"  # PSH doesn't implement this
    PSH_EXTENSION = "psh_extension"  # PSH-specific feature


@dataclass
class ComparisonResult:
    """Result of comparing PSH and bash outputs."""
    psh: CommandResult
    bash: CommandResult
    matches: bool
    difference_type: DifferenceType
    notes: str = ""
    
    def assert_identical(self):
        """Assert PSH and bash behave identically."""
        assert self.matches and self.difference_type == DifferenceType.IDENTICAL, \
            f"PSH and bash differ:\nCommand: {self.notes}\n" \
            f"PSH stdout: {self.psh.stdout}\n" \
            f"Bash stdout: {self.bash.stdout}\n" \
            f"PSH stderr: {self.psh.stderr}\n" \
            f"Bash stderr: {self.bash.stderr}\n" \
            f"PSH exit: {self.psh.exit_code}, Bash exit: {self.bash.exit_code}"
            
    def assert_documented_difference(self, expected_type: DifferenceType):
        """Assert difference is documented and expected."""
        assert self.difference_type == expected_type, \
            f"Expected {expected_type} difference, got {self.difference_type}"


class ConformanceTest(PSHTestCase):
    """Base class for conformance tests comparing PSH with bash."""
    
    def setup_method(self):
        """Set up for each test method."""
        super().setup_method()
        self.bash_path = self._find_bash()
        self.documented_differences = self._load_documented_differences()
        
    def _find_bash(self) -> str:
        """Find bash executable.

        Searches for bash in the following order:
        1. BASH_PATH environment variable (if set)
        2. Homebrew locations (/opt/homebrew/bin, /usr/local/bin)
        3. Standard locations (/bin, /usr/bin)
        4. bash in PATH
        """
        # Check environment variable first
        if "BASH_PATH" in os.environ:
            bash_path = os.environ["BASH_PATH"]
            if os.path.isfile(bash_path) and os.access(bash_path, os.X_OK):
                return bash_path

        # Common bash locations (Homebrew first for newer bash on macOS)
        bash_paths = [
            '/opt/homebrew/bin/bash',  # Apple Silicon Homebrew (bash 5.x)
            '/usr/local/bin/bash',      # Intel Mac Homebrew
            '/bin/bash',                # Standard location
            '/usr/bin/bash',            # Alternative standard location
        ]

        for path in bash_paths:
            if os.path.exists(path):
                return path

        # Try which/shutil.which
        import shutil
        bash_in_path = shutil.which('bash')
        if bash_in_path:
            return bash_in_path

        raise RuntimeError("Cannot find bash for conformance testing")
        
    def _load_documented_differences(self) -> Dict[str, DifferenceType]:
        """Load documented differences between PSH and bash."""
        # This would load from a configuration file
        # For now, return some known differences
        return {
            'echo -e': DifferenceType.OUTPUT_FORMAT,  # Different escape handling
            'set -o': DifferenceType.OUTPUT_FORMAT,   # Different option display
            'declare -p': DifferenceType.OUTPUT_FORMAT,  # Different variable display
            'trap -p': DifferenceType.FEATURE_MISSING,  # Not implemented
            'complete': DifferenceType.FEATURE_MISSING,  # No programmable completion
        }
        
    def run_in_psh(self, command: str, env: Optional[Dict[str, str]] = None,
                  input: Optional[str] = None) -> CommandResult:
        """Run command in PSH."""
        # Set up environment
        psh_env = os.environ.copy()
        psh_root = Path(__file__).parent.parent.parent
        psh_env['PYTHONPATH'] = str(psh_root)
        psh_env['PYTHONUNBUFFERED'] = '1'
        if env:
            psh_env.update(env)
            
        # Run in PSH as subprocess
        proc = subprocess.run(
            [sys.executable, '-u', '-m', 'psh', '--norc'],
            input=command if command else input,
            capture_output=True,
            text=True,
            env=psh_env,
            cwd=self.temp_dir
        )
        
        return CommandResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode
        )
        
    def run_in_bash(self, command: str, env: Optional[Dict[str, str]] = None,
                   input: Optional[str] = None) -> CommandResult:
        """Run command in bash."""
        # Set up environment
        bash_env = os.environ.copy()
        if env:
            bash_env.update(env)
            
        # Run in bash
        proc = subprocess.run(
            [self.bash_path, '-c', command],
            input=input,
            capture_output=True,
            text=True,
            env=bash_env,
            cwd=self.temp_dir
        )
        
        return CommandResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode
        )
        
    def run_in_both(self, command: str, env: Optional[Dict[str, str]] = None,
                   input: Optional[str] = None) -> Tuple[CommandResult, CommandResult]:
        """Run command in both PSH and bash."""
        psh_result = self.run_in_psh(command, env=env, input=input)
        bash_result = self.run_in_bash(command, env=env, input=input)
        return psh_result, bash_result
        
    def compare_shells(self, command: str, env: Optional[Dict[str, str]] = None,
                      input: Optional[str] = None) -> ComparisonResult:
        """Run command in both shells and compare results."""
        psh_result, bash_result = self.run_in_both(command, env=env, input=input)
        
        # Check for exact match
        if (psh_result.stdout == bash_result.stdout and
            psh_result.stderr == bash_result.stderr and
            psh_result.exit_code == bash_result.exit_code):
            return ComparisonResult(
                psh=psh_result,
                bash=bash_result,
                matches=True,
                difference_type=DifferenceType.IDENTICAL,
                notes=command
            )
            
        # Check for documented differences
        for pattern, diff_type in self.documented_differences.items():
            if pattern in command:
                return ComparisonResult(
                    psh=psh_result,
                    bash=bash_result,
                    matches=False,
                    difference_type=diff_type,
                    notes=command
                )
                
        # Undocumented difference
        return ComparisonResult(
            psh=psh_result,
            bash=bash_result,
            matches=False,
            difference_type=DifferenceType.IDENTICAL,  # Expected identical
            notes=command
        )
        
    def assert_same_behavior(self, command: str, env: Optional[Dict[str, str]] = None,
                           input: Optional[str] = None):
        """Assert PSH and bash produce identical results."""
        result = self.compare_shells(command, env=env, input=input)
        result.assert_identical()
        
    def assert_posix_compliant(self, command: str, env: Optional[Dict[str, str]] = None,
                             input: Optional[str] = None):
        """Assert PSH behaves in POSIX-compliant way."""
        # For POSIX compliance, we might compare with sh instead of bash
        # or use specific POSIX test suites
        result = self.compare_shells(command, env=env, input=input)
        
        # For now, just ensure it matches bash
        # In future, could have POSIX-specific checks
        result.assert_identical()
        
    def normalize_output(self, output: str, shell_type: str = 'both') -> str:
        """Normalize output for comparison."""
        # Remove trailing whitespace
        lines = output.split('\n')
        normalized = '\n'.join(line.rstrip() for line in lines)
        
        # Shell-specific normalizations
        if shell_type in ('psh', 'both'):
            # PSH-specific normalizations
            pass
            
        if shell_type in ('bash', 'both'):
            # Bash-specific normalizations
            pass
            
        return normalized
        
    def create_conformance_test(self, name: str, commands: list,
                              expected_behavior: DifferenceType = DifferenceType.IDENTICAL):
        """Create a conformance test from a list of commands."""
        for i, command in enumerate(commands):
            with self.subTest(command=command, index=i):
                result = self.compare_shells(command)
                
                if expected_behavior == DifferenceType.IDENTICAL:
                    result.assert_identical()
                else:
                    result.assert_documented_difference(expected_behavior)