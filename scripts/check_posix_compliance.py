#!/usr/bin/env python3
"""
Check PSH POSIX compliance by running a comprehensive test suite.
This script runs various POSIX shell constructs and compares PSH behavior
with a reference POSIX shell.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.posix_compliance.posix_comparison_framework import POSIXComparisonFramework


class POSIXComplianceChecker:
    """Check PSH compliance with POSIX specifications."""
    
    def __init__(self, verbose: bool = False):
        self.framework = POSIXComparisonFramework()
        self.verbose = verbose
        self.results = {
            "passed": [],
            "failed": [],
            "errors": []
        }
    
    def run_tests(self) -> Dict:
        """Run all POSIX compliance tests."""
        print("PSH POSIX Compliance Check")
        print("=" * 50)
        print(f"Reference shell: {' '.join(self.framework.posix_shell)}")
        print()
        
        # Set up test environment
        self.framework.setup()
        
        try:
            # Run test categories
            self._test_basic_syntax()
            self._test_parameter_expansion()
            self._test_special_parameters()
            self._test_control_structures()
            self._test_builtin_commands()
            self._test_redirections()
            self._test_quoting()
            self._test_expansions()
            self._test_exit_status()
            
        finally:
            # Clean up
            self.framework.teardown()
        
        # Generate report
        return self._generate_report()
    
    def _run_test(self, name: str, command: str, **kwargs) -> bool:
        """Run a single test and record results."""
        if self.verbose:
            print(f"Testing: {name}")
            print(f"Command: {command}")
        
        try:
            psh_result, posix_result = self.framework.compare_command(command, **kwargs)
            
            # Check if results match
            if (psh_result.stdout == posix_result.stdout and 
                psh_result.returncode == posix_result.returncode):
                self.results["passed"].append({
                    "name": name,
                    "command": command,
                    "output": psh_result.stdout,
                    "returncode": psh_result.returncode
                })
                if self.verbose:
                    print("✓ PASSED\n")
                return True
            else:
                self.results["failed"].append({
                    "name": name,
                    "command": command,
                    "psh_output": psh_result.stdout,
                    "psh_returncode": psh_result.returncode,
                    "posix_output": posix_result.stdout,
                    "posix_returncode": posix_result.returncode
                })
                if self.verbose:
                    print(f"✗ FAILED")
                    print(f"  PSH output: '{psh_result.stdout}' (exit {psh_result.returncode})")
                    print(f"  POSIX output: '{posix_result.stdout}' (exit {posix_result.returncode})\n")
                return False
                
        except Exception as e:
            self.results["errors"].append({
                "name": name,
                "command": command,
                "error": str(e)
            })
            if self.verbose:
                print(f"✗ ERROR: {e}\n")
            return False
    
    def _test_basic_syntax(self):
        """Test basic command syntax."""
        print("\n1. Basic Syntax Tests")
        print("-" * 30)
        
        tests = [
            ("Simple command", "echo hello"),
            ("Command with args", "echo one two three"),
            ("Multiple commands", "echo first; echo second"),
            ("Pipeline", "echo test | cat"),
            ("AND list", "true && echo success"),
            ("OR list", "false || echo recovery"),
            ("Background command", "sleep 0.01 &"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_parameter_expansion(self):
        """Test parameter expansion forms."""
        print("\n2. Parameter Expansion Tests")
        print("-" * 30)
        
        # Use compound commands to test multiple expansions
        tests = [
            ("Basic expansion", "var=value; echo ${var}"),
            ("Default value", "unset var; echo ${var:-default}"),
            ("Assign default", "unset var; echo ${var:=assigned}; echo $var"),
            ("Alternative value", "var=set; echo ${var:+alternative}"),
            ("String length", "var=hello; echo ${#var}"),
            ("Remove prefix", "path=/usr/bin/prog; echo ${path#*/}"),
            ("Remove suffix", "file=doc.txt; echo ${file%.txt}"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_special_parameters(self):
        """Test special parameters."""
        print("\n3. Special Parameters Tests")
        print("-" * 30)
        
        tests = [
            ("Positional params", "set -- one two; echo $1 $2"),
            ("Parameter count", "set -- a b c; echo $#"),
            ("All params (@)", 'set -- one "two three"; printf "[%s]\\n" "$@"'),
            ("All params (*)", 'set -- one two; echo "$*"'),
            ("Exit status", "true; echo $?"),
            ("Shell PID", "echo $$ | grep -q '^[0-9][0-9]*$'; echo $?"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_control_structures(self):
        """Test control structures."""
        print("\n4. Control Structures Tests")
        print("-" * 30)
        
        tests = [
            ("If statement", "if true; then echo yes; fi"),
            ("If-else", "if false; then echo no; else echo yes; fi"),
            ("While loop", "i=0; while [ $i -lt 2 ]; do echo $i; i=$((i+1)); done"),
            ("For loop", "for i in 1 2; do echo $i; done"),
            ("Case statement", 'x=b; case $x in a) echo A;; b) echo B;; esac'),
            ("Function", "f() { echo func; }; f"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_builtin_commands(self):
        """Test built-in commands."""
        print("\n5. Built-in Commands Tests")
        print("-" * 30)
        
        tests = [
            ("Colon command", ": arg1 arg2"),
            ("Dot command", "echo 'x=1' > /tmp/test.sh; . /tmp/test.sh; echo $x; rm /tmp/test.sh"),
            ("Export", "export VAR=exported; echo $VAR"),
            ("Unset", "x=1; unset x; echo ${x:-unset}"),
            ("Set positional", "set -- a b; echo $1 $2"),
            ("Break", "for i in 1 2 3; do if [ $i = 2 ]; then break; fi; echo $i; done"),
            ("Continue", "for i in 1 2 3; do if [ $i = 2 ]; then continue; fi; echo $i; done"),
            ("Return", "f() { return 42; }; f; echo $?"),
            ("Eval", "cmd='echo test'; eval $cmd"),
            ("Exit", "(exit 5); echo $?"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_redirections(self):
        """Test I/O redirections."""
        print("\n6. Redirection Tests")
        print("-" * 30)
        
        tests = [
            ("Output redirect", "echo test > /tmp/out; cat /tmp/out; rm /tmp/out"),
            ("Input redirect", "echo data > /tmp/in; cat < /tmp/in; rm /tmp/in"),
            ("Append", "echo 1 > /tmp/a; echo 2 >> /tmp/a; cat /tmp/a; rm /tmp/a"),
            ("Stderr redirect", "echo err >&2 2>&1"),
            ("Here doc", "cat << EOF\\nhello\\nEOF"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_quoting(self):
        """Test quoting rules."""
        print("\n7. Quoting Tests")
        print("-" * 30)
        
        tests = [
            ("Single quotes", "echo 'no $expansion'"),
            ("Double quotes", 'x=var; echo "$x"'),
            ("Backslash", "echo \\$HOME"),
            ("Mixed quotes", '''echo 'single' "double"'''),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_expansions(self):
        """Test word expansions."""
        print("\n8. Word Expansion Tests")
        print("-" * 30)
        
        tests = [
            ("Command substitution", "echo $(echo nested)"),
            ("Arithmetic expansion", "echo $((2 + 3))"),
            ("Tilde expansion", "echo ~ | grep -q '^/'; echo $?"),
            ("Field splitting", "IFS=:; set -- $(echo a:b:c); echo $#; IFS=' \t\n'"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _test_exit_status(self):
        """Test exit status handling."""
        print("\n9. Exit Status Tests")
        print("-" * 30)
        
        tests = [
            ("Success status", "true; echo $?"),
            ("Failure status", "false; echo $?"),
            ("Command not found", "nonexistent_command_xyz 2>/dev/null; echo $?"),
            ("Pipeline status", "true | false; echo $?"),
        ]
        
        for name, command in tests:
            self._run_test(name, command)
    
    def _generate_report(self) -> Dict:
        """Generate compliance report."""
        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["errors"])
        passed = len(self.results["passed"])
        failed = len(self.results["failed"])
        errors = len(self.results["errors"])
        
        compliance_rate = (passed / total * 100) if total > 0 else 0
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "reference_shell": ' '.join(self.framework.posix_shell),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "compliance_rate": f"{compliance_rate:.1f}%"
            },
            "details": self.results
        }
        
        # Print summary
        print("\n" + "=" * 50)
        print("POSIX Compliance Summary")
        print("=" * 50)
        print(f"Total tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Errors: {errors} ({errors/total*100:.1f}%)")
        print(f"\nOverall POSIX Compliance: {compliance_rate:.1f}%")
        
        if failed > 0:
            print("\nFailed tests:")
            for test in self.results["failed"][:5]:  # Show first 5 failures
                print(f"  - {test['name']}: {test['command']}")
            if failed > 5:
                print(f"  ... and {failed - 5} more")
        
        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check PSH POSIX compliance"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed test output"
    )
    parser.add_argument(
        "-o", "--output",
        help="Save detailed report to JSON file"
    )
    
    args = parser.parse_args()
    
    # Run compliance check
    checker = POSIXComplianceChecker(verbose=args.verbose)
    report = checker.run_tests()
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {args.output}")
    
    # Exit with status based on compliance
    compliance_rate = float(report["summary"]["compliance_rate"].rstrip('%'))
    sys.exit(0 if compliance_rate >= 80 else 1)


if __name__ == "__main__":
    main()