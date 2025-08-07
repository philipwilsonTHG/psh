# Bash vs PSH Lexer Token Comparison

## Overview

This document analyzes the key differences between tokens emitted by the bash lexer (as defined in bash's `parse.y` yacc grammar) and the PSH (Python Shell) lexer. The analysis is based on examining bash's grammar file and PSH's token type definitions.

## Key Token Differences

### 1. Token Granularity and Complexity

#### Bash Lexer
The bash lexer emits **higher-level semantic tokens** that carry meaning beyond simple syntax:

- **Context-aware word tokens:**
  - `WORD` - General word token
  - `ASSIGNMENT_WORD` - Recognized VAR=value patterns
  - `REDIR_WORD` - Words used in {varname}> style redirections
  
- **Specialized tokens:**
  - `NUMBER` - Numeric literals (primarily for file descriptors)
  - `ARITH_CMD` - Complete arithmetic command as a single token
  - `ARITH_FOR_EXPRS` - Arithmetic for-loop expressions
  - `COND_CMD` - Complete conditional command
  
- **Reserved words as tokens:**
  - `IF`, `THEN`, `ELSE`, `ELIF`, `FI`
  - `FOR`, `WHILE`, `UNTIL`, `DO`, `DONE`
  - `CASE`, `ESAC`, `SELECT`
  - `FUNCTION`, `COPROC`

#### PSH Lexer
The PSH lexer emits **lower-level syntactic tokens** that are more granular:

- Everything tends to be `WORD` initially, with context determined by the parser
- More explicit token types for operators and expansions
- Separate tokens for each type of expansion and operator
- Keywords are recognized but without context sensitivity

### 2. Context-Sensitive Lexing

#### Bash Approach
The bash lexer performs **significant context analysis** during tokenization:

- **Smart word recognition:**
  - Distinguishes `WORD` vs `ASSIGNMENT_WORD` based on VAR=value pattern
  - Identifies `REDIR_WORD` for redirection contexts
  - Reserved words only recognized after list terminators
  
- **Complex construct parsing:**
  - Returns complete parsed structures for `ARITH_CMD` and `COND_CMD`
  - The lexer actually parses arithmetic expressions and conditional commands
  
- **Parser state awareness:**
  - Uses parser state variables to determine token types
  - Token recognition depends heavily on preceding tokens

#### PSH Approach
PSH uses more **context-free tokenization**:

- Most text is initially tokenized as `WORD`
- Parser determines semantic meaning from token sequences
- Some pattern recognition exists (e.g., `ASSIGNMENT_WORD`)
- Keywords recognized regardless of position
- Cleaner separation between lexical and syntactic analysis

### 3. Operator Token Differences

#### Bash Operators
Bash combines related operators into single tokens:

**Redirection operators:**
- `LESS_LESS` (<<)
- `GREATER_GREATER` (>>)
- `LESS_AND` (<&)
- `GREATER_AND` (>&)
- `AND_GREATER` (&>)
- `AND_GREATER_GREATER` (&>>)
- `LESS_LESS_MINUS` (<<-)
- `LESS_LESS_LESS` (<<<)
- `LESS_GREATER` (<>)
- `GREATER_BAR` (>|)

**Control operators:**
- `AND_AND` (&&)
- `OR_OR` (||)
- `SEMI_SEMI` (;;)
- `SEMI_AND` (;&)
- `SEMI_SEMI_AND` (;;&)
- `BAR_AND` (|&)

#### PSH Operators
PSH uses more granular operator tokens:

**Redirection tokens:**
- `REDIRECT_IN` (<)
- `REDIRECT_OUT` (>)
- `REDIRECT_APPEND` (>>)
- `REDIRECT_ERR` (2>)
- `REDIRECT_ERR_APPEND` (2>>)
- `REDIRECT_DUP` (2>&1 style)
- `HEREDOC` (<<)
- `HEREDOC_STRIP` (<<-)
- `HERE_STRING` (<<<)

**Expansion tokens:**
- `COMMAND_SUB` ($(...))
- `COMMAND_SUB_BACKTICK` (`...`)
- `ARITH_EXPANSION` ($((...)
- `PARAM_EXPANSION` (${...})
- `PROCESS_SUB_IN` (<(...))
- `PROCESS_SUB_OUT` (>(...))

### 4. Special Constructs

#### Bash Special Tokens
- `DOLPAREN` - Set by parser for $( constructs (not by lexer)
- `DOLBRACE` - Set by parser for ${ constructs (not by lexer)
- `COND_START`, `COND_END` - Conditional expression boundaries
- `TIME`, `TIMEOPT`, `TIMEIGN` - Time command modifiers
- `BANG` - Negation operator (!)
- `IN` - "in" keyword for for/select loops

#### PSH Special Tokens
- `DOUBLE_LBRACKET`/`DOUBLE_RBRACKET` - [[ ]] tokens
- `DOUBLE_LPAREN`/`DOUBLE_RPAREN` - (( )) tokens
- `EXCLAMATION` - ! operator
- Explicit tokens for each assignment operator (+=, -=, etc.)
- Quote tracking via `quote_type` attribute on tokens

### 5. Architectural Differences

#### Bash Architecture
**Parser-driven lexing:**
- The parser frequently calls back into the lexer with context information
- Lexer uses parser state variables to determine token types
- Complex constructs are parsed during lexing phase
- Token recognition depends on:
  - Previous tokens
  - Parser state
  - Nesting depth
  - Special modes (heredoc, arithmetic, etc.)

**Implications:**
- Lexer and parser are tightly coupled
- Difficult to test lexer in isolation
- Complex state management
- More efficient for certain constructs

#### PSH Architecture
**Clean separation:**
- Lexer produces tokens with minimal context awareness
- Parser handles most semantic interpretation
- Token stream is more predictable
- Each component can be tested independently

**Implications:**
- More modular design
- Easier to understand and maintain
- Better for educational purposes
- May require more parser complexity

### 6. Practical Examples

#### Example 1: Variable Assignment
Input: `VAR=value echo $VAR`

**Bash tokens:**
1. `ASSIGNMENT_WORD` "VAR=value"
2. `WORD` "echo"
3. `WORD` "$VAR"

**PSH tokens:**
1. `ASSIGNMENT_WORD` "VAR=value"
2. `WORD` "echo"
3. `VARIABLE` "VAR"

#### Example 2: Arithmetic Expression
Input: `((x = 5 + 3))`

**Bash tokens:**
1. `ARITH_CMD` (containing parsed arithmetic expression)

**PSH tokens:**
1. `DOUBLE_LPAREN` "(("
2. `WORD` "x"
3. `ASSIGN` "="
4. `WORD` "5"
5. `WORD` "+"
6. `WORD` "3"
7. `DOUBLE_RPAREN` "))"

#### Example 3: Conditional Expression
Input: `[[ -f file.txt ]]`

**Bash tokens:**
1. `COND_START`
2. `COND_CMD` (containing parsed condition)
3. `COND_END`

**PSH tokens:**
1. `DOUBLE_LBRACKET` "[["
2. `WORD` "-f"
3. `WORD` "file.txt"
4. `DOUBLE_RBRACKET` "]]"

## Summary

The fundamental difference between bash and PSH lexers represents a classic trade-off in language processor design:

**Bash's approach:**
- **Pros:** Simpler parser, efficient handling of complex constructs, fewer tokens to process
- **Cons:** Complex lexer, tight coupling, harder to maintain and test

**PSH's approach:**
- **Pros:** Clean architecture, modular design, easier testing, better for education
- **Cons:** More complex parser, more tokens to process, potential performance overhead

PSH's design choice of a simpler lexer with a more sophisticated parser aligns well with its educational goals, making the tokenization process more transparent and the overall system easier to understand and modify.