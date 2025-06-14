#!/usr/bin/env python3
"""
Test runner for visitor executor validation.

This script runs the full test suite with the visitor executor enabled
and compares results with the legacy executor.
"""

import os
import sys
import subprocess
import json
import time
from collections import defaultdict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VisitorExecutorTester:
    """Test the visitor executor against the full test suite."""
    
    def __init__(self):
        self.results = {
            'legacy': {'passed': 0, 'failed': 0, 'errors': []},
            'visitor': {'passed': 0, 'failed': 0, 'errors': []},
            'differences': []
        }
        self.test_dir = Path(__file__).parent.parent / 'tests'
    
    def run_tests_with_executor(self, use_visitor=False):
        """Run pytest with specific executor."""
        env = os.environ.copy()
        if use_visitor:
            # Set environment variable to use visitor executor
            env['PSH_USE_VISITOR_EXECUTOR'] = '1'
        
        cmd = [
            sys.executable, '-m', 'pytest',
            str(self.test_dir),
            '-v',
            '--tb=short',
            '--no-header',
            '-q'
        ]
        
        print(f"\nRunning tests with {'visitor' if use_visitor else 'legacy'} executor...")
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        executor_type = 'visitor' if use_visitor else 'legacy'
        
        # Parse output
        lines = result.stdout.splitlines()
        for line in lines:
            if ' PASSED' in line:
                self.results[executor_type]['passed'] += 1
            elif ' FAILED' in line:
                self.results[executor_type]['failed'] += 1
                self.results[executor_type]['errors'].append(line.strip())
            elif ' ERROR' in line:
                self.results[executor_type]['failed'] += 1
                self.results[executor_type]['errors'].append(line.strip())
        
        # Also check summary line
        if result.stderr:
            for line in result.stderr.splitlines():
                if 'failed' in line and 'passed' in line:
                    # Parse pytest summary
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'passed' and i > 0:
                            try:
                                self.results[executor_type]['passed'] = int(parts[i-1])
                            except ValueError:
                                pass
                        elif part == 'failed' and i > 0:
                            try:
                                self.results[executor_type]['failed'] = int(parts[i-1])
                            except ValueError:
                                pass
        
        print(f"Completed in {elapsed:.2f}s")
        print(f"Passed: {self.results[executor_type]['passed']}")
        print(f"Failed: {self.results[executor_type]['failed']}")
        
        return result.returncode
    
    def find_test_differences(self):
        """Find tests that pass with one executor but fail with another."""
        legacy_errors = set(self.results['legacy']['errors'])
        visitor_errors = set(self.results['visitor']['errors'])
        
        # Tests that fail only with visitor
        visitor_only_failures = visitor_errors - legacy_errors
        # Tests that fail only with legacy
        legacy_only_failures = legacy_errors - visitor_errors
        
        if visitor_only_failures:
            self.results['differences'].append({
                'type': 'visitor_only_failures',
                'tests': list(visitor_only_failures),
                'count': len(visitor_only_failures)
            })
        
        if legacy_only_failures:
            self.results['differences'].append({
                'type': 'legacy_only_failures', 
                'tests': list(legacy_only_failures),
                'count': len(legacy_only_failures)
            })
    
    def generate_report(self):
        """Generate a detailed report of the test results."""
        report = []
        report.append("=" * 80)
        report.append("Visitor Executor Test Report")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append("Summary:")
        report.append("-" * 40)
        report.append(f"Legacy Executor:  {self.results['legacy']['passed']} passed, "
                     f"{self.results['legacy']['failed']} failed")
        report.append(f"Visitor Executor: {self.results['visitor']['passed']} passed, "
                     f"{self.results['visitor']['failed']} failed")
        report.append("")
        
        # Differences
        if self.results['differences']:
            report.append("Differences Found:")
            report.append("-" * 40)
            
            for diff in self.results['differences']:
                if diff['type'] == 'visitor_only_failures':
                    report.append(f"\nTests that fail ONLY with visitor executor ({diff['count']}):")
                    for test in diff['tests'][:10]:  # Show first 10
                        report.append(f"  - {test}")
                    if diff['count'] > 10:
                        report.append(f"  ... and {diff['count'] - 10} more")
                
                elif diff['type'] == 'legacy_only_failures':
                    report.append(f"\nTests that fail ONLY with legacy executor ({diff['count']}):")
                    for test in diff['tests'][:10]:  # Show first 10
                        report.append(f"  - {test}")
                    if diff['count'] > 10:
                        report.append(f"  ... and {diff['count'] - 10} more")
        else:
            report.append("No differences found - both executors behave identically!")
        
        report.append("")
        report.append("=" * 80)
        
        return '\n'.join(report)
    
    def save_results(self):
        """Save detailed results to JSON file."""
        output_file = Path(__file__).parent / 'visitor_executor_test_results.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed results saved to: {output_file}")
    
    def run_specific_test(self, test_path, use_visitor=False):
        """Run a specific test with the given executor."""
        env = os.environ.copy()
        if use_visitor:
            env['PSH_USE_VISITOR_EXECUTOR'] = '1'
        
        cmd = [
            sys.executable, '-m', 'pytest',
            test_path,
            '-xvs',
            '--tb=short'
        ]
        
        result = subprocess.run(cmd, env=env)
        return result.returncode == 0
    
    def diagnose_failures(self):
        """Run failing tests individually to get better error messages."""
        if not self.results['differences']:
            return
        
        print("\nDiagnosing visitor-only failures...")
        print("-" * 40)
        
        for diff in self.results['differences']:
            if diff['type'] == 'visitor_only_failures' and diff['tests']:
                # Take first failure for diagnosis
                test_spec = diff['tests'][0]
                print(f"\nDiagnosing: {test_spec}")
                
                # Extract test file and name
                if '::' in test_spec:
                    parts = test_spec.split('::')
                    test_file = parts[0].split()[-1]  # Handle pytest output format
                    
                    # Run with visitor executor for detailed output
                    print("With visitor executor:")
                    self.run_specific_test(test_file + '::' + '::'.join(parts[1:]), use_visitor=True)


def main():
    """Main entry point."""
    tester = VisitorExecutorTester()
    
    # Check if we should run a specific mode
    if len(sys.argv) > 1:
        if sys.argv[1] == '--diagnose':
            # Run tests and diagnose failures
            tester.run_tests_with_executor(use_visitor=False)
            tester.run_tests_with_executor(use_visitor=True)
            tester.find_test_differences()
            tester.diagnose_failures()
        elif sys.argv[1] == '--quick':
            # Just run with visitor executor
            return tester.run_tests_with_executor(use_visitor=True)
        else:
            print("Usage: test_visitor_executor.py [--diagnose|--quick]")
            return 1
    else:
        # Default: run both and compare
        print("Testing PSH with legacy and visitor executors...")
        print("=" * 80)
        
        # Run with legacy executor
        legacy_status = tester.run_tests_with_executor(use_visitor=False)
        
        # Run with visitor executor  
        visitor_status = tester.run_tests_with_executor(use_visitor=True)
        
        # Find differences
        tester.find_test_differences()
        
        # Generate and print report
        report = tester.generate_report()
        print("\n" + report)
        
        # Save results
        tester.save_results()
        
        # Return non-zero if visitor has more failures
        if tester.results['visitor']['failed'] > tester.results['legacy']['failed']:
            return 1
        return 0


if __name__ == '__main__':
    sys.exit(main())