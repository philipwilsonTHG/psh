# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Shell (psh) is an educational Unix shell implementation designed for teaching shell internals and compiler/interpreter concepts. It uses a hand-written recursive descent parser for clarity and educational value.

## Current Development Focus

**Latest**: Visitor Pattern Implementation - v0.45.0 (pending)
- ✓ Implemented AST Visitor Pattern (Phase 6 of parser improvements)
- ✓ Created base visitor classes: ASTVisitor[T] and ASTTransformer
- ✓ Implemented FormatterVisitor for pretty-printing AST as shell script
- ✓ Implemented ValidatorVisitor for semantic analysis and error checking
- ✓ Created ExecutorVisitor demonstration showing execution refactoring potential
- ✓ Added comprehensive test suite for visitor pattern functionality
- ✓ Created visitor pattern documentation and examples
- ✓ Visitor pattern provides clean separation between AST and operations
- ✓ Enables easy addition of new AST operations without modifying nodes
- ✓ Foundation for future enhancements: error recovery, optimization passes
- ✓ **Phase 1 Integration**: Reimplemented --debug-ast using DebugASTVisitor
  - Replaced static ASTFormatter with visitor-based implementation
  - Maintains backward compatibility with existing debug output format
  - Demonstrates successful integration without disrupting functionality

**Previous**: Advanced Debugging Features - v0.44.0
- ✓ Implemented comprehensive debugging capabilities for expansion and execution
- ✓ Added --debug-expansion flag to show expansions as they occur
- ✓ Added --debug-expansion-detail for detailed step-by-step expansion tracking
- ✓ Added --debug-exec to trace command execution paths and builtin/external routing
- ✓ Added --debug-exec-fork for detailed process creation and pipeline execution
- ✓ All debug options can be toggled at runtime via set builtin (e.g., set -o debug-expansion)
- ✓ Debug output goes to stderr to avoid interfering with normal stdout
- ✓ Created comprehensive architecture documentation for expansion/executor systems
- ✓ Updated all user guide chapters with debug option documentation
- ✓ Added example scripts demonstrating debug features
- ✓ All 1056 tests passing (100% success rate)

**Previous**: Associative Arrays - v0.43.0
- ✓ Implemented full associative array support with declare -A
- ✓ String-based keys with full bash-compatible syntax: array[key]="value"
- ✓ All array expansions: ${array[@]}, ${!array[@]}, ${#array[@]}
- ✓ Key-value assignment and initialization: declare -A arr=([key]="value")
- ✓ Complex key expressions with variable expansion: array[${prefix}_${suffix}]
- ✓ Keys with spaces and special characters: array["key with spaces"]
- ✓ Late binding parser approach for runtime type detection
- ✓ Integration with all parameter expansion features
- ✓ Enhanced variable expansion to handle escaped ! character
- ✓ Fixed arithmetic expression evaluation in array indices
- ✓ Updated user guide documentation with comprehensive examples
- ✓ All 1007 tests passing (100% success rate)

**Previous**: Complete Test Suite Success - v0.42.0
- ✓ All 962 tests passing (100% success rate)
- ✓ Fixed history expansion infinite loop with '!' followed by space
- ✓ Implemented += append operator for variables and arrays
- ✓ Fixed declare array initialization syntax parsing
- ✓ Fixed regex pattern tokenization in enhanced test operators
- ✓ Improved composite argument handling with quote preservation
- ✓ Fixed parameter expansion case modification with patterns
- ✓ Fixed case statement character class parsing
- ✓ Completed all remaining array implementation gaps from v0.41.0

**Earlier**: Array Variable Support - v0.41.0
- ✓ Implemented indexed arrays with full bash-compatible syntax
- ✓ Array element access: `${arr[0]}`, `${arr[index]}` with arithmetic evaluation
- ✓ Array expansions: `${arr[@]}`, `${arr[*]}`, `${#arr[@]}`, `${!arr[@]}`
- ✓ Array assignment and initialization: `arr[0]=value`, `arr=(one two three)`
- ✓ Negative indices and array slicing: `${arr[-1]}`, `${arr[@]:1:2}`
- ✓ Sparse array support with proper index tracking
- ✓ Array element parameter expansion: `${arr[0]/old/new}`, `${#arr[0]}`
- ✓ Unset array elements: `unset arr[index]`
- ✓ Integration with declare -a and declare -p

**Earlier**: Typeset Builtin - v0.39.1
- ✓ Added typeset builtin as ksh-compatible alias for declare
- ✓ Enhanced declare/typeset with -F flag to show function names only
- ✓ Created ShellFormatter utility for proper function definition display
- ✓ Full compatibility with ksh scripts using typeset
- ✓ All 900+ tests passing with comprehensive coverage

**Completed**: Line Continuation Support - v0.39.0
- ✓ Implemented POSIX-compliant line continuation (\<newline> sequences)
- ✓ Works in all input modes: scripts, interactive, -c commands
- ✓ Quote-aware processing preserves continuations inside quotes
- ✓ Fixed composite argument quote handling

**Completed**: Bug Fixes - v0.38.1
- ✓ Fixed brace expansion when sequences are followed by shell metacharacters
- ✓ Fixed read builtin file redirection by properly redirecting file descriptor 0

**Next Priority**: Advanced Features
- Trap command for signal handling
- Extended glob patterns
- Additional built-in commands
- Performance optimizations

## Architecture

The shell follows a component-based architecture with clear separation of concerns:

### Core Pipeline
1. **Input Preprocessing** (`input_preprocessing.py`): Handles line continuations
2. **Tokenization** (`state_machine_lexer.py`): State machine-based lexer for tokens
3. **Parsing** (`parser.py`): Builds an AST using recursive descent
4. **Execution** (component-based): Interprets the AST through specialized managers

### Component Organization

#### Main Orchestrator
- **`shell.py`** (~417 lines): Central orchestrator that coordinates all components
  - Initializes and manages component lifecycle
  - Provides unified API for command execution
  - Delegates actual work to specialized managers

#### Core Components
- **`core/`**: Shared state and exceptions
  - `state.py`: Centralized shell state (variables, environment, settings, options)
  - `exceptions.py`: Shell-specific exceptions (LoopBreak, LoopContinue, UnboundVariableError)
  - `options.py`: Shell option handlers (errexit, nounset, xtrace, pipefail)

#### Execution System (`executor/`)
- **`base.py`**: Base classes and ExecutorManager
- **`command.py`**: Single command execution (builtins, functions, external)
- **`pipeline.py`**: Pipeline execution with job control
- **`control_flow.py`**: Control structures (if, while, for, case)
- **`statement.py`**: Statement lists and logical operators (&&, ||)

#### Expansion System (`expansion/`)
- **`manager.py`**: Orchestrates all expansions in correct order
- **`variable.py`**: Variable and parameter expansion
- **`command_sub.py`**: Command substitution ($(...) and `...`)
- **`tilde.py`**: Tilde expansion (~ and ~user)
- **`glob.py`**: Pathname expansion (wildcards)

#### I/O Redirection (`io_redirect/`)
- **`manager.py`**: Manages all I/O redirections
- **`file_redirect.py`**: File redirections (<, >, >>, 2>, etc.)
- **`heredoc.py`**: Here documents and here strings
- **`process_sub.py`**: Process substitution (<(...), >(...))

#### Interactive Features (`interactive/`)
- **`base.py`**: Interactive manager and base classes
- **`repl_loop.py`**: Read-Eval-Print Loop implementation
- **`prompt_manager.py`**: PS1/PS2 prompt expansion
- **`history_manager.py`**: Command history management
- **`completion_manager.py`**: Tab completion
- **`signal_manager.py`**: Signal handling (SIGINT, SIGCHLD, etc.)

#### Script Handling (`scripting/`)
- **`base.py`**: Script manager and base classes
- **`script_executor.py`**: Script file execution
- **`script_validator.py`**: Script validation and security checks
- **`shebang_handler.py`**: Shebang (#!) processing
- **`source_processor.py`**: Source command implementation

#### Visitor Pattern (`visitor/`)
- **`base.py`**: Base visitor classes (ASTVisitor, ASTTransformer)
- **`formatter_visitor.py`**: Pretty-prints AST as shell script
- **`validator_visitor.py`**: Semantic validation and error checking
- **`executor_visitor.py`**: Demonstration of execution using visitors

#### Other Components
- **`builtins/`**: Built-in commands organized by category
  - `registry.py`: Central builtin registry
  - `core.py`: Core builtins (exit, :, true, false)
  - `navigation.py`: Directory navigation (cd, pwd)
  - `environment.py`: Environment management (export, unset, env, set)
  - `io.py`: I/O builtins (echo, read, printf)
  - `job_control.py`: Job control (jobs, fg, bg)
  - `aliases.py`: Alias management
  - `test_command.py`: Test/[ command implementation
  - `eval_command.py`: Eval builtin for dynamic command execution
  - `function_support.py`: Function management (declare, typeset, return)
- **`utils/`**: Utility modules
  - `ast_formatter.py`: AST pretty-printing
  - `token_formatter.py`: Token formatting
  - `file_tests.py`: File test utilities
  - `shell_formatter.py`: Shell syntax reconstruction from AST

Key design principles:
- Each component has a single, well-defined responsibility
- Components communicate through well-defined interfaces
- State is centralized in ShellState for consistency
- Educational clarity is maintained throughout

## Grammar

```
# Top-level structure
top_level    → statement*
statement    → function_def | if_stmt | while_stmt | for_stmt | case_stmt 
             | break_stmt | continue_stmt | command_list

# Function definitions
function_def → WORD '(' ')' compound_command
             | 'function' WORD ['(' ')'] compound_command
compound_command → '{' command_list '}'

# Control structures
if_stmt      → 'if' command_list 'then' command_list ['else' command_list] 'fi'
while_stmt   → 'while' command_list 'do' command_list 'done'
for_stmt     → 'for' WORD 'in' word_list 'do' command_list 'done'
             | 'for' '((' arith_expr? ';' arith_expr? ';' arith_expr? '))' ['do'] command_list 'done'
case_stmt    → 'case' expr 'in' case_item* 'esac'
expr         → WORD | STRING | VARIABLE | COMMAND_SUB | COMMAND_SUB_BACKTICK
case_item    → pattern_list ')' command_list [';;' | ';&' | ';;&']
pattern_list → pattern ('|' pattern)*
pattern      → WORD | STRING | VARIABLE

# Loop control
break_stmt   → 'break' [NUMBER]
continue_stmt → 'continue' [NUMBER]

# Command lists and pipelines
command_list → and_or_list (';' and_or_list)* [';']
and_or_list  → pipeline (('&&' | '||') pipeline)*
             | break_stmt | continue_stmt
pipeline     → command ('|' command)*

# Commands and arguments  
command      → simple_command | compound_command
simple_command → word+ redirect* ['&']
compound_command → if_stmt | while_stmt | for_stmt | case_stmt | select_stmt | arith_cmd
word         → WORD | STRING | VARIABLE | COMMAND_SUB | COMMAND_SUB_BACKTICK | ARITH_EXPANSION | PROCESS_SUB_IN | PROCESS_SUB_OUT
word_list    → word+

# Redirections
redirect     → [fd] redirect_op target
             | [fd] '>&' fd
redirect_op  → '<' | '>' | '>>' | '2>' | '2>>' | '<<' | '<<-' | '<<<'
fd           → NUMBER
target       → word

# Token types for expansions
COMMAND_SUB         → '$(' command_list ')'
COMMAND_SUB_BACKTICK → '`' command_list '`'
ARITH_EXPANSION     → '$((' arithmetic_expr '))'
PROCESS_SUB_IN      → '<(' command_list ')'
PROCESS_SUB_OUT     → '>(' command_list ')'
VARIABLE            → '$' (NAME | '{' NAME '}' | SPECIAL_VAR)
SPECIAL_VAR         → '?' | '$' | '!' | '#' | '@' | '*' | [0-9]+
STRING              → '"' (CHAR | VARIABLE | COMMAND_SUB | ARITH_EXPANSION)* '"'
                    | "'" CHAR* "'"
WORD                → (CHAR | ESCAPE_SEQUENCE)+
```

## Running the Project

```bash
# Run parser demonstration (shows tokenization and AST)
python3 demo.py

# Start interactive shell
python3 -m psh

# Execute single command
python3 -m psh -c "ls -la"

# Debug modes
python3 -m psh --debug-ast      # Show parsed AST before execution
python3 -m psh --debug-tokens    # Show tokenized output before parsing
python3 -m psh --debug-ast --debug-tokens -c "echo test"  # Both debug modes

# Debug options can also be toggled at runtime:
set -o debug-ast        # Enable AST debug output
set -o debug-tokens     # Enable token debug output
set +o debug-ast        # Disable AST debug output
set +o debug-tokens     # Disable token debug output
set -o                  # Show current option settings

# Shell options for scripts:
set -e                  # Exit on error (errexit)
set -u                  # Error on undefined variables (nounset)
set -x                  # Print commands before execution (xtrace)
set -o pipefail         # Pipeline fails if any command fails
set -eux -o pipefail    # Common combination for robust scripts

# RC file options
python3 -m psh --norc           # Skip ~/.pshrc loading
python3 -m psh --rcfile custom_rc  # Use custom RC file instead of ~/.pshrc

# Install psh locally (in development mode)
pip install -e .

# After installation, run directly
psh
psh -c "echo hello"
psh --help   # Show usage and options

# Run tests
python -m pytest tests/

# Run select statement tests (require special handling)
python -m pytest -s tests/test_select_statement.py::TestSelectStatement  # Interactive tests
python -m pytest tests/test_select_statement.py::TestSelectStatementNonInteractive  # Non-interactive tests
python scripts/test_select.py quick  # Convenience script for non-interactive tests

# Note: Select tests need pytest -s flag due to stdin requirements
# See tests/SELECT_TESTING.md for detailed explanation
```

## Prompt Customization

PSH supports customizable prompts through PS1 (primary) and PS2 (continuation) variables:

```bash
# Default prompts
PS1='\u@\h:\w\$ '  # username@hostname:path$ 
PS2='> '            # Continuation prompt

# Colored prompt examples
export PS1='\[\e[32m\]\u@\h\[\e[0m\]:\[\e[34m\]\w\[\e[0m\]\$ '  # Green user@host, blue path
export PS1='\[\e[1;35m\][\t]\[\e[0m\] \u@\h:\w\$ '  # Bold magenta time

# Two-line prompt
export PS1='\[\e[33m\]┌─[\u@\h:\w]\[\e[0m\]\n\[\e[33m\]└─\$\[\e[0m\] '

# Root-aware prompt (red for root, green for user)
export PS1='\[\e[$(($(id -u)==0?31:32))m\]\u@\h\[\e[0m\]:\w\$ '

# Continuation prompt with color
export PS2='\[\e[33m\]... \[\e[0m\]'
```

Multi-line commands are automatically detected and PS2 is shown for continuations:

```bash
$ if [ -f /etc/passwd ]; then
... echo "Password file exists"
... fi
Password file exists

$ for i in {1..3}; do
... echo "Number: $i"
... done
Number: 1
Number: 2
Number: 3
```

## Development Notes

- Test dependencies: pytest (install with `pip install -r requirements-dev.txt`)
- Comprehensive test suite covering tokenizer, parser, built-ins, and integration
- When adding features, maintain the educational clarity of the code
- Pipeline execution fully implemented using os.fork() and os.pipe()

## Current Implementation Status

Implemented:
- Basic command execution with external commands and built-ins
- I/O redirections (<, >, >>, 2>, 2>>, 2>&1, <<<)
- Multiple commands (;) and background execution (&)
- Quoted strings (single and double) with proper variable expansion
- Built-ins: exit, cd, export, pwd, echo (with -n, -e, -E flags), read (with -r, -p, -s, -t, -n, -d options), unset, env, source, ., history, set, declare (with -f, -F), typeset, return, jobs, fg, bg, alias, unalias, test, [, true, false, :, eval
- Wildcards/globbing (*, ?, [...])
- Exit status tracking ($? variable)
- Command history with persistence (~/.psh_history)
- Pipeline execution with proper process groups
- Signal handling (SIGINT, SIGTSTP, SIGCHLD)
- Shell variables (separate from environment)
- Positional parameters ($1, $2, etc.)
- Special variables ($$, $!, $#, $@, $*, $0)
- Variable assignment (VAR=value)
- Basic parameter expansion (${var}, ${var:-default})
- Advanced parameter expansion (all bash features: length, pattern removal/substitution, substring extraction, variable name matching, case modification)
- Here documents (<< and <<-) and here strings (<<<)
- Stderr redirection (2>, 2>>, 2>&1)
- Command substitution ($(...) and `...`) with proper nesting, including within double quotes
- Arithmetic expansion ($((...))) with full operator support
- Tab completion for files and directories
- Comments (# at word boundaries)
- Conditional execution (&& and || operators with short-circuit evaluation)
- Tilde expansion (~ and ~user)
- Vi and Emacs key bindings (set -o vi/emacs)
- Aliases (alias, unalias) with recursive expansion and trailing space support
- Shell functions with both POSIX (name() {}) and bash (function name {}) syntax
- Function management (declare -f/-F, typeset -f/-F, unset -f, return builtin)
- Function parameters and special variables within functions
- Job control (jobs, fg, bg commands, Ctrl-Z suspension, background job notifications)
- Job specifications (%1, %+, %-, %string)
- Process group management and terminal control
- Control structures: if/then/else/fi conditional statements
- Test command ([) with comprehensive string, numeric, and file operators (20+ file test operators)
- Loop constructs: while/do/done and for/in/do/done loops
- Loop control: break and continue statements with multi-level support (break 2, continue 3)
- Case statements (case/esac) with pattern matching and fallthrough control
- Pattern matching: wildcards (*), character classes ([abc], [a-z]), single character (?)
- Multiple patterns per case item (pattern1|pattern2|pattern3)
- Advanced case terminators: ;; (stop), ;& (fallthrough), ;;& (continue matching)
- Script file execution with arguments and shebang support
- Multi-line command support with POSIX-compliant line continuation (\<newline>)
- Nested control structures to arbitrary depth
- Command substitution in for loop iterables
- Brace expansion: Complete {a,b,c} list and {1..10} sequence expansion with proper escape handling
- Process substitution: <(...) for readable and >(...) for writable file descriptors
- RC file support: ~/.pshrc automatic initialization with --norc and --rcfile options
- Interactive multi-line command support with PS2 continuation prompts
- Prompt expansion (PS1/PS2) with escape sequences:
  - \u (username), \h (hostname), \w (working directory), \W (directory basename)
  - \t (time 24h), \T (time 12h), \@ (time am/pm), \A (time 24h short)
  - \d (date), \s (shell name), \v/\V (version), \$ ($ or # for root)
  - \! (history number), \# (command number)
  - \n (newline), \r (carriage return), \a (bell), \e (escape)
  - \nnn (octal character), \\ (literal backslash)
  - \[ and \] for non-printing sequences (ANSI color codes)
  - Full ANSI color support for customizable colored prompts
- Enhanced multi-line command detection:
  - Automatic detection of incomplete control structures
  - Proper handling of operators at end of line (|, &&, ||)
  - Detection of unclosed expansions and quotes
  - Support for escaped heredoc delimiters
- Enhanced test operators [[ ]] (v0.27.0):
  - Lexicographic string comparison (< and >)
  - Regular expression matching (=~)
  - No word splitting (safer variable handling)
  - Compound expressions with && and ||
  - All existing test operators from [ command

- Local variables in functions (local builtin) - ✅ **Implemented in v0.29.0**
  - Function-scoped variables with proper isolation
  - Variable scope stack with inheritance (locals visible to nested functions)
  - Debug support with --debug-scopes flag
  - Full test suite with comprehensive coverage

- Advanced parameter expansion - ✅ **Implemented in v0.29.2**
  - Complete bash-compatible string manipulation features
  - Length operations: ${#var}, ${#}, ${#*}, ${#@}
  - Pattern removal: ${var#pattern}, ${var##pattern}, ${var%pattern}, ${var%%pattern}
  - Pattern substitution: ${var/pattern/replacement}, ${var//pattern/replacement}, etc.
  - Substring extraction: ${var:offset}, ${var:offset:length} with negative offsets
  - Variable name matching: ${!prefix*}, ${!prefix@}
  - Case modification: ${var^}, ${var^^}, ${var,}, ${var,,} with pattern support
  - Unicode support and comprehensive error handling
  - 41 comprehensive tests with 98% success rate

- Echo builtin flags - ✅ **Implemented in v0.29.4**
  - Added -n flag to suppress trailing newline
  - Added -e flag to enable escape sequence interpretation
  - Added -E flag to disable escape interpretation (default)
  - Full escape sequence support: \n, \t, \r, \b, \f, \a, \v, \\, \e, \c
  - Unicode escapes: \xhh, \uhhhh, \Uhhhhhhhh
  - Octal escapes: \0nnn (bash-compatible format)
  - Combined flags support (-ne, -en, etc.)
  - Proper handling in pipelines and subprocesses

- Advanced read builtin features - ✅ **Implemented in v0.30.0**
  - Added -p prompt option to display custom prompts on stderr
  - Added -s silent mode for password input (no character echo)
  - Added -t timeout option with configurable timeout and exit code 142
  - Added -n chars option to read exactly N characters
  - Added -d delimiter option to use custom delimiter instead of newline
  - Proper terminal handling with termios for raw mode operations
  - Context manager ensures terminal state is always restored
  - Support for non-TTY inputs (StringIO) for better testability
  - All options can be combined (e.g., -sn 4 -p "PIN: " for 4-char password)
  - 29 comprehensive tests with full bash compatibility

- C-style for loops - ✅ **Implemented in v0.31.0**
  - Full arithmetic-based iteration: `for ((i=0; i<10; i++))`
  - Support for empty sections (init, condition, or update)
  - Multiple comma-separated expressions in each section
  - Integration with break/continue statements
  - I/O redirection support on loops
  - Optional 'do' keyword
  - 16+ comprehensive tests with 76% pass rate

- Arithmetic command syntax - ✅ **Implemented in v0.32.0**
  - Standalone arithmetic evaluation: `((expression))`
  - Exit status: 0 for non-zero results, 1 for zero (bash-compatible)
  - Full operator support matching arithmetic expansion
  - Enables conditional tests: `if ((x > 5)); then echo "big"; fi`
  - Standalone increment/decrement: `((i++))`, `((count--))`
  - Arithmetic assignments: `((x = y * 2))`
  - All 5 previously failing C-style for loop tests now pass
  - 10 comprehensive tests added for arithmetic commands
  - Known limitation: Cannot be used directly in pipelines with && or ||

- History expansion - ✅ **Implemented in v0.33.0**
  - Complete bash-compatible history expansion (!!, !n, !-n, !string, !?string?)
  - Context-aware expansion respects quotes and parameter expansions
  - Fixed for loop variable persistence to match bash behavior

- Select statement - ✅ **Implemented in v0.34.0**
  - Interactive menu system: `select var in items; do ...; done`
  - Displays numbered menu to stderr with PS3 prompt
  - Sets selected item in variable and raw input in REPLY
  - Multi-column layout for large lists
  - Full integration with break/continue statements
  - I/O redirection support on select loops
  - 12 comprehensive tests (require pytest -s for stdin access)

- Shell options - ✅ **Implemented in v0.35.0**
  - Script debugging and error handling options
  - `-e` (errexit): Exit on command failure (with conditional context awareness)
  - `-u` (nounset): Error on undefined variables (respects parameter expansion defaults)
  - `-x` (xtrace): Print commands before execution with PS4 prefix
  - `-o pipefail`: Pipeline fails if any command fails (returns rightmost non-zero exit)
  - Combined options support: `set -eux -o pipefail`
  - Centralized options storage with backward compatibility for debug options
  - 12 passing tests, 2 xfail due to test environment issues

- Eval builtin - ✅ **Implemented in v0.36.0**
  - Execute arguments as shell commands: `eval "echo hello"`
  - Concatenates all arguments with spaces before execution
  - Full shell processing: tokenization, parsing, all expansions
  - Executes in current shell context (variables/functions persist)
  - Proper exit status handling
  - Support for all shell features: pipelines, redirections, control structures
  - 17 comprehensive tests covering all use cases

- Control structures in pipelines - ✅ **Implemented in v0.37.0**
  - Unified command model enabling control structures as pipeline components
  - All control structures work in pipelines: while, for, if, case, select, arithmetic commands
  - Examples now work:
    - `echo "data" | while read line; do echo $line; done`
    - `seq 1 5 | for i in $(cat); do echo $i; done`
    - `echo "test" | if grep -q test; then echo "found"; fi`
  - Comprehensive test suite with full coverage

- Line continuation support - ✅ **Implemented in v0.39.0**
  - POSIX-compliant \<newline> processing before tokenization
  - Quote-aware handling preserves continuations inside quotes
  - Works in all input modes: scripts, interactive, -c commands
  - Cross-platform support for \n and \r\n line endings
  - Fixed composite argument quote handling as a bonus

- Enhanced declare/typeset - ✅ **Implemented in v0.40.0**
  - Complete variable attribute system with persistent storage
  - Integer (-i), lowercase (-l), uppercase (-u) attributes with transformations
  - Readonly (-r) and export (-x) attributes with proper enforcement
  - Array infrastructure with IndexedArray and AssociativeArray classes
  - Enhanced declare -p showing all variable attributes
  - Attribute removal with + prefix syntax
  - 84% test success rate (27/32 tests passing)

- Array variables - ✅ **Implemented in v0.41.0**
  - Full indexed array support with bash-compatible syntax
  - Array element access with arithmetic index evaluation
  - All array expansions: [@], [*], length, indices
  - Sparse arrays with proper gap handling
  - Negative indices and array slicing
  - Integration with all parameter expansion features
  - 99% test pass rate (162/164 tests passing)

- Typeset builtin - ✅ **Implemented in v0.39.1**
  - Added typeset as ksh-compatible alias for declare
  - Enhanced declare/typeset with -F flag for function names only
  - Created ShellFormatter utility for AST-to-shell syntax conversion
  - Full test coverage with 12 comprehensive tests

Not implemented:
- Trap command for signal handling
- Extended globbing patterns
- Deep recursion in shell functions (architectural limitation - see docs/recursion_depth_analysis.md)