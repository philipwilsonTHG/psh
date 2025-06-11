#!/usr/bin/env python3
"""
Comparison test runner for bash vs psh.

This module provides infrastructure to run the same commands/scripts in both
bash and psh, comparing their outputs to ensure compatibility.

This runner integrates with the new bash_comparison_framework.py for pytest-based
testing while maintaining standalone command-line functionality.
"""

import os
import sys
import subprocess
import tempfile
import difflib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import shlex


@dataclass
class TestResult:
    """Result of running a test in both shells."""
    test_name: str
    command: str
    bash_stdout: str
    bash_stderr: str
    bash_exit_code: int
    psh_stdout: str
    psh_stderr: str
    psh_exit_code: int
    passed: bool
    differences: List[str]
    execution_time: float
    skip_reason: Optional[str] = None


class ComparisonTestRunner:
    """Runs commands in both bash and psh and compares outputs."""
    
    def __init__(self, psh_path: str = None, bash_path: str = "/opt/homebrew/bin/bash"):
        """Initialize the test runner.
        
        Args:
            psh_path: Path to psh executable. If None, will try to find it.
            bash_path: Path to bash executable.
        """
        self.psh_path = psh_path or self._find_psh()
        self.bash_path = bash_path
        self.results: List[TestResult] = []
        
    def _find_psh(self) -> str:
        """Find the psh executable."""
        # Try common locations
        candidates = [
            "psh",  # In PATH
            "./psh",  # Current directory
            os.path.join(os.path.dirname(__file__), "..", "..", "psh"),
            os.path.expanduser("~/bin/psh"),
            "/usr/local/bin/psh",
        ]
        
        # Also try running as a module
        python_psh = [sys.executable, "-m", "psh"]
        
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
                
        # Default to running as Python module
        return " ".join(python_psh)
    
    def run_command(self, command: str, test_name: str = None, 
                    timeout: int = 5, env: Dict[str, str] = None,
                    stdin: str = None, working_dir: str = None) -> TestResult:
        """Run a command in both shells and compare results.
        
        Args:
            command: Command to run
            test_name: Name for this test (defaults to command)
            timeout: Timeout in seconds
            env: Environment variables to set
            stdin: Input to provide to the command
            working_dir: Working directory for command execution
            
        Returns:
            TestResult object with comparison data
        """
        test_name = test_name or command
        start_time = datetime.now()
        
        # Set up environment
        test_env = os.environ.copy()
        if env:
            test_env.update(env)
        
        # Create temporary directory if needed
        temp_dir = None
        if working_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="psh_test_")
            working_dir = temp_dir
        
        try:
            # Run in bash
            bash_result = self._run_shell_command(
                self.bash_path, command, timeout, test_env, stdin, working_dir
            )
            
            # Run in psh
            psh_result = self._run_shell_command(
                self.psh_path, command, timeout, test_env, stdin, working_dir
            )
            
            # Compare results
            differences = []
            
            # Compare stdout
            if bash_result['stdout'] != psh_result['stdout']:
                stdout_diff = list(difflib.unified_diff(
                    bash_result['stdout'].splitlines(keepends=True),
                    psh_result['stdout'].splitlines(keepends=True),
                    fromfile='bash stdout',
                    tofile='psh stdout'
                ))
                if stdout_diff:
                    differences.append("STDOUT differs:\n" + "".join(stdout_diff))
            
            # Compare stderr (more lenient - ignore certain differences)
            bash_stderr = self._normalize_stderr(bash_result['stderr'])
            psh_stderr = self._normalize_stderr(psh_result['stderr'])
            
            if bash_stderr != psh_stderr:
                stderr_diff = list(difflib.unified_diff(
                    bash_stderr.splitlines(keepends=True),
                    psh_stderr.splitlines(keepends=True),
                    fromfile='bash stderr',
                    tofile='psh stderr'
                ))
                if stderr_diff:
                    differences.append("STDERR differs:\n" + "".join(stderr_diff))
            
            # Compare exit codes
            if bash_result['exit_code'] != psh_result['exit_code']:
                differences.append(
                    f"Exit codes differ: bash={bash_result['exit_code']}, "
                    f"psh={psh_result['exit_code']}"
                )
            
            # Create result
            result = TestResult(
                test_name=test_name,
                command=command,
                bash_stdout=bash_result['stdout'],
                bash_stderr=bash_result['stderr'],
                bash_exit_code=bash_result['exit_code'],
                psh_stdout=psh_result['stdout'],
                psh_stderr=psh_result['stderr'],
                psh_exit_code=psh_result['exit_code'],
                passed=len(differences) == 0,
                differences=differences,
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            
            self.results.append(result)
            return result
            
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
    
    def _run_shell_command(self, shell: str, command: str, timeout: int,
                          env: Dict[str, str], stdin: str, 
                          working_dir: str) -> Dict[str, Any]:
        """Run a command in a specific shell."""
        # Handle multi-part shell command (e.g., "python -m psh")
        if ' ' in shell and not os.path.exists(shell):
            shell_parts = shlex.split(shell)
            cmd = shell_parts + ['-c', command]
        else:
            cmd = [shell, '-c', command]
        
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                input=stdin,
                cwd=working_dir
            )
            
            return {
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'exit_code': proc.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'stdout': '',
                'stderr': f'{shell}: Command timed out after {timeout} seconds',
                'exit_code': -1
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': f'{shell}: Error running command: {e}',
                'exit_code': -1
            }
    
    def _normalize_stderr(self, stderr: str) -> str:
        """Normalize stderr to ignore insignificant differences."""
        import re
        
        # Remove shell name prefixes that might differ
        lines = stderr.splitlines()
        normalized = []
        
        for line in lines:
            # Normalize shell executable paths in error messages
            # This handles cases like "/opt/homebrew/bin/bash:" or "/bin/bash:"
            line = re.sub(r'^/[^:]+/bash:', 'shell:', line)
            line = re.sub(r'^/[^:]+/psh:', 'shell:', line)
            
            # Also handle simple shell names
            line = re.sub(r'^bash:', 'shell:', line)
            line = re.sub(r'^psh:', 'shell:', line)
            
            # Normalize line numbers in error messages
            line = re.sub(r'line \d+:', 'line N:', line)
            
            normalized.append(line)
        
        return '\n'.join(normalized)
    
    def run_script(self, script_path: str, test_name: str = None,
                   timeout: int = 5, env: Dict[str, str] = None) -> TestResult:
        """Run a script file in both shells.
        
        Args:
            script_path: Path to script file
            test_name: Name for this test
            timeout: Timeout in seconds
            env: Environment variables to set
            
        Returns:
            TestResult object
        """
        test_name = test_name or os.path.basename(script_path)
        
        # Read the script content
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # Create a temporary directory with the script
        with tempfile.TemporaryDirectory(prefix="psh_test_") as temp_dir:
            # Copy script to temp directory
            temp_script = os.path.join(temp_dir, "test_script.sh")
            with open(temp_script, 'w') as f:
                f.write(script_content)
            os.chmod(temp_script, 0o755)
            
            # Run the script
            return self.run_command(
                f"./test_script.sh",
                test_name=test_name,
                timeout=timeout,
                env=env,
                working_dir=temp_dir
            )
    
    def generate_report(self, output_format: str = "text") -> str:
        """Generate a test report.
        
        Args:
            output_format: Format for report ('text', 'json', 'html')
            
        Returns:
            Report string
        """
        if output_format == "json":
            return self._generate_json_report()
        elif output_format == "html":
            return self._generate_html_report()
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate a text report."""
        lines = []
        lines.append("=" * 80)
        lines.append("BASH vs PSH Comparison Test Results")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        lines.append(f"Total tests: {total}")
        lines.append(f"Passed: {passed}")
        lines.append(f"Failed: {failed}")
        if total > 0:
            lines.append(f"Pass rate: {passed/total*100:.1f}%")
        lines.append("")
        
        # Failed tests details
        if failed > 0:
            lines.append("FAILED TESTS:")
            lines.append("-" * 80)
            
            for result in self.results:
                if not result.passed:
                    lines.append(f"\nTest: {result.test_name}")
                    lines.append(f"Command: {result.command}")
                    lines.append("Differences:")
                    for diff in result.differences:
                        lines.append("  " + diff.replace('\n', '\n  '))
        
        # Passed tests summary
        if passed > 0:
            lines.append("\nPASSED TESTS:")
            lines.append("-" * 80)
            
            for result in self.results:
                if result.passed:
                    lines.append(f"✓ {result.test_name}")
        
        return "\n".join(lines)
    
    def _generate_json_report(self) -> str:
        """Generate a JSON report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
            "results": [asdict(r) for r in self.results]
        }
        return json.dumps(report, indent=2)
    
    def _generate_html_report(self) -> str:
        """Generate an HTML report."""
        # Simple HTML report
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Bash vs PSH Comparison Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .passed { background-color: #d4edda; }
        .failed { background-color: #f8d7da; }
        .diff { background-color: #f8f9fa; padding: 10px; font-family: monospace; 
                white-space: pre-wrap; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Bash vs PSH Comparison Test Results</h1>
"""
        
        # Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        html += f"""
    <h2>Summary</h2>
    <p>Total tests: {total}</p>
    <p>Passed: {passed}</p>
    <p>Failed: {failed}</p>
    <p>Pass rate: {passed/total*100:.1f}%</p>
    
    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Command</th>
            <th>Status</th>
            <th>Details</th>
        </tr>
"""
        
        for result in self.results:
            status_class = "passed" if result.passed else "failed"
            status_text = "PASSED" if result.passed else "FAILED"
            
            html += f"""
        <tr class="{status_class}">
            <td>{result.test_name}</td>
            <td><code>{result.command}</code></td>
            <td>{status_text}</td>
            <td>
"""
            
            if not result.passed:
                html += "<div class='diff'>"
                for diff in result.differences:
                    html += f"{diff}\n"
                html += "</div>"
            
            html += """
            </td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        return html


def main():
    """Main entry point for command-line usage.
    
    For pytest-based testing, use bash_comparison_framework.py instead.
    This runner is for standalone command-line comparison testing.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compare bash and psh outputs",
        epilog="For pytest-based testing, see bash_comparison_framework.py"
    )
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("-f", "--file", help="Script file to run")
    parser.add_argument("-d", "--directory", help="Directory of test files")
    parser.add_argument("--psh", help="Path to psh executable")
    parser.add_argument("--format", choices=["text", "json", "html"], 
                       default="text", help="Output format")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("--pytest", action="store_true", 
                       help="Use pytest framework for testing")
    
    args = parser.parse_args()
    
    # Handle pytest framework usage
    if args.pytest:
        print("Running with pytest framework...")
        print("Use: pytest tests/comparison/ -v")
        return
    
    runner = ComparisonTestRunner(psh_path=args.psh)
    
    if args.command:
        runner.run_command(args.command)
    elif args.file:
        runner.run_script(args.file)
    elif args.directory:
        # Run all .sh files in directory
        for file in sorted(Path(args.directory).glob("*.sh")):
            runner.run_script(str(file))
    else:
        parser.error("Must specify either command (-c), file (-f), or directory (-d)")
    
    # Generate report
    report = runner.generate_report(args.format)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
    else:
        print(report)


if __name__ == "__main__":
    main()