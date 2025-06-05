# Python Shell (psh) - TODO List

**Current Version**: 0.29.2 (2025-04-06)

## Overview

PSH has achieved significant feature completeness with **680+ passing tests**. This document tracks remaining features, known issues, and development priorities.

## Remaining Features

### High Priority

#### C-style For Loops
- **Description**: Arithmetic-based iteration `for ((i=0; i<10; i++))`
- **Status**: Not implemented
- **Dependencies**: Leverages existing arithmetic expansion system (v0.28.9)
- **Impact**: Completes the iteration construct family

#### Enhanced Read Builtin
- **Description**: Additional options for interactive input
- **Status**: Basic functionality implemented (v0.20.1), advanced features in progress
- **Implementation Plan**: See `docs/advanced_read_builtin_plan.md`
- **Remaining**:
  - `-p prompt`: Display prompt string
  - `-s`: Silent mode (no echo)
  - `-t timeout`: Timeout after N seconds
  - `-n chars`: Read only N characters
  - `-d delimiter`: Use custom delimiter instead of newline

#### Shell Options (`set` command)
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

#### Select Statement
- **Description**: Menu generation for user selection
- **Status**: Not implemented
- **Syntax**: `select item in list; do ...; done`

### Low Priority

#### Interactive Enhancements
- Tab completion for commands (beyond files/directories)
- Programmable completion framework
- Syntax highlighting in prompt
- Custom prompt variables (PS3, PS4)

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

#### Variable Assignment with Spaces
- **Problem**: `VAR="value with spaces" command` incorrectly tokenized
- **Impact**: Assignment before command fails with quoted values
- **Workaround**: Set variable on separate line

#### Quote Handling in Words
- **Problem**: Quotes within words included in token value
- **Example**: `a'b'c` tokenizes as `a'b'c` instead of `abc`
- **Impact**: Incorrect output for concatenated quoted strings

### Other Issues

#### For Loop Variable Persistence
- **Problem**: Loop variables incorrectly restored after loop
- **Expected**: Variable should retain last iteration value
- **Workaround**: Save to different variable if persistence needed

#### Builtin I/O Redirection
- **Problem**: Builtins using `print()` don't respect redirections
- **Affected**: echo, pwd, env, set, declare, alias, history, jobs
- **Fix needed**: Use `os.write()` to file descriptors

## Test Suite Status

### Skipped Tests: 23 total

#### Can Be Fixed (15 tests)
- **CI-only failures** (3): Work locally, fail on GitHub Actions
- **Minor fixes needed** (5): Known issues with straightforward solutions
- **Test rewrite needed** (7): Pytest capture conflicts, need file-based verification

#### Need Architectural Changes (8 tests)
- **Parser changes** (3): Break/continue operator handling
- **Not implemented** (5): Escaped globs, complex escapes

### Test Recommendations
1. Remove CI-only skip decorators when running locally
2. Convert capture-based tests to file output verification
3. Fix for loop variable persistence
4. Fix tokenizer for quoted variable assignments

## Implementation History

### Recent Releases

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