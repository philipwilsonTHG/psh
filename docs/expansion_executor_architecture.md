# PSH Expansion and Executor Architecture

## Table of Contents

1. [Overview](#overview)
2. [Expansion System](#expansion-system)
   - [Expansion Manager](#expansion-manager)
   - [Expansion Order](#expansion-order)
   - [Individual Expanders](#individual-expanders)
   - [Special Cases](#special-cases)
3. [Executor System](#executor-system)
   - [Architecture](#architecture)
   - [Executor Components](#executor-components)
   - [Process Management](#process-management)
   - [I/O Redirection](#io-redirection)
4. [Execution Flow](#execution-flow)
5. [Debugging](#debugging)

## Overview

PSH (Python Shell) implements a complete Unix shell with a sophisticated expansion and execution system. The architecture separates concerns between:

- **Expansion**: Transforming shell syntax into executable arguments
- **Execution**: Running commands with proper process management

This document describes the current implementation as of version 0.43.0.

## Expansion System

The expansion system transforms shell input into executable arguments following POSIX shell semantics.

### Expansion Manager

The `ExpansionManager` (`psh/expansion/manager.py`) orchestrates all expansions. It's initialized with a reference to the shell and manages individual expanders:

```python
class ExpansionManager:
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize individual expanders
        self.variable_expander = VariableExpander(shell)
        self.command_sub = CommandSubstitution(shell)
        self.tilde_expander = TildeExpander(shell)
        self.glob_expander = GlobExpander(shell)
```

### Expansion Order

PSH follows the POSIX shell expansion order:

1. **Brace Expansion** - Handled by the tokenizer (e.g., `{a,b,c}`, `{1..5}`)
2. **Tilde Expansion** - Home directory expansion (`~`, `~user`)
3. **Variable Expansion** - Variables and parameters (`$VAR`, `${VAR}`)
4. **Command Substitution** - Command output (`$(cmd)`, `` `cmd` ``)
5. **Arithmetic Expansion** - Math expressions (`$((2+2))`)
6. **Word Splitting** - Split unquoted expansions on whitespace
7. **Pathname Expansion** - Glob patterns (`*.txt`, `file?`)
8. **Quote Removal** - Remove quotes after processing

### Individual Expanders

#### Variable Expander (`variable.py`)

Handles all variable and parameter expansions:

**Basic Variables:**
```bash
$VAR              # Simple variable
${VAR}            # Braced variable
${#VAR}           # Length of variable
```

**Special Variables:**
```bash
$?                # Last exit status
$$                # Shell PID
$!                # Last background PID
$#                # Number of positional parameters
$@                # All positional parameters (array-like)
$*                # All positional parameters (string)
$0                # Script/shell name
$1, $2, ...       # Positional parameters
```

**Parameter Expansion:**
```bash
${VAR:-default}   # Use default if VAR unset/null
${VAR:=default}   # Assign default if VAR unset/null
${VAR:?error}     # Error if VAR unset/null
${VAR:+alt}       # Use alt if VAR is set

${VAR#pattern}    # Remove shortest prefix match
${VAR##pattern}   # Remove longest prefix match
${VAR%pattern}    # Remove shortest suffix match
${VAR%%pattern}   # Remove longest suffix match

${VAR/old/new}    # Replace first occurrence
${VAR//old/new}   # Replace all occurrences
${VAR/#old/new}   # Replace if at start
${VAR/%old/new}   # Replace if at end

${VAR:offset}     # Substring from offset
${VAR:offset:len} # Substring with length

${VAR^}           # Uppercase first character
${VAR^^}          # Uppercase all characters
${VAR,}           # Lowercase first character
${VAR,,}          # Lowercase all characters

${!prefix*}       # Variable names starting with prefix
${!prefix@}       # Variable names starting with prefix (array-safe)
```

**Arrays:**
```bash
# Indexed arrays
${arr[0]}         # Element at index 0
${arr[@]}         # All elements (array-like)
${arr[*]}         # All elements (string)
${#arr[@]}        # Number of elements
${!arr[@]}        # Array indices
${arr[@]:1:2}     # Slice from index 1, length 2

# Associative arrays
declare -A assoc
${assoc[key]}     # Element with key
${assoc[@]}       # All values
${!assoc[@]}      # All keys
```

#### Command Substitution (`command_sub.py`)

Executes commands and captures output:

```bash
$(command)        # Modern syntax
`command`         # Legacy backtick syntax
$(command1 | command2)  # Pipelines work
$(
    multi
    line
    command
)                 # Multi-line supported
```

**Key Features:**
- Strips trailing newlines from output
- Handles nested substitutions
- Creates subshell for execution
- Preserves parent shell state

#### Tilde Expander (`tilde.py`)

Expands home directory references:

```bash
~                 # Current user's home
~/file            # File in home directory  
~user             # Specific user's home
~user/file        # File in user's home
~+                # Current directory (PWD)
~-                # Previous directory (OLDPWD)
```

**Rules:**
- Only expands at start of word
- Only in unquoted contexts
- Stops at first `/`

#### Glob Expander (`glob.py`)

Expands pathname patterns:

```bash
*                 # Match any characters
?                 # Match single character
[abc]             # Match any character in set
[a-z]             # Match character in range
[!abc]            # Match any character NOT in set
[^abc]            # Same as [!abc]
```

**Features:**
- Hidden files (starting with `.`) not matched by `*` unless pattern starts with `.`
- No matches returns pattern literally (nullglob not implemented)
- Sorted results for consistency

#### Arithmetic Expansion

Evaluates mathematical expressions:

```bash
$((expression))   # Arithmetic expansion
((expression))    # Arithmetic command
```

**Supported Operations:**
- Basic: `+`, `-`, `*`, `/`, `%` (modulo), `**` (power)
- Bitwise: `&`, `|`, `^`, `~`, `<<`, `>>`
- Comparison: `<`, `>`, `<=`, `>=`, `==`, `!=`
- Logical: `&&`, `||`, `!`
- Assignment: `=`, `+=`, `-=`, `*=`, `/=`, etc.
- Increment/Decrement: `++`, `--` (prefix and postfix)
- Ternary: `condition ? true_val : false_val`

### Special Cases

#### Composite Arguments

When the parser detects adjacent tokens, it creates composite arguments:

```bash
"hello"world      # Composite of STRING and WORD
prefix${var}suffix # Composite with variable
file[123].txt     # Composite with brackets
```

Types:
- `COMPOSITE` - Regular composite, subject to glob expansion
- `COMPOSITE_QUOTED` - Has quoted parts, no glob expansion

#### Process Substitution

Treated as a special expansion:

```bash
<(command)        # Read from command output via FIFO
>(command)        # Write to command input via FIFO
diff <(ls dir1) <(ls dir2)  # Compare directory listings
```

#### Here Strings

Variable expansion in here strings:

```bash
<<< "Hello $USER"  # Variables expanded
<<< 'Hello $USER'  # No expansion (single quotes)
```

## Executor System

The executor system runs commands after expansion, handling process management, job control, and I/O redirection.

### Architecture

Component-based design with clear separation:

```
ExecutorManager
├── CommandExecutor      # Single commands
├── PipelineExecutor     # Pipelines
├── ControlFlowExecutor  # Control structures
├── StatementExecutor    # Command lists
└── ArithmeticExecutor   # Arithmetic commands
```

Each executor inherits from `ExecutorComponent`:

```python
class ExecutorComponent(ABC):
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = shell.builtin_registry
        self.function_manager = shell.function_manager
```

### Executor Components

#### CommandExecutor (`command.py`)

Executes single commands in order of precedence:

1. **Assignments Only** - Variable/array assignments
2. **Builtins** - Internal shell commands
3. **Functions** - User-defined functions
4. **External** - System commands

**Features:**
- Temporary variable assignments: `VAR=value command`
- Array assignments: `arr=(1 2 3)` or `arr[0]=value`
- Exit status tracking
- Job control for background commands

#### PipelineExecutor (`pipeline.py`)

Handles command pipelines:

**Single Command:**
- Optimized path without creating pipes
- Handles negation: `! command`

**Multi-Command Pipeline:**
```bash
cmd1 | cmd2 | cmd3
```

Process:
1. Create N-1 pipes for N commands
2. Fork N processes
3. Connect stdout/stdin through pipes
4. Create process group for job control
5. Wait for completion (or background)

**Features:**
- `pipefail` option support
- Job control with process groups
- Proper signal handling
- Background pipeline support

#### ControlFlowExecutor (`control_flow.py`)

Executes control structures:

**Supported Structures:**
- `if/then/else/fi` - Conditionals
- `while/do/done` - While loops
- `for/do/done` - For loops (both styles)
- `case/esac` - Pattern matching
- `select` - Interactive menus
- `[[...]]` - Enhanced test
- `break/continue` - Loop control

**Features:**
- Proper exit status handling
- Break/continue with levels
- Nested structure support
- Context preservation

#### StatementExecutor (`statement.py`)

Handles command lists and logical operators:

**Command Lists:**
```bash
cmd1; cmd2; cmd3     # Sequential execution
cmd1 & cmd2 & cmd3   # Background execution
```

**Logical Operators:**
```bash
cmd1 && cmd2         # Execute cmd2 if cmd1 succeeds
cmd1 || cmd2         # Execute cmd2 if cmd1 fails
```

**Features:**
- Short-circuit evaluation
- Exit status propagation
- `errexit` option support

#### ArithmeticExecutor (`arithmetic_command.py`)

Executes arithmetic commands:

```bash
((x = 5))           # Assignment
((x++))             # Increment
((x > 5)) && echo "big"  # Conditional
```

**Exit Status:**
- 0 if expression evaluates to non-zero
- 1 if expression evaluates to zero

### Process Management

#### Fork/Exec Model

External commands use Unix fork/exec:

1. **Fork** - Create child process
2. **Setup** - In child:
   - Create new process group
   - Reset signal handlers
   - Set up I/O redirections
3. **Exec** - Replace child with command
4. **Wait** - Parent waits (or backgrounds)

#### Job Control

Full job control implementation:

**Job States:**
- `RUNNING` - Active job
- `STOPPED` - Suspended (SIGTSTP)
- `DONE` - Completed
- `TERMINATED` - Killed

**Features:**
- Job table tracking
- Process group management
- Foreground/background control
- Terminal control (tcsetpgrp)
- Signal handling (SIGCHLD, SIGTSTP, etc.)

**Commands:**
- `jobs` - List jobs
- `fg [%job]` - Bring to foreground
- `bg [%job]` - Resume in background
- `wait [pid/job]` - Wait for completion

### I/O Redirection

Managed by `IORedirectManager`:

**File Redirections:**
```bash
< file              # stdin from file
> file              # stdout to file
>> file             # stdout append
2> file             # stderr to file
2>> file            # stderr append
&> file             # stdout and stderr
>& file             # Same as &>
2>&1                # stderr to stdout
```

**Here Documents:**
```bash
<< EOF              # Here document
    content
EOF

<<- EOF             # Strip leading tabs
	content
EOF
```

**Here Strings:**
```bash
<<< "string"        # String as stdin
```

**Process Substitution:**
```bash
<(command)          # Read from command
>(command)          # Write to command
```

## Execution Flow

### Command Processing Pipeline

1. **Input** → Lexer → Tokens
2. **Tokens** → Parser → AST
3. **AST** → ExecutorManager → Component Selection
4. **Component** → Expansion → Expanded Arguments
5. **Execution** → Result/Exit Status

### Example: Pipeline Execution

For `echo "Hello $USER" | wc -l`:

1. **Parse**: Create Pipeline AST with two SimpleCommand nodes
2. **Execute Pipeline**:
   - Create pipe
   - Fork for `echo`
     - Expand `$USER`
     - Redirect stdout to pipe
     - Execute builtin echo
   - Fork for `wc`
     - Redirect stdin from pipe
     - Execute external `/usr/bin/wc`
   - Wait for both processes
3. **Return**: Exit status of last command (`wc`)

### Example: Control Flow

For `if [ -f file ]; then echo "exists"; fi`:

1. **Parse**: Create IfConditional AST
2. **Execute**:
   - Execute condition: `[ -f file ]`
   - Check exit status
   - If 0 (true): execute then-part
   - Return exit status of executed branch

## Debugging

### Current Debug Options

**Parser/Lexer:**
- `--debug-ast` - Show parsed AST
- `--debug-tokens` - Show lexer tokens
- `--debug-scopes` - Show variable scope operations

**Runtime:**
- `set -x` (xtrace) - Print commands before execution
- `set -e` (errexit) - Exit on error
- `set -u` (nounset) - Error on undefined variables

### Recommended Debug Workflow

1. **Syntax Issues**: Use `--debug-tokens` to see lexing
2. **Parsing Issues**: Use `--debug-ast` to see structure
3. **Expansion Issues**: Use `set -x` to see expanded commands
4. **Execution Issues**: Check exit status with `echo $?`
5. **Variable Issues**: Use `--debug-scopes` or `declare -p`

### Common Pitfalls

1. **Quote Handling**: Single quotes prevent all expansion
2. **Word Splitting**: Unquoted variables split on whitespace
3. **Glob Expansion**: Happens after variable expansion
4. **Exit Status**: Some builtins don't set it as expected
5. **Subshells**: Command substitution creates new shell context