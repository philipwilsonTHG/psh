# Python Shell (psh) - TODO List

Features ordered by ease of implementation, from simplest to most complex.

## Easy Features (1-2 hours each)

### 1. ✅ Additional Built-in Commands
- [x] `pwd` - Print working directory
- [x] `echo` - Print arguments (with proper quote handling)
- [x] `env` - Display environment variables
- [x] `unset` - Remove environment variables
- [x] `source` or `.` - Execute commands from file

### 2. ✅ Exit Status Handling
- [x] Set `$?` variable to last command's exit code
- [x] Display exit status in prompt when non-zero
- [x] Make exit status available to shell scripts

### 3. ✅ Command History
- [x] Store command history in memory
- [x] `history` built-in command
- [x] Up/down arrow navigation (using readline)
- [x] Save history to ~/.psh_history

## Medium Features (3-5 hours each)

### 4. ✅ Pipeline Execution
- [x] Implement actual pipe functionality between processes
- [x] Handle pipeline exit status (last command's status)
- [x] Proper signal handling in pipelines

### 5. 🔧 Wildcards/Globbing
- [ ] Implement `*` wildcard expansion
- [ ] Implement `?` single-character wildcard
- [ ] Implement `[...]` character classes
- [ ] Integrate with command argument parsing

### 6. 🔧 Enhanced Variable Support
- [ ] Positional parameters ($1, $2, etc.)
- [ ] Special variables ($$, $!, $#, $@, $*)
- [ ] Variable assignment without export
- [ ] Basic parameter expansion (${var:-default})

### 7. 🔧 Here Documents
- [ ] Parse << operator
- [ ] Implement here-doc input collection
- [ ] Support <<- for tab stripping
- [ ] Here-strings (<<<)

## Hard Features (1-2 days each)

### 8. 🚀 Job Control
- [ ] Track background processes
- [ ] `jobs` command to list jobs
- [ ] `fg` and `bg` commands
- [ ] Ctrl-Z to suspend foreground job
- [ ] Job notifications when complete

### 9. 🚀 Command Substitution
- [ ] Implement $(...) syntax
- [ ] Implement backtick syntax
- [ ] Nested command substitution
- [ ] Proper quote handling within substitutions

### 10. 🚀 Aliases and Functions
- [ ] `alias` built-in command
- [ ] Alias expansion during parsing
- [ ] Basic function definition syntax
- [ ] Function invocation

### 11. 🚀 Control Structures
- [ ] `if`/`then`/`else`/`fi`
- [ ] `while`/`do`/`done`
- [ ] `for` loops (both styles)
- [ ] `case`/`esac` statements
- [ ] `&&` and `||` operators

## Advanced Features (Multiple days)

### 12. 🎯 Arithmetic Expansion
- [ ] $((...)) arithmetic evaluation
- [ ] Basic operators (+, -, *, /, %)
- [ ] Comparison operators
- [ ] Variable references in arithmetic

### 13. 🎯 Advanced Expansions
- [ ] Brace expansion ({a,b,c})
- [ ] Tilde expansion (~, ~user)
- [ ] Advanced parameter expansion (${var%pattern}, etc.)
- [ ] Process substitution (<(...), >(...))

### 14. 🎯 Script Support
- [ ] Execute .psh scripts
- [ ] Shebang support
- [ ] Script arguments
- [ ] `set` options (-e, -u, -x, etc.)
- [ ] Error handling and trap

### 15. 🎯 Interactive Enhancements
- [ ] Tab completion for commands
- [ ] Tab completion for files
- [ ] Syntax highlighting
- [ ] Multi-line command editing
- [ ] Custom prompts (PS1, PS2)

## Implementation Notes

### Starting Points

1. **Built-ins are easiest** - Just add to the `execute_command` method
2. **Pipeline execution** - Critical missing feature, good learning experience
3. **History** - Use Python's `readline` module for quick implementation
4. **Wildcards** - Use `glob` module from standard library

### Testing Strategy

- Create test scripts for each feature
- Build a test harness that compares psh output with bash
- Focus on POSIX compliance where reasonable

### Architecture Considerations

- Keep parser additions clean and well-documented
- Maintain separation between parsing and execution
- Consider creating a separate module for built-ins
- Add integration tests as features are implemented

### Learning Goals

Each feature teaches different concepts:
- Built-ins → Command dispatch patterns
- Pipelines → Process management and IPC
- Job control → Signal handling
- Control structures → Interpreter design
- Expansions → String processing and parsing complexity

Start with easy features to build momentum, then tackle medium features that add significant functionality. Hard features may require parser restructuring.