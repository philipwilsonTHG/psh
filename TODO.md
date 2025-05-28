# Python Shell (psh) - TODO List

Features ordered by implementation status and complexity.

## ✅ Completed Features

### Core Shell Features
1. **Basic Command Execution** - External commands, built-ins, exit status
2. **Additional Built-in Commands** - pwd, echo, env, unset, source, exit, cd, export, history, set, declare, return, jobs, fg, bg, alias, unalias, version
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

### **🎯 Script Execution (v0.10.0 - v0.11.0)**
18. **Script File Execution** - Execute psh scripts with `psh script.sh`
19. **Script Arguments** - Proper $0, $1, $2, etc. handling
20. **Enhanced Input Processing** - Line continuation with backslash (\), unified input system
21. **Enhanced Source Builtin** - PATH search, argument passing (source script.sh arg1 arg2)
22. **Enhanced Command Line** - -h/--help, -V/--version, -- separator support
23. **Enhanced Error Handling** - File:line error messages, proper exit codes (126, 127)
24. **Script vs Interactive Mode** - Appropriate signal handling for each mode
25. **Shebang Support** - Full #!/interpreter support, env patterns, fallback to psh
26. **Enhanced Binary Detection** - Multi-factor analysis, file signature recognition

## 🚧 Remaining Features

### High Priority Features

#### Control Structures (Most Important)
- [ ] `if`/`then`/`else`/`fi` - Conditional execution blocks
- [ ] `while`/`do`/`done` loops - Iteration constructs  
- [ ] `for` loops (both C-style and in-list style) - Enhanced iteration
- [ ] `case`/`esac` statements - Pattern matching
- [ ] `break` and `continue` - Loop control
- [ ] `test` or `[` command for conditionals - Boolean testing

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
- [ ] `$((...))` arithmetic evaluation
- [ ] Basic operators (+, -, *, /, %, **)
- [ ] Comparison operators (<, >, <=, >=, ==, !=)
- [ ] Logical operators (&&, ||, !)
- [ ] Variable references in arithmetic
- [ ] C-style increment/decrement (++, --)

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

1. **Control Structures** - `if`/`then`/`else`/`fi` - Most impactful for shell scripting
2. **Arithmetic Expansion** - `$((...))` - Essential for loops and conditionals  
3. **While Loops** - `while`/`do`/`done` - Basic iteration
4. **Local Variables** - `local` builtin for function scope
5. **Set Options** - `-e`, `-u`, `-x` for better script debugging

### Recent Major Accomplishments (v0.10.0 - v0.11.0)

#### ✅ Complete Script Execution System
- **Phase 1**: Basic script file execution with arguments
- **Phase 2**: Enhanced input processing with line continuation and error reporting  
- **Phase 3**: Enhanced source builtin with PATH search and arguments
- **Phase 4**: Full shebang support with multi-interpreter execution

**Impact**: psh now supports production-level script execution while maintaining educational clarity.

### Architecture Considerations

#### Lessons from Script Execution Implementation
- Unified input processing improves consistency across execution modes
- Proper state management crucial for source builtin and nested execution
- Shebang support requires careful subprocess handling and error management
- Binary file detection needs multi-factor analysis for accuracy

#### For Control Structures (Next Major Feature)
- Will require significant AST extensions for block constructs
- Need to handle multi-line parsing and block delimiters
- Consider separate parsing modes for complex constructs
- Exit status propagation through blocks is crucial

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

### **Major Milestone: Complete Script Execution System (v0.11.0)**

psh has evolved from a basic educational shell into a **production-capable script execution environment** while maintaining its educational mission. Key achievements:

**Script Execution Capabilities:**
- ✅ Execute shell scripts: `psh script.sh arg1 arg2`
- ✅ Enhanced source builtin: `source helper.sh arg1 arg2`  
- ✅ Line continuation: `echo "line 1" \ "line 2"`
- ✅ Shebang support: `#!/bin/bash`, `#!/usr/bin/env python3`
- ✅ Multi-interpreter execution with proper fallback
- ✅ Production-quality error handling and reporting

**Development Quality:**
- ✅ 26 major features implemented and tested
- ✅ Comprehensive test suite with 45+ passing tests
- ✅ Robust architecture supporting complex features
- ✅ Educational clarity preserved throughout

**Next Phase Focus:**
Control structures (`if`/`then`/`else`) will transform psh from a command executor into a full programming language, enabling complex scripts and automation workflows.

### Feature Implementation Stats
- **🟢 Completed**: 26 major features (Core shell, Advanced features, Interactive features, Programming features, Script execution)
- **🟡 High Priority**: 8 features (Control structures, Advanced shell options)  
- **🟠 Medium Priority**: 8 features (Arithmetic, Advanced expansions)
- **🔵 Lower Priority**: 5 features (Interactive enhancements)

**Total Progress**: ~65% of planned shell features complete, with all foundational systems in place for advanced programming constructs.