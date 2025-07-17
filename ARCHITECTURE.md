# PSH Architecture Guide

## Overview

Python Shell (psh) is designed with a clean, component-based architecture that separates concerns and makes the codebase easy to understand, test, and extend. The shell follows a traditional interpreter pipeline: lexing → parsing → expansion → execution, with each phase carefully designed for educational clarity and correctness.

**Current Version**: 0.91.3 (as of 2025-01-17)

**Note:** For LLM-optimized architecture documentation, see `ARCHITECTURE.llm`

**Key Architectural Features**:
- **Unified Lexer Architecture** (v0.91.3): Completed lexer deprecation plan with simplified architecture
  - **Single Token System**: Unified Token class with built-in metadata and context information
  - **Enhanced Features Standard**: All advanced features (context tracking, semantic analysis) built-in
  - **Simplified API**: 30% reduction in API surface through token class unification
  - **No Compatibility Overhead**: Single implementation path for optimal performance
- **Enhanced Parser System** (v0.85.0): Complete implementation of Parser High-Priority Plan
  - **Parser Configuration**: Comprehensive configuration system with multiple parsing modes
  - **AST Validation**: Semantic analysis and validation with symbol table management
  - **Centralized ParserContext**: Unified state management for all parser components
  - **Parse Tree Visualization**: Multiple output formats with CLI integration
  - **Advanced Error Recovery**: Smart suggestions and multi-error collection
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

### 2.1 Unified Lexer Package Architecture (v0.91.3)
**Package**: `psh/lexer/`

The lexer has undergone a comprehensive deprecation process to create a unified, simplified architecture. As of v0.91.3, the enhanced lexer features are now standard throughout PSH operation, with all compatibility code removed:

#### Core Package Structure
- **`psh/lexer/core.py`** - Main StateMachineLexer class
- **`psh/lexer/helpers.py`** - LexerHelpers mixin with utility methods
- **`psh/lexer/state_handlers.py`** - StateHandlers mixin with state machine logic
- **`psh/lexer/constants.py`** - All lexer constants and character sets
- **`psh/lexer/unicode_support.py`** - Unicode character classification
- **`psh/lexer/token_parts.py`** - TokenPart and RichToken classes
- **`psh/lexer/position.py`** - Position tracking, error handling, and lexer configuration
- **`psh/lexer/__init__.py`** - Clean public API

#### Phase 1: State Management Layer
- **`psh/lexer/state_context.py`** - Unified LexerContext for all state
- **`psh/lexer/transitions.py`** - State transition management with history tracking
- **`psh/lexer/enhanced_state_machine.py`** - Enhanced lexer with unified state

#### Phase 2: Pure Function Helpers
- **`psh/lexer/pure_helpers.py`** - 15+ stateless helper functions
- **`psh/lexer/enhanced_helpers.py`** - Wrapper maintaining existing API

#### Phase 3: Unified Parsing
- **`psh/lexer/quote_parser.py`** - Unified quote parsing with configurable rules
- **`psh/lexer/expansion_parser.py`** - All expansion types ($VAR, ${VAR}, $(...), $((...)))
- **`psh/lexer/unified_lexer.py`** - Integrates unified parsers

#### Phase 4: Token Recognition
- **`psh/lexer/recognizers/`** - Modular token recognition system
  - `base.py` - TokenRecognizer abstract interface
  - `operator.py` - Shell operators with context awareness
  - `keyword.py` - Shell keywords with position validation
  - `literal.py` - Words, identifiers, and numbers
  - `whitespace.py` - Whitespace handling
  - `comment.py` - Comment recognition
  - `registry.py` - Priority-based recognizer dispatch
- **`psh/lexer/modular_lexer.py`** - ModularLexer integrating all systems

The architecture combines all components while maintaining backward compatibility:
```python
class ModularLexer:
    """Lexer integrating all refactored components"""
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        self.position_tracker = PositionTracker(input_string)
        self.state_manager = StateManager()
        self.registry = RecognizerRegistry()
        self.expansion_parser = ExpansionParser(self.config)
        self.quote_parser = UnifiedQuoteParser(self.expansion_parser)
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

### 2.3 Unified Token System (v0.91.3)
**Files**: `token_types.py`, `psh/lexer/token_parts.py`

The lexer produces unified `Token` objects with built-in metadata and context information. Enhanced functionality has been merged into the base Token class:
```python
@dataclass
class Token:
    """Unified token class with metadata and context information (formerly EnhancedToken)."""
    type: TokenType
    value: str
    position: int
    end_position: int = 0
    quote_type: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    metadata: Optional['TokenMetadata'] = field(default=None)
    parts: Optional[List['TokenPart']] = field(default=None)
    
    def add_context(self, context: TokenContext):
        """Add context information to token metadata."""
        
    def has_context(self, context: TokenContext) -> bool:
        """Check if token has specific context."""
        
    def is_in_test_context(self) -> bool:
        """Check if token is in test expression context."""
```

### 2.4 Unified Architecture Benefits (v0.91.3)

The completed lexer deprecation plan provides numerous advantages:

#### Unified Token System
- **Single Token Class**: Token class includes metadata and enhanced functionality by default
- **Built-in Context Tracking**: All tokens have context information for semantic analysis
- **Metadata Integration**: TokenMetadata and context tracking built into every token
- **No Conversion Overhead**: Direct creation and usage without compatibility layers

#### Simplified Architecture  
- **Single Implementation Path**: Enhanced lexer features now standard throughout PSH
- **Eliminated Compatibility Code**: Removed feature flags, adapters, and dual code paths
- **30% API Reduction**: Token class unification significantly reduced API surface
- **Clean Codebase**: Focused implementation without legacy compatibility overhead

#### Enhanced Features Standard
- **Context Tracking**: Tokens know their lexical context (command position, test expression, etc.)
- **Semantic Analysis**: Built-in semantic type classification for tokens
- **Error Recovery**: Comprehensive error detection and suggestions
- **Rich Metadata**: Position, line/column tracking, and part decomposition

Overall benefits:
- **Performance**: No compatibility overhead, single optimized code path
- **Maintainability**: Simplified codebase with consistent token handling
- **Reliability**: Enhanced error detection and recovery standard for all users
- **Future Development**: Easier to add features without compatibility concerns

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

The parser converts tokens into an Abstract Syntax Tree (AST) using a modular delegation architecture with comprehensive configuration and validation systems.

### 3.1 Enhanced Parser Package Architecture (v0.85.0)
**Package**: `psh/parser/`

The parser has been significantly enhanced with a complete implementation of the Parser High-Priority Improvements Plan:

#### Core Parser Modules
- **`psh/parser/main.py`** - Main Parser class with delegation orchestration and ParserContext integration
- **`psh/parser/commands.py`** - Command and pipeline parsing  
- **`psh/parser/statements.py`** - Statement list and control flow parsing
- **`psh/parser/control_structures.py`** - All control structures (if, while, for, case, select)
- **`psh/parser/tests.py`** - Enhanced test expression parsing with regex support
- **`psh/parser/arithmetic.py`** - Arithmetic command and expression parsing
- **`psh/parser/redirections.py`** - I/O redirection parsing
- **`psh/parser/arrays.py`** - Array initialization and assignment parsing
- **`psh/parser/functions.py`** - Function definition parsing
- **`psh/parser/utils.py`** - Utility functions and heredoc handling
- **`psh/parser/base.py`** - Base parser class with token management
- **`psh/parser/base_context.py`** - New ContextBaseParser using ParserContext
- **`psh/parser/helpers.py`** - Helper classes and token groups
- **`psh/parser/__init__.py`** - Clean public API with backward compatibility

#### Parser Configuration System (v0.85.0)
- **`psh/parser/config.py`** - Comprehensive ParserConfig with 40+ configuration options
- **`psh/parser/factory.py`** - ParserFactory with preset configurations for different use cases

#### Centralized State Management (v0.85.0)
- **`psh/parser/context.py`** - ParserContext class for unified state management
- **`psh/parser/context_factory.py`** - Factory for creating contexts with different configurations
- **`psh/parser/context_snapshots.py`** - Context snapshots for backtracking and speculation

#### AST Validation System (v0.85.0)
- **`psh/parser/validation/`** - Complete validation package
  - `semantic_analyzer.py` - SemanticAnalyzer using visitor pattern
  - `validation_rules.py` - Modular validation rules system
  - `symbol_table.py` - Symbol table for semantic analysis
  - `warnings.py` - Warning system with severity levels
  - `validation_pipeline.py` - Validation orchestration

#### Parse Tree Visualization (v0.85.0)
- **`psh/parser/visualization/`** - Multi-format AST visualization
  - `ast_formatter.py` - Pretty printer for human-readable AST output
  - `dot_generator.py` - Graphviz DOT format for visual diagrams
  - `ascii_tree.py` - ASCII tree renderer for terminal display

### 3.2 Enhanced Delegation Architecture with ParserContext

The main parser orchestrates specialized parsers through delegation with centralized state management:
```python
class Parser(ContextBaseParser):
    """Main parser with delegation to specialized parsers using ParserContext"""
    def __init__(self, tokens: List[Token], config: Optional[ParserConfig] = None):
        # Create or use existing ParserContext
        self.ctx = ParserContextFactory.create(tokens, config)
        super().__init__(self.ctx)
        
        # Initialize specialized parsers with shared context
        self.commands = CommandParser(self)
        self.statements = StatementParser(self)
        self.control_structures = ControlStructureParser(self)
        self.redirections = RedirectionParser(self)
        self.arithmetic = ArithmeticParser(self)
        # ... other specialized parsers

    def parse_with_error_collection(self) -> MultiErrorParseResult:
        """Parse with enhanced error collection and recovery"""
        if self.ctx.config.collect_errors:
            # Collect multiple errors for better user experience
            return self._parse_with_recovery()
        return self.parse()
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

### 3.5 Parser Configuration System (v0.85.0)

The parser now supports comprehensive configuration for different parsing modes and behaviors:

```python
@dataclass
class ParserConfig:
    """Parser configuration with 40+ options"""
    # Parsing modes
    parsing_mode: ParsingMode = ParsingMode.BASH_COMPAT
    error_handling: ErrorHandlingMode = ErrorHandlingMode.STRICT
    
    # Feature toggles
    enable_validation: bool = False
    enable_profiling: bool = False
    collect_errors: bool = False
    
    # POSIX compliance
    strict_posix: bool = False
    allow_bash_extensions: bool = True
    
    # Error recovery
    max_errors: int = 10
    panic_mode_recovery: bool = True
    
    @classmethod
    def strict_posix(cls) -> 'ParserConfig':
        """Strict POSIX compliance mode"""
        return cls(
            parsing_mode=ParsingMode.STRICT_POSIX,
            strict_posix=True,
            allow_bash_extensions=False
        )
    
    @classmethod
    def educational(cls) -> 'ParserConfig':
        """Educational mode with enhanced error reporting"""
        return cls(
            collect_errors=True,
            enable_validation=True,
            panic_mode_recovery=True,
            max_errors=50
        )

# Factory for creating parsers with different configurations
parser = ParserFactory.create_bash_compatible_parser(tokens, source_text)
parser = ParserFactory.create_strict_posix_parser(tokens, source_text)
```

### 3.6 Centralized ParserContext (v0.85.0)

All parser state is now managed through a centralized ParserContext:

```python
@dataclass
class ParserContext:
    """Centralized parser state management"""
    # Core parsing state
    tokens: List[Token]
    current: int = 0
    config: ParserConfig = field(default_factory=ParserConfig)
    
    # Error handling
    errors: List[ParseError] = field(default_factory=list)
    error_recovery_mode: bool = False
    
    # Parsing context
    scope_stack: List[str] = field(default_factory=list)
    nesting_depth: int = 0
    
    # Special state
    in_case_pattern: bool = False
    in_arithmetic: bool = False
    in_function_body: bool = False
    
    # Performance tracking
    profiler: Optional[ParserProfiler] = None
    
    def enter_scope(self, scope: str):
        """Enter a new parsing scope with tracking"""
        self.scope_stack.append(scope)
        self.nesting_depth += 1
        if self.profiler:
            self.profiler.enter_scope(scope)
```

### 3.7 AST Validation and Semantic Analysis (v0.85.0)

The parser now includes comprehensive AST validation and semantic analysis:

```python
class SemanticAnalyzer(ASTVisitor[None]):
    """Perform semantic analysis on parsed AST"""
    
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.issues: List[Issue] = []
        self.warnings: List[Warning] = []
    
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """Validate function definition"""
        if self.symbol_table.has_function(node.name):
            self.issues.append(Issue(
                f"Function '{node.name}' already defined",
                node.position,
                Severity.ERROR
            ))
        
        # Track function context for return validation
        self.symbol_table.enter_function(node.name)
        self.visit(node.body)
        self.symbol_table.exit_function()

# Validation rules system
class NoEmptyBodyRule(ValidationRule):
    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        if isinstance(node, (WhileLoop, ForLoop)):
            if not node.body or not node.body.statements:
                return [Issue("Empty loop body", node.position, Severity.WARNING)]
        return []
```

### 3.8 Parse Tree Visualization (v0.85.0)

Multiple visualization formats are available for AST inspection:

```python
# Pretty-printed format
formatter = ASTPrettyPrinter(indent=2, show_positions=True)
print(formatter.visit(ast))

# Graphviz DOT format for visual diagrams
dot_generator = ASTDotGenerator(compact=False)
dot_content = dot_generator.visit(ast)

# ASCII tree for terminal display
tree_renderer = ASTAsciiTreeRenderer(style='standard')
print(tree_renderer.visit(ast))

# Integration with shell commands
psh --debug-ast=pretty -c "if true; then echo hi; fi"
parse-tree -f dot "for i in 1 2 3; do echo $i; done"
show-ast "case $var in pattern) echo match;; esac"
```

### 3.9 Enhanced Error Recovery (v0.85.0)

Advanced error recovery strategies provide better user experience:

```python
class ErrorCollector:
    """Collect multiple parse errors for batch reporting"""
    
    def add_error(self, error: ParseError) -> bool:
        """Add error and determine if parsing should continue"""
        self.errors.append(error)
        
        # Check for fatal errors
        if error.is_fatal or len(self.errors) >= self.max_errors:
            return False
        
        return True

def panic_mode_recovery(self, sync_tokens: Set[TokenType]):
    """Recover by skipping to synchronization points"""
    self.ctx.error_recovery_mode = True
    
    while not self.ctx.at_end() and not self.ctx.match(*sync_tokens):
        self.ctx.advance()
    
    self.ctx.error_recovery_mode = False
```

### 3.10 Recursive Descent Implementation

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

### 3.11 AST Node Hierarchy
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

### 3.12 Enhanced Error Recovery (Legacy)

The parser provides helpful error messages with enhanced context. In v0.85.0, this has been significantly enhanced with the new error recovery system:

```python
def _error(self, message: str) -> ParseError:
    """Create ParseError with current context"""
    error_context = ErrorContext(
        token=self.peek(),
        message=message,
        position=self.peek().position,
        suggestions=self._generate_suggestions(),  # v0.85.0 enhancement
        related_errors=[]  # v0.85.0 enhancement
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

### Version 0.85.0 - Complete Parser High-Priority Implementation
**Major parser system overhaul with comprehensive enhancements:**
- **Parser Configuration System**: Comprehensive ParserConfig with 40+ options and multiple parsing modes
  - STRICT_POSIX, BASH_COMPAT, PERMISSIVE, EDUCATIONAL modes
  - ParserFactory with preset configurations for different use cases
  - Feature toggles for validation, profiling, error collection
- **Centralized ParserContext**: Unified state management for all parser components
  - Consolidated parser state in single ParserContext class
  - Context factory and snapshots for backtracking support  
  - Performance profiling and debugging capabilities
  - Migrated all sub-parsers to use shared context
- **AST Validation System**: Complete semantic analysis and validation framework
  - SemanticAnalyzer with visitor pattern for AST analysis
  - Modular validation rules system with Issue and Severity classification
  - Symbol table management for function and variable tracking
  - Warning system with configurable severity levels
- **Parse Tree Visualization**: Multiple output formats with CLI integration
  - AST formatters: pretty printer, DOT generator, ASCII tree renderer
  - Shell integration: --debug-ast, parse-tree, show-ast, ast-dot commands
  - Interactive debug control via set -o and convenience builtins
- **Enhanced Error Recovery**: Advanced error handling and user experience
  - Smart error suggestions and context-aware recovery
  - Multi-error collection infrastructure with ErrorCollector
  - Panic mode recovery and phrase-level error repair
  - Enhanced incomplete command detection for multiline input

### Version 0.68.0 - Executor Package Refactoring
- Modular executor package with delegation architecture
- Main ExecutorVisitor delegates to specialized executors
- ExecutionContext state management and Strategy pattern for commands
- 73% code reduction in core executor module

### Version 0.60.0 - Parser Package Refactoring
- Transformed monolithic 1806-line parser.py into modular package structure
- Created 8 focused parser modules with clean separation of concerns
- Delegation-based architecture enabling clean component interaction
- Enhanced test expression parser with complete operator precedence
- Fixed C-style for loop parsing with proper arithmetic section handling
- Fixed stderr redirection parsing to separate operator from file descriptor
- Maintained 100% backward compatibility with existing parser API

### Version 0.58.0+ - Lexer Package Refactoring
- Comprehensive 4-phase refactoring of the lexer subsystem:
  - **Phase 1**: Unified state management with LexerContext
  - **Phase 2**: Pure function helpers for testability
  - **Phase 3**: Unified quote and expansion parsing
  - **Phase 4**: Modular token recognition system
- Created extensible architecture with backward compatibility
- Added 136+ tests across all refactoring phases
- Improved performance with priority-based recognition

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
2. **Security Visitors**: Static security analysis (partially implemented in visitor CLI features)
3. **Transformation Visitors**: Code modernization and refactoring (partially implemented in visitor CLI features)
4. ~~**Enhanced Error Recovery**: Continue parsing after errors~~ ✅ **Completed in v0.85.0**
5. **Incremental Parsing**: Reparse only changed portions
6. **Parallel Execution**: Execute independent commands concurrently
7. **Advanced AST Transformations**: Code optimization and refactoring passes
8. **Language Server Protocol**: LSP support for shell script editing
9. **Interactive Debugging**: Step-through debugging of shell scripts