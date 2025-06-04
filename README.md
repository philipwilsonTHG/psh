# Python Shell (psh)

An educational Unix shell implementation in Python, designed to teach shell internals and compiler/interpreter concepts through a clean, readable codebase.

## Overview

Python Shell (psh) is a POSIX-style shell written entirely in Python. It uses a hand-written recursive descent parser for clarity and educational value, making it easy to understand how shells parse and execute commands.

The shell features a modern component-based architecture where each subsystem (execution, expansion, I/O, etc.) is cleanly separated into its own module. This makes the codebase easy to understand, test, and extend. See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

## Features

### Core Shell Features

- ✅ **Command Execution**
  - External command execution with arguments
  - Multiple commands (`;` separator)
  - Background processes (`&`)
  - Script execution with shebang support
  
- ✅ **I/O Redirection**
  - Input redirection (`<`)
  - Output redirection (`>`, `>>`)
  - Stderr redirection (`2>`, `2>>`, `2>&1`)
  - Here documents (`<<`, `<<-`)
  - Here strings (`<<<`)
  - File descriptor manipulation

- ✅ **Pipes and Pipelines**
  - Full pipeline support (`cmd1 | cmd2 | cmd3`)
  - Proper process group management
  - Signal propagation
  
- ✅ **Variable Expansion**
  - Environment variables (`$VAR`)
  - Shell variables (separate from environment)
  - Special variables (`$?`, `$$`, `$!`, `$#`, `$@`, `$*`, `$0`)
  - Positional parameters (`$1`, `$2`, ...)
  - Basic parameter expansion (`${VAR}`, `${VAR:-default}`)
  - **Advanced parameter expansion** with all bash features:
    - String length: `${#var}`, `${#}`, `${#*}`, `${#@}`
    - Pattern removal: `${var#pattern}`, `${var##pattern}`, `${var%pattern}`, `${var%%pattern}`
    - Pattern substitution: `${var/pattern/replacement}`, `${var//pattern/replacement}`, etc.
    - Substring extraction: `${var:offset}`, `${var:offset:length}`
    - Variable name matching: `${!prefix*}`, `${!prefix@}`
    - Case modification: `${var^}`, `${var^^}`, `${var,}`, `${var,,}`
  
- ✅ **Command Substitution**
  - Modern syntax: `$(command)`
  - Legacy syntax: `` `command` ``
  - Nested substitution support
  - Works within double-quoted strings
  
- ✅ **Arithmetic Expansion**
  - Full arithmetic evaluation: `$((expression))`
  - All standard operators: `+`, `-`, `*`, `/`, `%`, `**`
  - Comparison operators: `<`, `>`, `<=`, `>=`, `==`, `!=`
  - Logical operators: `&&`, `||`, `!`
  - Bitwise operators: `&`, `|`, `^`, `~`, `<<`, `>>`
  - Assignment operators: `=`, `+=`, `-=`, etc.
  
- ✅ **Brace Expansion**
  - List expansion: `{a,b,c}`
  - Sequence expansion: `{1..10}`, `{a..z}`
  - Nested expansions: `{a,b}{1,2}`
  - Proper handling of escaped braces and special characters
  
- ✅ **Process Substitution**
  - Input process substitution: `<(command)`
  - Output process substitution: `>(command)`
  
- ✅ **Pattern Matching**
  - Wildcards/globbing (`*`, `?`, `[...]`)
  - Character classes (`[a-z]`, `[!abc]`)
  - Quote handling to prevent expansion

### Programming Constructs

- ✅ **Control Structures**
  - `if`/`then`/`else`/`elif`/`fi` conditional statements with command substitution
  - `while`/`do`/`done` loops
  - `for`/`in`/`do`/`done` loops with brace and glob expansion
  - `case`/`esac` pattern matching with command substitution
  - `break` and `continue` statements with multi-level support (`break 2`)
  
- ✅ **Functions**
  - POSIX syntax: `name() { commands; }`
  - Bash syntax: `function name { commands; }`
  - Function parameters and local scope
  - `local` builtin for function-scoped variables (v0.29.0)
  - Advanced parameter expansion with string manipulation (v0.29.2)
  - `return` builtin
  - `declare -f` to list functions
  - `unset -f` to remove functions
  
- ✅ **Test Command**
  - `[` builtin with full operator support
  - String comparisons: `=`, `!=`, `-z`, `-n`
  - Numeric comparisons: `-eq`, `-ne`, `-lt`, `-le`, `-gt`, `-ge`
  - File tests: `-e`, `-f`, `-d`, `-r`, `-w`, `-x`, `-s`, etc.
  - Logical operators: `-a`, `-o`, `!`

### Interactive Features

- ✅ **Line Editing**
  - Vi and Emacs key bindings (`set -o vi/emacs`)
  - Command history with persistence (`~/.psh_history`)
  - History navigation with arrow keys
  - Multi-line command editing
  
- ✅ **Tab Completion**
  - File and directory completion
  - Handles spaces and special characters
  - Shows multiple matches when ambiguous
  - Hidden file support
  
- ✅ **Prompt Customization**
  - PS1 (primary) and PS2 (continuation) prompts
  - Escape sequences: `\u`, `\h`, `\w`, `\t`, `\$`, etc.
  - Command (`\#`) and history (`\!`) numbers
  - ANSI color support with `\[` and `\]`
  - Multi-line command detection
  
- ✅ **Job Control**
  - Background job execution (`&`)
  - Job suspension (Ctrl-Z)
  - Job management (`jobs`, `fg`, `bg`)
  - Job specifications (`%1`, `%+`, `%-`, `%string`)
  - Process group management
  - Background job notifications

### Built-in Commands

- **Core**: `exit`, `cd`, `pwd`, `echo`, `true`, `false`, `:`
- **Variables**: `export`, `unset`, `set`, `declare`, `env`, `local`
- **Job Control**: `jobs`, `fg`, `bg`
- **Functions**: `return`, `source`, `.`
- **Aliases**: `alias`, `unalias`
- **Test**: `test`, `[`, `[[`
- **History**: `history`
- **I/O**: `read`

### Additional Features

- ✅ **Comments** - `#` at word boundaries
- ✅ **Aliases** - Command aliases with recursive expansion
- ✅ **RC File** - `~/.pshrc` startup configuration
- ✅ **Tilde Expansion** - `~` and `~user`
- ✅ **Conditional Execution** - `&&` and `||` operators
- ✅ **Signal Handling** - SIGINT, SIGTSTP, SIGCHLD

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/psh.git
cd psh

# Install in development mode
pip install -e .

# Install test dependencies
pip install -r requirements-dev.txt
```

## Usage

### Interactive Mode

```bash
# Run directly
psh

# With options
psh --norc              # Skip ~/.pshrc
psh --rcfile custom_rc  # Use custom RC file
```

### Execute Commands

```bash
# Single command
psh -c "echo hello world"

# Script file
psh script.sh

# With debugging
psh --debug-ast -c "echo test"      # Show parsed AST
psh --debug-tokens -c "echo test"   # Show tokens

# Debug options can be toggled at runtime:
$ set -o debug-ast                  # Enable AST debugging
$ set -o debug-tokens               # Enable token debugging
$ set -o                            # Show all options
```

## Examples

### Basic Usage

```bash
# Commands and pipelines
$ ls -la | grep python | wc -l
$ find . -name "*.py" | xargs grep "TODO"

# Variables and expansions
$ name="World"
$ echo "Hello, ${name}!"
$ echo "Current directory: $(pwd)"
$ echo "2 + 2 = $((2 + 2))"

# Control structures
$ if [ -f /etc/passwd ]; then
>   echo "Password file exists"
> fi

$ for file in *.txt; do
>   echo "Processing $file"
> done

# Multi-level break/continue
$ for i in 1 2 3; do
>   for j in a b c; do
>     if [ "$i$j" = "2b" ]; then
>       break 2  # Break out of both loops
>     fi
>     echo "$i$j"
>   done
> done

# Functions with local variables
$ greet() {
>   local name=$1
>   echo "Hello, ${name}!"
> }
$ greet "Python Shell"
```

### Advanced Features

```bash
# Process substitution
$ diff <(ls dir1) <(ls dir2)
$ tee >(wc -l) >(grep error) < logfile

# Brace expansion
$ echo {1..5}
$ mkdir -p project/{src,tests,docs}
$ cp file.{txt,bak}

# Case statements with command substitution
$ case $(uname) in
>   Linux)  echo "Running on Linux" ;;
>   Darwin) echo "Running on macOS" ;;
>   *)      echo "Unknown OS" ;;
> esac

# Job control
$ long_command &
[1] 12345
$ jobs
[1]+ Running    long_command
$ fg %1
```

### Prompt Customization

```bash
# Colored prompt with git branch
export PS1='\[\e[32m\]\u@\h\[\e[0m\]:\[\e[34m\]\w\[\e[0m\]\$ '

# Two-line prompt with time
export PS1='\[\e[33m\][\t]\[\e[0m\] \u@\h:\w\n\$ '

# Show command and history numbers
export PS1='[\!:\#] \$ '

# Continuation prompt
export PS2='\[\e[33m\]... \[\e[0m\]'
```

## Grammar

The shell implements a comprehensive grammar supporting modern shell features:

```
# Top-level structure
program      → statement*
statement    → function_def | control_structure | command_list

# Function definitions
function_def → WORD '(' ')' compound_command
             | 'function' WORD ['(' ')'] compound_command

# Control structures
control_structure → if_stmt | while_stmt | for_stmt | case_stmt
if_stmt      → 'if' command_list 'then' command_list 
               ['elif' command_list 'then' command_list]* 
               ['else' command_list] 'fi'
while_stmt   → 'while' command_list 'do' command_list 'done'
for_stmt     → 'for' WORD 'in' word_list 'do' command_list 'done'
case_stmt    → 'case' word 'in' case_item* 'esac'
case_item    → pattern_list ')' command_list terminator
terminator   → ';;' | ';&' | ';;&'

# Commands
command_list → and_or_list (';' and_or_list)* [';']
and_or_list  → pipeline (('&&' | '||') pipeline)*
pipeline     → command ('|' command)*
command      → simple_command | compound_command
simple_command → word* redirect*
compound_command → '{' command_list '}'

# Words and expansions
word         → WORD | STRING | expansion
expansion    → variable | command_sub | arith_exp | brace_exp | proc_sub
variable     → '$' (NAME | '{' NAME [':' '-' word] '}' | special_var)
command_sub  → '$(' command_list ')' | '`' command_list '`'
arith_exp    → '$((' arithmetic_expression '))'
brace_exp    → '{' brace_list '}' | '{' range '}'
proc_sub     → '<(' command_list ')' | '>(' command_list ')'

# Redirections
redirect     → [fd] redirect_op target
redirect_op  → '<' | '>' | '>>' | '2>' | '2>>' | '>&' | '<<' | '<<-' | '<<<'
```

## Architecture

The shell follows a classic three-phase interpreter architecture:

1. **Tokenization** (`psh/tokenizer.py`)
   - Lexical analysis
   - Token recognition
   - Quote and escape handling
   
2. **Parsing** (`psh/parser.py`)
   - Recursive descent parser
   - AST construction
   - Syntax validation
   
3. **Execution** (`psh/shell.py`)
   - AST interpretation
   - Process management
   - Built-in implementation

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_parser.py -v
python -m pytest tests/test_control_structures.py -v
python -m pytest tests/test_multiline.py -v

# Run with coverage
python -m pytest tests/ --cov=psh --cov-report=html
```

## Project Structure

```
psh/
├── psh/
│   ├── __init__.py
│   ├── shell.py           # Main shell implementation
│   ├── tokenizer.py       # Lexical analysis
│   ├── parser.py          # Syntax analysis
│   ├── ast_nodes.py       # AST definitions
│   ├── multiline_handler.py # Multi-line input handling
│   ├── prompt.py          # Prompt expansion
│   ├── line_editor.py     # Line editing (vi/emacs)
│   ├── tab_completion.py  # Tab completion
│   ├── job_control.py     # Job management
│   ├── functions.py       # Function management
│   ├── aliases.py         # Alias management
│   ├── arithmetic.py      # Arithmetic evaluation
│   ├── brace_expansion.py # Brace expansion
│   └── builtins/          # Built-in commands
├── tests/                 # Comprehensive test suite
├── docs/                  # Documentation
└── examples/              # Example scripts
```

## Known Limitations

While PSH implements most shell features, there are some architectural limitations:

- **Control structures in pipelines**: Control structures (while, for, if, case) cannot be used as part of pipelines. For example, `echo "data" | while read line; do echo $line; done` will not parse. Use the control structure to wrap the pipeline instead.
- **Deep recursion in functions**: Recursive shell functions using command substitution hit Python's recursion limit quickly. For example, recursive factorial with `$(factorial $((n-1)))` fails for small values. Use iterative algorithms instead. See [docs/recursion_depth_analysis.md](docs/recursion_depth_analysis.md) for details.
- **C-style for loops**: Not implemented - use traditional `for var in list` syntax
- **Advanced parameter expansion**: ✅ **Fully implemented** (v0.29.2) - All bash string manipulation features supported
- **Arrays**: Not implemented - use space-separated strings instead

See TODO.md for a complete list of unimplemented features.

## Contributing

This is an educational project designed to be clear and understandable. When contributing:

- Maintain code clarity over cleverness
- Add comments explaining complex logic
- Include tests for new features
- Update documentation
- Follow existing code patterns

## License

MIT License - see LICENSE file for details

## Acknowledgments

This project was created as an educational tool to understand shell internals. It draws inspiration from traditional Unix shells while prioritizing readability and educational value.