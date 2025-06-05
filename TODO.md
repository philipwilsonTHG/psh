# Python Shell (psh) - TODO List

**Current Version**: 0.34.0 (2025-01-06)

## Overview

PSH has achieved significant feature completeness with **751 passing tests**. This document tracks remaining features, known issues, and development priorities.

## Remaining Features

### High Priority

#### Shell Options (`set` command) - **NEXT PRIORITY**
- **Description**: Script debugging and error handling options
- **Status**: Not implemented
- **Options**:
  - `-e` (errexit): Exit on command failure
  - `-u` (nounset): Error on undefined variables
  - `-x` (xtrace): Print commands before execution
  - `-o pipefail`: Pipeline fails if any command fails

#### Trap Command
- **Description**: Signal handling for cleanup and error management
- **Status**: Not implemented
- **Use cases**: Cleanup on exit, error handling, signal interception


### Medium Priority

#### Array Variables
- **Description**: Indexed and associative arrays
- **Status**: Not implemented
- **Features**:
  - Indexed arrays: `arr=(a b c)`, `${arr[0]}`
  - Associative arrays: `declare -A map`
  - Array operations: `${#arr[@]}`, `${arr[@]}`


### Low Priority

#### Interactive Enhancements
- Tab completion for commands (beyond files/directories)
- Programmable completion framework
- Syntax highlighting in prompt
- Custom prompt variables (PS4)

## Known Issues

### Critical Issues

#### Deep Recursion Limitation
- **Problem**: Recursive functions with command substitution hit Python's recursion limit
- **Example**: `factorial(5)` using `$(factorial $((n-1)))` fails
- **Impact**: Limits recursive algorithm implementation
- **Workaround**: Use iterative algorithms
- **Documentation**: See `docs/recursion_depth_analysis.md`

### Parser Limitations

#### Control Structures in Pipelines
- **Problem**: Control structures cannot be used in pipelines
- **Example**: `echo "data" | while read line; do echo $line; done` fails
- **Cause**: Parser expects Command objects in pipelines, not statements
- **Workaround**: Wrap entire pipeline in control structure

#### Composite Argument Quote Handling
- **Problem**: Parser loses quote information when creating composite arguments
- **Example**: `file'*'.txt` may incorrectly expand wildcards
- **Status**: Partially mitigated by disabling glob expansion for composites

### Tokenizer Issues

#### Quote Handling in Words
- **Problem**: Quotes within words included in token value
- **Example**: `a'b'c` tokenizes as `a'b'c` instead of `abc`
- **Impact**: Incorrect output for concatenated quoted strings

### Other Issues

## Test Suite Status

### Skipped Tests: 26 total (down from 28 - fixed 2 in v0.33.0)

#### Pytest Output Capture Issues (8 tests)
- **Pipeline tests**: Builtins in pipelines don't work with pytest's output capture
- **Workaround**: Tests pass with `pytest -s` or manual execution
- **Not PSH bugs**: These are pytest infrastructure limitations

#### Can Be Fixed (10 tests)
- **CI-only failures** (3): Work locally, fail on GitHub Actions
- **Minor fixes needed** (5): Known issues with straightforward solutions
- **Test rewrite needed** (2): Can use file-based verification instead

#### Need Architectural Changes (8 tests)
- **Parser changes** (3): Break/continue operator handling  
- **Not implemented** (5): Escaped globs, arrays, PS1 history numbers

### Test Recommendations
1. Mark pipeline tests with custom pytest marker for clarity
2. Convert capture-based tests to file output verification
3. Document pytest limitations in affected test files

## Implementation History

### Recent Releases

#### v0.33.0 - History Expansion and Bug Fixes
- Implemented complete bash-compatible history expansion (!!, !n, !-n, !string, !?string?)
- Fixed for loop variable persistence to match bash behavior
- Removed incorrect TODO entries for already-working features
- Updated test suite to 751 passing tests (fixed 2 previously skipped tests)

#### v0.32.0 - Arithmetic Command Syntax
- Implemented standalone arithmetic commands: `((expression))`
- Exit status: 0 for non-zero results, 1 for zero (bash-compatible)
- Full operator support matching arithmetic expansion
- Enables conditional tests: `if ((x > 5)); then echo "big"; fi`
- Standalone increment/decrement: `((i++))`, `((count--))`
- Arithmetic assignments: `((x = y * 2))`
- All 5 previously failing C-style for loop tests now pass
- 10 comprehensive tests added for arithmetic commands
- Known limitation: Cannot be used directly in pipelines with && or ||

#### v0.31.0 - C-style For Loops
- Implemented arithmetic-based iteration: `for ((i=0; i<10; i++))`
- Support for empty sections (any or all can be omitted)
- Multiple comma-separated expressions in init/update sections
- Integration with existing arithmetic expansion system
- Support for break/continue statements
- I/O redirection support on loops
- Optional 'do' keyword
- 21 comprehensive tests with 76% pass rate

#### v0.30.0 - Advanced Read Builtin Features
- Implemented -p prompt, -s silent, -t timeout, -n chars, -d delimiter options
- Proper terminal handling with termios for raw mode operations
- Support for non-TTY inputs for better testability
- All options can be combined (e.g., -sn 4 -p "PIN: ")
- 29 comprehensive tests with full bash compatibility

#### v0.29.4 - Echo Builtin Flags
- Added -n, -e, -E flags with full escape sequence support
- Unicode and octal escape sequences
- Proper handling in pipelines and subprocesses

#### v0.29.2 - Advanced Parameter Expansion
- Complete bash-compatible string manipulation
- 41 comprehensive tests with 98% success rate
- Fixed pytest infrastructure issues

#### v0.29.0 - Local Variables
- Function-scoped variables with `local` builtin
- Variable scope stack with inheritance
- Debug support with `--debug-scopes`

#### v0.28.x - Major Refactoring
- Component-based architecture (shell.py: 2,712 → 417 lines)
- State machine lexer replacing old tokenizer
- Parser improvements with 30% code reduction

### Feature Summary
- **Core Shell**: ✓ Complete (execution, I/O, pipelines, variables)
- **Expansions**: ✓ Complete (variable, parameter, command, arithmetic, brace, process)
- **Control Flow**: ✓ Complete (if/elif/else, while, for, case, break/continue)
- **Functions**: ✓ Complete (definition, local variables, return)
- **Job Control**: ✓ Complete (background, suspension, fg/bg)
- **Interactive**: ✓ Complete (line editing, completion, history, prompts)
- **Builtins**: ✓ 25 implemented with modular architecture

## Development Guidelines

### Architecture Principles
1. **Component separation**: Each subsystem in its own module
2. **Educational clarity**: Code remains readable and teachable
3. **Test coverage**: Comprehensive tests for all features
4. **Error handling**: Clear messages with context

### Adding Features
1. Check dependencies and existing infrastructure
2. Design clean interfaces between components
3. Write tests before implementation
4. Update documentation (README.md, ARCHITECTURE.md)
5. Follow existing patterns and conventions

### References
- POSIX Shell Specification
- Bash Reference Manual
- "The Linux Programming Interface" (process management)
- "Advanced Programming in the Unix Environment" (system calls)