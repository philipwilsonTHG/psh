#!/usr/bin/env python3
"""Version information for Python Shell (psh)."""

# Semantic versioning: MAJOR.MINOR.PATCH
__version__ = "0.22.0"

# Version history
VERSION_HISTORY = """
0.22.0 (2025-01-30) - Brace expansion Phase 2: Sequence expansion
  - Implemented numeric sequence expansion: {1..10} → 1 2 3 4 5 6 7 8 9 10
  - Reverse sequences supported: {10..1} → 10 9 8 7 6 5 4 3 2 1
  - Character sequences: {a..z}, {A..Z} with ASCII ordering
  - Sequences with increment: {1..10..2} → 1 3 5 7 9
  - Zero-padded sequences: {01..10} → 01 02 03 04 05 06 07 08 09 10
  - Special padding behavior for ranges crossing zero: {-05..05}
  - Cross-case character sequences: {X..c} includes all ASCII between
  - Invalid sequences gracefully fall back to unexpanded form
  - Mixed list and sequence expansions: {{1..3},{a..c}} → 1 2 3 a b c
  - Memory limits apply to sequence expansions for safety
  - Complete bash-compatible brace expansion implementation
  - 10 new tests added, all 27 brace expansion tests passing

0.21.0 (2025-01-30) - Brace expansion implementation (Phase 1)
  - Added bash-style brace expansion as pre-tokenization step
  - Implemented list expansion: {a,b,c} → a b c
  - Support for preamble/postscript: file{1,2,3}.txt → file1.txt file2.txt file3.txt
  - Nested brace expansion: {a,b{1,2}} → a b1 b2
  - Empty element support: {a,,c} → a  c
  - Quote awareness: braces inside quotes are not expanded
  - Escape handling: \\{a,b\\} is not expanded
  - Memory limits to prevent excessive expansions (default 10,000 items)
  - Graceful error handling with fallback to original string
  - Comprehensive test suite with 22 tests covering all edge cases
  - Foundation laid for Phase 2 sequence expansion ({1..10}, {a..z})

0.20.1 (2025-01-30) - Read builtin implementation
  - Added read builtin with core POSIX functionality
  - Supports reading into variables with IFS-based field splitting
  - Raw mode (-r) preserves backslashes without escape processing
  - Handles escape sequences (\n, \t, \\, etc.) and line continuation
  - Proper handling of single vs multiple variable assignments
  - Default to REPLY variable when no variable names specified
  - Comprehensive test suite with 17 tests covering all features
  - Documentation and examples for future enhancements

0.20.0 (2025-01-30) - Modular builtin architecture
  - Complete refactoring of all 24 builtins into modular architecture
  - Created abstract base class Builtin for consistent interface
  - Implemented registry pattern with @builtin decorator for auto-registration
  - Organized builtins into logical modules: core, environment, file_ops, flow_control,
    history, job_control, shell_state, test_command, source_command, function_support
  - Removed 394 lines from shell.py, improving maintainability
  - Fixed job control fg/bg commands to properly handle Job objects
  - Updated all tests to use run_command() instead of direct builtin method calls
  - Preserved full backward compatibility and educational clarity
  - All 422 tests pass without modification

0.19.3 (2025-01-07) - Command substitution in for loops
  - Fixed parser to accept COMMAND_SUB and COMMAND_SUB_BACKTICK tokens in for loop iterables
  - Updated execute_for_statement() to properly expand command substitutions with word splitting
  - Command substitution results are split on whitespace and iterated over
  - Works with both $(...) and `...` syntax
  - Mixed iterables supported: for x in a $(cmd) b
  - Comprehensive test suite added with 8 test cases
  - Fixed examples/nested_control_demo.sh which previously had parsing errors

0.19.2 (2025-01-07) - Token debugging support
  - Added --debug-tokens command-line flag for debugging tokenization
  - Prints token list with type and value before parsing
  - Shows token index, type name, and value in formatted output
  - Works with --debug-ast flag to show both tokens and AST
  - Preserves debug flags in sub-shells for command substitution
  - Useful for understanding tokenizer behavior and troubleshooting lexical issues
  - Token types shown include: WORD, STRING, VARIABLE, PIPE, REDIRECT_*, keywords, etc.

0.19.1 (2025-01-07) - AST debugging support
  - Added --debug-ast command-line flag for debugging parsed commands
  - Prints hierarchical AST structure to stderr before execution
  - Works in both -c command mode and script execution mode
  - Preserves debug flag in sub-shells for command substitution
  - Comprehensive AST formatter shows all node types with proper indentation
  - Useful for understanding parser behavior and troubleshooting parsing issues

0.19.0 (2025-01-07) - Arbitrarily nested control structures
  - Implemented Statement base class unifying all executable constructs
  - Replaced CommandList with StatementList supporting any statement type
  - Added unified parse_statement() method eliminating dual parsing paths
  - Control structures (if, while, for, case) can now be nested to any depth
  - Functions can contain nested control structures without limitation
  - Full backward compatibility maintained through property delegation
  - Fixed $@ expansion in for loops to properly handle multiple arguments
  - Fixed pipeline execution to correctly run in foreground
  - Enhanced heredoc collection to work recursively through nested structures
  - 17 comprehensive tests for nested control structures
  - All 394 existing tests pass without modification
  - Educational architecture preserved while enabling complex shell scripts

0.18.0 (2025-05-29) - Arithmetic expansion and multi-line parsing
  - Implemented complete $((...)) arithmetic expansion with separate subsystem
  - ArithmeticTokenizer supporting numbers (decimal/hex/octal), operators, variables, parentheses
  - ArithmeticParser with recursive descent and proper operator precedence
  - ArithmeticEvaluator supporting all bash arithmetic features
  - Full operator support: +,-,*,/,%,** (arithmetic), <,>,<=,>=,==,!= (comparison), &&,||,! (logical), &,|,^,~,<<,>> (bitwise)
  - Advanced features: ternary (?:), comma, assignments (=,+=,-=,*=,/=,%=), increment/decrement (++,--)
  - Variable integration with shell variables, non-numeric strings evaluate to 0
  - Fixed arithmetic expansion in assignments: c=$((a + b))
  - Fixed stderr redirection tokenization: >&2 now tokenizes as single REDIRECT_DUP token
  - Fixed arithmetic expansion inside double quotes
  - Fixed variable expansion in assignments (a=$b now works correctly)
  - Implemented multi-line control structure parsing for scripts
  - While loops, if statements, functions, for loops, case statements can span multiple lines
  - Smart incomplete command detection continues reading until syntactic completion
  - Fixed all failing pytest tests related to parse error handling
  - 35 comprehensive arithmetic tests added
  - Complete Fibonacci calculator demonstrating arithmetic capabilities

0.17.1 (2025-05-28) - Refactoring preparation
  - Added comprehensive refactoring proposal document for shell.py restructuring
  - Documented plan to extract built-ins, process execution, environment management, I/O redirection, and script running
  - Prepared architectural improvements to reduce shell.py from 2230+ lines to focused orchestration
  - Outlined component-based design with BuiltinCommands, ProcessExecutor, Environment, RedirectionManager, and ScriptRunner
  - Enhanced maintainability and testability through separation of concerns
  - Preserved educational value while improving code organization

0.17.0 (2025-05-28) - Case statements (case/esac)
  - Implemented complete case/esac conditional statements with pattern matching
  - Added CaseStatement, CaseItem, and CasePattern AST nodes for structured representation
  - Extended tokenizer with CASE/ESAC tokens and case terminator operators (;;, ;&, ;;&)
  - Enhanced parser with comprehensive case parsing: expressions, patterns, commands, terminators
  - Added robust execution engine with fnmatch-based shell pattern matching
  - Support for all shell patterns: wildcards (*), character classes ([abc], [a-z]), single char (?)
  - Multiple patterns per case item with pipe (|) separator
  - Variable expansion in both case expressions and patterns
  - Advanced fallthrough control: ;; (stop), ;& (fallthrough), ;;& (continue matching)
  - Proper integration with break/continue statements for use within loops
  - Default pattern support (*) for catch-all cases
  - Created comprehensive test suite with 10 test methods covering all functionality
  - Full compatibility with bash-style case statement syntax and semantics
  - Complete control structure suite: if/then/else/fi, while/do/done, for/in/do/done, case/esac

0.16.0 (2025-05-28) - Break and continue statements
  - Implemented break and continue statements for loop control
  - Added LoopBreak and LoopContinue exception classes for control flow
  - Added BreakStatement and ContinueStatement AST nodes
  - Extended tokenizer with BREAK/CONTINUE tokens and keyword context detection
  - Enhanced parser to handle break/continue statements within loop bodies
  - Added execution methods with proper exception-based control flow
  - Modified while and for loop execution to catch and handle break/continue exceptions
  - Added comprehensive error handling for break/continue used outside loops
  - Break exits loops immediately; continue skips to next iteration
  - Works correctly in nested loops (affects only innermost loop)
  - Works correctly in functions called from within loops
  - Created comprehensive test suite with full break/continue functionality
  - Full integration into existing control structures and loop constructs
  - Complete loop control capabilities matching bash behavior

0.15.0 (2025-05-28) - For loops implementation
  - Implemented complete for/in/do/done loop constructs
  - Added ForStatement AST node with variable, iterable, and body fields
  - Extended tokenizer with FOR/IN tokens and keyword context detection
  - Enhanced parser with parse_for_statement() method supporting WORD, STRING, and VARIABLE tokens
  - Added robust loop execution with variable expansion and glob pattern support
  - Variable scoping: loop variables are properly isolated and restored after execution
  - Support for complex iterables: simple lists, quoted items, variable expansion, glob patterns
  - I/O redirection and pipeline support in loop bodies
  - Comprehensive test suite with 20 test methods and 85% success rate
  - Full integration into main parsing and execution flow
  - Complete iteration capabilities with both while and for loops

0.14.0 (2025-05-28) - While loops implementation
  - Implemented complete while/do/done loop constructs
  - Added WhileStatement AST node with condition and body CommandLists
  - Extended tokenizer with WHILE/DO/DONE tokens and keyword context detection
  - Enhanced parser with parse_while_statement() method following if statement patterns
  - Added robust loop execution with condition evaluation and exit status handling
  - Support for complex conditions: file tests, string/numeric comparisons, pipelines, && and ||
  - Variable modification support within loop bodies for practical programming
  - I/O redirection support in both conditions and loop bodies
  - Natural termination based on condition evaluation (exit code 0 = continue, non-zero = stop)
  - Created comprehensive test suite with 17 test methods and 94% success rate
  - Full integration into main parsing and execution flow
  - Complete programming language capabilities with conditionals and iteration

0.13.1 (2025-05-28) - Complete file test operators
  - Implemented all missing POSIX and bash file test operators
  - Added file size and type operators: -s, -L/-h, -b, -c, -p, -S
  - Added file permission operators: -k, -u, -g, -O, -G
  - Added file comparison operators: -nt, -ot, -ef
  - Added special operators: -t (terminal), -N (modified since read)
  - Enhanced test command with comprehensive file condition testing
  - Added stat module integration for detailed file information
  - Created extensive test suite covering all new operators
  - Proper error handling for non-existent files and invalid arguments
  - Full compatibility with bash file test semantics

0.13.0 (2025-05-28) - Control structures (if/then/else/fi)
  - Implemented full if/then/else/fi conditional statements
  - Added IfStatement AST node for control structure representation
  - Extended tokenizer with context-aware keyword recognition (if, then, else, fi)
  - Enhanced parser to handle conditional statements with proper precedence
  - Added execution logic for conditional branches based on exit status
  - Implemented comprehensive test command ([) with string, numeric, and file operators
  - Added true and false builtins for reliable condition testing
  - Created 18 comprehensive tests covering all control structure scenarios
  - Supports complex conditions with &&, ||, pipelines, and command substitution
  - Full compatibility with bash-style conditional syntax and semantics

0.12.0 (2025-05-28) - Shebang support and advanced script execution
  - Full shebang support for multi-interpreter execution (#!/bin/bash, #!/usr/bin/env python3)
  - Enhanced binary file detection with multi-factor analysis
  - Improved script argument passing and state management
  - Production-quality script execution with proper fallback handling
  - Support for common shebang patterns and env-based interpreters
  - Comprehensive file signature recognition and encoding handling
  - Updated documentation and TODO.md reflecting 26 completed features

0.11.0 (2025-05-28) - Enhanced script execution
  - Enhanced source builtin with PATH search and argument support
  - Improved command line processing with -h, -V, and -- options
  - Line continuation support with backslash
  - Enhanced error messages with file and line number information
  - Script vs interactive mode distinction with appropriate signal handling
  - Unified input processing system for better consistency
  - Comprehensive help and usage examples
  - Better file validation and error handling

0.10.0 (2025-05-28) - Script file execution
  - Added script file execution support with `psh script.sh`
  - Implemented InputSource abstraction for flexible input handling
  - Added proper $0 variable handling for script names
  - Support script arguments as $1, $2, etc. via set_positional_params()
  - File validation with appropriate exit codes (126, 127)
  - Comment and empty line handling in scripts
  - Binary file detection and rejection
  - Enhanced -c flag to accept additional arguments
  - Comprehensive architecture documentation for future development

0.9.0 (2025-05-28) - Job control
  - Full job control implementation with process group management
  - Job suspension with Ctrl-Z (SIGTSTP handling)
  - Built-in commands: jobs, fg, bg for job management
  - Job specifications: %1, %+, %-, %string for referencing jobs
  - Background job completion notifications
  - Terminal control management between shell and jobs
  - Terminal mode preservation when switching jobs
  - SIGCHLD handler for tracking job state changes
  - Comprehensive test suite for job control features

0.8.0 (2025-05-28) - Shell functions
  - Added shell function definitions (POSIX name() {} and bash function name {})
  - Functions stored as AST nodes for proper execution
  - Function execution in current shell process (no fork)
  - Proper parameter isolation with positional parameters
  - Return builtin with exception-based control flow
  - Function management (declare -f, unset -f)
  - Functions work in pipelines and subshells
  - Comprehensive test suite with 32 passing tests

0.7.0 (2025-05-27) - Shell aliases
  - Added alias and unalias builtin commands
  - Implemented recursive alias expansion with loop prevention
  - Support for trailing space in aliases (enables next word expansion)
  - Position-aware expansion (only at command positions)
  - Proper handling of quoted alias definitions
  - Added comprehensive test suite for alias functionality

0.6.0 (2025-05-27) - Vi and Emacs key bindings
  - Added comprehensive vi and emacs key binding support
  - Emacs mode (default): Ctrl-A/E, Ctrl-K/U/W, Ctrl-Y, Alt-F/B, and more
  - Vi mode: normal/insert modes, hjkl movement, word motions, editing commands
  - Implemented reverse history search with Ctrl-R (works in both modes)
  - Added kill ring for cut/paste operations
  - Support mode switching via 'set -o vi/emacs' command
  - Added full documentation and test coverage for key bindings

0.5.0 (2025-05-27) - Tilde expansion
  - Added tilde expansion for home directories (~ and ~user)
  - Tilde expansion works in arguments, redirections, and variable assignments
  - Only expands unquoted tildes at the beginning of words
  - Added comprehensive test suite for tilde expansion
  - Note: Escaped tilde handling requires future architectural changes

0.4.0 (2025-05-27) - Here strings and bug fixes
  - Added here string support (<<<) for passing strings as stdin
  - Fixed command substitution to properly capture external command output
  - Fixed history builtin to show last 10 commands by default (bash behavior)
  - Fixed set builtin to support positional parameters ($1, $2, etc.)
  - Fixed multiple test suite issues for better reliability
  - Improved error handling for empty heredocs

0.3.0 (2025-01-27) - Conditional execution
  - Added && and || operators for conditional command execution
  - Implemented short-circuit evaluation
  - Fixed pipeline execution issues by removing cat builtin
  - Improved test suite reliability

0.2.0 (2025-01-23) - Tab completion and comments
  - Added interactive tab completion for files/directories
  - Added comment support (# at word boundaries)
  - Fixed prompt positioning issues in raw terminal mode
  - Fixed history navigation display
  - Added version builtin command

0.1.0 (2025-01-23) - Initial versioned release
  - Basic command execution
  - I/O redirection (<, >, >>, 2>, 2>>, 2>&1)
  - Pipelines
  - Background processes (&)
  - Command history
  - Built-in commands: cd, exit, pwd, echo, env, export, unset, source, history, set, cat
  - Variable expansion and special variables
  - Command substitution ($() and ``)
  - Wildcards/globbing (*, ?, [...])
  - Here documents (<< and <<-)
"""

def get_version():
    """Return the current version string."""
    return __version__

def get_version_info():
    """Return detailed version information."""
    return f"Python Shell (psh) version {__version__}"