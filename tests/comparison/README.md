# Bash vs PSH Comparison Tests

This directory contains a comprehensive test suite that compares the behavior of bash and psh to ensure compatibility for implemented features.

## Overview

The comparison test framework runs the same commands and scripts in both bash and psh, then compares:
- Standard output (stdout)
- Standard error (stderr)  
- Exit codes

This helps ensure that psh behaves consistently with bash for all implemented features.

## Test Structure

```
comparison/
├── comparison_runner.py      # Core test framework
├── test_basic_commands.py    # Basic command execution and operators
├── test_expansions.py        # Variable, command, arithmetic, brace expansion
├── test_control_structures.py # if/while/for/case statements
├── run_all_tests.py          # Master test runner
└── README.md                 # This file
```

## Running Tests

### Run All Tests

```bash
# Run all comparison tests
python3 run_all_tests.py

# This generates three report files:
# - comparison_report.html  (detailed HTML report)
# - comparison_report.txt   (text summary)
# - comparison_report.json  (machine-readable results)
```

### Run Individual Test Suites

```bash
# Run basic command tests
python3 test_basic_commands.py

# Run expansion tests
python3 test_expansions.py

# Run control structure tests
python3 test_control_structures.py

# Generate detailed report for a suite
python3 test_basic_commands.py --report
```

### Run Single Commands

```bash
# Compare a single command
python3 comparison_runner.py "echo hello world"

# Run a script file in both shells
python3 comparison_runner.py -f script.sh

# Run all scripts in a directory
python3 comparison_runner.py -d ./test_scripts/

# Specify custom psh path
python3 comparison_runner.py --psh /path/to/psh "echo test"
```

## Test Categories

### Basic Commands (test_basic_commands.py)
- Simple command execution
- Multiple commands with semicolons
- Pipes and pipelines
- Conditional operators (&& and ||)
- Comments
- Globbing and wildcards
- Exit status handling

### Expansions (test_expansions.py)
- Variable expansion ($VAR, ${VAR})
- Special variables ($?, $$, $#, $@, $*)
- Parameter expansion (${VAR:-default})
- Command substitution ($(...) and `...`)
- Arithmetic expansion ($((...)))
- Brace expansion ({a,b,c}, {1..10})
- Tilde expansion (~, ~user)

### Control Structures (test_control_structures.py)
- if/then/else/fi statements
- while loops
- for loops
- case statements with pattern matching
- break and continue
- Nested control structures

## Understanding Test Results

### Pass Criteria
A test passes when bash and psh produce:
- Identical stdout output
- Equivalent stderr output (with normalization)
- The same exit code

### Common Differences
Some differences are expected and normalized:
- Shell name in error messages (bash: vs psh:)
- Line numbers in error messages
- Exact error message wording (as long as the error is detected)

### Report Format

The HTML report provides:
- Summary statistics
- Color-coded pass/fail status
- Detailed diff output for failures
- Command and test name for each test

## Adding New Tests

To add new comparison tests:

1. **Add to existing test file** (if appropriate):
```python
tests = [
    ("new command here", "description of test"),
    # ...
]
```

2. **Create a new test file** for new categories:
```python
#!/usr/bin/env python3
"""Description of test category."""

from comparison_runner import ComparisonTestRunner

def run_my_tests():
    runner = ComparisonTestRunner()
    
    tests = [
        ("command", "test name"),
    ]
    
    for command, test_name in tests:
        result = runner.run_command(command, test_name)
        # ...
    
    return runner
```

## Troubleshooting

### PSH Not Found
The runner tries to find psh in several locations:
- In PATH (if installed)
- Current directory
- As a Python module (`python -m psh`)

You can specify the path explicitly:
```bash
python3 comparison_runner.py --psh /path/to/psh "echo test"
```

### Timeout Issues
Some tests may timeout (default 5 seconds). This usually indicates:
- An infinite loop in psh
- A command waiting for input
- A significant performance difference

### Debugging Failures
For failed tests, the report shows:
- The exact command that was run
- Stdout/stderr from both shells
- A unified diff of any differences
- Exit codes from both shells

## Future Enhancements

Planned additions to the test suite:
- I/O redirection tests
- Process substitution tests
- Function definition and execution tests
- Alias tests
- Job control tests
- Signal handling tests
- Script execution tests
- Performance comparison metrics