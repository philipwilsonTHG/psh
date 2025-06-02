#!/usr/bin/env python3
"""
Master test runner for bash vs psh comparison tests.

Runs all test suites and generates a comprehensive report.
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime
from comparison_runner import ComparisonTestRunner


def run_test_module(module_path: str) -> tuple[int, int]:
    """Run a test module and return (passed, total) counts."""
    print(f"\n{'='*60}")
    print(f"Running {Path(module_path).stem}...")
    print(f"{'='*60}")
    
    # Import and run the module
    spec = importlib.util.spec_from_file_location("test_module", module_path)
    module = importlib.util.module_from_spec(spec)
    
    # Capture results by running the module's main
    old_argv = sys.argv
    sys.argv = [module_path]  # Don't pass --report to individual modules
    
    try:
        spec.loader.exec_module(module)
        # Extract results from the module's runners
        all_results = []
        
        # Each test module creates runners, we need to collect their results
        # This is a bit hacky but works for our structure
        import test_basic_commands
        import test_expansions
        import test_control_structures
        
        if 'basic' in module_path:
            runner1 = test_basic_commands.run_basic_tests()
            runner2 = test_basic_commands.run_glob_tests()
            all_results = runner1.results + runner2.results
        elif 'expansion' in module_path:
            runners = [
                test_expansions.run_variable_expansion_tests(),
                test_expansions.run_command_substitution_tests(),
                test_expansions.run_arithmetic_expansion_tests(),
                test_expansions.run_brace_expansion_tests(),
                test_expansions.run_tilde_expansion_tests(),
            ]
            for runner in runners:
                all_results.extend(runner.results)
        elif 'control' in module_path:
            runners = [
                test_control_structures.run_if_tests(),
                test_control_structures.run_while_tests(),
                test_control_structures.run_for_tests(),
                test_control_structures.run_case_tests(),
                test_control_structures.run_break_continue_tests(),
            ]
            for runner in runners:
                all_results.extend(runner.results)
        
        total = len(all_results)
        passed = sum(1 for r in all_results if r.passed)
        
        return passed, total, all_results
        
    except SystemExit:
        # Modules call sys.exit, catch it
        return 0, 0, []
    finally:
        sys.argv = old_argv


def main():
    """Run all comparison tests and generate comprehensive report."""
    print("Bash vs PSH Comparison Test Suite")
    print("=================================")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find all test modules
    test_dir = Path(__file__).parent
    test_modules = sorted(test_dir.glob("test_*.py"))
    
    # Skip the runner itself
    test_modules = [m for m in test_modules if m.name != "run_all_tests.py"]
    
    # Run each test module and collect results
    all_results = []
    module_summaries = []
    
    for module_path in test_modules:
        passed, total, results = run_test_module(str(module_path))
        all_results.extend(results)
        module_summaries.append({
            'name': module_path.stem,
            'passed': passed,
            'total': total,
            'failed': total - passed
        })
    
    # Generate summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_tests = sum(m['total'] for m in module_summaries)
    total_passed = sum(m['passed'] for m in module_summaries)
    total_failed = total_tests - total_passed
    
    # Module breakdown
    print("\nBy Module:")
    for summary in module_summaries:
        if summary['total'] > 0:
            pass_rate = summary['passed'] / summary['total'] * 100
            print(f"  {summary['name']:.<30} "
                  f"{summary['passed']:>3}/{summary['total']:<3} "
                  f"({pass_rate:>5.1f}%)")
    
    print("\nOverall:")
    print(f"  Total tests: {total_tests}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    if total_tests > 0:
        print(f"  Pass rate: {total_passed/total_tests*100:.1f}%")
    
    # Generate detailed HTML report
    print("\nGenerating detailed report...")
    runner = ComparisonTestRunner()
    runner.results = all_results
    
    # HTML report
    html_report = runner.generate_report("html")
    with open("comparison_report.html", "w") as f:
        f.write(html_report)
    print("  HTML report: comparison_report.html")
    
    # Text report
    text_report = runner.generate_report("text")
    with open("comparison_report.txt", "w") as f:
        f.write(text_report)
    print("  Text report: comparison_report.txt")
    
    # JSON report for processing
    json_report = runner.generate_report("json")
    with open("comparison_report.json", "w") as f:
        f.write(json_report)
    print("  JSON report: comparison_report.json")
    
    # Show failed tests summary
    if total_failed > 0:
        print(f"\n{total_failed} tests failed. See reports for details.")
        
        # Quick summary of failures
        print("\nFailed tests:")
        for result in all_results:
            if not result.passed:
                print(f"  - {result.test_name}")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with error if any tests failed
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()