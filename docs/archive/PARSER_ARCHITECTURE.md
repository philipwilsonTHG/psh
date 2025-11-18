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
- Special handling for regex patterns after `=~` operator
- Context-aware bracket parsing for array subscripts vs test command

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
    
    # Grouping
    LPAREN, RPAREN
    LBRACE, RBRACE
    LBRACKET, RBRACKET
    DOUBLE_LPAREN  # (( for arithmetic
    
    # Control structures
    IF, THEN, ELSE, ELIF, FI
    WHILE, DO, DONE
    FOR, IN
    CASE, ESAC
    SELECT  # select statement
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
- `parse_pipeline_component()`: Single component of a pipeline (simple or compound command)
- `parse_command()`: Simple command with args and redirects
- `parse_composite_argument()`: Handles concatenated tokens (e.g., `pre${var}post`)

#### Control Structures (Statement Context)
- `parse_if_statement()`: If/then/elif/else/fi
- `parse_while_statement()`: While loops
- `parse_for_statement()`: For loops (traditional or C-style)
- `parse_case_statement()`: Case statements
- `parse_select_statement()`: Select loops
- `parse_function_def()`: Function definitions
- `parse_enhanced_test_statement()`: [[ ]] tests
- `parse_arithmetic_command()`: Arithmetic evaluation ((expr))

#### Control Structures (Pipeline Context)
- `parse_if_command()`: If as pipeline component
- `parse_while_command()`: While as pipeline component
- `parse_for_command()`: For as pipeline component
- `parse_case_command()`: Case as pipeline component
- `parse_select_command()`: Select as pipeline component
- `parse_arithmetic_compound_command()`: Arithmetic as pipeline component

#### Neutral Parsers (Context-Independent)
- `_parse_if_neutral()`: Parse if without setting execution context
- `_parse_while_neutral()`: Parse while without setting execution context
- `_parse_for_neutral()`: Parse for without setting execution context
- `_parse_case_neutral()`: Parse case without setting execution context
- `_parse_select_neutral()`: Parse select without setting execution context
- `_parse_arithmetic_neutral()`: Parse arithmetic without setting execution context

#### Array Parsing
- `_is_array_assignment()`: Check if current position starts an array assignment
- `_parse_array_assignment()`: Parse array initialization or element assignment
- `_parse_array_initialization()`: Parse `arr=(elements)` or `arr+=(elements)`
- `_parse_array_element_assignment()`: Parse `arr[index]=value`
- `_parse_array_key_tokens()`: Parse array key as token list for late binding

### 4. AST Nodes (`ast_nodes.py`)

The parser produces an Abstract Syntax Tree with these node types:

```python
# Base classes
class ASTNode(ABC): pass
class Statement(ASTNode): pass
class Command(ASTNode): pass
class CompoundCommand(Command): pass

# I/O Redirection
@dataclass
class Redirect(ASTNode):
    type: str  # '<', '>', '>>', '<<', '<<-', '2>', '2>>', '2>&1', etc.
    target: str
    fd: Optional[int] = None  # File descriptor
    dup_fd: Optional[int] = None  # For duplications like 2>&1
    heredoc_content: Optional[str] = None  # For here documents

# Execution context for unified control structures
class ExecutionContext(Enum):
    STATEMENT = "statement"  # Execute in current shell process
    PIPELINE = "pipeline"    # Execute in subshell for pipeline

# Commands and execution
@dataclass
class SimpleCommand(Command):
    args: List[str]
    arg_types: List[str]  # WORD, STRING, VARIABLE, etc.
    quote_types: List[Optional[str]]  # Quote character used
    redirects: List[Redirect]
    background: bool
    array_assignments: List[ArrayAssignment]  # Array assignments before command

@dataclass
class Pipeline(ASTNode):
    commands: List[Command]  # Can contain SimpleCommand or CompoundCommand
    negated: bool  # True if prefixed with !

@dataclass
class AndOrList(Statement):
    pipelines: List[Pipeline]
    operators: List[str]  # '&&' or '||' between pipelines

@dataclass
class StatementList(ASTNode):
    statements: List[Statement]

# Alias for backward compatibility
CommandList = StatementList

# Unified control structures (can be used as both Statement and Command)
class UnifiedControlStructure(Statement, CompoundCommand):
    """Base class for unified control structures."""
    pass

@dataclass
class WhileLoop(UnifiedControlStructure):
    condition: StatementList
    body: StatementList
    redirects: List[Redirect]
    execution_context: ExecutionContext
    background: bool

@dataclass
class ForLoop(UnifiedControlStructure):
    variable: str
    items: List[str]
    body: StatementList
    redirects: List[Redirect]
    execution_context: ExecutionContext
    background: bool

@dataclass
class CStyleForLoop(UnifiedControlStructure):
    init_expr: Optional[str]
    condition_expr: Optional[str]
    update_expr: Optional[str]
    body: StatementList
    redirects: List[Redirect]
    execution_context: ExecutionContext
    background: bool

@dataclass
class IfConditional(UnifiedControlStructure):
    condition: StatementList
    then_part: StatementList
    elif_parts: List[Tuple[StatementList, StatementList]]
    else_part: Optional[StatementList]
    redirects: List[Redirect]
    execution_context: ExecutionContext
    background: bool

@dataclass
class SelectLoop(UnifiedControlStructure):
    variable: str
    items: List[str]
    body: StatementList
    redirects: List[Redirect]
    execution_context: ExecutionContext
    background: bool

@dataclass
class ArithmeticEvaluation(UnifiedControlStructure):
    expression: str
    redirects: List[Redirect]
    execution_context: ExecutionContext
    background: bool

# Array assignment nodes
@dataclass
class ArrayInitialization(ArrayAssignment):
    name: str
    elements: List[str]
    element_types: List[str]
    element_quote_types: List[Optional[str]]
    is_append: bool  # True for += initialization

@dataclass
class ArrayElementAssignment(ArrayAssignment):
    name: str
    index: Union[str, List[Token]]  # Late binding: tokens for runtime evaluation
    value: str
    value_type: str
    value_quote_type: Optional[str]
    is_append: bool  # True for += assignment

# Other nodes
@dataclass
class ProcessSubstitution(ASTNode):
    direction: str  # 'in' or 'out'
    command: str

@dataclass
class EnhancedTestStatement(Statement):
    expression: TestExpression
    redirects: List[Redirect]

# Test expression nodes for [[ ]] construct
class TestExpression(ASTNode): pass

@dataclass
class BinaryTestExpression(TestExpression):
    left: str
    operator: str  # =, !=, <, >, =~, -eq, -ne, etc.
    right: str

@dataclass
class UnaryTestExpression(TestExpression):
    operator: str  # -z, -n, -f, -d, etc.
    operand: str

@dataclass
class CompoundTestExpression(TestExpression):
    operator: str  # && or ||
    left: TestExpression
    right: TestExpression

@dataclass
class NegatedTestExpression(TestExpression):
    expression: TestExpression
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
             | 'for' '((' [arith_expr] ';' [arith_expr] ';' [arith_expr] '))' 
               ['do'] command_list 'done'
select_stmt  → 'select' WORD 'in' word_list 'do' command_list 'done'
case_stmt    → 'case' expr 'in' case_item* 'esac'
arith_cmd    → '((' arith_expr '))'
enhanced_test → '[[' test_expr ']]'
function_def → WORD '(' ')' compound_command
             | 'function' WORD ['(' ')'] compound_command

# Command execution
command_list → and_or_list (separator and_or_list)* [separator]
separator    → ';' | '\n'
and_or_list  → pipeline (('&&' | '||') pipeline)*
             | break_stmt | continue_stmt
pipeline     → ['!'] pipeline_component ('|' pipeline_component)*
pipeline_component → simple_command | compound_command
simple_command → [array_assignment+] word+ redirect* ['&']
compound_command → if_stmt | while_stmt | for_stmt | case_stmt 
                 | select_stmt | arith_cmd

# Array assignments
array_assignment → WORD '[' arith_expr ']' '=' word
                 | WORD '[' arith_expr ']' '+=' word
                 | WORD '=' '(' word* ')'
                 | WORD '+=' '(' word* ')'

# Loop control
break_stmt   → 'break' [NUMBER]
continue_stmt → 'continue' [NUMBER]

# Test expressions (for [[ ]])
test_expr    → unary_test | binary_test | '!' test_expr
             | test_expr '&&' test_expr | test_expr '||' test_expr
             | '(' test_expr ')'
unary_test   → '-' test_op word
binary_test  → word test_op word
test_op      → '=' | '!=' | '<' | '>' | '=~' | '-eq' | '-ne' | '-lt' 
             | '-le' | '-gt' | '-ge' | '-f' | '-d' | '-e' | '-z' | '-n'

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
- Context-aware bracket parsing: `[` as command vs array subscript

### 3. Unified Control Structures
- Single AST node type serves both statement and pipeline contexts
- `ExecutionContext` enum determines execution behavior (current shell vs subshell)
- All control structures can be used as pipeline components

### 4. Late Binding Array Keys
- Array keys parsed as token lists without evaluation
- Allows runtime determination of array type (indexed vs associative)
- Supports complex key expressions: `arr[${prefix}_${suffix}]`

### 5. Control Structures in Pipelines
All control structures can now be used as pipeline components:
```bash
echo "data" | while read line; do echo $line; done
seq 1 5 | for i in $(cat); do echo $i; done
```

### 6. Error Recovery
- Synchronization at statement boundaries (`;`, newline)
- Human-readable error messages with position information
- Graceful handling of unexpected tokens

### 7. Heredoc Support
The parser recognizes heredoc operators and delimiters, with actual content processing deferred to the executor phase.

### 8. Backward Compatibility
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

## Recent Enhancements

The following features have been recently implemented:

### Arrays (v0.41.0 - v0.43.0)
- **Indexed arrays**: `arr[0]=value`, `arr=(one two three)`
- **Associative arrays**: `declare -A dict; dict[key]="value"`
- **Array expansions**: `${arr[@]}`, `${!arr[@]}`, `${#arr[@]}`
- **Array slicing**: `${arr[@]:1:2}`
- **Append operator**: `arr+=(new elements)`
- **Late binding keys**: Parser defers key evaluation for runtime type detection

### Control Structures
- **C-style for loops**: `for ((i=0; i<10; i++))`
- **Arithmetic commands**: `((expression))` as standalone commands
- **Select statements**: Interactive menu loops
- **Control structures in pipelines**: All structures usable as pipeline components

### Enhanced Features
- **Process substitution**: `<(command)` and `>(command)`
- **Enhanced test**: `[[ ]]` with regex matching `=~` and string comparison
- **Arithmetic evaluation**: Full expression support in `$(())` and `(())`

## Future Enhancements

Potential parser improvements:
- Extended glob patterns (`?(pattern)`, `*(pattern)`, etc.)
- Coprocess support
- Named references (`declare -n`)
- Additional parameter expansion features