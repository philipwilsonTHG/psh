#!/usr/bin/env python3
"""
PSH Test Runner

This script runs the full PSH test suite with proper handling for tests that
require special pytest configuration (e.g., subshell tests that need capture disabled).

Usage:
    python run_tests.py                    # Run all tests with smart handling
    python run_tests.py --all-nocapture    # Run ALL tests with -s flag
    python run_tests.py --quick            # Run only fast tests
    python run_tests.py --help             # Show help
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'=' * 80}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('=' * 80)

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run PSH tests with proper handling for special test requirements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Smart mode (recommended)
  python run_tests.py --all-nocapture    # All tests with -s (simpler but noisy)
  python run_tests.py --quick            # Fast tests only
  python run_tests.py --verbose          # Verbose output
  python run_tests.py --subshells-only   # Just subshell tests
        """
    )

    parser.add_argument(
        '--all-nocapture', '-s',
        action='store_true',
        help='Run ALL tests with -s flag (disable capture everywhere). Simpler but loses pytest output capture benefits.'
    )

    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Run only fast tests (skip slow performance tests)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output (show each test)'
    )

    parser.add_argument(
        '--subshells-only',
        action='store_true',
        help='Run only subshell tests (with -s flag)'
    )

    parser.add_argument(
        '--no-subshells',
        action='store_true',
        help='Skip subshell tests entirely'
    )

    parser.add_argument(
        'pytest_args',
        nargs='*',
        help='Additional arguments to pass to pytest'
    )

    args = parser.parse_args()

    # Build base pytest command
    base_cmd = ['python', '-m', 'pytest']

    if args.verbose:
        base_cmd.append('-v')

    # Add any extra pytest args
    if args.pytest_args:
        base_cmd.extend(args.pytest_args)

    exit_codes = []

    if args.all_nocapture:
        # Simple mode: run everything with -s
        print("\n" + "=" * 80)
        print("MODE: Running ALL tests with capture disabled (-s flag)")
        print("=" * 80)

        cmd = base_cmd + ['tests/', '-s']
        if args.quick:
            cmd.extend(['-m', 'not slow'])

        exit_code = run_command(cmd, "All tests with capture disabled")
        exit_codes.append(exit_code)

    elif args.subshells_only:
        # Just run subshell tests
        print("\n" + "=" * 80)
        print("MODE: Running subshell tests only")
        print("=" * 80)

        cmd = base_cmd + ['tests/integration/subshells/', '-s']
        exit_code = run_command(cmd, "Subshell tests (with -s)")
        exit_codes.append(exit_code)

    else:
        # Smart mode: Run tests in two phases
        print("\n" + "=" * 80)
        print("MODE: Smart test runner (recommended)")
        print("  - Phase 1: Regular tests with normal capture")
        print("  - Phase 2: Subshell tests with capture disabled (-s)")
        print("=" * 80)

        if not args.no_subshells:
            # Phase 1: Run non-subshell tests normally
            cmd = base_cmd + [
                'tests/',
                '--ignore=tests/integration/subshells/',
                '--ignore=tests/integration/functions/test_function_advanced.py',
                '--ignore=tests/integration/variables/test_variable_assignment.py',
            ]
            if args.quick:
                cmd.extend(['-m', 'not slow'])

            exit_code = run_command(cmd, "Phase 1: Regular tests (with capture)")
            exit_codes.append(exit_code)

        if not args.no_subshells:
            # Phase 2: Run subshell tests with -s
            cmd = base_cmd + [
                'tests/integration/subshells/',
                '-s'
            ]

            exit_code = run_command(cmd, "Phase 2: Subshell tests (with -s)")
            exit_codes.append(exit_code)

            # Phase 3: Run the other tests that need -s
            cmd = base_cmd + [
                'tests/integration/functions/test_function_advanced.py::test_function_with_subshell',
                'tests/integration/variables/test_variable_assignment.py::test_assignment_with_subshell',
                '-s'
            ]

            exit_code = run_command(cmd, "Phase 3: Other tests needing -s")
            exit_codes.append(exit_code)

    # Summary
    print("\n" + "=" * 80)
    print("TEST RUN SUMMARY")
    print("=" * 80)

    if all(code == 0 for code in exit_codes):
        print("✅ All test phases PASSED")
        return 0
    else:
        print("❌ Some test phases FAILED")
        for i, code in enumerate(exit_codes, 1):
            status = "✅ PASSED" if code == 0 else "❌ FAILED"
            print(f"   Phase {i}: {status} (exit code: {code})")
        return 1


if __name__ == '__main__':
    sys.exit(main())
