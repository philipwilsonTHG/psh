#!/usr/bin/env python3
"""
Convenience script for running select statement tests.

This script handles the pytest -s requirement automatically and provides
easy access to different types of select tests.
"""

import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and display the description."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd)
    return result.returncode

def main():
    """Main function to run select tests."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "help"
    
    # Base directory
    psh_dir = Path(__file__).parent.parent
    
    if test_type == "help" or test_type == "-h" or test_type == "--help":
        print("""
Select Statement Test Runner

Usage: python scripts/test_select.py [option]

Options:
  all           Run all select tests (interactive + non-interactive)
  interactive   Run only interactive tests (requires user input simulation)
  non-interactive Run only non-interactive tests (parsing, syntax)
  quick         Run quick non-interactive tests only
  verbose       Run all tests with verbose output
  help          Show this help message

Examples:
  python scripts/test_select.py all              # Run everything  
  python scripts/test_select.py interactive      # Interactive tests only
  python scripts/test_select.py quick            # Fast tests only
  python scripts/test_select.py verbose          # All tests with -v

Note: Interactive tests use file redirection to simulate user input,
      so they don't actually require manual input despite needing -s flag.
""")
        return 0
    
    # Build pytest commands
    base_cmd = ["python", "-m", "pytest"]
    test_file = "tests/test_select_statement.py"
    
    if test_type == "all":
        # First run non-interactive (always works)
        exit_code = run_command(
            base_cmd + [f"{test_file}::TestSelectStatementNonInteractive", "-v"],
            "Non-Interactive Select Tests"
        )
        
        # Then run interactive with -s
        exit_code2 = run_command(
            base_cmd + [f"{test_file}::TestSelectStatement", "-s", "-v"],
            "Interactive Select Tests (with -s flag)"
        )
        
        return exit_code or exit_code2
    
    elif test_type == "interactive":
        # Remove skip decorator temporarily for this run
        print("Note: This temporarily enables interactive tests for demonstration")
        return run_command(
            base_cmd + [f"{test_file}::TestSelectStatement", "-s", "-v"],
            "Interactive Select Tests"
        )
    
    elif test_type == "non-interactive" or test_type == "quick":
        return run_command(
            base_cmd + [f"{test_file}::TestSelectStatementNonInteractive", "-v"],
            "Non-Interactive Select Tests"
        )
    
    elif test_type == "verbose":
        # Run all with extra verbosity
        exit_code = run_command(
            base_cmd + [f"{test_file}::TestSelectStatementNonInteractive", "-vv"],
            "Non-Interactive Select Tests (Verbose)"
        )
        
        exit_code2 = run_command(
            base_cmd + [f"{test_file}::TestSelectStatement", "-s", "-vv"],
            "Interactive Select Tests (Verbose)"
        )
        
        return exit_code or exit_code2
    
    else:
        print(f"Unknown option: {test_type}")
        print("Use 'python scripts/test_select.py help' for usage information")
        return 1

if __name__ == "__main__":
    sys.exit(main())