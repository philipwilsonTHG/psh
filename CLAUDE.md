# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Shell (psh) is an educational Unix shell implementation designed for teaching shell internals and compiler/interpreter concepts. It uses a hand-written recursive descent parser for clarity and educational value.

## Architecture

The shell follows a three-phase architecture:

1. **Tokenization** (`tokenizer.py`): Converts input strings into tokens, handling operators, quotes, and variables
2. **Parsing** (`parser.py`): Builds an AST using recursive descent, with one function per grammar rule
3. **Execution** (`shell.py`): Interprets the AST, executing commands and managing I/O

Key design principle: Each component is intentionally simple and readable for teaching purposes.

## Grammar

```
top_level    → (statement)*
statement    → function_def | if_stmt | while_stmt | for_stmt | case_stmt | break_stmt | continue_stmt | command_list

function_def → WORD '(' ')' compound_command
             | 'function' WORD ['(' ')'] compound_command
compound_command → '{' command_list '}'

if_stmt      → 'if' command_list 'then' command_list ['else' command_list] 'fi'
while_stmt   → 'while' command_list 'do' command_list 'done'
for_stmt     → 'for' WORD 'in' word_list 'do' command_list 'done'
case_stmt    → 'case' word 'in' case_items 'esac'
case_items   → case_item*
case_item    → pattern_list ')' command_list [';;' | ';&' | ';;&']
pattern_list → pattern ('|' pattern)*
pattern      → WORD | STRING | VARIABLE
break_stmt   → 'break'
continue_stmt → 'continue'

command_list → and_or_list (SEMICOLON and_or_list)* [SEMICOLON]
and_or_list  → (pipeline | break_stmt | continue_stmt) ((AND_AND | OR_OR) pipeline)*
pipeline     → command (PIPE command)*
command      → word+ redirect* [AMPERSAND]
redirect     → REDIRECT_OP word
word         → WORD | STRING | VARIABLE | COMMAND_SUB
word_list    → word+
```

## Running the Project

```bash
# Run parser demonstration (shows tokenization and AST)
python3 demo.py

# Start interactive shell
python3 -m psh

# Execute single command
python3 -m psh -c "ls -la"

# Install psh locally (in development mode)
pip install -e .

# After installation, run directly
psh
psh -c "echo hello"

# Run tests
python -m pytest tests/
```

## Development Notes

- Test dependencies: pytest (install with `pip install -r requirements-dev.txt`)
- Comprehensive test suite covering tokenizer, parser, built-ins, and integration
- When adding features, maintain the educational clarity of the code
- Pipeline execution fully implemented using os.fork() and os.pipe()

## Current Implementation Status

Implemented:
- Basic command execution
- I/O redirections (<, >, >>, 2>, 2>>, 2>&1, <<<)
- Multiple commands (;)
- Background execution (&)
- Quoted strings and variable expansion
- Built-ins: exit, cd, export, pwd, echo, unset, env, source, history, set, declare, return, jobs, fg, bg, alias, unalias, test, [, true, false
- Wildcards/globbing (*, ?, [...])
- Exit status tracking ($? variable)
- Command history with persistence
- Pipeline execution with proper process groups
- Signal handling (SIGINT, SIGTSTP)
- Shell variables (separate from environment)
- Positional parameters ($1, $2, etc.)
- Special variables ($$, $!, $#, $@, $*, $0)
- Variable assignment (VAR=value)
- Basic parameter expansion (${var}, ${var:-default})
- Here documents (<< and <<-) and here strings (<<<)
- Stderr redirection (2>, 2>>, 2>&1)
- Command substitution ($(...) and `...`)
- Tab completion for files and directories
- Comments (# at word boundaries)
- Conditional execution (&& and || operators with short-circuit evaluation)
- Tilde expansion (~ and ~user)
- Vi and Emacs key bindings (set -o vi/emacs)
- Aliases (alias, unalias) with recursive expansion and trailing space support
- Shell functions with both POSIX (name() {}) and bash (function name {}) syntax
- Function management (declare -f, unset -f, return builtin)
- Function parameters and special variables within functions
- Job control (jobs, fg, bg commands, Ctrl-Z suspension, background job notifications)
- Job specifications (%1, %+, %-, %string)
- Process group management and terminal control
- Control structures: if/then/else/fi conditional statements
- Test command ([) with comprehensive string, numeric, and file operators (15+ file test operators)
- Loop constructs: while/do/done and for/in/do/done loops
- Loop control: break and continue statements
- Case statements (case/esac) with pattern matching and fallthrough control
- Pattern matching: wildcards (*), character classes ([abc], [a-z]), single character (?)
- Multiple patterns per case item (pattern1|pattern2|pattern3)
- Advanced case terminators: ;; (stop), ;& (fallthrough), ;;& (continue matching)
- Script file execution with arguments and shebang support

Not implemented:
- Arithmetic expansion ($((...)))
- C-style for loops (for ((i=0; i<10; i++)))
- Advanced expansions (brace expansion, advanced parameter expansion)
- Local variables in functions
- Advanced shell options (set -e, -u, -x)
- Trap command for signal handling