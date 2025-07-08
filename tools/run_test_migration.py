#!/usr/bin/env python3
"""
Test migration runner - runs both old and new test suites with comparison.

This script helps track progress during the test migration by running
both test suites and comparing results.
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime


class TestMigrationRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'legacy': {},
            'new': {},
            'comparison': {}
        }
        
    def run_legacy_tests(self):
        """Run the legacy test suite."""
        print("\n" + "="*60)
        print("Running Legacy Test Suite")
        print("="*60)
        
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short'],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start_time
        
        # Parse results
        output_lines = result.stdout.split('\n')
        summary_line = next((line for line in output_lines if 'passed' in line and 'failed' in line), '')
        
        self.results['legacy'] = {
            'return_code': result.returncode,
            'elapsed_time': elapsed,
            'summary': summary_line,
            'passed': result.returncode == 0
        }
        
        print(f"\nLegacy tests completed in {elapsed:.2f}s")
        print(f"Summary: {summary_line}")
        
        return result.returncode == 0
        
    def run_new_tests(self):
        """Run the new test suite."""
        print("\n" + "="*60)
        print("Running New Test Suite")
        print("="*60)
        
        # Check if new tests exist
        new_test_dir = self.project_root / 'tests_new'
        if not new_test_dir.exists():
            print("New test directory not found")
            return False
            
        test_files = list(new_test_dir.rglob('test_*.py'))
        if not test_files:
            print("No test files found in new test suite")
            return True
            
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests_new/', '-v', '--tb=short'],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start_time
        
        # Parse results
        output_lines = result.stdout.split('\n')
        summary_line = next((line for line in output_lines if 'passed' in line), '')
        
        self.results['new'] = {
            'return_code': result.returncode,
            'elapsed_time': elapsed,
            'summary': summary_line,
            'passed': result.returncode == 0,
            'test_files': len(test_files)
        }
        
        print(f"\nNew tests completed in {elapsed:.2f}s")
        print(f"Found {len(test_files)} test files")
        print(f"Summary: {summary_line}")
        
        return result.returncode == 0
        
    def analyze_migration_progress(self):
        """Analyze and report migration progress."""
        print("\n" + "="*60)
        print("Migration Progress Analysis")
        print("="*60)
        
        # Run analysis script on both directories
        legacy_analysis = self._run_analysis('tests')
        new_analysis = self._run_analysis('tests_new')
        
        if legacy_analysis and new_analysis:
            legacy_count = legacy_analysis['summary']['total_test_methods']
            new_count = new_analysis['summary']['total_test_methods']
            
            progress = (new_count / legacy_count * 100) if legacy_count > 0 else 0
            
            print(f"\nTest Migration Progress:")
            print(f"  Legacy tests: {legacy_count}")
            print(f"  New tests: {new_count}")
            print(f"  Progress: {progress:.1f}%")
            
            # Component coverage comparison
            print("\nComponent Coverage:")
            all_components = set(legacy_analysis['by_component'].keys()) | set(new_analysis['by_component'].keys())
            
            for component in sorted(all_components):
                legacy_files = len(legacy_analysis['by_component'].get(component, {}).get('files', []))
                new_files = len(new_analysis['by_component'].get(component, {}).get('files', []))
                status = "✓" if new_files > 0 else "✗"
                print(f"  {component:20} Legacy: {legacy_files:3d} files, New: {new_files:3d} files {status}")
                
            self.results['comparison'] = {
                'progress_percentage': progress,
                'legacy_test_count': legacy_count,
                'new_test_count': new_count
            }
            
    def _run_analysis(self, test_dir):
        """Run test analysis script."""
        try:
            result = subprocess.run(
                [sys.executable, 'tools/analyze_tests.py', '--test-dir', test_dir, '--output-json', '-'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            pass
        return None
        
    def run_conformance_tests(self):
        """Run conformance tests."""
        print("\n" + "="*60) 
        print("Running Conformance Tests")
        print("="*60)
        
        conformance_dir = self.project_root / 'conformance_tests'
        if not conformance_dir.exists():
            print("Conformance tests not found")
            return
            
        result = subprocess.run(
            [sys.executable, 'run_conformance_tests.py', '--mode', 'posix', '--bash-compare'],
            cwd=conformance_dir,
            capture_output=True,
            text=True
        )
        
        # Extract pass/fail counts
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if 'tests passed' in line:
                print(f"Conformance: {line}")
                
    def generate_report(self):
        """Generate a summary report."""
        print("\n" + "="*60)
        print("Test Migration Summary")
        print("="*60)
        
        # Overall status
        all_passed = (
            self.results['legacy'].get('passed', False) and 
            self.results['new'].get('passed', True)  # True if no new tests
        )
        
        print(f"\nOverall Status: {'✓ PASSED' if all_passed else '✗ FAILED'}")
        print(f"\nLegacy Suite: {'✓ PASSED' if self.results['legacy'].get('passed') else '✗ FAILED'}")
        print(f"New Suite: {'✓ PASSED' if self.results['new'].get('passed') else '✗ FAILED'}")
        
        if 'progress_percentage' in self.results['comparison']:
            print(f"\nMigration Progress: {self.results['comparison']['progress_percentage']:.1f}%")
            
        # Save results
        report_file = self.project_root / 'test_migration_report.json'
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")
        
        return all_passed
        
    def run(self):
        """Run the complete test migration check."""
        print("PSH Test Migration Runner")
        print(f"Project: {self.project_root}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run test suites
        legacy_ok = self.run_legacy_tests()
        new_ok = self.run_new_tests()
        
        # Run analysis
        self.analyze_migration_progress()
        
        # Run conformance tests
        self.run_conformance_tests()
        
        # Generate report
        all_ok = self.generate_report()
        
        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0 if all_ok else 1


def main():
    """Main entry point."""
    runner = TestMigrationRunner()
    sys.exit(runner.run())


if __name__ == '__main__':
    main()