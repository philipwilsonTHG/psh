# Python Shell (psh) - TODO List

Features ordered by ease of implementation, from simplest to most complex.

## ✅ Completed Features

### Easy Features (1-2 hours each)
1. **Additional Built-in Commands** - pwd, echo, env, unset, source
2. **Exit Status Handling** - $? variable, prompt display, shell script access
3. **Command History** - In-memory storage, history command, readline integration, persistence

### Medium Features (3-5 hours each)
4. **Pipeline Execution** - Process pipes, exit status handling, signal management
5. **Wildcards/Globbing** - *, ?, [...] patterns with proper quote handling
6. **Enhanced Variable Support** - Positional params, special variables, shell variables, ${var:-default}
7. **Here Documents** - << and <<- operators with tab stripping
8. **I/O Redirection Extensions** - stderr redirection (2>, 2>>, 2>&1)
9. **Command Substitution** - $(...) and `...` with nesting support
10. **Tab Completion** - File/directory completion with special character handling
11. **Comments** - # at word boundaries, preserved in quotes and when escaped
12. **Conditional Execution** - && and || operators with short-circuit evaluation
13. **Here Strings** - <<< operator for single-line stdin input with variable expansion
14. **Tilde Expansion** - ~ for home directory, ~user for user's home directory
15. **Vi/Emacs Key Bindings** - Full command line editing with set -o vi/emacs, history search (Ctrl-R)
16. **Aliases** - alias/unalias commands, recursive expansion prevention, trailing space support

## 🚧 In Progress / Remaining Features

### Easy-Medium Features

#### Command Separators
- [x] `;` (already implemented)
- [x] `&&` - Run second command only if first succeeds
- [x] `||` - Run second command only if first fails


### Hard Features (1-2 days each)

#### Job Control
- [ ] Track background processes in job table
- [ ] `jobs` command to list jobs
- [ ] `fg` command to bring job to foreground
- [ ] `bg` command to resume suspended job in background
- [ ] Ctrl-Z (SIGTSTP) to suspend foreground job
- [ ] Job notifications when background jobs complete
- [ ] %job notation for referring to jobs

#### Aliases
- [x] `alias` built-in command
- [x] Alias expansion during tokenization
- [x] Recursive alias prevention
- [x] `unalias` command

#### Shell Functions
- [ ] Function definition syntax: `name() { commands; }`
- [ ] Function invocation
- [ ] Local variables in functions
- [ ] Return values from functions

### Very Hard Features (Multiple days)

#### Control Structures
- [ ] `if`/`then`/`else`/`fi`
- [ ] `while`/`do`/`done` loops
- [ ] `for` loops (both C-style and in-list style)
- [ ] `case`/`esac` statements
- [ ] `break` and `continue`
- [ ] `test` or `[` command for conditionals

#### Arithmetic Expansion
- [ ] `$((...))` arithmetic evaluation
- [ ] Basic operators (+, -, *, /, %, **)
- [ ] Comparison operators (<, >, <=, >=, ==, !=)
- [ ] Logical operators (&&, ||, !)
- [ ] Variable references in arithmetic
- [ ] C-style increment/decrement (++, --)

#### Advanced Expansions
- [ ] Brace expansion (`{a,b,c}`, `{1..10}`)
- [x] Tilde expansion (`~`, `~user`)
- [ ] Advanced parameter expansion:
  - [ ] `${var#pattern}` - Remove shortest prefix
  - [ ] `${var##pattern}` - Remove longest prefix
  - [ ] `${var%pattern}` - Remove shortest suffix
  - [ ] `${var%%pattern}` - Remove longest suffix
  - [ ] `${var/pattern/replacement}` - Pattern substitution
  - [ ] `${#var}` - String length
- [ ] Process substitution (`<(...)`, `>(...)`)

#### Script Support
- [ ] Execute .psh scripts from files
- [ ] Shebang (`#!/usr/bin/env psh`) support
- [ ] Script arguments ($0, $@, etc.)
- [ ] `set` options:
  - [ ] `-e` (errexit) - Exit on error
  - [ ] `-u` (nounset) - Error on undefined variables
  - [ ] `-x` (xtrace) - Print commands before execution
  - [ ] `-o pipefail` - Pipeline fails if any command fails
- [ ] `trap` command for signal handling
- [ ] `exit` with cleanup

#### Interactive Enhancements
- [ ] Tab completion for commands
- [x] Tab completion for files/directories
- [ ] Programmable completion
- [ ] Syntax highlighting in prompt
- [ ] Multi-line command editing with PS2
- [ ] Custom prompts (PS1, PS2, PS3, PS4)
- [x] Vi/Emacs key bindings (set -o vi/emacs)
- [x] Command line editing shortcuts (Ctrl-A/E, Ctrl-K/U, Ctrl-R for history search, etc.)

## Implementation Priorities

### Next Features to Implement

1. **Job control basics** - Start with jobs tracking and notifications
2. **Simple control structures** - Start with `if`/`then`/`else`
3. **Basic arithmetic expansion** - `$((...))` 
4. **Shell functions** - Function definition and invocation

### Architecture Considerations

#### Lessons from && and || Implementation
- Grammar changes can require AST restructuring
- Backward compatibility important for existing tests
- Short-circuit evaluation requires careful exit status tracking
- Operator precedence affects grammar design

#### For Control Structures
- Need to extend AST significantly
- Consider separate parsing mode for multi-line constructs
- May need lookahead in tokenizer

#### For Job Control
- Need job table data structure
- Process group management is crucial
- Signal handling becomes more complex

#### For Advanced Expansions
- Order of expansions matters (follow POSIX)
- Need careful quote handling
- Some expansions happen at different phases

### Testing Strategy

- Unit tests for each component (tokenizer, parser, executor)
- Integration tests comparing with bash output
- Edge case testing for each feature
- Performance testing for recursive features

### Learning Resources

- POSIX Shell specification
- Bash source code for implementation details
- "The Linux Programming Interface" for process management
- "Advanced Programming in the Unix Environment" for system calls