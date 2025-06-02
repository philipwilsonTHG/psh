#!/usr/bin/env python3
"""Test to verify which bash is being used."""

from comparison_runner import ComparisonTestRunner

def main():
    runner = ComparisonTestRunner()
    
    # Test that shows bash version
    result = runner.run_command("echo $BASH_VERSION", "bash version check")
    
    print(f"Bash path: {runner.bash_path}")
    print(f"Bash version output: {result.bash_stdout.strip()}")
    print(f"PSH output: {result.psh_stdout.strip()}")
    
    # Also test with explicit path
    result2 = runner.run_command("which bash", "which bash")
    print(f"\nWhich bash: {result2.bash_stdout.strip()}")

if __name__ == "__main__":
    main()