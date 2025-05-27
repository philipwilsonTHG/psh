# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Shell (psh) is an educational Unix shell implementation designed for teaching shell internals and compiler/interpreter concepts. It uses a hand-written recursive descent parser for clarity and educational value.

## Architecture

The shell follows a three-phase architecture:

1. **Tokenization** (`tokenizer.py`): Converts input strings into tokens, handling operators, quotes, and variables
2. **Parsing** (`parser.py`): Builds an AST using recursive descent, with one function per grammar rule
3. **Execution** (`simple_shell.py`): Interprets the AST, executing commands and managing I/O

Key design principle: Each component is intentionally simple and readable for teaching purposes.

## Grammar

```
command_list → and_or_list (SEMICOLON and_or_list)* [SEMICOLON]
and_or_list  → pipeline ((AND_AND | OR_OR) pipeline)*
pipeline     → command (PIPE command)*
command      → word+ redirect* [AMPERSAND]
redirect     → REDIRECT_OP word
word         → WORD | STRING | VARIABLE
```

## Running the Project

```bash
# Run parser demonstration (shows tokenization and AST)
python3 demo.py

# Start interactive shell
python3 simple_shell.py

# Execute single command
python3 simple_shell.py "ls -la"

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
- I/O redirections (<, >, >>, 2>, 2>>, 2>&1)
- Multiple commands (;)
- Background execution (&)
- Quoted strings and variable expansion
- Built-ins: exit, cd, export, pwd, echo, unset, env, source, history, set, cat
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
- Here documents (<< and <<-)
- Stderr redirection (2>, 2>>, 2>&1)
- Command substitution ($(...) and `...`)
- Tab completion for files and directories
- Comments (# at word boundaries)
- Conditional execution (&& and || operators with short-circuit evaluation)
- Tilde expansion (~ and ~user)

Not implemented:
- Job control (fg, bg, jobs commands)
- Control structures (if, while, for)
- Command substitution
- Advanced expansions (brace, tilde, parameter)