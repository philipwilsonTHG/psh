# Python Shell (psh) - TODO List

**Current Version**: 0.39.1 (2025-06-12)

## Overview

PSH has achieved significant feature completeness with **900+ total tests (all passing)**. This document tracks remaining features, known issues, and development priorities.

## Recent Major Changes

### v0.39.1 - Typeset Builtin
- **Added typeset builtin**: ksh-compatible alias for declare
- **Enhanced declare/typeset**: Added -F flag to show function names only
- **ShellFormatter utility**: Proper function definition display
- **Full compatibility**: Works with ksh scripts using typeset

### v0.39.0 - Line Continuation Support
- **POSIX-compliant line continuation**: Implemented \<newline> sequences
- **Works in all input modes**: Scripts, interactive, -c commands
- **Quote-aware processing**: Preserves continuations inside quotes
- **Fixed composite argument quote handling**: Bonus fix during implementation

### v0.38.1 - Bug Fixes
- **Fixed brace expansion**: `{1..10};` now correctly expands without including semicolon
- **Fixed read builtin**: `read var < file` now properly reads from files

### v0.38.0 - Unified Types
- **Completed unified control structure types**: Removed all deprecated Command/Statement dual types
- **Simplified AST architecture**: Single type system for all control structures
- **Cleaned codebase**: Removed ~1000 lines of deprecated code and migration infrastructure
- **No functionality regression**: All features continue to work as before

## Remaining Features

### High Priority

#### Array Variables and Enhanced Declare - **NEXT PRIORITY**
- **Description**: Indexed/associative arrays and declare enhancements
- **Status**: Implementation plan ready (see `docs/DECLARE_ENHANCEMENT_PLAN.md`)
- **Features**:
  - Indexed arrays: `declare -a arr=(a b c)`, `${arr[0]}`
  - Associative arrays: `declare -A map`, `map[key]=value`
  - Array operations: `${#arr[@]}`, `${arr[@]}`, `${!arr[@]}`
  - Variable attributes: `-r` (readonly), `-x` (export), `-i` (integer), `-l`/`-u` (case)
  - Print functionality: `declare -p` to display variables with attributes

#### Trap Command
- **Description**: Signal handling for cleanup and error management
- **Status**: Not implemented
- **Use cases**: Cleanup on exit, error handling, signal interception


### Medium Priority


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

### Recently Resolved Issues

PSH has resolved all major parser and tokenizer limitations as of v0.38.3:

#### ✅ **Composite Argument Quote Handling in Redirection** (Fixed in v0.38.2)
- Commands like `echo test > file'name'.txt` now correctly create `filename.txt`
- Test: `pytest tests/comparison/test_todo_documented_limitations.py -k redirection`

#### ✅ **Backslash Escaping** (Fixed in v0.38.3)  
- Commands like `echo \$variable` now correctly output `$variable` instead of expanding
- Test: `pytest tests/comparison/test_todo_documented_limitations.py -k backslash`

#### ✅ **Quote Handling in Words** (Working)
- Quote concatenation like `a'b'c` works correctly despite internal tokenizer behavior
- All bash comparison tests pass (56/56)

### Other Issues

## Test Suite Status

### Overall: 900+ tests passing
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

#### v0.39.1 - Typeset Builtin Implementation
- Added typeset builtin as ksh-compatible alias for declare
- Enhanced DeclareBuiltin class to support -F flag (function names only)
- Created ShellFormatter utility class for reconstructing shell syntax from AST
- Proper function definition display matching bash/ksh output format
- Added TypesetBuiltin class inheriting from DeclareBuiltin
- Full test suite with 12 comprehensive tests covering all use cases
- Enables compatibility with ksh scripts that use typeset
- Total tests: 900+ (all passing) with full feature coverage

#### v0.39.0 - Line Continuation Support
- Implemented POSIX-compliant \<newline> line continuation processing
- Added InputPreprocessor component before tokenization
- Quote-aware continuation handling preserves escapes inside quotes
- Works in all input modes: scripts, interactive sessions, -c commands
- Cross-platform support for both \n and \r\n line endings
- Fixed composite argument quote handling as a bonus improvement
- Enables multi-line commands without explicit continuation prompts
- Comprehensive test suite validating all continuation scenarios
- Total tests: 900+ (all passing) maintaining full compatibility

#### v0.38.1 - Bug Fixes
- Fixed brace expansion when sequences are followed by shell metacharacters
  - Example: `{1..10};` now correctly expands without semicolon in elements
- Fixed read builtin file redirection by properly redirecting file descriptor 0
  - Example: `read var < file` now reads from files as expected
- Both fixes include comprehensive test coverage
- No regressions in existing functionality

#### v0.38.0 - Unified Control Structure Types
- Completed migration to unified AST type system
- Removed all deprecated Command/Statement dual types
- Single consistent type hierarchy for all control structures
- Removed ~1000 lines of migration infrastructure and deprecated code
- Simplified parser and executor implementations
- Maintained full backward compatibility
- All 850+ tests continue to pass without modification

#### v0.37.0 - Control Structures in Pipelines Implementation
- Implemented unified command model enabling control structures as pipeline components
- Addresses major architectural limitation that prevented control structures in pipelines
- All control structures now work in pipelines: while, for, if, case, select, arithmetic commands
- Examples now work:
  - `echo "data" | while read line; do echo $line; done`
  - `seq 1 5 | for i in $(cat); do echo $i; done` 
  - `echo "test" | if grep -q test; then echo "found"; fi`
- Created new AST hierarchy with Command base class, SimpleCommand and CompoundCommand subclasses
- Enhanced parser with parse_pipeline_component() method supporting both command types
- Updated PipelineExecutor to handle compound commands in subshells with proper isolation
- Fixed redirection handling and execution routing for compound commands in pipeline context
- Full backward compatibility maintained - all existing functionality works unchanged
- Comprehensive test suite with 7 tests covering all control structure types
- Total tests: 847 (840 passing, 40 skipped, 5 xfailed) - no regressions introduced
- Educational architecture preserved while enabling advanced shell programming

#### v0.36.0 - Eval Builtin Implementation
- Added eval builtin for executing arguments as shell commands
- Concatenates all arguments with spaces and executes as full shell commands
- Complete shell processing: tokenization, parsing, expansions, execution
- Executes in current shell context (variables and functions persist)
- Proper exit status handling from executed commands
- Support for all shell features: pipelines, redirections, control structures
- 17 comprehensive tests covering all use cases
- Implementation follows bash-compatible behavior and semantics

#### v0.35.0 - Shell Options Implementation
- Implemented core shell options: `set -e`, `set -u`, `set -x`, `set -o pipefail`
- Centralized options storage with backward-compatible debug option migration
- Xtrace (-x): Print commands with PS4 prefix before execution
- Nounset (-u): Error on undefined variable access (with parameter expansion exceptions)
- Errexit (-e): Exit on command failure (with proper conditional context handling)
- Pipefail: Pipeline returns rightmost non-zero exit code
- Enhanced set builtin to handle combined options (e.g., `set -eux`)
- Added comprehensive test suite: 12 passing tests, 2 xfail (subprocess isolation issues)
- Total tests: 771 passing (with comprehensive option coverage)

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
- **Core Shell**: ✓ Complete (execution, I/O, pipelines, variables, line continuation)
- **Expansions**: ✓ Complete (variable, parameter, command, arithmetic, brace, process)
- **Control Flow**: ✓ Complete (if/elif/else, while, for, case, break/continue, arithmetic commands)
- **Functions**: ✓ Complete (definition, local variables, return, declare -f/-F, typeset)
- **Job Control**: ✓ Complete (background, suspension, fg/bg)
- **Interactive**: ✓ Complete (line editing, completion, history, prompts, multi-line)
- **Builtins**: ✓ 26 implemented with modular architecture (including typeset)
- **Shell Options**: ✓ Complete (set -e/-u/-x/-o pipefail, debug options)

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