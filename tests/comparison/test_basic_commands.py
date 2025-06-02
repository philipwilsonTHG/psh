#!/usr/bin/env python3
"""
Basic command and operator comparison tests.

Tests basic shell functionality like command execution, pipes, 
semicolons, background processes, and conditional operators.
"""

from comparison_runner import ComparisonTestRunner


def run_basic_tests():
    """Run basic command and operator tests."""
    runner = ComparisonTestRunner()
    
    # Simple command execution
    tests = [
        # Basic commands
        ("echo hello", "simple echo"),
        ("echo hello world", "echo with multiple args"),
        ("echo 'hello world'", "echo with single quotes"),
        ('echo "hello world"', "echo with double quotes"),
        ("echo hello; echo world", "multiple commands with semicolon"),
        ("echo one; echo two; echo three", "three commands"),
        
        # Command with exit codes
        ("true", "true command"),
        ("false", "false command"),
        ("true; echo $?", "exit code of true"),
        ("false; echo $?", "exit code of false"),
        
        # Pipes
        ("echo hello | cat", "simple pipe"),
        ("echo hello world | wc -w", "pipe to wc"),
        ("echo -e 'one\\ntwo\\nthree' | grep two", "pipe to grep"),
        ("echo hello | cat | cat", "double pipe"),
        ("echo -e 'a\\nb\\nc' | head -2 | tail -1", "triple pipe"),
        
        # Conditional operators
        ("true && echo success", "AND operator - success"),
        ("false && echo success", "AND operator - failure"),
        ("true || echo failure", "OR operator - success"),
        ("false || echo failure", "OR operator - failure"),
        ("true && echo first && echo second", "chained AND"),
        ("false || echo first || echo second", "chained OR"),
        ("true && false || echo recovered", "AND then OR"),
        
        # Comments
        ("echo hello # this is a comment", "inline comment"),
        ("# this is a comment\necho hello", "comment line"),
        ("echo hello#world", "hash not at word boundary"),
        ("echo 'hello # world'", "hash in quotes"),
        ('echo "hello # world"', "hash in double quotes"),
        
        # Multiple commands and operators
        ("echo one; false; echo two", "semicolon ignores exit code"),
        ("echo one && false && echo two", "AND stops on failure"),
        ("echo one || false || echo two", "OR continues on success"),
        
        # Whitespace handling
        ("echo    hello    world", "multiple spaces"),
        ("echo\thello\tworld", "tabs"),
        ("   echo hello   ", "leading/trailing spaces"),
        
        # Empty and whitespace-only commands
        ("", "empty command"),
        ("   ", "whitespace-only command"),
        ("echo hello;; echo world", "empty command between semicolons"),
        
        # Special characters in arguments
        ("echo '$HOME'", "single-quoted variable"),
        ('echo "$HOME"', "double-quoted variable (not expanded yet)"),
        ("echo \\$HOME", "escaped dollar sign"),
        ("echo 'hello\\'world'", "escaped quote in single quotes"),
        ('echo "hello\\"world"', "escaped quote in double quotes"),
    ]
    
    print("Running basic command tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            print(f"    Command: {command}")
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_glob_tests():
    """Run globbing/wildcard tests."""
    runner = ComparisonTestRunner()
    
    # Set up test files - note: no mkdir -p needed, we start fresh each time
    setup_commands = """
    touch file1.txt file2.txt file3.log
    touch .hidden
    mkdir subdir
    touch subdir/nested.txt
    """
    
    tests = [
        ("ls *.txt | sort", "glob txt files"),
        ("ls file?.txt | sort", "single char glob"),
        ("ls file[12].txt | sort", "character class glob"),
        ("ls file[!3].txt | sort", "negated character class"),
        ("echo *.txt", "glob expansion in echo"),
        ("echo '*'.txt", "quoted glob not expanded"),
        ("echo *.txt", "glob with path"),  # Fixed: was "test_dir/*.txt" but we're already in the test dir
        ("echo .hidd*", "glob hidden files"),
        ("echo */nested.txt", "glob with directory"),
        ("echo no_match_*", "glob with no matches"),
    ]
    
    print("\nRunning glob tests...")
    for command, test_name in tests:
        # Run with setup - each test gets its own temporary directory
        full_command = setup_commands + "\n" + command
        result = runner.run_command(full_command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences[:3]:  # Limit output
                print(f"    {diff}")
    
    return runner


def main():
    """Run all basic tests and generate report."""
    import sys
    
    # Run different test categories
    runner1 = run_basic_tests()
    runner2 = run_glob_tests()
    
    # Combine results
    all_results = runner1.results + runner2.results
    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed)
    
    print(f"\n{'='*60}")
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print(f"Pass rate: {passed/total*100:.1f}%")
    
    # Generate detailed report
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        report = runner1.generate_report("text")
        with open("basic_tests_report.txt", "w") as f:
            f.write(report)
        print("\nDetailed report written to basic_tests_report.txt")
    
    # Exit with error if any tests failed
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()