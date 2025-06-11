# PSH Architecture Guide

## Overview

Python Shell (psh) is designed with a clean, component-based architecture that separates concerns and makes the codebase easy to understand, test, and extend. The shell has been refactored from a monolithic design into a modular system where each component has a specific responsibility.

**Current Version**: 0.38.0 (as of 2025-01-10)

**Key Recent Additions**:
- **Major refactor v0.38.0**: Completed unified control structure types, removed all deprecated dual types
- **Revolutionary v0.37.0**: Control structures in pipelines with unified command model
- Eval builtin for dynamic command execution (v0.36.0)
- Shell options for robust scripting: set -e, -u, -x, -o pipefail (v0.35.0)
- Select statement for interactive menus (v0.34.0)
- History expansion and arithmetic command syntax (v0.33.0, v0.32.0)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                              │
└─────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shell (shell.py)                           │
│                    Main Orchestrator                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Initializes: State, Managers, Components                │    │
│  │ Coordinates: Execution flow, Component lifecycle        │    │
│  │ Delegates: All actual work to specialized components    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────┬───────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────────┐                ┌─────────────────────┐
│  State Machine       │                │   Parser            │
│  Lexer               │                │ (parser.py)         │
│ (state_machine_      │                │                     │
│  lexer.py)           │                │ Tokens → AST        │
│                      │                │                     │
│ String → RichTokens  │                └─────────────────────┘
└──────────────────────┘                          │
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
│                 (core/state.py + core/scope.py)                 │
│                                                                 │
│  • Environment variables        • Shell variables               │
│  • Variable scope stack         • Function-local variables      │
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
    def __init__(self, parent_shell=None, ...):
        # Initialize state with optional parent for subshell inheritance
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
        
        # Inherit from parent shell if specified (for command/process substitution)
        if parent_shell:
            self._inherit_from_parent(parent_shell)
```

### 2. Core State Management

**Directory**: `core/`

#### ShellState (`core/state.py`)
Centralized state management for the entire shell:
- Environment variables (`env`)
- Shell variables (managed through ScopeManager)
- Positional parameters (`positional_params`)
- Execution state (exit codes, process info)
- Configuration (debug flags, RC file settings)
- Integration with scope management for variable operations

#### ScopeManager (`core/scope.py`)
Variable scope management for function-local variables:
- Stack-based scope tracking with `VariableScope` objects
- Function-local variable support via `local` builtin
- Proper scope inheritance (locals visible to nested functions)
- Debug support with `--debug-scopes` flag
- Methods: `push_scope()`, `pop_scope()`, `get_variable()`, `set_variable()`, `create_local()`

#### Exceptions (`core/exceptions.py`)
Shell-specific exceptions:
- `LoopBreak`: For break statements
- `LoopContinue`: For continue statements
- `ShellError`: Base exception class
- `FunctionReturn`: For return builtin (added for function support)

### 3. Tokenization System

**Files**: `state_machine_lexer.py`, `token_types.py`, `token_transformer.py`

The tokenization system has been completely rewritten as a state machine lexer.

#### StateMachineLexer (`state_machine_lexer.py`)
State machine-based tokenizer that solves complex tokenization issues:
- **State-based parsing**: Uses `LexerState` enum (NORMAL, IN_WORD, IN_SINGLE_QUOTE, etc.)
- **Rich token support**: Produces `RichToken` objects with metadata about token parts
- **Composite handling**: `TokenPart` dataclass tracks components of composite tokens
- **Context awareness**: Different behavior inside `[[ ]]`, proper keyword recognition
- **Quote preservation**: Maintains quote information for proper expansion
- **Operator recognition**: Length-based lookup for efficient operator matching

#### Token Types (`token_types.py`)
Defines token types and base token classes:
- `TokenType` enum with all token categories
- `Token` dataclass for basic token representation
- Shared between lexer and parser for consistency

#### Token Transformer (`token_transformer.py`)
Context-aware token processing:
- Handles special cases like double semicolon (`;;`) outside case statements
- Token stream transformations based on parsing context

### 4. Execution System

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
Handles command pipelines with **revolutionary v0.37.0 enhancements**:
- **Unified Command Model**: Supports both SimpleCommand and CompoundCommand types
- **Control Structures in Pipelines**: All control structures can now be pipeline components
  - Examples: `echo "data" | while read line; do echo $line; done`
  - `seq 1 5 | for i in $(cat); do echo $i; done`
  - `echo "test" | if grep -q test; then echo "found"; fi`
- **Compound Command Execution**: Executes control structures in subshells with proper isolation
- **Enhanced Redirection Handling**: Proper file descriptor management for compound commands
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

### 5. Expansion System

**Directory**: `expansion/`

The expansion system handles all shell expansions in the correct order.

#### ExpansionManager (`expansion/manager.py`)
Orchestrates expansions in POSIX order:
1. Brace expansion (handled by BraceExpander before tokenization)
2. Tilde expansion
3. Parameter/variable expansion
4. Command substitution
5. Arithmetic expansion
6. Word splitting
7. Pathname expansion (globbing)
8. Quote removal

#### Component Expanders
- **VariableExpander** (`variable.py`): `$var`, `${var}`, special parameters
- **ParameterExpansion** (`parameter_expansion.py`): Advanced parameter expansion features
  - Length operations: `${#var}`, `${#}`, `${#*}`, `${#@}`
  - Pattern removal: `${var#pattern}`, `${var##pattern}`, `${var%pattern}`, `${var%%pattern}`
  - Pattern substitution: `${var/pattern/replacement}`, `${var//pattern/replacement}`
  - Substring extraction: `${var:offset}`, `${var:offset:length}`
  - Variable name matching: `${!prefix*}`, `${!prefix@}`
  - Case modification: `${var^}`, `${var^^}`, `${var,}`, `${var,,}`
- **CommandSubstitution** (`command_sub.py`): `$(...)` and `` `...` ``
- **TildeExpander** (`tilde.py`): `~` and `~user`
- **GlobExpander** (`glob.py`): `*`, `?`, `[...]` patterns
- **BraceExpander** (`brace_expansion.py`): `{a,b,c}` lists and `{1..10}` sequences

### 6. I/O Redirection System

**Directory**: `io_redirect/`

Handles all forms of I/O redirection with proper builtin support.

#### IOManager (`io_redirect/manager.py`)
Central manager for all I/O operations:
- Coordinates redirection handlers
- Manages file descriptor manipulation
- Handles cleanup
- **Builtin I/O Support**: 
  - `setup_builtin_redirections()` temporarily modifies `sys.stdout/stderr/stdin`
  - `restore_builtin_redirections()` restores original streams
  - Ensures all builtins respect redirections properly

#### Redirection Handlers
- **FileRedirector** (`file_redirect.py`): `<`, `>`, `>>`, `2>`, `2>&1`, etc.
- **HeredocHandler** (`heredoc.py`): `<<`, `<<-`, `<<<`
- **ProcessSubstitutionHandler** (`process_sub.py`): `<(...)`, `>(...)`

#### Builtin I/O Pattern
All builtins follow a consistent pattern for I/O handling:
```python
# In parent process
if hasattr(shell, 'stdout'):
    print(output, file=shell.stdout)
else:
    print(output)

# In child process (pipelines)
if shell._in_forked_child:
    os.write(1, output.encode())  # Direct to file descriptor
```

### 7. Interactive Features

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

### 8. Script Handling

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

### 9. Built-in Commands

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
- **Environment** (`environment.py`): `export`, `unset`, `env`, `set`, `local`
- **I/O** (`io.py`): `echo`, `read`, `printf`
- **Job Control** (`job_control.py`): `jobs`, `fg`, `bg`
- **Aliases** (`aliases.py`): `alias`, `unalias`
- **Functions** (`function_support.py`): `return`, function helpers
- **Shell State** (`shell_state.py`): `set`, `declare`
- **Test Command** (`test_command.py`): `test`, `[`
- **Source Command** (`source_command.py`): `source`, `.`
- **Read Builtin** (`read_builtin.py`): Advanced read functionality

### 10. Parser and AST

**Files**: `parser.py`, `ast_nodes.py`

#### Parser (`parser.py`)
Clean recursive descent parser with recent improvements:
- **TokenGroups class**: Defines semantic groups (WORD_LIKE, REDIRECTS, CONTROL_KEYWORDS)
- **Helper methods**: `skip_newlines()`, `skip_separators()`, `at_end()` for cleaner code
- **Composite arguments**: `parse_composite_argument()` handles adjacent tokens
- **Unified parsing**: Single `parse_statement()` method for all statement types
- **Enhanced test support**: `[[ ]]` constructs with compound expressions
- **Function parsing**: Both POSIX and bash syntax support
- **Error messages**: Human-readable token names in errors

#### AST Nodes (`ast_nodes.py`)
Well-organized node hierarchy:
- **Base classes**: `ASTNode`, `Statement` for type hierarchy
- **Control structures**: `IfConditional`, `WhileLoop`, `ForLoop`, `CaseConditional`, `SelectLoop`, `ArithmeticEvaluation`
- **Enhanced nodes**: Support for `elif` chains, test expressions, composite arguments
- **Statement lists**: `StatementList` allows arbitrary nesting of control structures
- **Function definitions**: `FunctionDef` with both syntaxes supported

### 11. Other Components

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

#### ArithmeticEvaluator (`arithmetic.py`)
Complete arithmetic expression evaluation:
- Separate tokenizer, parser, and evaluator subsystem
- Full operator support: arithmetic, comparison, logical, bitwise
- Advanced features: ternary (?:), assignments (+=, -=), increment/decrement
- Variable integration with shell variables
- Command substitution support within arithmetic expressions

## Data Flow

### Command Execution Flow

1. **Input** → Shell receives command string
2. **Tokenization** → Tokenizer converts to token stream
3. **Parsing** → Parser builds AST from tokens
4. **Pre-execution**:
   - Alias expansion (if interactive)
   - Heredoc collection
5. **Execution** → ExecutorManager routes to appropriate executor:
   - Simple command → CommandExecutor
   - Pipeline (SimpleCommand or CompoundCommand) → PipelineExecutor
   - Control structure statement → ControlFlowExecutor  
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

## Recent Architectural Improvements

### Version 0.37.0 - Revolutionary Unified Command Model
1. **Control Structures in Pipelines** (v0.37.0)
   - **Problem Solved**: Control structures can now be used as pipeline components
   - **Revolutionary Examples**: 
     - `echo "data" | while read line; do echo $line; done`
     - `seq 1 5 | for i in $(cat); do echo $i; done`
     - `echo "test" | if grep -q test; then echo "found"; fi`
   - **Technical Implementation**:
     - Created unified `Command` hierarchy with `SimpleCommand` and `CompoundCommand`
     - All control structures use unified types that work in both contexts
     - Enhanced parser with `parse_pipeline_component()` method
     - Updated `PipelineExecutor` to handle compound commands in subshells
     - Proper process isolation and redirection handling for compound commands
   - **Impact**: Addresses major architectural limitation, enables advanced shell programming
   - **Compatibility**: Full backward compatibility - no regressions introduced

### Version 0.36.0 - Dynamic Command Execution
1. **Eval Builtin Implementation**
   - Dynamic command execution from strings: `eval "echo hello"`
   - Full shell processing pipeline: tokenization, parsing, expansions, execution
   - Current context execution (variables and functions persist)
   - Support for all shell features: pipelines, redirections, control structures

### Version 0.35.0 - Shell Options and Robust Scripting
1. **Core Shell Options Implementation**
   - `-e` (errexit): Exit on command failure with conditional context awareness
   - `-u` (nounset): Error on undefined variables (respects parameter expansion defaults)
   - `-x` (xtrace): Print commands before execution with PS4 prefix
   - `-o pipefail`: Pipeline returns rightmost non-zero exit code
   - Centralized options storage with backward-compatible debug option migration

### Version 0.29.x Series
1. **Local Variable Support** (v0.29.0)
   - Added `ScopeManager` for function-local variables
   - Stack-based scope tracking with proper inheritance
   - Integration with all variable operations

2. **Advanced Parameter Expansion** (v0.29.2)
   - Complete bash-compatible string manipulation
   - Pattern matching with shell wildcards
   - Unicode support throughout
   - 98% test success rate

### Version 0.28.x Series
1. **State Machine Lexer** (v0.28.5-0.28.6)
   - Replaced old tokenizer with state machine implementation
   - Rich token support with metadata
   - Better quote and expansion handling
   - Improved error messages

2. **Component Refactoring** (v0.28.0)
   - Reduced shell.py from 2,712 to 417 lines (85% reduction)
   - Created logical component organization
   - Improved testability and maintainability
   - Preserved educational value

3. **Parser Improvements** (v0.28.7)
   - 30% code reduction through refactoring
   - TokenGroups for semantic token grouping
   - Cleaner recursive descent patterns

## AST Structure (v0.37.0 Unified Command Model)

### Command Hierarchy
The v0.37.0 release introduced a revolutionary unified command model that enables control structures in pipelines:

```python
# Base command class for all executable units
class Command(ASTNode):
    """Base class for all executable commands."""
    pass

# Simple commands (traditional commands)
@dataclass  
class SimpleCommand(Command):
    """Traditional command with arguments."""
    args: List[str] = field(default_factory=list)
    arg_types: List[str] = field(default_factory=list)
    quote_types: List[Optional[str]] = field(default_factory=list)
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False

# Compound commands (control structures as commands)
@dataclass
class CompoundCommand(Command):
    """Base class for control structures used as commands."""
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False

# Unified control structures (v0.38.0)
# These types work in both statement and pipeline contexts
class WhileLoop(UnifiedControlStructure):
    """Unified while loop that works in both statement and pipeline contexts."""
    condition: StatementList
    body: StatementList
    redirects: List[Redirect]
    execution_context: ExecutionContext  # STATEMENT or PIPELINE
    background: bool = False

class ForLoop(UnifiedControlStructure): ...
class IfConditional(UnifiedControlStructure): ...
class CaseConditional(UnifiedControlStructure): ...
class SelectLoop(UnifiedControlStructure): ...
class ArithmeticEvaluation(UnifiedControlStructure): ...
```

### Pipeline Support
Pipelines can now contain any Command type:
- `Pipeline.commands: List[Command]` (not just SimpleCommand)
- Parser routes via `parse_pipeline_component()` method
- PipelineExecutor handles both simple and compound commands

## Known Architectural Limitations

1. **Composite Arguments**: Parser creates COMPOSITE type but loses quote information from RichTokens
2. ~~**Control Structures in Pipelines**: Not supported due to statement-based architecture~~ ✅ **SOLVED in v0.37.0**
   - ~~**Dual Type System**: Had separate Statement/Command types for control structures~~ ✅ **REMOVED in v0.38.0**
3. **Deep Recursion**: Shell functions have recursion depth limitations

## Future Improvements

1. **Plugin System**: Dynamic component loading
2. **Async Execution**: Non-blocking command execution
3. **Remote Execution**: SSH-like capabilities
4. **Advanced Debugging**: Step-through execution
5. **Performance Monitoring**: Built-in profiling
6. **RichToken Integration**: Full utilization of token metadata in parser
7. **C-style For Loops**: Arithmetic-based iteration using existing arithmetic system