# PSH Architecture Guide

## Overview

Python Shell (psh) is designed with a clean, component-based architecture that separates concerns and makes the codebase easy to understand, test, and extend. The shell follows a traditional interpreter pipeline: lexing → parsing → expansion → execution, with each phase carefully designed for educational clarity and correctness.

**Current Version**: 0.68.0 (as of 2025-07-02)

**Note:** For LLM-optimized architecture documentation, see `ARCHITECTURE.llm`

**Key Architectural Features**:
- **Modular Executor Package** (v0.68.0): Visitor pattern with 9 specialized executor modules
- **Modular Parser Package** (v0.60.0): Delegation-based parser with 8 focused modules
- **Modular Lexer Package** (v0.58.0): State machine lexer with clean component separation
- **Multi-phase Expansion**: POSIX-compliant expansion ordering
- **Component-based Design**: Each subsystem has clear boundaries and responsibilities

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                              │
└─────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Input Processing                             │
│                                                                 │
│  Line Continuation → History Expansion → Brace Expansion       │
└─────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Lexical Analysis (Tokenization)                 │
│                   State Machine Lexer                           │
│                                                                 │
│  Character Stream → Finite State Machine → Rich Token Stream   │
└─────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Syntactic Analysis (Parsing)                 │
│                 Modular Parser Package (v0.60.0)                │
│                                                                 │
│  Token Stream → Delegation Architecture → Abstract Syntax Tree │
└─────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Execution                               │
│              Visitor Pattern Executor (Default)                 │
│                                                                 │
│  AST Traversal → Expansion → Command Execution → Exit Status   │
└─────────────────────────────────────────────────────────────────┘
```

## Phase 1: Input Processing

Before tokenization begins, several preprocessing steps occur:

### 1.1 Line Continuation Processing
**File**: `input_preprocessing.py`

Handles POSIX-compliant line continuations (`\<newline>`):
```bash
echo "This is a very \
long line that continues"
```

The preprocessor:
- Scans for backslash-newline sequences
- Preserves them inside single quotes
- Removes them elsewhere
- Maintains line number tracking for error reporting

### 1.2 History Expansion
**File**: `history_expansion.py`

Processes history expansions before tokenization:
- `!!` - Previous command
- `!n` - Command number n
- `!-n` - n commands ago
- `!string` - Most recent command starting with string

Context-aware to avoid expansion in quotes and certain contexts.

### 1.3 Brace Expansion
**File**: `expansion/brace_expansion.py`

Expands brace patterns before tokenization:
- List expansion: `{a,b,c}` → `a b c`
- Sequence expansion: `{1..10}` → `1 2 3 4 5 6 7 8 9 10`
- Nested expansion: `{a,b{1,2}}` → `a b1 b2`

This happens early because it can create multiple tokens from a single pattern.

## Phase 2: Lexical Analysis (Tokenization)

The lexer converts character streams into meaningful tokens using a state machine approach.

### 2.1 Lexer Package Architecture
**Package**: `psh/lexer/`

The lexer is implemented as a modular package with clean separation of concerns:

- **`psh/lexer/core.py`** - Main StateMachineLexer class
- **`psh/lexer/helpers.py`** - LexerHelpers mixin with utility methods
- **`psh/lexer/state_handlers.py`** - StateHandlers mixin with state machine logic
- **`psh/lexer/constants.py`** - All lexer constants and character sets
- **`psh/lexer/unicode_support.py`** - Unicode character classification
- **`psh/lexer/token_parts.py`** - TokenPart and RichToken classes
- **`psh/lexer/position.py`** - Position tracking, error handling, and lexer configuration
- **`psh/lexer/__init__.py`** - Clean public API

The main lexer uses mixin classes for code organization:
```python
class StateMachineLexer(LexerHelpers, StateHandlers):
    """State machine-based lexer combining helper methods and state handlers"""
```

### 2.2 State Machine Architecture

The lexer uses a finite state machine with these states:
```python
class LexerState(Enum):
    NORMAL = "NORMAL"
    IN_WORD = "IN_WORD"
    IN_SINGLE_QUOTE = "IN_SINGLE_QUOTE"
    IN_DOUBLE_QUOTE = "IN_DOUBLE_QUOTE"
    IN_BACKQUOTE = "IN_BACKQUOTE"
    IN_COMMENT = "IN_COMMENT"
    AFTER_DOLLAR = "AFTER_DOLLAR"
    IN_VARIABLE = "IN_VARIABLE"
    IN_COMMAND_SUB = "IN_COMMAND_SUB"
    IN_ARITHMETIC = "IN_ARITHMETIC"
    IN_PARAM_EXPANSION = "IN_PARAM_EXPANSION"
```

### 2.3 Rich Token System
**Files**: `token_types.py`, `psh/lexer/token_parts.py`

The lexer produces `RichToken` objects that maintain metadata:
```python
@dataclass
class TokenPart:
    """Component of a composite token"""
    value: str
    type: str  # 'literal', 'variable', 'command_sub', etc.
    quote_context: Optional[str]  # Which quotes it was in

@dataclass
class RichToken:
    """Token with rich metadata"""
    type: TokenType
    value: str
    parts: List[TokenPart]  # Components for COMPOSITE tokens
    position: int
    original_quotes: Optional[str]
```

### 2.4 Modular Design Benefits

The package structure provides several advantages:
- **Separation of Concerns**: Helper methods, state handlers, constants, and core logic are cleanly separated
- **Mixin Architecture**: Combines functionality from multiple mixins for extensibility
- **Unicode Support**: Dedicated module for Unicode character classification and POSIX compatibility
- **Maintainability**: Clean modular design with focused components
- **Clean API**: Direct imports from `psh.lexer` package with no compatibility layers needed

### 2.5 Context-Aware Tokenization

The lexer handles context-sensitive tokenization:
- `<` and `>` are operators inside `[[ ]]`, redirections elsewhere
- Keywords like `in` are recognized only in appropriate contexts
- Operators are recognized using length-based lookup for efficiency
- Quote information is preserved for proper expansion later

### 2.6 Composite Token Handling

Adjacent string-like tokens become COMPOSITE tokens:
```bash
echo "hello"world'!' → COMPOSITE["hello", world, '!']
```

This preserves quote information for each part, enabling correct expansion behavior.

## Phase 3: Syntactic Analysis (Parsing)

The parser converts tokens into an Abstract Syntax Tree (AST) using a modular delegation architecture.

### 3.1 Parser Package Architecture (v0.60.0)
**Package**: `psh/parser/`

The parser is implemented as a modular package with clean separation of concerns:

- **`psh/parser/main.py`** - Main Parser class with delegation orchestration
- **`psh/parser/commands.py`** - Command and pipeline parsing  
- **`psh/parser/statements.py`** - Statement list and control flow parsing
- **`psh/parser/control_structures.py`** - All control structures (if, while, for, case, select)
- **`psh/parser/tests.py`** - Enhanced test expression parsing with regex support
- **`psh/parser/arithmetic.py`** - Arithmetic command and expression parsing
- **`psh/parser/redirections.py`** - I/O redirection parsing
- **`psh/parser/arrays.py`** - Array initialization and assignment parsing
- **`psh/parser/functions.py`** - Function definition parsing
- **`psh/parser/utils.py`** - Utility functions and heredoc handling
- **`psh/parser/base.py`** - Base parser class with token management (moved from parser_base.py)
- **`psh/parser/helpers.py`** - Helper classes and token groups (moved from parser_helpers.py)
- **`psh/parser/__init__.py`** - Clean public API with backward compatibility

### 3.2 Delegation Architecture

The main parser orchestrates specialized parsers through delegation:
```python
class Parser(BaseParser):
    """Main parser with delegation to specialized parsers"""
    def __init__(self, tokens: List[Token]):
        super().__init__(tokens)
        # Initialize specialized parsers
        self.commands = CommandParser(self)
        self.statements = StatementParser(self)
        self.control_structures = ControlStructureParser(self)
        # ... other specialized parsers
```

### 3.3 Grammar Overview

The shell grammar (simplified):
```
top_level    → statement*
statement    → function_def | control_structure | command_list

control_structure → if_stmt | while_stmt | for_stmt | case_stmt | select_stmt
command_list → and_or_list (';' and_or_list)* [';']
and_or_list  → pipeline (('&&' | '||') pipeline)*
pipeline     → command ('|' command)*
command      → simple_command | compound_command

simple_command → word+ redirect* ['&']
compound_command → control_structure redirect* ['&']
```

### 3.4 Modular Design Benefits

The package structure provides several advantages:
- **Separation of Concerns**: Each parser module handles a focused aspect of shell syntax
- **Delegation Architecture**: Clean component interaction through main parser orchestration
- **Enhanced Maintainability**: Smaller, focused files easier to understand and modify
- **Improved Testability**: Each component can be tested in isolation
- **Backward Compatibility**: Existing parser API is fully preserved
- **Extensibility**: New parsing features can be added incrementally

### 3.5 Recursive Descent Implementation

Each grammar rule has a corresponding parse method across specialized parsers:
```python
# In ControlStructureParser
def parse_if_statement(self):
    """Parse if/then/else/fi statement"""
    # Delegate to control structure parser
    
# In CommandParser  
def parse_command(self):
    """Parse simple command with arguments"""
    # Delegate to command parser
```

### 3.6 AST Node Hierarchy
**File**: `ast_nodes.py`

The AST uses a clean class hierarchy:
```python
# Base classes
class ASTNode: pass
class Statement(ASTNode): pass
class Command(ASTNode): pass

# Commands (can appear in pipelines)
class SimpleCommand(Command): 
    args: List[str]
    redirects: List[Redirect]
    background: bool

class CompoundCommand(Command):
    # Control structures as commands (v0.37.0)
    pass

# Control structures
class WhileLoop(Statement, CompoundCommand):
    condition: StatementList
    body: StatementList
    redirects: List[Redirect]

class IfConditional(Statement, CompoundCommand):
    condition: StatementList
    then_stmt: StatementList
    elif_parts: List[Tuple[StatementList, StatementList]]
    else_stmt: Optional[StatementList]
```

### 3.7 Error Recovery

The parser provides helpful error messages with enhanced context:
```python
def _error(self, message: str) -> ParseError:
    """Create ParseError with current context"""
    error_context = ErrorContext(
        token=self.peek(),
        message=message,
        position=self.peek().position
    )
    return ParseError(error_context)
```

## Phase 4: Execution

The execution phase traverses the AST and performs the actual work.

### 4.1 Modular Executor Package Architecture (v0.68.0)
**Directory**: `executor/`

As of v0.68.0, the executor uses a modular package architecture with specialized executors:

#### Package Structure
```
executor/
├── __init__.py          # Public API exports
├── core.py              # Main ExecutorVisitor (542 lines, down from ~2000)
├── command.py           # Simple command execution with strategies
├── pipeline.py          # Pipeline execution and process management  
├── control_flow.py      # Control structures (if, loops, case, select)
├── array.py             # Array initialization and element operations
├── function.py          # Function definition and execution
├── subshell.py          # Subshell and brace group execution
├── context.py           # ExecutionContext state management
└── strategies.py        # Command type execution strategies
```

#### Core Architecture
```python
class ExecutorVisitor(ASTVisitor[int]):
    """Main executor that delegates to specialized components"""
    
    def __init__(self, shell: Shell):
        super().__init__()
        self.shell = shell
        self.context = ExecutionContext()
        
        # Initialize specialized executors
        self.command_executor = CommandExecutor(shell)
        self.pipeline_executor = PipelineExecutor(shell) 
        self.control_flow_executor = ControlFlowExecutor(shell)
        self.array_executor = ArrayOperationExecutor(shell)
        self.function_executor = FunctionOperationExecutor(shell)
        self.subshell_executor = SubshellExecutor(shell)
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> int:
        # Delegate to CommandExecutor
        return self.command_executor.execute(node, self.context)
    
    def visit_Pipeline(self, node: Pipeline) -> int:
        # Delegate to PipelineExecutor
        return self.pipeline_executor.execute(node, self.context, self)
```

#### Execution Context
```python
@dataclass
class ExecutionContext:
    """Encapsulates execution state for cleaner parameter passing"""
    in_pipeline: bool = False
    in_subshell: bool = False
    in_forked_child: bool = False
    loop_depth: int = 0
    current_function: Optional[str] = None
    pipeline_context: Optional[PipelineContext] = None
    background_job: Optional[Job] = None
```

### 4.2 Specialized Executors

#### CommandExecutor
Handles simple command execution with the Strategy pattern:
```python
class CommandExecutor:
    def __init__(self, shell: Shell):
        self.strategies = [
            BuiltinExecutionStrategy(),
            FunctionExecutionStrategy(),
            ExternalExecutionStrategy()
        ]
    
    def execute(self, node: SimpleCommand, context: ExecutionContext) -> int:
        # Expand arguments
        # Extract assignments
        # Find appropriate strategy
        # Execute command
```

#### PipelineExecutor
Manages pipeline execution with process forking and pipe management:
```python
class PipelineExecutor:
    def execute(self, node: Pipeline, context: ExecutionContext, 
                visitor: ASTVisitor[int]) -> int:
        # Create pipes
        # Fork processes
        # Set up process groups
        # Manage job control
        # Wait for completion
```

#### ControlFlowExecutor
Handles all control structures:
- If/elif/else conditionals
- While and for loops (including C-style)
- Case statements
- Select loops
- Break and continue statements

#### FunctionOperationExecutor
Manages function definition and execution:
```python
class FunctionOperationExecutor:
    def execute_function_call(self, name: str, args: List[str], 
                             context: ExecutionContext,
                             visitor: ASTVisitor[int]) -> int:
        # Set up positional parameters
        # Manage function stack
        # Execute function body
        # Handle return builtin
```

### 4.3 Command Execution Strategy Pattern

The CommandExecutor uses strategies for different command types:

```python
class ExecutionStrategy(ABC):
    @abstractmethod
    def can_execute(self, cmd_name: str, shell: Shell) -> bool:
        pass
    
    @abstractmethod
    def execute(self, cmd_name: str, args: List[str], 
                shell: Shell, context: ExecutionContext) -> int:
        pass

class BuiltinExecutionStrategy(ExecutionStrategy):
    # Handles builtin commands

class FunctionExecutionStrategy(ExecutionStrategy):
    # Handles shell functions

class ExternalExecutionStrategy(ExecutionStrategy):
    # Handles external commands with fork/exec
```

### 4.4 Pipeline Execution

Pipeline execution is handled by the PipelineExecutor:

```python
def _execute_pipeline(self, node: Pipeline, context: ExecutionContext,
                     visitor: ASTVisitor[int]) -> int:
    if len(node.commands) == 1:
        # Single command optimization
        return visitor.visit(node.commands[0])
    
    # Multi-command pipeline
    pipeline_ctx = PipelineContext(self.job_manager)
    
    # Create pipes
    for i in range(len(node.commands) - 1):
        pipeline_ctx.add_pipe()
    
    # Fork processes for each command
    for i, command in enumerate(node.commands):
        pid = os.fork()
        if pid == 0:
            # Child: set up pipes and execute
            self._setup_pipeline_redirections(i, pipeline_ctx)
            exit_status = visitor.visit(command)
            os._exit(exit_status)
        else:
            # Parent: track process
            pipeline_ctx.add_process(pid)
    
    # Create job and wait for completion
    job = self.job_manager.create_job(pgid, command_string)
    return self._wait_for_foreground_pipeline(job, node)
```

### 4.5 Benefits of Modular Architecture

The refactored executor package provides:

1. **Separation of Concerns**: Each executor handles one aspect of execution
2. **Reduced Complexity**: Core visitor reduced from ~2000 to 542 lines (73% reduction)
3. **Improved Testability**: Isolated components with clear interfaces
4. **Better Maintainability**: Focused modules easier to understand and modify
5. **Extensibility**: New execution features can be added to specific modules
6. **Clean Delegation**: Main visitor coordinates specialized executors

### 4.6 Execution Statistics

- **Original ExecutorVisitor**: ~1994 lines in single file
- **Refactored Package**: 9 modules with clear responsibilities
- **Code Reduction**: 73% in core module
- **New Architecture**: Strategy pattern for commands, delegation for all operations

## Phase 5: Expansion

Expansions happen during execution in POSIX-specified order.

### 5.1 Expansion Manager
**File**: `expansion/manager.py`

Orchestrates all expansions in the correct order:

```python
def expand_argument(self, arg: str, arg_type: str) -> List[str]:
    """Expand a single argument following POSIX rules"""
    # 1. Tilde expansion (if unquoted)
    if should_expand_tilde(arg, arg_type):
        arg = self.tilde_expander.expand(arg)
    
    # 2. Parameter/variable expansion
    arg = self.variable_expander.expand(arg)
    
    # 3. Command substitution
    arg = self.expand_command_substitution(arg)
    
    # 4. Arithmetic expansion
    arg = self.expand_arithmetic(arg)
    
    # 5. Word splitting (if unquoted)
    if should_split(arg, arg_type):
        words = self.split_words(arg)
    else:
        words = [arg]
    
    # 6. Pathname expansion (if unquoted)
    expanded = []
    for word in words:
        if should_glob(word, arg_type):
            expanded.extend(self.glob_expander.expand(word))
        else:
            expanded.append(word)
    
    # 7. Quote removal
    return [self.remove_quotes(w) for w in expanded]
```

### 5.2 Variable Expansion
**Files**: `expansion/variable.py`, `expansion/parameter_expansion.py`

Handles all forms of variable expansion:
- Simple: `$var`, `${var}`
- Special parameters: `$?`, `$$`, `$!`, `$#`, `$@`, `$*`
- Positional: `$1`, `$2`, etc.
- Advanced parameter expansion:
  - Length: `${#var}`
  - Substring: `${var:offset:length}`
  - Pattern removal: `${var#pattern}`, `${var%pattern}`
  - Substitution: `${var/pattern/replacement}`
  - Case modification: `${var^^}`, `${var,,}`

### 5.3 Command Substitution
**File**: `expansion/command_sub.py`

Executes commands and captures output:
```python
def expand_command_substitution(self, text: str) -> str:
    """Expand $(...) and `...` in text"""
    # Create subshell with inherited state
    subshell = Shell(parent_shell=self.shell)
    
    # Execute command and capture output
    output = subshell.run_command(command, capture_output=True)
    
    # Strip trailing newlines
    return output.rstrip('\n')
```

### 5.4 Arithmetic Expansion
**File**: `arithmetic.py`

Evaluates arithmetic expressions:
```python
def expand_arithmetic(self, text: str) -> str:
    """Expand $((...)) in text"""
    # Extract expression
    expr = text[3:-2]  # Remove $(( and ))
    
    # Evaluate using arithmetic subsystem
    result = evaluate_arithmetic(expr, self.shell)
    
    return str(result)
```

## Phase 6: I/O Redirection

I/O redirections are applied around command execution.

### 6.1 Redirection Manager
**File**: `io_redirect/manager.py`

Manages all forms of redirection:
```python
def apply_redirections(self, redirects: List[Redirect]) -> Dict[int, int]:
    """Apply redirections and return saved file descriptors"""
    saved_fds = {}
    
    for redirect in redirects:
        if redirect.type == '>':
            # Output redirection
            fd = redirect.source_fd or 1
            saved_fds[fd] = os.dup(fd)
            target_fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            os.dup2(target_fd, fd)
            os.close(target_fd)
        # ... handle other redirection types
    
    return saved_fds
```

### 6.2 Here Documents
**File**: `io_redirect/heredoc.py`

Here documents create temporary files:
```python
def setup_heredoc(self, delimiter: str, content: str, strip_tabs: bool) -> int:
    """Create a temporary file with heredoc content"""
    if strip_tabs:
        # Remove leading tabs from each line
        lines = content.splitlines()
        content = '\n'.join(line.lstrip('\t') for line in lines)
    
    # Create temporary file
    fd, path = tempfile.mkstemp()
    os.write(fd, content.encode())
    os.close(fd)
    
    # Open for reading
    return os.open(path, os.O_RDONLY)
```

### 6.3 Process Substitution
**File**: `io_redirect/process_sub.py`

Creates pipes to/from processes:
```python
def setup_process_substitution(self, command: str, mode: str) -> str:
    """Set up <(...) or >(...) and return /dev/fd/N path"""
    if mode == 'read':
        # <(...) - reading from command output
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            # Child: redirect stdout to pipe
            os.close(read_fd)
            os.dup2(write_fd, 1)
            os.close(write_fd)
            # Execute command
            self.shell.run_command(command)
            sys.exit(0)
        else:
            # Parent: return read end
            os.close(write_fd)
            return f"/dev/fd/{read_fd}"
```

## Component Communication

### State Management
**Files**: `core/state.py`, `core/scope.py`

All components share state through a centralized `ShellState` object:
- Environment variables
- Shell variables with scope management
- Positional parameters
- Process information
- Debug flags
- Shell options

### Manager Pattern

Components are organized as managers that coordinate related functionality:
- `ExpansionManager` - All expansions
- `IOManager` - All I/O operations
- `ExecutorManager` - Command execution (legacy)
- `InteractiveManager` - Interactive features
- `ScriptManager` - Script execution

### Exception-Based Control Flow

Special exceptions handle control flow:
- `LoopBreak` - Break statement
- `LoopContinue` - Continue statement  
- `FunctionReturn` - Return from function
- `SystemExit` - Exit shell

## Performance Considerations

### Efficient Tokenization
- State machine minimizes backtracking
- Length-based operator lookup
- Minimal string concatenation

### Optimized Parsing
- Single-pass recursive descent
- Minimal lookahead
- Efficient token consumption

### Smart Expansion
- Lazy evaluation where possible
- Caching of expanded values
- Minimal subprocess creation

### Visitor Pattern Benefits
- Direct method dispatch via method cache
- No intermediate representations
- Minimal object allocation

## Educational Value

The architecture prioritizes clarity and correctness:
- Each phase is clearly separated
- Algorithms follow standard compiler techniques
- Code is heavily documented
- Complex features are broken into understandable pieces

## Recent Architectural Improvements

### Version 0.60.0 - Parser Package Refactoring
- Transformed monolithic 1806-line parser.py into modular package structure
- Created 8 focused parser modules with clean separation of concerns
- Delegation-based architecture enabling clean component interaction
- Enhanced test expression parser with complete operator precedence
- Fixed C-style for loop parsing with proper arithmetic section handling
- Fixed stderr redirection parsing to separate operator from file descriptor
- Maintained 100% backward compatibility with existing parser API

### Version 0.50.0 - Visitor Pattern Default
- Visitor executor now the primary execution model
- Cleaner separation between AST and operations
- Better extensibility for future enhancements

### Version 0.37.0-0.38.0 - Unified Command Model
- Control structures can be used in pipelines
- Single type system for all commands
- Removed deprecated dual types

### Version 0.28.x - Component Refactoring
- Reduced monolithic shell.py by 85%
- Created logical component organization
- Improved testability and maintainability

## Known Limitations

1. **Deep Recursion**: Command substitution in recursive functions can hit Python's stack limit due to the multiple layers of function calls per shell recursion level.

2. **Command Substitution Output Capture**: Issues in pytest environments due to complex interaction between pytest's capture mechanism and subshell creation.

3. **Composite Token Quote Loss**: Parser creates COMPOSITE tokens but loses some quote information from RichTokens.

## Future Enhancements

1. **Optimization Visitors**: Performance analysis and optimization passes
2. **Security Visitors**: Static security analysis
3. **Transformation Visitors**: Code modernization and refactoring
4. **Enhanced Error Recovery**: Continue parsing after errors
5. **Incremental Parsing**: Reparse only changed portions
6. **Parallel Execution**: Execute independent commands concurrently