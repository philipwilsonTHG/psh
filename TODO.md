# Python Shell (psh) - TODO List

Features ordered by implementation status and complexity.

## ✅ Completed Features

### Core Shell Features
1. **Basic Command Execution** - External commands, built-ins, exit status
2. **Additional Built-in Commands** - pwd, echo, env, unset, source, exit, cd, export, history, set, declare, return, jobs, fg, bg, alias, unalias, version, true, false, :, ., read
3. **I/O Redirection** - stdin (<), stdout (>, >>), stderr (2>, 2>>, 2>&1), here documents (<<, <<-), here strings (<<<)
4. **Pipeline Execution** - Process pipes, exit status handling, signal management
5. **Command History** - In-memory storage, history command, readline integration, persistence
6. **Exit Status Handling** - $? variable, prompt display, shell script access

### Advanced Shell Features  
7. **Wildcards/Globbing** - *, ?, [...] patterns with proper quote handling
8. **Enhanced Variable Support** - Positional params ($1, $2, etc.), special variables ($$, $!, $#, $@, $*, $0), shell variables, ${var:-default} expansion
9. **Command Substitution** - $(...) and `...` with nesting support
10. **Comments** - # at word boundaries, preserved in quotes and when escaped
11. **Conditional Execution** - && and || operators with short-circuit evaluation
12. **Tilde Expansion** - ~ for home directory, ~user for user's home directory

### Interactive Features
13. **Tab Completion** - File/directory completion with special character handling
14. **Vi/Emacs Key Bindings** - Full command line editing with set -o vi/emacs, history search (Ctrl-R)
15. **Aliases** - alias/unalias commands, recursive expansion prevention, trailing space support

### Programming Features
16. **Shell Functions** - Function definition (POSIX and bash syntax), invocation, parameters, return builtin, declare -f, unset -f
17. **Job Control** - Background processes (&), job tracking, jobs/fg/bg commands, Ctrl-Z suspension, process group management
18. **Control Structures** - if/then/else/fi conditional statements with full bash compatibility, multi-level break/continue support

### **🎯 Script Execution (v0.10.0 - v0.12.0)**
19. **Script File Execution** - Execute psh scripts with `psh script.sh`
20. **Script Arguments** - Proper $0, $1, $2, etc. handling
21. **Enhanced Input Processing** - Line continuation with backslash (\), unified input system
22. **Enhanced Source Builtin** - PATH search, argument passing (source script.sh arg1 arg2)
23. **Enhanced Command Line** - -h/--help, -V/--version, -- separator support
24. **Enhanced Error Handling** - File:line error messages, proper exit codes (126, 127)
25. **Script vs Interactive Mode** - Appropriate signal handling for each mode
26. **Shebang Support** - Full #!/interpreter support, env patterns, fallback to psh
27. **Enhanced Binary Detection** - Multi-factor analysis, file signature recognition

### **🎯 Control Structures (v0.13.0 - v0.15.0)**
28. **Conditional Statements** - if/then/else/fi with exit status-based evaluation
29. **Test Command** - Comprehensive test and [ commands with string, numeric, and file operators
30. **True/False Builtins** - Reliable true and false commands for condition testing
31. **Enhanced File Test Operators** - Complete POSIX and bash file test operators (v0.13.1)
32. **While Loops** - while/do/done iteration constructs with full condition support (v0.14.0)
33. **For Loops** - for/in/do/done iteration with variable expansion and glob patterns (v0.15.0)
34. **Break and Continue Statements** - Loop control statements for while and for loops (v0.16.0)
35. **Case Statements** - case/esac pattern matching with fallthrough control (v0.17.0)
36. **Arithmetic Expansion** - $((...)) with full bash-compatible arithmetic evaluation (v0.18.0)
37. **Read Builtin** - Core POSIX functionality with IFS field splitting, raw mode, escape processing (v0.20.1)
38. **Brace Expansion** - Complete bash-style {a,b,c} list and {1..10} sequence expansion, with shell metacharacter awareness (v0.21.0-v0.22.0, enhanced v0.26.3)
39. **Process Substitution** - <(...) and >(...) for treating command output as files (v0.24.0)
40. **RC File Support** - ~/.pshrc automatic initialization for interactive shells (v0.25.0)

## 🚧 Remaining Features

### High Priority Features

#### Enhanced Test Command and File Operators  
- [x] **Complete File Test Operators** - ✅ Comprehensive POSIX and bash file test operators implemented (v0.13.1)
  - [x] `-f` (regular file), `-d` (directory), `-e` (exists) - ✅ Implemented  
  - [x] `-r` (readable), `-w` (writable), `-x` (executable) - ✅ Implemented
  - [x] `-s` (non-empty file) - ✅ Check if file exists and has size > 0
  - [x] `-L` or `-h` (symbolic link) - ✅ Check if file is a symbolic link
  - [x] `-b` (block device) - ✅ Check if file is a block special device
  - [x] `-c` (character device) - ✅ Check if file is a character special device  
  - [x] `-p` (named pipe/FIFO) - ✅ Check if file is a named pipe
  - [x] `-S` (socket) - ✅ Check if file is a socket
  - [x] `-k` (sticky bit) - ✅ Check if file has sticky bit set
  - [x] `-u` (setuid) - ✅ Check if file has setuid bit set
  - [x] `-g` (setgid) - ✅ Check if file has setgid bit set
  - [x] `-O` (owned by effective UID) - ✅ Check if file is owned by effective user ID
  - [x] `-G` (owned by effective GID) - ✅ Check if file is owned by effective group ID
  - [x] `-N` (modified since last read) - ✅ Check if file was modified since last read
  - [x] `-t FD` (terminal) - ✅ Check if file descriptor FD is open and refers to terminal
  - [x] `FILE1 -nt FILE2` (newer than) - ✅ Check if FILE1 is newer than FILE2
  - [x] `FILE1 -ot FILE2` (older than) - ✅ Check if FILE1 is older than FILE2  
  - [x] `FILE1 -ef FILE2` (same file) - ✅ Check if FILE1 and FILE2 refer to same file
- [ ] **Enhanced String Test Operators**
  - [x] `-z` (zero length), `-n` (non-zero length) - ✅ Implemented
  - [ ] `STRING1 < STRING2` - Lexicographic string comparison (in [[ ]])
  - [ ] `STRING1 > STRING2` - Lexicographic string comparison (in [[ ]])
  - [ ] `STRING =~ REGEX` - Pattern matching with regular expressions (in [[ ]])
- [ ] **Compound Test Expressions**
  - [ ] `! EXPR` - Logical negation
  - [ ] `EXPR1 -a EXPR2` - Logical AND (deprecated, use && in [[ ]])
  - [ ] `EXPR1 -o EXPR2` - Logical OR (deprecated, use || in [[ ]])
  - [ ] `[[ ]]` command - Enhanced test with pattern matching and logical operators
- [ ] **Test Command Error Handling**
  - [x] Proper error codes (0=true, 1=false, 2=syntax error) - ✅ Implemented
  - [ ] Detailed error messages for invalid operators/syntax
  - [ ] File permission error handling (vs file not found)

#### Remaining Control Structures
- [x] `if`/`then`/`else`/`fi` - Conditional execution blocks (✅ v0.13.0)
- [x] `test` or `[` command for conditionals - Boolean testing (✅ v0.13.0)
- [x] `while`/`do`/`done` loops - ✅ Iteration constructs (v0.14.0)
- [x] `for` loops (in-list style) - ✅ Enhanced iteration with variable expansion and glob support (v0.15.0)
- [x] `break` and `continue` - ✅ Loop control statements for while and for loops (v0.16.0)
- [x] `case`/`esac` statements - ✅ Pattern matching with wildcards, character classes, and fallthrough control (v0.17.0)
- [ ] `for` loops (C-style) - Arithmetic-based iteration `for ((i=0; i<10; i++))`

#### Core Commands (All Implemented)
- [x] **Colon Command (`:`)** - ✅ Null command for empty statements, always returns exit status 0 (v0.17.3)
- [x] **Dot Command (`.`)** - ✅ Synonym for `source` builtin (already implemented as `source`)

#### Advanced Shell Options  
- [ ] `set` options:
  - [ ] `-e` (errexit) - Exit on error
  - [ ] `-u` (nounset) - Error on undefined variables
  - [ ] `-x` (xtrace) - Print commands before execution
  - [ ] `-o pipefail` - Pipeline fails if any command fails
- [ ] `trap` command for signal handling
- [ ] Local variables in functions (local builtin)

### Medium Priority Features

#### Arithmetic Expansion
- [x] `$((...))` arithmetic evaluation - ✅ Complete arithmetic subsystem with tokenizer, parser, and evaluator (v0.18.0)
- [x] Basic operators (+, -, *, /, %, **) - ✅ All basic arithmetic operators implemented
- [x] Comparison operators (<, >, <=, >=, ==, !=) - ✅ Full comparison operator support
- [x] Logical operators (&&, ||, !) - ✅ Short-circuit logical operators
- [x] Variable references in arithmetic - ✅ Variable expansion and assignment
- [x] C-style increment/decrement (++, --) - ✅ Pre/post increment and decrement
- [x] Bitwise operators (&, |, ^, ~, <<, >>) - ✅ Complete bitwise operation support
- [x] Ternary operator (? :) - ✅ Conditional expressions
- [x] Assignment operators (=, +=, -=, *=, /=, %=) - ✅ Compound assignments
- [x] Comma operator - ✅ Sequential evaluation
- [x] Hexadecimal (0xFF) and octal (077) number support - ✅ Multiple number bases

#### Advanced Expansions
- [x] Brace expansion - ✅ Complete implementation with list and sequence expansion (v0.21.0-v0.22.0)
  - [x] Phase 1: List expansion `{a,b,c}` with nesting and quote awareness (v0.21.0)
  - [x] Phase 2: Sequence expansion `{1..10}`, `{a..z}`, `{10..1..2}` (v0.22.0)
- [ ] Advanced parameter expansion:
  - [ ] `${var#pattern}` - Remove shortest prefix
  - [ ] `${var##pattern}` - Remove longest prefix
  - [ ] `${var%pattern}` - Remove shortest suffix
  - [ ] `${var%%pattern}` - Remove longest suffix
  - [ ] `${var/pattern/replacement}` - Pattern substitution
  - [ ] `${#var}` - String length

### Lower Priority Features

#### Interactive Enhancements
- [ ] Tab completion for commands (beyond files/directories)
- [ ] Programmable completion
- [ ] Syntax highlighting in prompt
- [ ] Multi-line command editing with PS2
- [ ] Custom prompts (PS1, PS2, PS3, PS4)

## Implementation Priorities

### Immediate Next Features (Recommended Order)

1. **C-style For Loops** - `for ((i=0; i<10; i++))` - Arithmetic-based iteration (leverages v0.18.0 arithmetic expansion)
2. **Enhanced Read Features** - `-p` prompt, `-s` silent, `-t` timeout, `-n` chars, `-d` delimiter
3. **Local Variables** - `local` builtin for function scope
4. **Set Options** - `-e`, `-u`, `-x` for better script debugging
5. **Enhanced Parameter Expansion** - `${#var}`, `${var#pattern}`, `${var%pattern}`, etc.
6. **Trap Command** - Signal handling for cleanup and error management

### Recent Major Accomplishments (v0.10.0 - v0.22.0)

#### ✅ Complete Script Execution System (v0.10.0 - v0.12.0)
- **Phase 1**: Basic script file execution with arguments
- **Phase 2**: Enhanced input processing with line continuation and error reporting  
- **Phase 3**: Enhanced source builtin with PATH search and arguments
- **Phase 4**: Full shebang support with multi-interpreter execution

#### ✅ Control Structures Implementation (v0.13.0)
- **Complete if/then/else/fi conditional statements** with full bash compatibility
- **Context-aware keyword tokenization** preventing conflicts with command arguments
- **Comprehensive test command** ([) with string, numeric, and file operators
- **Exit status-based conditional evaluation** (0=true, non-zero=false)
- **18 comprehensive tests** covering all control structure scenarios
- **Production-ready examples** demonstrating real-world usage patterns

**Impact**: psh now supports conditional logic and has evolved into a full programming language capable of sophisticated shell scripting.

#### ✅ Enhanced File Test Operators (v0.13.1)
- **Complete POSIX and bash file test operators** with 15 new operators added
- **File size and type operators**: -s, -L/-h, -b, -c, -p, -S for comprehensive file checking
- **File permission operators**: -k, -u, -g, -O, -G for security and ownership testing
- **File comparison operators**: -nt, -ot, -ef for timestamp and inode comparisons
- **Special operators**: -t (terminal), -N (modified since read) for advanced conditions
- **Robust error handling** for non-existent files and invalid arguments
- **6 comprehensive test methods** with 20+ individual test cases covering all scenarios

**Impact**: psh now supports the complete set of bash file test semantics for full script compatibility.

#### ✅ While Loops Implementation (v0.14.0) 
- **Complete while/do/done loop constructs** following same architectural patterns as if statements
- **WhileStatement AST node** with condition and body CommandLists for clean representation
- **WHILE/DO/DONE tokenization** with proper keyword context detection
- **Robust loop execution** with condition evaluation and proper exit status handling
- **Complex condition support**: file tests, string/numeric comparisons, pipelines, && and ||
- **17 comprehensive tests** with 94% success rate covering all loop scenarios
- **Natural termination** based on condition evaluation (exit code 0 = continue, non-zero = stop)
- **Variable modification support** within loop bodies for practical programming
- **I/O redirection support** in both conditions and loop bodies

**Impact**: psh now supports iteration constructs, completing the core programming language capabilities with conditionals and loops.

#### ✅ For Loops Implementation (v0.15.0)
- **Complete for/in/do/done loop constructs** with flexible iteration support
- **ForStatement AST node** with variable, iterable, and body fields following established patterns
- **FOR/IN tokenization** with proper keyword context detection in tokenizer
- **Enhanced parser** supporting WORD, STRING, and VARIABLE tokens in iterable lists
- **Robust execution engine** with variable expansion and glob pattern support
- **Multiple iteration types**: simple lists, variable expansion, glob patterns, quoted items
- **Variable scoping**: loop variables properly isolated and restored after execution
- **20 comprehensive tests** with 85% success rate covering all iteration scenarios
- **I/O redirection and pipeline support** in loop bodies for complex automation
- **Complete iteration capabilities** with both while and for loops

**Impact**: psh achieves complete iteration capabilities, enabling sophisticated automation and real-world shell scripting with full bash-like functionality.

#### ✅ Break and Continue Statements Implementation (v0.16.0)
- **Complete break and continue statements** for loop control with proper exception-based flow
- **LoopBreak and LoopContinue exception classes** following established FunctionReturn pattern for control flow
- **BreakStatement and ContinueStatement AST nodes** integrating seamlessly with existing control structures
- **BREAK/CONTINUE tokenization** with proper keyword context detection in tokenizer
- **Enhanced parser** handling break/continue statements within loop bodies using Union types
- **Exception-based execution** with proper catch/handle mechanisms in while and for loop execution
- **Comprehensive error handling** for break/continue used outside loops with clear error messages
- **Nested loop support**: break/continue only affects innermost loop, preserving outer loop execution
- **Function integration**: works correctly in functions called from within loops
- **Multi-level exception handling** at command list, top-level, and buffered command execution levels
- **Complete loop control capabilities** matching bash behavior with immediate exit (break) and iteration skip (continue)
- **8 comprehensive tests** covering basic functionality, error cases, parsing, and nested scenarios

**Impact**: psh now provides complete loop control capabilities, enabling sophisticated iteration patterns and early loop termination/continuation that matches bash behavior for advanced shell scripting.

#### ✅ Case Statements Implementation (v0.17.0)
- **Complete case/esac conditional statements** with comprehensive pattern matching and fallthrough control
- **CaseStatement, CaseItem, and CasePattern AST nodes** providing structured representation of case constructs
- **CASE/ESAC tokenization** with special terminator operators (;;, ;&, ;;&) for advanced control flow
- **Comprehensive case parsing** handling expressions, pattern lists, commands, and terminators with proper syntax validation
- **Robust pattern matching engine** using fnmatch for shell-style pattern matching with full compatibility
- **Complete pattern support**: wildcards (*), character classes ([abc], [a-z]), single character (?), and literal patterns
- **Multiple patterns per case item** with pipe (|) separator for flexible pattern matching
- **Variable expansion** in both case expressions and patterns for dynamic pattern matching
- **Advanced fallthrough control**: ;; (stop), ;& (fallthrough), ;;& (continue matching) for sophisticated control flow
- **Break/continue integration** enabling loop control within case statements for complex iteration patterns
- **Default pattern support** with (*) catch-all patterns for comprehensive condition handling
- **10 comprehensive tests** covering parsing, pattern matching, variable expansion, and fallthrough behavior
- **Full bash compatibility** with case statement syntax and semantics

**Impact**: psh achieves complete control structure capabilities with if/then/else/fi, while/do/done, for/in/do/done, and case/esac, providing a full programming language with sophisticated pattern matching and control flow that matches bash functionality.

#### ✅ Arithmetic Expansion Implementation (v0.18.0)
- **Complete $((...)) arithmetic expansion** with separate subsystem architecture for clean separation of concerns
- **ArithmeticTokenizer** recognizing numbers (decimal/hex/octal), operators, variables, and parentheses
- **ArithmeticParser** implementing recursive descent with proper operator precedence and associativity
- **ArithmeticEvaluator** supporting all bash arithmetic features with shell variable integration
- **Full operator support**: arithmetic (+,-,*,/,%,**), comparison (<,>,<=,>=,==,!=), logical (&&,||,!), bitwise (&,|,^,~,<<,>>)
- **Advanced features**: ternary (?:), comma (,), assignments (=,+=,-=,*=,/=,%=), increment/decrement (++,--)
- **Variable integration**: read/write shell variables, non-numeric strings evaluate to 0 (bash behavior)
- **Number format support**: decimal (42), hexadecimal (0xFF), octal (077) with automatic base detection
- **Error handling**: division by zero, syntax errors, with graceful fallback to 0
- **35 comprehensive tests** covering tokenization, parsing, evaluation, and shell integration
- **Educational architecture**: separate subsystem makes arithmetic evaluation independently studyable

**Impact**: psh now supports full arithmetic evaluation enabling mathematical computations in shell scripts, test conditions, and paving the way for C-style for loops. The clean architecture demonstrates best practices for adding subsystems to interpreters.

#### ✅ Modular Builtin Architecture (v0.20.0)
- **Complete refactoring of all 24 builtins** into a modular architecture with base class and registry
- **Abstract base class Builtin** provides consistent interface for all builtin commands
- **Registry pattern with @builtin decorator** enables automatic registration and discovery
- **Logical module organization**: core, environment, file_ops, flow_control, history, job_control, etc.
- **394 lines removed from shell.py** improving maintainability and readability
- **Job control bug fixes** for fg/bg commands properly handling Job objects
- **Test refactoring** from direct method calls to run_command() for better integration
- **Full backward compatibility** maintained with all existing functionality
- **Educational architecture preserved** while enabling easier extension and maintenance

**Impact**: The modular builtin architecture provides a clean foundation for adding new builtins and maintaining existing ones. The registry pattern makes it trivial to add new commands, and the logical organization helps developers quickly find and modify functionality.

#### ✅ Read Builtin Implementation (v0.20.1)
- **Core POSIX read functionality** with proper IFS field splitting and variable assignment
- **Raw mode (-r)** preserves backslashes without escape processing
- **Escape sequence processing** handles \n, \t, \\, and other standard sequences
- **Line continuation support** with backslash-newline handling
- **Single vs multiple variable handling** with appropriate field splitting behavior
- **Default REPLY variable** when no variable names are specified
- **Comprehensive test suite** with 17 tests covering all edge cases
- **Proper EOF and signal handling** with correct exit codes

**Impact**: The read builtin enables interactive scripts and file processing loops, essential for real-world shell scripting. This brings the total builtin count to 25, with a solid foundation for adding interactive features in future phases.

#### ✅ Brace Expansion Implementation (v0.21.0)
- **Pre-tokenization brace expansion** matching bash expansion order
- **List expansion support**: `{a,b,c}` → `a b c` with proper whitespace handling
- **Preamble/postscript support**: `file{1,2,3}.txt` → `file1.txt file2.txt file3.txt`
- **Nested brace expansion**: `{a,b{1,2}}` → `a b1 b2` with recursive processing
- **Empty element handling**: `{a,,c}` → `a  c` preserving empty strings
- **Quote and escape awareness**: Braces inside quotes or escaped are not expanded
- **Memory safety**: Configurable limit (10,000 items) prevents excessive expansions
- **Error handling**: Graceful fallback to original string on expansion failure
- **Clean architecture**: Separate BraceExpander module with single responsibility
- **Comprehensive test suite**: 22 tests covering all edge cases and integration
- **Foundation for Phase 2**: Architecture ready for sequence expansion `{1..10}`, `{a..z}`

**Impact**: Brace expansion enables powerful file manipulation patterns and reduces repetitive typing. The pre-tokenization approach ensures correct bash semantics while maintaining clean separation of concerns in the codebase.

#### ✅ Brace Expansion Phase 2: Sequence Expansion (v0.22.0)
- **Complete sequence expansion**: numeric `{1..10}`, character `{a..z}`, with increment `{1..20..2}`
- **Numeric sequences**: forward/reverse, negative numbers, automatic direction detection
- **Character sequences**: ASCII ordering, cross-case support ({X..c} includes non-letters)
- **Zero-padded sequences**: {01..10} → 01 02 03 04 05 06 07 08 09 10
- **Special cross-zero padding**: {-05..05} uses different padding for negative/positive
- **Increment support**: optional third parameter, sign ignored, 0 treated as 1
- **Invalid sequence handling**: graceful fallback for mixed types, floats, invalid chars
- **Mixed expansions**: {{1..3},{a..c}} → 1 2 3 a b c combining lists and sequences
- **Memory safety**: sequence expansions respect same limits as list expansions
- **Full bash compatibility**: matches bash behavior for all edge cases
- **10 additional tests**: comprehensive coverage of sequences, padding, increments

**Impact**: Complete brace expansion implementation enables powerful iteration patterns in shell commands. Users can now generate file sequences (backup{001..100}.tar), create test data (test_{a..z}.txt), and perform bulk operations with minimal typing. The implementation demonstrates clean subsystem design with clear separation between list and sequence expansion logic.

#### ✅ Process Substitution Implementation (v0.24.0)
- **Complete <(...) and >(...) syntax** for treating command output as files
- **PROCESS_SUB_IN and PROCESS_SUB_OUT tokens** with proper parenthesis balancing in tokenizer
- **ProcessSubstitution AST node** cleanly integrates with existing word and redirect parsing
- **Pipe-based execution** creates readable/writable file descriptors accessible via /dev/fd/N
- **Support in multiple contexts**: command arguments, redirect targets, pipelines
- **Robust process management**: proper cleanup, signal handling, and zombie prevention
- **Educational demo script** showing low-level mechanics of process substitution
- **15 comprehensive tests** covering basic usage, multiple substitutions, error cases
- **Common use cases enabled**: diff <(ls dir1) <(ls dir2), tee >(log1) >(log2), paste <(cmd1) <(cmd2)

**Impact**: Process substitution completes the major bash expansion features, enabling sophisticated command composition patterns. Users can now compare command outputs directly, split data streams to multiple processors, and treat any command's output as a file. The implementation leverages existing pipe infrastructure while maintaining clean separation of concerns.

#### ✅ RC File Support Implementation (v0.25.0)
- **~/.pshrc automatic loading** for interactive shells with proper isatty() detection
- **--norc flag** to skip RC file loading for clean environment testing
- **--rcfile FILE option** to specify alternative initialization file
- **Security checks** preventing loading of world-writable or untrusted files
- **Graceful error handling** showing warnings without preventing shell startup
- **Proper $0 preservation** during RC file execution and restoration after
- **Full shell context** allowing aliases, functions, exports, and variables
- **Force interactive mode** for testing with _force_interactive attribute
- **Comprehensive test suite** with 10 tests covering all scenarios
- **Example .pshrc file** demonstrating common aliases, functions, and customizations
- **Complete documentation** in docs/pshrc_implementation_plan.md

**Impact**: RC file support enables users to customize their shell environment with personal aliases, functions, and settings that persist across sessions. The implementation follows bash conventions while maintaining security through permission checks. Users can now create productivity-enhancing shortcuts and maintain consistent environments across different machines by sharing their .pshrc files.

#### ✅ Enhanced Command Substitution and Break/Continue (v0.26.3)
- **Command substitution in double-quoted strings** now properly expands $(command) and `command` within "..." strings
- **Multi-level break/continue support** with `break 2`, `continue 3` for escaping nested loops
- **Improved brace expansion** with shell metacharacter awareness, fixing issues with `{1..5};` patterns
- **Case statement command substitution** support for `case $(command) in ...` patterns
- **Control structures test suite** improved from 74.1% to 83.3% pass rate
- **Architectural limitations documented** for control structures in pipelines

**Impact**: These enhancements improve bash compatibility and fix several edge cases in command substitution and loop control. The multi-level break/continue feature enables more sophisticated loop control patterns, while the command substitution fixes ensure consistent behavior across all contexts.

### Architecture Considerations

#### Lessons from Script Execution Implementation
- Unified input processing improves consistency across execution modes
- Proper state management crucial for source builtin and nested execution
- Shebang support requires careful subprocess handling and error management
- Binary file detection needs multi-factor analysis for accuracy

#### From Control Structures Implementation (v0.13.0 - v0.15.0)
- ✅ Context-aware keyword tokenization successfully prevents parsing conflicts
- ✅ Exit status-based conditional evaluation works seamlessly with existing commands
- ✅ AST extensions for block constructs integrate cleanly with parser architecture
- ✅ Production-ready test command implementation covers comprehensive operator set
- ✅ **While loops** successfully implement same architectural patterns as if statements
- ✅ **For loops** demonstrate excellent architectural consistency and reusability
- ✅ **Loop execution patterns** work seamlessly with all existing command types
- ✅ **Variable scoping mechanisms** provide clean isolation without side effects
- ✅ **Iteration capabilities** enable sophisticated automation with both while and for loops
- ✅ **Consistent parsing patterns** make adding new control structures straightforward
- ✅ **Break/continue statements** successfully implement exception-based control flow patterns
- ✅ **Loop control mechanisms** provide clean early termination and continuation without side effects
- ✅ **Case statements** successfully implement pattern matching with fnmatch integration and fallthrough control
- ✅ **Complete control structure suite** provides full programming language capabilities
- **Next**: C-style for loops will build on established arithmetic expansion

#### For Job Control (Already Implemented)
- ✅ Process group management working correctly
- ✅ Signal handling properly configured
- ✅ Job table and notification system complete

#### For Advanced Expansions (Future)
- Order of expansions matters (follow POSIX specification)
- Need careful quote handling during expansion phases
- Some expansions happen at different parsing stages

### Current Architecture Strengths

1. **Modular Design** - Clear separation between tokenizer, parser, executor
2. **Educational Clarity** - Code remains readable and teachable
3. **Robust Error Handling** - Comprehensive error messages with file:line info
4. **Unified Input System** - Consistent handling across interactive, script, and source modes
5. **Production Compatibility** - Full shebang support enables real-world usage
6. **Context-Aware Parsing** - Smart keyword recognition prevents conflicts
7. **Conditional Logic** - Full programming language capabilities with if statements
8. **Complete File Testing** - All POSIX and bash file test operators supported
9. **Complete Iteration** - Both while and for loops with full condition and variable support
10. **Variable Scoping** - Proper isolation and restoration in loops and functions
11. **Complete Loop Control** - Break and continue statements with exception-based flow control
12. **Modular Builtin Architecture** - Registry pattern with logical organization for maintainability
13. **Interactive Features** - Read builtin and job suspension notifications enhance user experience

### Testing Strategy

- ✅ **Unit Tests** - Comprehensive coverage of core components  
- ✅ **Integration Tests** - Real-world script execution scenarios
- ✅ **Compatibility Tests** - Cross-interpreter script execution
- ✅ **Edge Case Testing** - Error conditions and boundary cases
- ✅ **Performance Testing** - Large script handling and recursive features
- 🔄 **Test Suite Health** - 15 skipped tests: 11 can be fixed/rewritten, 4 await feature implementation

### Learning Resources

- POSIX Shell specification for standard compliance
- Bash source code for implementation reference
- "The Linux Programming Interface" for process management
- "Advanced Programming in the Unix Environment" for system calls
- "Compilers: Principles, Techniques, and Tools" for parsing techniques

## 🎯 Current Status Summary

### **Major Milestone: Complete Programming Language with RC File Support (v0.25.0)**

psh has evolved from a basic educational shell into a **complete programming language** with full conditional logic, complete iteration capabilities, sophisticated loop control, comprehensive pattern matching, arithmetic evaluation, user input capabilities, and a clean modular architecture while maintaining its educational mission. Key achievements:

**Programming Language Capabilities:**
- ✅ Complete control structures: `if/then/else/fi`, `while/do/done`, `for/in/do/done`, `case/esac`
- ✅ Sophisticated pattern matching: wildcards (*), character classes ([abc], [a-z]), single character (?)
- ✅ Advanced case control: multiple patterns (a|b|c), fallthrough (;;, ;&, ;;&), default patterns (*)
- ✅ Loop control: `break` and `continue` statements for early termination and iteration skipping
- ✅ Comprehensive test operators: 15+ file test operators, string, numeric conditions
- ✅ Complex condition support: `&&`, `||`, pipelines, command substitution
- ✅ Variable expansion and scoping: proper isolation in loops with glob pattern support
- ✅ Flexible iteration: simple lists, variables, glob patterns, quoted items
- ✅ Execute shell scripts: `psh script.sh arg1 arg2`
- ✅ Enhanced source builtin: `source helper.sh arg1 arg2`  
- ✅ Line continuation: `echo "line 1" \ "line 2"`
- ✅ Shebang support: `#!/bin/bash`, `#!/usr/bin/env python3`
- ✅ Multi-interpreter execution with proper fallback
- ✅ Production-quality error handling and reporting
- ✅ Core POSIX commands: colon (:) null command and dot (.) source synonym
- ✅ Arithmetic expansion: $((...)) with full operator support, variables, and bash compatibility
- ✅ Modular builtin architecture: All 25 builtins extracted with registry pattern and base class (v0.20.0)
- ✅ Read builtin: Core POSIX functionality with IFS splitting, raw mode, escape processing (v0.20.1)
- ✅ Job suspension notifications: Ctrl-Z shows "[job]+  Stopped" message like bash
- ✅ Brace expansion: Complete implementation with list {a,b,c} and sequence {1..10} expansion (v0.21.0-v0.22.0)
- ✅ Process substitution: <(...) and >(...) for treating command output as files (v0.24.0)
- ✅ RC file support: ~/.pshrc automatic initialization with security checks (v0.25.0)

**Development Quality:**
- ✅ 54 major features implemented and tested
- ✅ Comprehensive test suite with 510+ passing tests, 22 skipped, 1 xfailed
- ✅ Robust architecture supporting complete control structure suite with pattern matching
- ✅ Clean modular design: shell.py reduced by 394 lines, builtins organized into logical modules
- ✅ Educational clarity preserved throughout
- 🔄 Test suite health: 11 of 17 skipped tests can be fixed/rewritten, 4 await feature implementation

**Next Phase Focus:**
C-style for loops `for ((i=0; i<10; i++))` will complete the iteration constructs, leveraging the newly implemented arithmetic expansion for initialization, condition testing, and increment operations.

### Feature Implementation Stats
- **🟢 Completed**: 54 major features (Core shell, Advanced features, Interactive features, Programming features, Script execution, Control structures, File test operators, While loops, For loops, Break/continue statements, Case statements, Core POSIX commands, Arithmetic expansion, Modular builtin architecture, Read builtin, Brace expansion complete, Process substitution, RC file support)
- **🟡 High Priority**: 1 feature (C-style for loops) + enhanced read features
- **🟡 High Priority**: 1 feature group (Advanced shell options)  
- **🟠 Medium Priority**: 1 feature group (Advanced parameter expansions)
- **🔵 Lower Priority**: 1 feature group (Interactive enhancements)

**Total Progress**: ~97% of planned shell features complete, with **RC file support** enabling persistent user customization and productivity enhancements through automatic shell initialization.

## 🚨 Known Issues & Limitations

### Architectural Limitations
- ~~**Nested Control Structures**~~: ✅ FIXED in v0.19.0 - Control structures can now be nested to arbitrary depth with the new Statement-based architecture
- **Multi-line Input Parsing**: Complex multi-line commands with nested structures fail to parse correctly. Single-line equivalents work fine.
- **Pipeline Job Control Issues**: Some pipelines are incorrectly treated as background jobs instead of running in foreground.
- **For Loop Variable Persistence**: Loop variables are incorrectly restored to their previous value after the loop completes. In bash, they retain their last iteration value.
- **Builtin Redirections**: Builtins that use Python's `print()` function (like echo, pwd) don't respect file descriptor redirections. They need to be updated to use `os.write()` directly to file descriptors for proper redirection support.
- **Control Structures in Pipelines**: Control structures (while, for, if, case) cannot be used as part of pipelines. For example, `echo "data" | while read line; do echo $line; done` fails to parse. This is a fundamental parser architecture limitation where pipelines expect Command objects, not control structures. Workaround: Use the control structure to wrap the entire pipeline instead.

### Tokenizer Issues
- **Arithmetic Expansion in Assignments**: The tokenizer incorrectly breaks `c=$((a + b))` into separate tokens because `read_word()` stops at `(`. This should tokenize as `WORD='c='` followed by `ARITH_EXPANSION='$((a + b))'`.
- **Stderr Redirection**: The tokenizer incorrectly tokenizes `>&2` as three separate tokens (`>`, `&`, `2`) instead of recognizing it as a redirect duplication operator. This causes parser failures with "Expected file name after redirection" errors.
- **Arithmetic Inside Quotes**: Arithmetic expansion inside double quotes (e.g., `echo "Result: $((2 + 2))"`) is not being expanded because `_expand_string_variables()` only handles variable expansion, not arithmetic expansion.
- **Variable Assignment with Quoted Values** (NEW - discovered v0.20.1): The tokenizer doesn't handle `VAR="value with spaces"` correctly when it appears before a command. For example, `MSG="hello world" echo $MSG` fails with "world": command not found" because the quoted value is split incorrectly.

### Parser Edge Cases
- **Empty Commands**: Consecutive semicolons (`;;`, `;;;`) are not handled gracefully in command parsing (though they work correctly in case statements).
- **Complex Quoting**: Some edge cases with complex nested quoting and escaping may not parse correctly.
- **EOF Cascade Errors**: When early parsing fails (e.g., redirect errors), the parser continues looking for closing keywords (`fi`, `done`) but hits EOF, causing cascading "Expected FI/DONE, got EOF" errors.
- ~~**Command Substitution in For Loops**~~: ✅ FIXED in v0.19.3 - Command substitution `$(...)` and backticks are now properly parsed and executed in for loop iterables. The parser accepts COMMAND_SUB tokens and the executor expands them with word splitting.
- **Break/Continue Parsing**: The parser returns break/continue as statements, but some tests expect them as and_or_lists, indicating a mismatch between parser output and test expectations.
- **Break/Continue with Operators**: Using break/continue after && or || operators (e.g., `echo "test" && break`) causes parse errors.

### Workarounds in Use
- Tests use single-line command syntax to avoid multi-line parsing issues
- ~~Nested control structure tests are skipped with clear documentation~~ - No longer needed after v0.19.0
- Some pipeline tests are skipped due to job control issues
- Avoid stderr redirection (`>&2`) in scripts; use `2>&1` or file redirection instead
- Avoid arithmetic expansion inside quotes; use unquoted arithmetic or concatenation
- ~~Use explicit lists in for loops instead of command substitution~~ - No longer needed after v0.19.3
- Avoid quoted values in variable assignments before commands; use `VAR=value` without quotes or set the variable on a separate line
- Don't rely on loop variables persisting after the loop; save to a different variable if needed
- Avoid using break/continue after && or || operators; use if statements instead

### Future Improvements Needed
1. ~~**AST Architecture Redesign**~~: ✅ COMPLETED in v0.19.0 - Implemented Statement base class and StatementList with full nesting support
2. **Multi-line Parser Enhancement**: Improve newline and indentation handling
3. **Job Control Refinement**: Fix pipeline classification between foreground/background
4. **Tokenizer Fixes**:
   - Fix `read_word()` to handle arithmetic expansion that starts within a word
   - Add proper tokenization for redirect duplication operators (`>&`, `<&`)
   - Enhance `_expand_string_variables()` to also handle arithmetic expansion inside strings
   - Fix tokenization of `VAR="value with spaces"` to keep the assignment as a single token
5. **Parser Error Recovery**: Improve error handling to avoid cascade errors when early parsing fails
6. ~~**For Loop Enhancement**~~: ✅ COMPLETED in v0.19.3 - parse_for_statement() now accepts COMMAND_SUB tokens and executor properly expands them
7. **For Loop Variable Scoping**: Fix execute_for_statement to preserve loop variable value after loop completion (match bash behavior)
8. **Break/Continue Parser Integration**: Allow break/continue statements in and_or_lists for use after operators
9. **Fix Builtin Redirections**: Update all builtins that use `print()` to use `os.write()` directly to file descriptors. This includes:
   - echo, pwd (in io.py)
   - env, set, declare, alias (output commands)
   - history, jobs (listing commands)
   - Any other builtin that produces output

## 📋 Test Suite Skip Status

### Currently Skipped Tests (22 total as of v0.22.0)
Analysis of skipped tests reveals they fall into several categories:

#### Tests that CAN be fixed or rewritten (14 tests):
1. **CI-only skips (2 tests)** - Already work locally:
   - `test_stderr_redirect.py:75, 100` - Stderr redirection tests (skip only on GitHub Actions)
   - `test_command_substitution.py:179` - Command substitution in pipeline (skip only on GitHub Actions)

2. **Minor implementation fixes needed (5 tests)**:
   - `test_variables.py:111` - `$!` variable test - Implementation exists, might need minor fixes
   - `test_variable_assignment_command.py:99` - VAR="value with spaces" tokenizer issue (documented)
   - `test_tilde_expansion.py:124` - Escaped tilde handling (tokenizer removes backslashes too early)
   - `test_break_continue.py:86, 111` - For loop variable persistence issue (fixable)

3. **Pytest capture conflicts (7 tests)** - Need rewriting to use file output:
   - `test_glob.py:192` - Glob expansion in pipeline
   - `test_heredoc.py:105, 133` - Heredoc with external commands and pipelines
   - `test_nested_control_structures.py:342, 382, 422` - Nested control structures with pipelines
   - `test_pipeline.py:77` - Built-in commands in pipelines
   - `test_builtin_refactor.py:119` - Built-in commands in pipelines

#### Tests that need architectural changes (8 tests):
1. **Parser/AST changes needed (3 tests)**:
   - `test_break_continue.py:369` - Parser returns statements, not and_or_lists for break/continue
   - `test_break_continue.py:395` - Break after && operator causes parse errors
   - `test_break_continue.py:425` - For loop variable restoration issue

2. **Complex features not implemented (5 tests)**:
   - `test_nested_control_structures.py:232` - Requires `read` builtin (✅ implemented in v0.20.1 - can be unskipped)
   - `test_glob.py:224` - Requires escaped glob pattern support (not implemented)
   - `test_command_substitution.py:160` - Complex backtick escape sequences (needs tokenizer work)
   - `test_heredoc.py:118` - Multiple redirections with heredocs (needs special handling)
   - `test_builtin_phase2.py` - Unknown status (file not examined)

### Test Improvement Recommendations
1. **Immediate actions**:
   - Remove `skipif` decorators for CI-only tests when running locally
   - Fix `test_variables.py:111` - the `$!` test might already work
   - Unskip `test_nested_control_structures.py:232` - read builtin was implemented in v0.20.1
   - Enable 11 break/continue tests from `test_break_continue.py.disabled` (✅ Done - 11 now pass, 5 skipped)

2. **Test rewriting needed**:
   - Convert pytest capture tests to use file-based output verification
   - Create helper functions for testing pipeline output
   - Use script files for complex multi-line heredoc tests

3. **Implementation fixes needed**:
   - Fix for loop variable persistence (should retain last value after loop)
   - Fix tokenizer for VAR="value with spaces" assignments
   - Enhance parser to handle break/continue after && or || operators

4. **Keep skipped until features implemented**:
   - Escaped glob pattern tests
   - Complex escape sequence tests
   - Multiple redirections with heredocs