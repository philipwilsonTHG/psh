# Python Shell (psh)

An educational Unix shell implementation in Python, designed to teach shell internals and compiler/interpreter concepts through a clean, readable codebase.

## Overview

Python Shell (psh) is a POSIX-style shell written entirely in Python. It uses a hand-written recursive descent parser for clarity and educational value, making it easy to understand how shells parse and execute commands.

## Features

### Currently Implemented

- ✅ **Command Execution**
  - Basic command execution with arguments
  - Multiple commands (`;` separator)
  - Background processes (`&`)
  
- ✅ **I/O Redirection**
  - Input redirection (`<`)
  - Output redirection (`>`, `>>`)
  - Stderr redirection (`2>`, `2>>`, `2>&1`)
  - Here documents (`<<`, `<<-`)

- ✅ **Pipes and Pipelines**
  - Full pipeline support (`cmd1 | cmd2 | cmd3`)
  - Proper process group management
  
- ✅ **Variable Expansion**
  - Environment variables (`$VAR`)
  - Shell variables (separate from environment)
  - Special variables (`$?`, `$$`, `$!`, `$#`, `$@`, `$*`, `$0`)
  - Positional parameters (`$1`, `$2`, ...)
  - Parameter expansion (`${VAR}`, `${VAR:-default}`)
  
- ✅ **Command Substitution**
  - Modern syntax: `$(command)`
  - Legacy syntax: `` `command` ``
  - Nested substitution support
  
- ✅ **Pattern Matching**
  - Wildcards/globbing (`*`, `?`, `[...]`)
  - Quote handling to prevent expansion

- ✅ **Comments**
  - Hash (`#`) starts a comment at word boundaries
  - Everything after `#` is ignored
  - Preserved in quotes and when escaped (`\#`)
  
- ✅ **Tab Completion**
  - File and directory completion
  - Handles spaces and special characters
  - Shows multiple matches when ambiguous
  - Hidden file support (when explicitly requested)
  - Path navigation with `/` preservation
  
- ✅ **Built-in Commands**
  - `cd` - Change directory
  - `exit` - Exit shell
  - `export` - Export variables
  - `pwd` - Print working directory
  - `echo` - Print arguments
  - `env` - Display environment
  - `unset` - Remove variables
  - `source` - Execute commands from file
  - `history` - Command history
  - `set` - Set positional parameters
  - `cat` - Concatenate files
  - `version` - Display shell version
  - `alias`/`unalias` - Manage command aliases
  - `declare` - Declare variables and functions
  - `return` - Return from function
  - `jobs` - List active jobs
  - `fg` - Bring job to foreground
  - `bg` - Resume job in background
  
- ✅ **Interactive Features**
  - Command history with persistence
  - Exit status in prompt
  - Signal handling (Ctrl-C, Ctrl-Z)
  - Vi and Emacs key bindings (`set -o vi/emacs`)
  
- ✅ **Job Control**
  - Background job execution (`&`)
  - Job suspension (Ctrl-Z)
  - Job management (`jobs`, `fg`, `bg`)
  - Job specifications (`%1`, `%+`, `%-`, `%string`)
  - Process group management
  - Background job completion notifications
  
- ✅ **Functions**
  - POSIX syntax: `name() { commands; }`
  - Bash syntax: `function name { commands; }`
  - Function parameters and local scope
  - `declare -f` to list functions
  - `unset -f` to remove functions
  - `return` builtin
  
- ✅ **Aliases**
  - Command aliases with `alias` builtin
  - Recursive alias expansion
  - Trailing space for continued expansion
  - `unalias` to remove aliases
  
- ✅ **Conditional Execution**
  - AND operator (`&&`) - run if previous succeeded
  - OR operator (`||`) - run if previous failed
  - Short-circuit evaluation
  
- ✅ **Additional Features**
  - Tilde expansion (`~`, `~user`)
  - Here strings (`<<<`)
  - Command line editing with history navigation

### Not Yet Implemented

- ❌ Control structures (`if`, `while`, `for`)
- ❌ Advanced expansions (arithmetic, brace)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/psh.git
cd psh

# Install development dependencies (for testing)
pip install -r requirements-dev.txt
```

## Usage

### Interactive Mode

```bash
python3 simple_shell.py
```

### Execute Single Command

```bash
python3 simple_shell.py "ls -la | grep python"
```

### Execute Command with -c Flag

```bash
python3 simple_shell.py -c "echo hello world"
```

## Examples

```bash
# Basic commands
$ ls -la
$ cd /usr/local
$ pwd

# I/O redirection
$ echo "Hello, World!" > output.txt
$ cat < input.txt
$ ls /nonexistent 2> errors.txt
$ command > output.txt 2>&1

# Pipelines
$ ls -la | grep python | wc -l
$ cat file.txt | sort | uniq

# Variables
$ export PATH=/usr/local/bin:$PATH
$ echo "Home is $HOME"
$ echo "Exit status: $?"

# Command substitution
$ echo "Today is $(date)"
$ files=`ls *.txt`

# Wildcards
$ ls *.py
$ rm temp?.txt
$ cat [abc]*.log

# Here documents
$ cat << EOF
Line 1
Line 2
EOF
```

## Architecture

The shell follows a classic three-phase interpreter architecture:

1. **Tokenization** (`tokenizer.py`)
   - Converts input strings into tokens
   - Handles operators, quotes, and special characters
   
2. **Parsing** (`parser.py`)
   - Builds an Abstract Syntax Tree (AST)
   - Uses recursive descent parsing
   - One function per grammar rule
   
3. **Execution** (`simple_shell.py`)
   - Interprets the AST
   - Manages processes and I/O
   - Implements built-in commands

## Grammar

```
command_list → pipeline (SEMICOLON pipeline)* [SEMICOLON]
pipeline     → command (PIPE command)*
command      → word+ redirect* [AMPERSAND]
redirect     → REDIRECT_OP word
word         → WORD | STRING | VARIABLE | COMMAND_SUB
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_parser.py -v

# Run with coverage
python -m pytest tests/ --cov=.
```

## Development

### Project Structure

```
psh/
├── simple_shell.py      # Main shell implementation
├── tokenizer.py         # Lexical analysis
├── parser.py           # Syntax analysis
├── ast_nodes.py        # AST node definitions
├── tests/              # Test suite
│   ├── test_tokenizer.py
│   ├── test_parser.py
│   └── ...
└── docs/               # Documentation
    └── command_substitution_strategy.md
```

### Adding New Features

1. Update the tokenizer if new tokens are needed
2. Extend the parser to handle new syntax
3. Implement execution logic in the shell
4. Add comprehensive tests
5. Update documentation

## Contributing

This is an educational project designed to be clear and understandable. When contributing:

- Maintain code clarity over cleverness
- Add comments explaining complex logic
- Include tests for new features
- Update documentation

## License

MIT License - see LICENSE file for details

## Acknowledgments

This project was created as an educational tool to understand shell internals. It draws inspiration from traditional Unix shells while prioritizing readability and educational value.