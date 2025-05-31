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
case_stmt    → 'case' word 'in' case_item* 'esac'
case_item    → pattern_list ')' command_list [';;' | ';&' | ';;&']
pattern_list → pattern ('|' pattern)*
pattern      → WORD | STRING | VARIABLE

# Loop control
break_stmt   → 'break'
continue_stmt → 'continue'

# Command lists and pipelines
command_list → and_or_list (';' and_or_list)* [';']
and_or_list  → pipeline (('&&' | '||') pipeline)*
             | break_stmt | continue_stmt
pipeline     → command ('|' command)*

# Commands and arguments
command      → word+ redirect* ['&']
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

# Install psh locally (in development mode)
pip install -e .

# After installation, run directly
psh
psh -c "echo hello"
psh --help   # Show usage and options

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
- Basic command execution with external commands and built-ins
- I/O redirections (<, >, >>, 2>, 2>>, 2>&1, <<<)
- Multiple commands (;) and background execution (&)
- Quoted strings (single and double) with proper variable expansion
- Built-ins: exit, cd, export, pwd, echo, unset, env, source, ., history, set, declare, return, jobs, fg, bg, alias, unalias, test, [, true, false, :
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
- Here documents (<< and <<-) and here strings (<<<)
- Stderr redirection (2>, 2>>, 2>&1)
- Command substitution ($(...) and `...`) with proper nesting
- Arithmetic expansion ($((...))) with full operator support
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
- Test command ([) with comprehensive string, numeric, and file operators (20+ file test operators)
- Loop constructs: while/do/done and for/in/do/done loops
- Loop control: break and continue statements
- Case statements (case/esac) with pattern matching and fallthrough control
- Pattern matching: wildcards (*), character classes ([abc], [a-z]), single character (?)
- Multiple patterns per case item (pattern1|pattern2|pattern3)
- Advanced case terminators: ;; (stop), ;& (fallthrough), ;;& (continue matching)
- Script file execution with arguments and shebang support
- Multi-line command support with line continuation (\)
- Nested control structures to arbitrary depth
- Command substitution in for loop iterables
- Brace expansion: Complete {a,b,c} list and {1..10} sequence expansion
- Process substitution: <(...) for readable and >(...) for writable file descriptors

Not implemented:
- C-style for loops (for ((i=0; i<10; i++)))
- Advanced parameter expansion beyond ${var:-default} (${var#pattern}, ${var%pattern}, etc.)
- Local variables in functions (local builtin)
- Advanced shell options (set -e, -u, -x, -o pipefail)
- Trap command for signal handling
- Advanced read builtin features (-p prompt, -s silent, -t timeout, -n chars, -d delimiter)
- Escaped glob patterns
- Array variables
- Select statement