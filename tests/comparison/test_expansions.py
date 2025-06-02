#!/usr/bin/env python3
"""
Expansion comparison tests.

Tests variable expansion, command substitution, arithmetic expansion,
brace expansion, and parameter expansion features.
"""

from comparison_runner import ComparisonTestRunner


def run_variable_expansion_tests():
    """Test variable and parameter expansion."""
    runner = ComparisonTestRunner()
    
    # Set up some variables
    env = {
        'TEST_VAR': 'hello',
        'EMPTY_VAR': '',
        'PATH_VAR': '/usr/bin:/bin',
        'NUMBER': '42',
    }
    
    tests = [
        # Basic variable expansion
        ("echo $TEST_VAR", "basic variable"),
        ("echo ${TEST_VAR}", "braced variable"),
        ("echo $TEST_VAR$TEST_VAR", "concatenated variables"),
        ("echo ${TEST_VAR}world", "variable with suffix"),
        ("echo prefix${TEST_VAR}", "variable with prefix"),
        
        # Special variables
        ("echo $$ > /dev/null; echo pid", "PID variable"),
        ("echo $? after true", "exit status after true"),
        ("false; echo $?", "exit status after false"),
        ("echo $0", "shell name"),
        
        # Empty and unset variables
        ("echo $EMPTY_VAR", "empty variable"),
        ("echo '$EMPTY_VAR'", "empty variable single quoted"),
        ('echo "$EMPTY_VAR"', "empty variable double quoted"),
        ("echo $UNSET_VAR", "unset variable"),
        
        # Parameter expansion with defaults
        ("echo ${TEST_VAR:-default}", "expansion with default - var set"),
        ("echo ${UNSET_VAR:-default}", "expansion with default - var unset"),
        ("echo ${EMPTY_VAR:-default}", "expansion with default - var empty"),
        
        # Variables in different contexts
        ('echo "Hello $TEST_VAR"', "variable in double quotes"),
        ("echo 'Hello $TEST_VAR'", "variable in single quotes"),
        ("echo Hello\\ $TEST_VAR", "variable after escaped space"),
        
        # Positional parameters
        ("set -- one two three; echo $1", "first positional parameter"),
        ("set -- one two three; echo $2", "second positional parameter"),
        ("set -- one two three; echo $#", "number of parameters"),
        ('set -- one two "three four"; echo $@', "all parameters unquoted"),
        ('set -- one two "three four"; echo "$@"', "all parameters quoted"),
        ('set -- one two "three four"; echo $*', "all parameters as string"),
        ('set -- one two "three four"; echo "$*"', "all parameters as single string"),
    ]
    
    print("Running variable expansion tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name, env=env)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_command_substitution_tests():
    """Test command substitution."""
    runner = ComparisonTestRunner()
    
    tests = [
        # Modern syntax
        ("echo $(echo hello)", "simple command substitution"),
        ("echo $(echo hello world)", "command sub with multiple words"),
        ("echo prefix$(echo middle)suffix", "command sub with surrounding text"),
        ("echo $(echo one) $(echo two)", "multiple command substitutions"),
        
        # Nested command substitution
        ("echo $(echo $(echo nested))", "nested command substitution"),
        ("echo $(echo one $(echo two) three)", "nested with surrounding text"),
        
        # Legacy backtick syntax
        ("echo `echo hello`", "backtick substitution"),
        ("echo `echo hello world`", "backtick with multiple words"),
        
        # Command substitution with multiple lines
        ("echo $(echo -e 'line1\\nline2')", "multiline command sub"),
        ("lines=$(echo -e 'one\\ntwo\\nthree'); echo $lines", "multiline stored in var"),
        
        # Command substitution with pipes
        ("echo $(echo hello | tr a-z A-Z)", "command sub with pipe"),
        ("echo $(echo -e 'one\\ntwo' | grep two)", "command sub with grep"),
        
        # Empty command substitution
        ("echo $(true)", "empty command substitution"),
        ("echo prefix$(true)suffix", "empty command sub with text"),
        
        # Command substitution in different contexts
        ('echo "Result: $(echo hello)"', "command sub in double quotes"),
        ("echo 'Result: $(echo hello)'", "command sub in single quotes"),
        
        # Error handling in command substitution
        ("echo $(false; echo hello)", "command sub with failed command"),
        ("result=$(echo output; echo error >&2); echo $result", "command sub captures stdout only"),
    ]
    
    print("\nRunning command substitution tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_arithmetic_expansion_tests():
    """Test arithmetic expansion."""
    runner = ComparisonTestRunner()
    
    tests = [
        # Basic arithmetic
        ("echo $((2 + 2))", "simple addition"),
        ("echo $((10 - 3))", "subtraction"),
        ("echo $((4 * 5))", "multiplication"),
        ("echo $((20 / 4))", "division"),
        ("echo $((17 % 5))", "modulo"),
        ("echo $((2 ** 8))", "exponentiation"),
        
        # Precedence
        ("echo $((2 + 3 * 4))", "precedence multiply over add"),
        ("echo $(((2 + 3) * 4))", "parentheses for precedence"),
        
        # Comparison operators
        ("echo $((5 > 3))", "greater than"),
        ("echo $((3 < 5))", "less than"),
        ("echo $((5 >= 5))", "greater or equal"),
        ("echo $((5 <= 5))", "less or equal"),
        ("echo $((5 == 5))", "equality"),
        ("echo $((5 != 3))", "inequality"),
        
        # Logical operators
        ("echo $((1 && 1))", "logical AND true"),
        ("echo $((1 && 0))", "logical AND false"),
        ("echo $((0 || 1))", "logical OR true"),
        ("echo $((0 || 0))", "logical OR false"),
        ("echo $((!0))", "logical NOT true"),
        ("echo $((!1))", "logical NOT false"),
        
        # Bitwise operators
        ("echo $((5 & 3))", "bitwise AND"),
        ("echo $((5 | 3))", "bitwise OR"),
        ("echo $((5 ^ 3))", "bitwise XOR"),
        ("echo $((~5))", "bitwise NOT"),
        ("echo $((5 << 2))", "left shift"),
        ("echo $((20 >> 2))", "right shift"),
        
        # Variables in arithmetic
        ("x=10; echo $((x + 5))", "variable in arithmetic"),
        ("x=10; y=3; echo $((x * y))", "multiple variables"),
        ("x=5; echo $((x += 3)); echo $x", "assignment in arithmetic"),
        
        # Complex expressions
        ("echo $(( (10 + 5) * 2 - 8 / 4 ))", "complex expression"),
        ("x=5; y=3; echo $(( x > y ? x : y ))", "ternary operator"),
    ]
    
    print("\nRunning arithmetic expansion tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_brace_expansion_tests():
    """Test brace expansion."""
    runner = ComparisonTestRunner()
    
    tests = [
        # List expansion
        ("echo {a,b,c}", "simple list expansion"),
        ("echo {one,two,three}", "word list expansion"),
        ("echo pre{A,B,C}post", "list with prefix/suffix"),
        ("echo {a,b}{1,2}", "multiple brace expansions"),
        ("echo {{a,b},{c,d}}", "nested brace expansion"),
        
        # Sequence expansion
        ("echo {1..5}", "numeric sequence"),
        ("echo {5..1}", "reverse numeric sequence"),
        ("echo {01..10}", "zero-padded sequence"),
        ("echo {a..e}", "letter sequence"),
        ("echo {e..a}", "reverse letter sequence"),
        ("echo {A..E}", "uppercase sequence"),
        
        # Mixed with other expansions
        ("echo {1..3}.txt", "sequence with suffix"),
        ("echo file{1..3}.{txt,log}", "sequence and list combined"),
        ("x=5; echo {1..$x}", "variable in brace expansion"),
        
        # Empty and single element
        ("echo {}", "empty brace"),
        ("echo {single}", "single element"),
        
        # Escaping and quoting
        ("echo '{a,b,c}'", "quoted brace expansion"),
        ("echo \\{a,b,c\\}", "escaped braces"),
        
        # Complex patterns
        ("echo {a..c}{1..3}", "letter and number sequences"),
        ("mkdir -p test/{src,bin,doc}/{main,test}", "nested for mkdir"),
    ]
    
    print("\nRunning brace expansion tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def run_tilde_expansion_tests():
    """Test tilde expansion."""
    runner = ComparisonTestRunner()
    
    tests = [
        ("echo ~", "home directory"),
        ("echo ~/file", "home with path"),
        ("echo ~root", "other user home"),
        ("echo '~'", "quoted tilde not expanded"),
        ('echo "~"', "double quoted tilde not expanded"),
        ("echo \\~", "escaped tilde"),
        ("cd /tmp; echo ~-", "previous directory"),
        ("cd /tmp; cd /; echo ~-", "previous directory after cd"),
    ]
    
    print("\nRunning tilde expansion tests...")
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not result.passed:
            for diff in result.differences:
                print(f"    {diff}")
    
    return runner


def main():
    """Run all expansion tests and generate report."""
    import sys
    
    # Run different test categories
    runners = [
        run_variable_expansion_tests(),
        run_command_substitution_tests(),
        run_arithmetic_expansion_tests(),
        run_brace_expansion_tests(),
        run_tilde_expansion_tests(),
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
        with open("expansion_tests_report.txt", "w") as f:
            f.write(report)
        print("\nDetailed report written to expansion_tests_report.txt")
    
    # Exit with error if any tests failed
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()