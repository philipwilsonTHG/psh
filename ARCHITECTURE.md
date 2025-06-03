# PSH Architecture Guide

## Overview

Python Shell (psh) is designed with a clean, component-based architecture that separates concerns and makes the codebase easy to understand, test, and extend. The shell has been refactored from a monolithic design into a modular system where each component has a specific responsibility.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                              │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shell (shell.py)                           │
│                    Main Orchestrator                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Initializes: State, Managers, Components                │  │
│  │ Coordinates: Execution flow, Component lifecycle        │  │
│  │ Delegates: All actual work to specialized components    │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────┬───────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────┐                    ┌─────────────────────┐
│   Tokenizer      │                    │   Parser            │
│ (tokenizer.py)   │                    │ (parser.py)         │
│                  │                    │                     │
│ String → Tokens  │                    │ Tokens → AST        │
└──────────────────┘                    └─────────────────────┘
        │                                         │
        └────────────────────┬────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Component Managers                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ ExpansionMgr   │  │ ExecutorMgr    │  │ IOManager      │  │
│  │                │  │                │  │                │  │
│  │ • Variable     │  │ • Command      │  │ • File I/O     │  │
│  │ • Command Sub  │  │ • Pipeline     │  │ • Heredoc      │  │
│  │ • Tilde        │  │ • Control Flow │  │ • Process Sub  │  │
│  │ • Glob         │  │ • Statement    │  │                │  │
│  └────────────────┘  └────────────────┘  └────────────────┘  │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ ScriptManager  │  │ InteractiveMgr │  │ Other          │  │
│  │                │  │                │  │                │  │
│  │ • Execution    │  │ • REPL Loop    │  │ • JobManager   │  │
│  │ • Validation   │  │ • Prompt       │  │ • FunctionMgr  │  │
│  │ • Shebang      │  │ • History      │  │ • AliasManager │  │
│  │ • Source       │  │ • Completion   │  │ • BuiltinReg   │  │
│  └────────────────┘  └────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core State                                 │
│                    (core/state.py)                              │
│                                                                 │
│  • Environment variables        • Shell variables               │
│  • Positional parameters        • Function stack                │
│  • Exit codes                   • Debug flags                   │
│  • I/O streams                  • Job control state             │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Shell (Main Orchestrator)

**File**: `shell.py` (~417 lines)

The Shell class is the main entry point and orchestrator. It:
- Initializes all component managers
- Provides the public API (`run_command`, `run_script`, `interactive_loop`)
- Delegates execution to appropriate components
- Manages the overall lifecycle

```python
class Shell:
    def __init__(self, ...):
        # Initialize state
        self.state = ShellState(...)
        
        # Initialize managers
        self.expansion_manager = ExpansionManager(self)
        self.io_manager = IOManager(self)
        self.executor_manager = ExecutorManager(self)
        self.script_manager = ScriptManager(self)
        self.interactive_manager = InteractiveManager(self)
        
        # Initialize other components
        self.alias_manager = AliasManager()
        self.function_manager = FunctionManager()
        self.job_manager = JobManager(self)
        self.builtin_registry = BuiltinRegistry()
```

### 2. Core State Management

**Directory**: `core/`

#### ShellState (`core/state.py`)
Centralized state management for the entire shell:
- Environment variables (`env`)
- Shell variables (`variables`)
- Positional parameters (`positional_params`)
- Execution state (exit codes, process info)
- Configuration (debug flags, RC file settings)

#### Exceptions (`core/exceptions.py`)
Shell-specific exceptions:
- `LoopBreak`: For break statements
- `LoopContinue`: For continue statements
- `ShellError`: Base exception class

### 3. Execution System

**Directory**: `executor/`

The execution system is responsible for executing the parsed AST.

#### ExecutorManager (`executor/base.py`)
Routes execution requests to appropriate executor components:
- `CommandExecutor`: Single commands
- `PipelineExecutor`: Command pipelines
- `ControlFlowExecutor`: Control structures
- `StatementExecutor`: Statement lists

#### CommandExecutor (`executor/command.py`)
Executes single commands:
- Variable assignments (VAR=value)
- Built-in commands
- Shell functions
- External commands
- Process forking and job control

#### PipelineExecutor (`executor/pipeline.py`)
Handles command pipelines:
- Creates pipes between processes
- Manages process groups
- Handles job control for pipelines
- Supports background execution

#### ControlFlowExecutor (`executor/control_flow.py`)
Executes control structures:
- `if`/`then`/`else`/`fi`
- `while`/`do`/`done`
- `for`/`in`/`do`/`done`
- `case`/`esac` with pattern matching
- `break` and `continue` statements
- Enhanced test `[[ ]]`

#### StatementExecutor (`executor/statement.py`)
Handles statement lists and logical operators:
- Command lists (`;` separator)
- AND lists (`&&` operator)
- OR lists (`||` operator)
- Top-level script execution

### 4. Expansion System

**Directory**: `expansion/`

The expansion system handles all shell expansions in the correct order.

#### ExpansionManager (`expansion/manager.py`)
Orchestrates expansions in POSIX order:
1. Brace expansion (handled by tokenizer)
2. Tilde expansion
3. Parameter/variable expansion
4. Command substitution
5. Arithmetic expansion
6. Word splitting
7. Pathname expansion (globbing)
8. Quote removal

#### Component Expanders
- **VariableExpander** (`variable.py`): `$var`, `${var}`, special parameters
- **CommandSubstitution** (`command_sub.py`): `$(...)` and `` `...` ``
- **TildeExpander** (`tilde.py`): `~` and `~user`
- **GlobExpander** (`glob.py`): `*`, `?`, `[...]` patterns

### 5. I/O Redirection System

**Directory**: `io_redirect/`

Handles all forms of I/O redirection.

#### IOManager (`io_redirect/manager.py`)
Central manager for all I/O operations:
- Coordinates redirection handlers
- Manages file descriptor manipulation
- Handles cleanup

#### Redirection Handlers
- **FileRedirector** (`file_redirect.py`): `<`, `>`, `>>`, `2>`, `2>&1`, etc.
- **HeredocHandler** (`heredoc.py`): `<<`, `<<-`, `<<<`
- **ProcessSubstitutionHandler** (`process_sub.py`): `<(...)`, `>(...)`

### 6. Interactive Features

**Directory**: `interactive/`

Provides all interactive shell features.

#### InteractiveManager (`interactive/base.py`)
Coordinates interactive components:
- REPL loop
- Prompt management
- History
- Tab completion
- Signal handling

#### Interactive Components
- **REPLLoop** (`repl_loop.py`): Main read-eval-print loop
- **PromptManager** (`prompt_manager.py`): PS1/PS2 expansion
- **HistoryManager** (`history_manager.py`): Command history with persistence
- **CompletionManager** (`completion_manager.py`): Tab completion
- **SignalManager** (`signal_manager.py`): SIGINT, SIGCHLD, etc.

### 7. Script Handling

**Directory**: `scripting/`

Handles script execution and sourcing.

#### ScriptManager (`scripting/base.py`)
Coordinates script-related operations:
- Script file execution
- Source command
- RC file loading

#### Script Components
- **ScriptExecutor** (`script_executor.py`): Executes script files
- **ScriptValidator** (`script_validator.py`): Validates scripts
- **ShebangHandler** (`shebang_handler.py`): Processes `#!` lines
- **SourceProcessor** (`source_processor.py`): Implements source/`.` command

### 8. Built-in Commands

**Directory**: `builtins/`

Built-in commands organized by category.

#### BuiltinRegistry (`builtins/registry.py`)
Central registry for all built-ins:
- Registration system
- Lookup mechanism
- Help system integration

#### Built-in Categories
- **Core** (`core.py`): `exit`, `:`, `true`, `false`
- **Navigation** (`navigation.py`): `cd`, `pwd`
- **Environment** (`environment.py`): `export`, `unset`, `env`, `set`
- **I/O** (`io.py`): `echo`, `read`, `printf`
- **Job Control** (`job_control.py`): `jobs`, `fg`, `bg`
- **Aliases** (`aliases.py`): `alias`, `unalias`
- **Functions** (`function_support.py`): `return`, function helpers
- **Shell State** (`shell_state.py`): `set`, `declare`
- **Test Command** (`test_command.py`): `test`, `[`

### 9. Other Components

#### JobManager (`job_control.py`)
Manages background jobs:
- Job creation and tracking
- Process group management
- Terminal control
- Job state notifications

#### FunctionManager (`functions.py`)
Manages shell functions:
- Function definition and storage
- Function lookup
- Function execution support

#### AliasManager (`aliases.py`)
Handles command aliases:
- Alias definition and expansion
- Recursive alias resolution
- Trailing space handling

## Data Flow

### Command Execution Flow

1. **Input** → Shell receives command string
2. **Tokenization** → Tokenizer converts to token stream
3. **Parsing** → Parser builds AST from tokens
4. **Pre-execution**:
   - Alias expansion (if interactive)
   - Heredoc collection
5. **Execution** → ExecutorManager routes to appropriate executor:
   - Single command → CommandExecutor
   - Pipeline → PipelineExecutor
   - Control structure → ControlFlowExecutor
   - Statement list → StatementExecutor
6. **Expansion** → ExpansionManager handles all expansions
7. **I/O Setup** → IOManager sets up redirections
8. **Process Execution**:
   - Built-in → Direct execution
   - Function → Function body execution
   - External → Fork/exec with job control
9. **Cleanup** → Restore I/O, update job state
10. **Result** → Return exit status

### State Management

All components share state through `ShellState`:
- Read access: Direct property access
- Write access: Through setter methods
- Consistency: Single source of truth

### Component Communication

Components communicate through:
1. **Manager References**: Components hold references to needed managers
2. **Shell Reference**: For accessing other components when needed
3. **State Sharing**: Through centralized ShellState
4. **Exceptions**: For control flow (LoopBreak, LoopContinue, FunctionReturn)

## Extension Points

### Adding a New Built-in

1. Create a new class inheriting from `Builtin`
2. Implement `name` property and `execute` method
3. Register in `BuiltinRegistry`

```python
# In builtins/mybuiltin.py
class MyBuiltin(Builtin):
    @property
    def name(self):
        return "mycommand"
    
    def execute(self, args, shell):
        # Implementation
        return 0  # Exit code
```

### Adding a New Expansion

1. Create expander class in `expansion/`
2. Add to `ExpansionManager`
3. Call from appropriate expansion phase

### Adding a Control Structure

1. Add AST node in `ast_nodes.py`
2. Add parsing in `parser.py`
3. Add execution in `ControlFlowExecutor`

## Testing Strategy

The component architecture enables isolated testing:

1. **Unit Tests**: Test individual components
   - Expanders with mock shell
   - Executors with mock state
   - Managers with mock dependencies

2. **Integration Tests**: Test component interactions
   - Command execution flow
   - Pipeline execution
   - I/O redirection

3. **System Tests**: Test complete shell behavior
   - Script execution
   - Interactive sessions
   - Job control

## Performance Considerations

1. **Lazy Loading**: Components initialized only when needed
2. **State Caching**: Frequently accessed state cached
3. **Minimal Indirection**: Direct component access where possible
4. **Efficient Algorithms**: O(1) lookups for builtins, functions, aliases

## Future Improvements

1. **Plugin System**: Dynamic component loading
2. **Async Execution**: Non-blocking command execution
3. **Remote Execution**: SSH-like capabilities
4. **Advanced Debugging**: Step-through execution
5. **Performance Monitoring**: Built-in profiling