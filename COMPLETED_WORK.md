# Python Shell (psh) - Completed Work

## Phase 1: Parser Architecture Design and Implementation

### Date: May 23, 2025

### Summary
Designed and implemented a hand-written recursive descent parser for a Unix shell written in Python, optimized for readability and teaching purposes.

### Completed Components

#### 1. Design Documentation
- **DESIGN_DECISIONS.md** - Outlined 8 key design decision areas for the shell project
- **PARSER_ARCHITECTURE.md** - Detailed recommendations for recursive descent parser approach
- **README.md** - Project overview with implementation roadmap

#### 2. Core Parser Implementation

##### Tokenizer (`tokenizer.py`)
- Implemented lexical analysis with support for:
  - Basic words and operators (|, <, >, >>, ;, &)
  - Quoted strings (single and double quotes with escape handling)
  - Variable references ($VAR syntax)
  - Proper position tracking for error reporting
- Clean token stream output for parser consumption

##### AST Nodes (`ast_nodes.py`)
- Defined simple dataclass-based AST structure:
  - `CommandList` - Top-level container for multiple pipelines
  - `Pipeline` - Sequence of piped commands
  - `Command` - Individual command with args, redirects, and background flag
  - `Redirect` - I/O redirection specification

##### Parser (`parser.py`)
- Implemented recursive descent parser with:
  - One function per grammar rule
  - Clear error reporting with position information
  - Support for command lists, pipelines, redirections, and background execution
  - Proper handling of quotes and variables

#### 3. Demonstration Tools

##### Demo Script (`demo.py`)
- Interactive demonstration showing:
  - Token stream visualization
  - AST structure printing
  - Various command examples including:
    - Simple commands: `ls -la`
    - Pipelines: `cat file.txt | grep pattern | wc -l`
    - Redirections: `echo hello > output.txt`
    - Multiple commands: `echo first; echo second`
    - Background execution: `sleep 10 &`
    - Complex combinations

##### Simple Shell (`simple_shell.py`)
- Basic executor demonstrating parser usage:
  - Interactive REPL loop
  - Built-in commands: exit, cd, export
  - External command execution
  - I/O redirection support
  - Variable expansion
  - Background job launching

### Key Design Decisions Made

1. **Two-Phase Processing**: Separate tokenization and parsing for clarity
2. **Token Types**: Comprehensive set covering all basic shell operators
3. **Error Handling**: Position-aware errors with helpful messages
4. **AST Design**: Simple, teaching-friendly structure using dataclasses
5. **Parser Style**: Hand-written recursive descent for transparency

### Current Feature Set

✅ Command execution with arguments
✅ I/O redirections (<, >, >>)
✅ Semicolon-separated commands
✅ Background execution (&)
✅ Quoted strings (preserving spaces)
✅ Variable references ($VAR)
✅ Basic built-ins (cd, exit, export)
✅ Error position reporting

### Grammar Implemented

```
command_list → pipeline (SEMICOLON pipeline)* [SEMICOLON]
pipeline     → command (PIPE command)*
command      → word+ redirect* [AMPERSAND]
redirect     → REDIRECT_OP word
word         → WORD | STRING | VARIABLE
```

### Next Steps (Not Yet Implemented)

1. **Pipeline Execution** - Actual piping between processes
2. **Job Control** - Process management, fg/bg commands
3. **Advanced Expansions** - Command substitution, wildcards
4. **Control Structures** - if/then/else, loops
5. **Interactive Features** - Line editing, history, completion

### Usage

```bash
# Run parser demonstration
python3 demo.py

# Start interactive shell
python3 simple_shell.py

# Execute single command
python3 simple_shell.py "ls -la"
```

### Educational Value

The implementation prioritizes:
- Clear mapping between grammar rules and code
- Readable, well-structured Python code
- Separation of concerns (tokenizer → parser → executor)
- Extensible design for incremental feature addition
- Comprehensive error messages for debugging

This provides a solid foundation for teaching shell internals and compiler/interpreter design principles.