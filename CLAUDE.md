# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Shell (psh) is an educational Unix shell implementation designed for teaching shell internals and compiler/interpreter concepts. It uses a hand-written recursive descent parser for clarity and educational value.

## Architecture

The shell follows a component-based architecture with clear separation of concerns:

### Core Pipeline
1. **Tokenization** (`tokenizer.py`): Converts input strings into tokens
2. **Parsing** (`parser.py`): Builds an AST using recursive descent
3. **Execution** (component-based): Interprets the AST through specialized managers

### Component Organization

#### Main Orchestrator
- **`shell.py`** (~417 lines): Central orchestrator that coordinates all components
  - Initializes and manages component lifecycle
  - Provides unified API for command execution
  - Delegates actual work to specialized managers

#### Core Components
- **`core/`**: Shared state and exceptions
  - `state.py`: Centralized shell state (variables, environment, settings)
  - `exceptions.py`: Shell-specific exceptions (LoopBreak, LoopContinue)

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

#### Other Components
- **`builtins/`**: Built-in commands organized by category
  - `registry.py`: Central builtin registry
  - `core.py`: Core builtins (exit, :, true, false)
  - `navigation.py`: Directory navigation (cd, pwd)
  - `environment.py`: Environment management (export, unset, env)
  - `io.py`: I/O builtins (echo, read, printf)
  - `job_control.py`: Job control (jobs, fg, bg)
  - `aliases.py`: Alias management
  - `test_command.py`: Test/[ command implementation
- **`utils/`**: Utility modules
  - `ast_formatter.py`: AST pretty-printing
  - `token_formatter.py`: Token formatting
  - `file_tests.py`: File test utilities

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

# Debug options can also be toggled at runtime:
set -o debug-ast        # Enable AST debug output
set -o debug-tokens     # Enable token debug output
set +o debug-ast        # Disable AST debug output
set +o debug-tokens     # Disable token debug output
set -o                  # Show current option settings

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
- Command substitution ($(...) and `...`) with proper nesting, including within double quotes
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
- Loop control: break and continue statements with multi-level support (break 2, continue 3)
- Case statements (case/esac) with pattern matching and fallthrough control
- Pattern matching: wildcards (*), character classes ([abc], [a-z]), single character (?)
- Multiple patterns per case item (pattern1|pattern2|pattern3)
- Advanced case terminators: ;; (stop), ;& (fallthrough), ;;& (continue matching)
- Script file execution with arguments and shebang support
- Multi-line command support with line continuation (\)
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

Not implemented:
- C-style for loops (for ((i=0; i<10; i++)))
- Advanced parameter expansion beyond ${var:-default} (${var#pattern}, ${var%pattern}, etc.)
- Local variables in functions (local builtin) - **Implementation planned, see docs/local_variables_implementation_plan.md**
- Advanced shell options (set -e, -u, -x, -o pipefail)
- Trap command for signal handling
- Advanced read builtin features (-p prompt, -s silent, -t timeout, -n chars, -d delimiter)
- Escaped glob patterns
- Array variables
- Select statement
- Control structures in pipelines (architectural limitation - see TODO.md)