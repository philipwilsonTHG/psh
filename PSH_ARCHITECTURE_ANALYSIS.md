# PSH Architecture Analysis

This document provides a comprehensive analysis of the Python Shell (PSH) architecture, focusing on the four major subsystems: Lexer, Parser, Expansion, and Executor.

## Table of Contents
1. [Overview](#overview)
2. [Lexer System](#lexer-system)
3. [Parser System](#parser-system)
4. [Expansion System](#expansion-system)
5. [Executor System](#executor-system)
6. [Data Flow](#data-flow)
7. [Key Design Patterns](#key-design-patterns)
8. [Extension Points](#extension-points)

## Overview

PSH follows a traditional shell architecture with clear separation of concerns:

```
Input → [Lexer] → Tokens → [Parser] → AST → [Expansion] → [Executor] → Output
```

Each stage is modular and extensible, with well-defined interfaces between components.

## Lexer System

### Architecture

The lexer is a modular, state-machine based tokenizer with Unicode support and configurable features.

#### Key Components:

1. **ModularLexer** (`lexer/modular_lexer.py`)
   - Main lexer class coordinating tokenization
   - Uses recognizer registry pattern for extensibility
   - Integrates quote parser and expansion parser
   - Maintains lexical context and state

2. **Token Recognizers** (`lexer/recognizers/`)
   - Pluggable recognizers for different token types
   - OperatorRecognizer: Multi-character operators
   - KeywordRecognizer: Shell keywords with context awareness
   - LiteralRecognizer: Words, numbers, identifiers
   - ProcessSubstitutionRecognizer: `<(...)` and `>(...)`

3. **Quote Parser** (`lexer/quote_parser.py`)
   - Unified handling of all quote types (', ", $')
   - ANSI-C escape sequence processing
   - Proper nesting and escaping rules

4. **Expansion Parser** (`lexer/expansion_parser.py`)
   - Pre-parsing of expansions during tokenization
   - Handles `$var`, `${var}`, `$(cmd)`, `$((expr))`, backticks
   - Context-aware expansion detection

5. **State Management** (`lexer/state_context.py`, `lexer/transitions.py`)
   - LexerContext tracks parsing state
   - StateTransition and StateManager handle state changes
   - Bracket depth tracking for `[[ ]]` and `(( ))`

### Key Features:

- **Unicode Support**: Full Unicode identifier and whitespace handling
- **Configurable**: LexerConfig controls features (quotes, expansions, etc.)
- **Error Recovery**: RecoverableLexerError for interactive mode
- **Position Tracking**: Line/column information for error messages
- **Rich Tokens**: TokenPart system for preserving expansion structure

### Token Types:

The lexer produces tokens of various types including:
- Basic: WORD, STRING, VARIABLE, EOF
- Operators: PIPE, SEMICOLON, AND_AND, OR_OR
- Redirections: REDIRECT_IN, REDIRECT_OUT, REDIRECT_APPEND
- Keywords: IF, THEN, ELSE, FI, WHILE, DO, DONE, etc.
- Special: COMMAND_SUB, ARITH_EXPANSION, PROCESS_SUB_IN/OUT

## Parser System

### Architecture

The parser uses recursive descent with modular components for different language constructs.

#### Key Components:

1. **Main Parser** (`parser/main.py`)
   - Orchestrates parsing by delegating to specialized parsers
   - Maintains token stream and source text for error messages
   - Provides backward compatibility methods

2. **Specialized Parsers**:
   - **CommandParser** (`parser/commands.py`): Simple commands, pipelines
   - **ControlStructureParser** (`parser/control_structures.py`): if/while/for/case
   - **TestParser** (`parser/tests.py`): `[[ ]]` enhanced tests
   - **ArithmeticParser** (`parser/arithmetic.py`): `(( ))` arithmetic
   - **RedirectionParser** (`parser/redirections.py`): I/O redirections
   - **ArrayParser** (`parser/arrays.py`): Array syntax
   - **FunctionParser** (`parser/functions.py`): Function definitions

3. **Helper Infrastructure**:
   - **TokenGroups**: Semantic grouping of related tokens
   - **ParseError**: Rich error context with source location
   - **BaseParser**: Common parsing utilities

### AST Node Types:

The parser produces a rich AST with nodes including:
- **Commands**: SimpleCommand, Pipeline, AndOrList
- **Control**: WhileLoop, ForLoop, IfConditional, CaseConditional
- **Functions**: FunctionDef
- **Arrays**: ArrayInitialization, ArrayElementAssignment
- **Special**: ProcessSubstitution, SubshellGroup, BraceGroup

### Key Features:

- **Unified Types**: Modern unified control structure types
- **Context Awareness**: Tracks parsing context for better errors
- **Composite Arguments**: Handles complex word concatenation
- **Error Recovery**: Detailed error messages with source context

## Expansion System

### Architecture

The expansion system orchestrates all shell expansions in the correct POSIX order.

#### Key Components:

1. **ExpansionManager** (`expansion/manager.py`)
   - Central coordinator for all expansions
   - Implements POSIX expansion order
   - Handles debug output for expansion tracing

2. **Individual Expanders**:
   - **VariableExpander** (`expansion/variable.py`): `$var`, `${var}` expansions
   - **CommandSubstitution** (`expansion/command_sub.py`): `$(cmd)` and backticks
   - **TildeExpander** (`expansion/tilde.py`): Home directory expansion
   - **GlobExpander** (`expansion/glob.py`): Pathname expansion

### Expansion Order:

1. Brace expansion (handled by tokenizer)
2. Tilde expansion
3. Variable expansion
4. Command substitution
5. Arithmetic expansion
6. Word splitting
7. Pathname expansion (globbing)
8. Quote removal

### Key Features:

- **Array Support**: Proper handling of `${arr[@]}` expansions
- **Word Splitting**: IFS-based splitting for unquoted expansions
- **Process Substitution**: Integration with I/O manager
- **Debug Support**: Detailed expansion tracing with --debug-expansion

## Executor System

### Architecture

The executor uses the visitor pattern with specialized executors for different node types.

#### Key Components:

1. **ExecutorVisitor** (`executor/core.py`)
   - Main visitor implementing ASTVisitor[int]
   - Coordinates execution by delegating to specialized executors
   - Manages execution context and state

2. **Specialized Executors**:
   - **CommandExecutor** (`executor/command.py`): Simple command execution
   - **PipelineExecutor** (`executor/pipeline.py`): Pipeline management
   - **ControlFlowExecutor** (`executor/control_flow.py`): Control structures
   - **ArrayOperationExecutor** (`executor/array.py`): Array operations
   - **FunctionOperationExecutor** (`executor/function.py`): Functions
   - **SubshellExecutor** (`executor/subshell.py`): Subshells and brace groups

3. **Execution Strategies** (`executor/strategies.py`):
   - **BuiltinExecutionStrategy**: Built-in commands
   - **FunctionExecutionStrategy**: User-defined functions
   - **ExternalExecutionStrategy**: External programs
   - **AliasExecutionStrategy**: Alias expansion

4. **Context Management**:
   - **ExecutionContext**: Tracks execution state
   - **PipelineContext**: Pipeline-specific state

### Key Features:

- **Process Management**: Proper fork/exec with job control
- **I/O Redirection**: File descriptor manipulation
- **Signal Handling**: Proper signal management for job control
- **Error Handling**: Exception-based control flow (break/continue)

## Data Flow

### 1. Tokenization Phase
```
Input String
    ↓
BraceExpander (pre-tokenization)
    ↓
ModularLexer
    ├─ RecognizerRegistry
    ├─ QuoteParser
    └─ ExpansionParser
    ↓
Token Stream
```

### 2. Parsing Phase
```
Token Stream
    ↓
Parser (main orchestrator)
    ├─ CommandParser
    ├─ ControlStructureParser
    ├─ TestParser
    └─ [other specialized parsers]
    ↓
Abstract Syntax Tree (AST)
```

### 3. Execution Phase
```
AST Node
    ↓
ExecutorVisitor.visit(node)
    ↓
ExpansionManager (for SimpleCommand)
    ├─ TildeExpander
    ├─ VariableExpander
    ├─ CommandSubstitution
    └─ GlobExpander
    ↓
Specialized Executor
    ├─ BuiltinRegistry (for builtins)
    ├─ FunctionManager (for functions)
    └─ Process creation (for externals)
    ↓
Exit Status
```

## Key Design Patterns

### 1. Visitor Pattern
- Used extensively in the executor system
- Enables clean separation of AST structure from operations
- Easy to add new operations without modifying AST nodes

### 2. Registry Pattern
- Token recognizers use registry for extensibility
- Builtin commands use registry with decorator pattern
- Enables plugin-style architecture

### 3. Strategy Pattern
- Execution strategies select appropriate execution method
- Configurable precedence (aliases → functions → builtins → external)

### 4. Delegation Pattern
- Main parser delegates to specialized parsers
- Main executor delegates to specialized executors
- Promotes single responsibility principle

### 5. Context Objects
- LexerContext, ExecutionContext, PipelineContext
- Encapsulate state without globals
- Enable proper scoping and cleanup

## Extension Points

### Adding New Token Types
1. Add to TokenType enum in `token_types.py`
2. Create recognizer in `lexer/recognizers/`
3. Register recognizer in ModularLexer

### Adding New Builtins
1. Create class inheriting from Builtin
2. Add @builtin decorator
3. Implement execute() method

### Adding New AST Nodes
1. Define node class in `ast_nodes.py`
2. Add parsing method to appropriate parser module
3. Add visitor method to ExecutorVisitor

### Adding New Expansions
1. Create expander class in `expansion/`
2. Integrate into ExpansionManager
3. Ensure correct position in expansion order

## Notable Architectural Decisions

1. **Modular Design**: Each subsystem is highly modular with clear interfaces
2. **Educational Focus**: Code prioritizes clarity over performance
3. **POSIX Compliance**: Architecture supports ~93% POSIX compliance
4. **Visitor Pattern**: Enables the CLI analysis tools (--format, --metrics, etc.)
5. **Rich Token Information**: Preserves source location and structure
6. **Process Isolation**: Command substitution and subshells use proper fork()
7. **Exception-Based Control**: Break/continue use exceptions for clean propagation

This architecture provides a solid foundation for both educational purposes and practical shell functionality, with clear extension points for future enhancements.