#!/usr/bin/env python3
"""
Control structure comparison tests.

Tests if/then/else, while loops, for loops, case statements,
and break/continue functionality.
"""

from comparison_runner import ComparisonTestRunner


def run_if_tests():
    """Test if/then/else/fi statements."""
    runner = ComparisonTestRunner()
    
    tests = [
        # Basic if statements
        ("if true; then echo yes; fi", "simple if true"),
        ("if false; then echo yes; fi", "simple if false"),
        ("if true; then echo yes; else echo no; fi", "if-else true"),
        ("if false; then echo yes; else echo no; fi", "if-else false"),
        
        # elif chains
        ("if false; then echo one; elif true; then echo two; fi", "elif chain"),
        ("if false; then echo one; elif false; then echo two; else echo three; fi", "elif with else"),
        
        # Test command conditions
        ("if [ 1 -eq 1 ]; then echo equal; fi", "test numeric equality"),
        ("if [ 5 -gt 3 ]; then echo greater; fi", "test numeric comparison"),
        ('if [ "hello" = "hello" ]; then echo same; fi', "test string equality"),
        ('if [ -z "" ]; then echo empty; fi', "test empty string"),
        ('if [ -n "text" ]; then echo nonempty; fi', "test non-empty string"),
        
        # File tests
        ("touch testfile; if [ -f testfile ]; then echo exists; fi; rm testfile", "test file exists"),
        ("mkdir testdir; if [ -d testdir ]; then echo isdir; fi; rmdir testdir", "test directory exists"),
        
        # Command substitution in condition
        ('if [ "$(echo hello)" = "hello" ]; then echo match; fi', "command sub in test"),
        
        # Multi-line if
        ("""if true; then
    echo line1
    echo line2
fi""", "multi-line if body"),
        
        # Nested if
        ("""if true; then
    if true; then
        echo nested
    fi
fi""", "nested if statements"),
        
        # Complex conditions
        ("if true && true; then echo both; fi", "AND in condition"),
        ("if true || false; then echo either; fi", "OR in condition"),
        ("if ! false; then echo not_false; fi", "NOT in condition"),
    ]
    
    print("Running if/then/else tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_while_tests():
    """Test while loops."""
    runner = ComparisonTestRunner()
    
    tests = [
        # Basic while loops
        ("i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done", "simple while loop"),
        ("i=3; while [ $i -gt 0 ]; do echo $i; i=$((i-1)); done", "countdown while loop"),
        
        # While with break
        ("i=0; while true; do echo $i; i=$((i+1)); if [ $i -eq 3 ]; then break; fi; done", "while with break"),
        
        # While with continue
        ("i=0; while [ $i -lt 5 ]; do i=$((i+1)); if [ $i -eq 3 ]; then continue; fi; echo $i; done", "while with continue"),
        
        # Empty while body
        ("i=0; while [ $i -lt 0 ]; do :; done; echo done", "while with empty body"),
        
        # While reading input
        ('echo -e "one\\ntwo\\nthree" | while read line; do echo "Got: $line"; done', "while read pattern"),
        
        # Nested while
        ("""i=0; while [ $i -lt 2 ]; do
    j=0
    while [ $j -lt 2 ]; do
        echo "$i,$j"
        j=$((j+1))
    done
    i=$((i+1))
done""", "nested while loops"),
        
        # While with command substitution
        ("while [ $(echo 0) -eq 0 ]; do echo once; break; done", "while with command sub"),
    ]
    
    print("\nRunning while loop tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_for_tests():
    """Test for loops."""
    runner = ComparisonTestRunner()
    
    tests = [
        # Basic for loops
        ("for i in 1 2 3; do echo $i; done", "simple for loop"),
        ("for word in hello world; do echo $word; done", "for with words"),
        
        # For with glob expansion
        ("touch a.txt b.txt c.txt; for f in *.txt; do echo $f; done | sort; rm *.txt", "for with glob"),
        
        # For with brace expansion
        ("for i in {1..5}; do echo $i; done", "for with brace expansion"),
        ("for letter in {a..c}; do echo $letter; done", "for with letter sequence"),
        
        # For with command substitution
        ('for word in $(echo one two three); do echo $word; done', "for with command sub"),
        
        # For with break and continue
        ("for i in 1 2 3 4 5; do if [ $i -eq 3 ]; then break; fi; echo $i; done", "for with break"),
        ("for i in 1 2 3 4 5; do if [ $i -eq 3 ]; then continue; fi; echo $i; done", "for with continue"),
        
        # Empty for list
        ('for i in; do echo $i; done; echo "done"', "for with empty list"),
        
        # For with variable expansion
        ("list='a b c'; for item in $list; do echo $item; done", "for with variable"),
        
        # Nested for loops
        ("""for i in 1 2; do
    for j in a b; do
        echo "$i$j"
    done
done""", "nested for loops"),
        
        # For with quoted strings
        ('for word in "one two" three; do echo "[$word]"; done', "for with quoted strings"),
    ]
    
    print("\nRunning for loop tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_case_tests():
    """Test case statements."""
    runner = ComparisonTestRunner()
    
    tests = [
        # Basic case statements
        ("""x=hello; case $x in
    hello) echo greeting ;;
    bye) echo farewell ;;
esac""", "simple case match"),
        
        ("""x=bye; case $x in
    hello) echo greeting ;;
    bye) echo farewell ;;
esac""", "case second pattern"),
        
        ("""x=other; case $x in
    hello) echo greeting ;;
    bye) echo farewell ;;
    *) echo unknown ;;
esac""", "case default pattern"),
        
        # Multiple patterns
        ("""x=yes; case $x in
    yes|y|Y) echo affirmative ;;
    no|n|N) echo negative ;;
esac""", "case multiple patterns"),
        
        # Pattern matching
        ("""x=hello123; case $x in
    hello*) echo starts_with_hello ;;
    *123) echo ends_with_123 ;;
esac""", "case glob patterns"),
        
        # Character classes
        ("""x=5; case $x in
    [0-9]) echo digit ;;
    [a-z]) echo lowercase ;;
    *) echo other ;;
esac""", "case character class"),
        
        # Fallthrough with ;&
        ("""x=a; case $x in
    a) echo first ;&
    b) echo second ;;
    c) echo third ;;
esac""", "case fallthrough"),
        
        # Continue with ;;&
        ("""x=hello; case $x in
    h*) echo starts_h ;;&
    *o) echo ends_o ;;&
    hello) echo exact ;;
esac""", "case continue matching"),
        
        # Multi-line case bodies
        ("""x=test; case $x in
    test)
        echo line1
        echo line2
        ;;
esac""", "case multi-line body"),
        
        # Case with command substitution
        ("""case $(echo hello) in
    hello) echo matched ;;
esac""", "case with command sub"),
    ]
    
    print("\nRunning case statement tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_break_continue_tests():
    """Test break and continue in loops."""
    runner = ComparisonTestRunner()
    
    tests = [
        # Break in nested loops
        ("""for i in 1 2 3; do
    for j in a b c; do
        if [ "$i$j" = "2b" ]; then break; fi
        echo "$i$j"
    done
done""", "break in nested loop"),
        
        # Continue in nested loops
        ("""for i in 1 2; do
    for j in a b c; do
        if [ "$j" = "b" ]; then continue; fi
        echo "$i$j"
    done
done""", "continue in nested loop"),
        
        # Break with levels (if supported)
        ("""for i in 1 2; do
    for j in a b; do
        if [ "$i$j" = "1b" ]; then break 2; fi
        echo "$i$j"
    done
    echo "outer $i"
done""", "break with level"),
        
        # Break/continue outside loop (should error)
        ("break; echo after", "break outside loop"),
        ("continue; echo after", "continue outside loop"),
    ]
    
    print("\nRunning break/continue tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def main():
    """Run all control structure tests and generate report."""
    import sys
    
    # Run different test categories
    runners = [
        run_if_tests(),
        run_while_tests(),
        run_for_tests(),
        run_case_tests(),
        run_break_continue_tests(),
    ]
    
    # Combine results
    all_results = []
    for runner in runners:
        all_results.extend(runner.results)
    
    total = len(all_results)
    passed = sum(1 for r in all_results if r.passed)
    
    print(f"\n{'='*60}")
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print(f"Pass rate: {passed/total*100:.1f}%")
    
    # Generate detailed report
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        # Combine all results into first runner for reporting
        runners[0].results = all_results
        report = runners[0].generate_report("text")
        with open("control_structures_report.txt", "w") as f:
            f.write(report)
        print("\nDetailed report written to control_structures_report.txt")
    
    # Exit with error if any tests failed
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()