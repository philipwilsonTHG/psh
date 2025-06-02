#!/usr/bin/env python3
"""
Quick demo of the comparison testing framework.
"""

from comparison_runner import ComparisonTestRunner

def main():
    """Run a few simple comparison tests as a demo."""
    print("PSH vs Bash Comparison Demo")
    print("===========================\n")
    
    runner = ComparisonTestRunner()
    
    # Simple tests to demonstrate the framework
    demo_tests = [
        ("echo hello world", "Simple echo"),
        ("echo $HOME", "Variable expansion"),
        ("echo $(date +%Y)", "Command substitution"),
        ("echo {1..5}", "Brace expansion"),
        ("true && echo success", "Conditional execution"),
        ("echo one | tr a-z A-Z", "Pipeline"),
        ("for i in 1 2 3; do echo $i; done", "For loop"),
    ]
    
    print("Running demo tests...\n")
    
    for command, description in demo_tests:
        result = runner.run_command(command, description)
        
        if result.passed:
            print(f"✓ {description}")
            print(f"  Command: {command}")
            print(f"  Output: {result.psh_stdout.strip()}")
        else:
            print(f"✗ {description}")
            print(f"  Command: {command}")
            print(f"  Differences:")
            for diff in result.differences:
                print(f"    {diff}")
        print()
    
    # Summary
    total = len(runner.results)
    passed = sum(1 for r in runner.results if r.passed)
    
    print(f"\nSummary: {passed}/{total} tests passed")
    
    # Generate a simple HTML report
    print("\nGenerating demo_report.html...")
    html = runner.generate_report("html")
    with open("demo_report.html", "w") as f:
        f.write(html)
    print("Report saved to demo_report.html")


if __name__ == "__main__":
    main()