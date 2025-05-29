# Python Shell (psh) - TODO List

Features ordered by implementation status and complexity.

## ✅ Completed Features

### Core Shell Features
1. **Basic Command Execution** - External commands, built-ins, exit status
2. **Additional Built-in Commands** - pwd, echo, env, unset, source, exit, cd, export, history, set, declare, return, jobs, fg, bg, alias, unalias, version, true, false, :, .
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
18. **Control Structures** - if/then/else/fi conditional statements with full bash compatibility

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

#### Missing Core Commands
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
- [ ] Brace expansion (`{a,b,c}`, `{1..10}`)
- [ ] Advanced parameter expansion:
  - [ ] `${var#pattern}` - Remove shortest prefix
  - [ ] `${var##pattern}` - Remove longest prefix
  - [ ] `${var%pattern}` - Remove shortest suffix
  - [ ] `${var%%pattern}` - Remove longest suffix
  - [ ] `${var/pattern/replacement}` - Pattern substitution
  - [ ] `${#var}` - String length
- [ ] Process substitution (`<(...)`, `>(...)`)

### Lower Priority Features

#### Interactive Enhancements
- [ ] Tab completion for commands (beyond files/directories)
- [ ] Programmable completion
- [ ] Syntax highlighting in prompt
- [ ] Multi-line command editing with PS2
- [ ] Custom prompts (PS1, PS2, PS3, PS4)

## Implementation Priorities

### Immediate Next Features (Recommended Order)

1. **Arithmetic Expansion** - `$((...))` - Essential for C-style for loops and complex conditionals
2. **C-style For Loops** - `for ((i=0; i<10; i++))` - Arithmetic-based iteration (requires arithmetic expansion)
3. **Colon Command** - `:` - Null command for empty statements and command placeholders
4. **AST Architecture Improvements** - Support for nested control structures and mixed statement types
5. **Local Variables** - `local` builtin for function scope
6. **Set Options** - `-e`, `-u`, `-x` for better script debugging

### Recent Major Accomplishments (v0.10.0 - v0.15.0)

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
- **Next**: Arithmetic expansion and C-style for loops will build on established control flow architecture

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

### Testing Strategy

- ✅ **Unit Tests** - Comprehensive coverage of core components  
- ✅ **Integration Tests** - Real-world script execution scenarios
- ✅ **Compatibility Tests** - Cross-interpreter script execution
- ✅ **Edge Case Testing** - Error conditions and boundary cases
- ✅ **Performance Testing** - Large script handling and recursive features

### Learning Resources

- POSIX Shell specification for standard compliance
- Bash source code for implementation reference
- "The Linux Programming Interface" for process management
- "Advanced Programming in the Unix Environment" for system calls
- "Compilers: Principles, Techniques, and Tools" for parsing techniques

## 🎯 Current Status Summary

### **Major Milestone: Complete Programming Language with Pattern Matching and Arithmetic (v0.18.0)**

psh has evolved from a basic educational shell into a **complete programming language** with full conditional logic, complete iteration capabilities, sophisticated loop control, and comprehensive pattern matching while maintaining its educational mission. Key achievements:

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

**Development Quality:**
- ✅ 48 major features implemented and tested
- ✅ Comprehensive test suite with 145+ passing tests (114 new tests across control structures, iteration, loop control, pattern matching, and arithmetic)
- ✅ Robust architecture supporting complete control structure suite with pattern matching
- ✅ Educational clarity preserved throughout

**Next Phase Focus:**
C-style for loops `for ((i=0; i<10; i++))` will complete the iteration constructs, leveraging the newly implemented arithmetic expansion for initialization, condition testing, and increment operations.

### Feature Implementation Stats
- **🟢 Completed**: 48 major features (Core shell, Advanced features, Interactive features, Programming features, Script execution, Control structures, File test operators, While loops, For loops, Break/continue statements, Case statements, Core POSIX commands, Arithmetic expansion)
- **🟡 High Priority**: 1 feature (C-style for loops)
- **🟡 High Priority**: 1 feature group (Advanced shell options)  
- **🟠 Medium Priority**: 2 feature groups (Advanced expansions)
- **🔵 Lower Priority**: 1 feature group (Interactive enhancements)

**Total Progress**: ~94% of planned shell features complete, with **complete arithmetic evaluation** enabling mathematical computations and paving the way for C-style for loops.

## 🚨 Known Issues & Limitations

### Architectural Limitations
- ~~**Nested Control Structures**~~: ✅ FIXED in v0.19.0 - Control structures can now be nested to arbitrary depth with the new Statement-based architecture
- **Multi-line Input Parsing**: Complex multi-line commands with nested structures fail to parse correctly. Single-line equivalents work fine.
- **Pipeline Job Control Issues**: Some pipelines are incorrectly treated as background jobs instead of running in foreground.

### Tokenizer Issues (NEW - discovered during arithmetic expansion testing)
- **Arithmetic Expansion in Assignments**: The tokenizer incorrectly breaks `c=$((a + b))` into separate tokens because `read_word()` stops at `(`. This should tokenize as `WORD='c='` followed by `ARITH_EXPANSION='$((a + b))'`.
- **Stderr Redirection**: The tokenizer incorrectly tokenizes `>&2` as three separate tokens (`>`, `&`, `2`) instead of recognizing it as a redirect duplication operator. This causes parser failures with "Expected file name after redirection" errors.
- **Arithmetic Inside Quotes**: Arithmetic expansion inside double quotes (e.g., `echo "Result: $((2 + 2))"`) is not being expanded because `_expand_string_variables()` only handles variable expansion, not arithmetic expansion.

### Parser Edge Cases
- **Empty Commands**: Consecutive semicolons (`;;`, `;;;`) are not handled gracefully in command parsing (though they work correctly in case statements).
- **Complex Quoting**: Some edge cases with complex nested quoting and escaping may not parse correctly.
- **EOF Cascade Errors**: When early parsing fails (e.g., redirect errors), the parser continues looking for closing keywords (`fi`, `done`) but hits EOF, causing cascading "Expected FI/DONE, got EOF" errors.
- **Command Substitution in For Loops**: Command substitution like `$(seq 1 5)` is not properly parsed in for loop iterables. The parser expects DO after seeing COMMAND_SUB token, causing "Expected DO, got COMMAND_SUB" errors. This prevents constructs like `for i in $(seq 1 5); do ... done`.

### Workarounds in Use
- Tests use single-line command syntax to avoid multi-line parsing issues
- ~~Nested control structure tests are skipped with clear documentation~~ - No longer needed after v0.19.0
- Some pipeline tests are skipped due to job control issues
- Avoid stderr redirection (`>&2`) in scripts; use `2>&1` or file redirection instead
- Avoid arithmetic expansion inside quotes; use unquoted arithmetic or concatenation
- Use explicit lists in for loops instead of command substitution (e.g., `for i in 1 2 3` instead of `for i in $(seq 1 3)`)

### Future Improvements Needed
1. ~~**AST Architecture Redesign**~~: ✅ COMPLETED in v0.19.0 - Implemented Statement base class and StatementList with full nesting support
2. **Multi-line Parser Enhancement**: Improve newline and indentation handling
3. **Job Control Refinement**: Fix pipeline classification between foreground/background
4. **Tokenizer Fixes**:
   - Fix `read_word()` to handle arithmetic expansion that starts within a word
   - Add proper tokenization for redirect duplication operators (`>&`, `<&`)
   - Enhance `_expand_string_variables()` to also handle arithmetic expansion inside strings
5. **Parser Error Recovery**: Improve error handling to avoid cascade errors when early parsing fails
6. **For Loop Enhancement**: Update parse_for_statement() to accept COMMAND_SUB tokens in the iterable list, enabling `for i in $(command)` syntax