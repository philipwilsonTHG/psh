# PSH Parser Architecture

## Overview

PSH uses a hand-written recursive descent parser for educational clarity and maintainability. The parser is implemented as a two-phase system: tokenization (lexical analysis) followed by parsing (syntax analysis).

## Architecture Components

### 1. Tokenization: State Machine Lexer (`state_machine_lexer.py`)

The lexer uses a state machine approach to handle the complex tokenization requirements of shell syntax:

```python
class LexerState(Enum):
    NORMAL = auto()
    IN_WORD = auto()
    IN_SINGLE_QUOTE = auto()
    IN_DOUBLE_QUOTE = auto()
    IN_VARIABLE = auto()
    IN_COMMAND_SUB = auto()
    IN_ARITHMETIC = auto()
    IN_COMMENT = auto()
    IN_BACKTICK = auto()
    IN_BRACE_VAR = auto()  # Inside ${...}
```

Key features:
- Preserves quote information for proper variable expansion
- Handles embedded variables in words (e.g., `pre${var}post`)
- Maintains context for operators and keywords
- Provides rich token metadata including position information

### 2. Token Types (`token_types.py`)

The tokenizer produces tokens of the following types:

```python
class TokenType(Enum):
    # Basic tokens
    WORD, PIPE, SEMICOLON, AMPERSAND, NEWLINE, EOF
    
    # Redirections
    REDIRECT_IN, REDIRECT_OUT, REDIRECT_APPEND
    REDIRECT_ERR, REDIRECT_ERR_APPEND, REDIRECT_DUP
    HEREDOC, HEREDOC_STRIP, HERE_STRING
    
    # Quotes and expansions
    STRING, VARIABLE
    COMMAND_SUB, COMMAND_SUB_BACKTICK
    ARITH_EXPANSION
    PROCESS_SUB_IN, PROCESS_SUB_OUT
    
    # Control structures
    IF, THEN, ELSE, ELIF, FI
    WHILE, DO, DONE
    FOR, IN
    CASE, ESAC
    BREAK, CONTINUE
    FUNCTION
    
    # Operators
    AND_AND, OR_OR  # && ||
    DOUBLE_SEMICOLON, SEMICOLON_AMP, AMP_SEMICOLON  # ;; ;& ;;&
    EXCLAMATION  # !
    DOUBLE_LBRACKET, DOUBLE_RBRACKET  # [[ ]]
    REGEX_MATCH  # =~
```

### 3. Parser (`parser.py`)

The parser uses recursive descent with the following key methods:

#### Token Management
- `peek()`: Look at current token without consuming
- `advance()`: Consume and return current token
- `expect(token_type)`: Consume expected token or error
- `match(*token_types)`: Check if current token matches

#### Parsing Methods (Grammar Rules)
- `parse()`: Top-level entry point
- `parse_command_list()`: Commands separated by `;` or newline
- `parse_and_or_list()`: Pipelines connected by `&&` or `||`
- `parse_pipeline()`: Commands connected by `|`
- `parse_command()`: Single command with args and redirects

#### Control Structures
- `parse_if_statement()`: If/then/elif/else/fi
- `parse_while_statement()`: While loops
- `parse_for_statement()`: For loops
- `parse_case_statement()`: Case statements
- `parse_function_def()`: Function definitions
- `parse_enhanced_test_statement()`: [[ ]] tests

### 4. AST Nodes (`ast_nodes.py`)

The parser produces an Abstract Syntax Tree with these node types:

```python
# Base classes
class ASTNode(ABC): pass
class Statement(ASTNode): pass

# Commands and execution
@dataclass
class Command(ASTNode):
    args: List[str]
    arg_types: List[str]  # WORD, STRING, VARIABLE, etc.
    quote_types: List[Optional[str]]  # Quote character used
    redirects: List[Redirect]
    background: bool

@dataclass
class Pipeline(ASTNode):
    commands: List[Command]
    negated: bool  # True if prefixed with !

@dataclass
class AndOrList(Statement):
    pipelines: List[Pipeline]
    operators: List[str]  # '&&' or '||' between pipelines

# Control structures
@dataclass
class IfStatement(Statement):
    condition: StatementList
    then_part: StatementList
    elif_parts: List[Tuple[StatementList, StatementList]]
    else_part: Optional[StatementList]
    redirects: List[Redirect]

# Similar structures for WhileStatement, ForStatement, CaseStatement, etc.
```

## Grammar

The parser implements the following grammar:

```
# Top-level
top_level    → statement*
statement    → function_def | control_structure | command_list

# Control structures
if_stmt      → 'if' command_list 'then' command_list 
               ('elif' command_list 'then' command_list)*
               ['else' command_list] 'fi'
while_stmt   → 'while' command_list 'do' command_list 'done'
for_stmt     → 'for' WORD 'in' word_list 'do' command_list 'done'
case_stmt    → 'case' expr 'in' case_item* 'esac'
function_def → WORD '(' ')' compound_command
             | 'function' WORD ['(' ')'] compound_command

# Command execution
command_list → and_or_list (separator and_or_list)* [separator]
separator    → ';' | '\n'
and_or_list  → pipeline (('&&' | '||') pipeline)*
pipeline     → ['!'] command ('|' command)*
command      → word+ redirect* ['&']

# Expansions and words
word         → WORD | STRING | VARIABLE | COMMAND_SUB 
             | ARITH_EXPANSION | PROCESS_SUB_IN | PROCESS_SUB_OUT

# Redirections
redirect     → [fd] redirect_op target
redirect_op  → '<' | '>' | '>>' | '2>' | '2>>' | '<<' | '<<-' | '<<<'
             | '>&' | '2>&1'
```

## Key Design Features

### 1. Composite Argument Handling
The parser can handle concatenated tokens (e.g., `pre${var}post`) by detecting adjacent tokens and combining them into composite arguments.

### 2. Context-Sensitive Parsing
- Keywords are only recognized in command position
- Special handling for regex patterns in `[[ ... =~ pattern ]]`
- Different word terminators inside `[[ ]]` constructs

### 3. Error Recovery
- Synchronization at statement boundaries (`;`, newline)
- Human-readable error messages with position information
- Graceful handling of unexpected tokens

### 4. Heredoc Support
The parser recognizes heredoc operators and delimiters, with actual content processing deferred to the executor phase.

### 5. Backward Compatibility
The AST maintains backward compatibility through properties that expose the structure in ways expected by older code.

## Execution Flow

1. **Input**: Shell command string
2. **Tokenization**: `StateMachineLexer` produces list of tokens
3. **Parsing**: `Parser` consumes tokens to build AST
4. **Execution**: Executor traverses AST to run commands

## Testing Considerations

The parser is extensively tested with:
- Unit tests for individual parsing methods
- Integration tests for complete commands
- Edge cases: empty input, syntax errors, complex nesting
- Comparison tests against bash behavior

## Future Enhancements

Planned parser improvements:
- C-style for loops: `for ((i=0; i<10; i++))`
- Arithmetic expressions as first-class constructs
- Array syntax support
- Extended glob patterns