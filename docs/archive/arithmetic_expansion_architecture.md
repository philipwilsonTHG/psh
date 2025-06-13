# Arithmetic Expansion Architecture Proposal

## Overview

This document proposes an architecture for implementing arithmetic expansion `$((...))` in psh, following bash semantics while maintaining the educational clarity of the codebase.

## Current Architecture Analysis

### Command Substitution Pattern
The current implementation handles command substitution `$(...)` with a three-phase approach:
1. **Tokenization**: Recognizes `$(...)` patterns and creates `COMMAND_SUB` tokens
2. **Parsing**: Preserves the substitution text in the AST as command arguments
3. **Execution**: Evaluates substitutions during command expansion phase

This deferred evaluation model works well because command substitution requires full shell parsing/execution.

## Proposed Architecture: Separate Arithmetic Subsystem

### Recommendation: Separate Subsystem Approach

I recommend implementing arithmetic expansion as a **separate subsystem** that is invoked during the execution phase, similar to command substitution. Here's why:

#### Advantages:
1. **Clean Separation of Concerns**: Arithmetic has different syntax/semantics than shell commands
2. **Educational Clarity**: Students can study arithmetic evaluation independently
3. **Reusability**: The arithmetic evaluator can be used for other features (test operators, C-style for loops)
4. **Simpler Main Parser**: Keeps the shell parser focused on shell syntax
5. **Better Error Messages**: Arithmetic errors can be reported with arithmetic-specific context

#### Implementation Strategy:

### 1. Tokenization Phase
```python
# In tokenizer.py
class TokenType(Enum):
    # ... existing tokens ...
    ARITH_EXPANSION = auto()  # $((...))

# Tokenizer recognizes $(( and creates ARITH_EXPANSION token
# Similar to COMMAND_SUB but for arithmetic
```

### 2. Parsing Phase
```python
# In parser.py
# Arithmetic expansion is treated as another word type
# The parser preserves the expression text without parsing it
elif token.type == TokenType.ARITH_EXPANSION:
    command.args.append(token.value)
    command.arg_types.append('ARITH_EXPANSION')
```

### 3. Arithmetic Subsystem (New Module: arithmetic.py)
```python
# arithmetic.py - Separate arithmetic expression evaluator

class ArithmeticTokenType(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    POWER = auto()
    LPAREN = auto()
    RPAREN = auto()
    VARIABLE = auto()
    # Comparison operators
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    EQ = auto()
    NE = auto()
    # Logical operators
    AND = auto()
    OR = auto()
    NOT = auto()
    # Bitwise operators
    BIT_AND = auto()
    BIT_OR = auto()
    BIT_XOR = auto()
    BIT_NOT = auto()
    LSHIFT = auto()
    RSHIFT = auto()
    # Assignment operators
    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    # Increment/decrement
    INCREMENT = auto()
    DECREMENT = auto()

class ArithmeticParser:
    """Recursive descent parser for arithmetic expressions"""
    
    def parse_expression(self) -> ArithmeticNode:
        """Top-level expression parsing with precedence climbing"""
        return self.parse_ternary()
    
    def parse_ternary(self) -> ArithmeticNode:
        """Handle ?: operator"""
        pass
    
    def parse_logical_or(self) -> ArithmeticNode:
        """Handle || operator"""
        pass
    
    # ... other precedence levels ...

class ArithmeticEvaluator:
    """Evaluate arithmetic AST nodes"""
    
    def __init__(self, shell):
        self.shell = shell  # Access to variables
    
    def evaluate(self, node: ArithmeticNode) -> int:
        """Evaluate arithmetic expression to integer result"""
        pass
```

### 4. Execution Phase Integration
```python
# In shell.py
def _expand_arguments(self, command: Command) -> list:
    # ... existing code ...
    elif arg_type == 'ARITH_EXPANSION':
        # Execute arithmetic expansion
        result = self._execute_arithmetic_expansion(arg)
        args.append(str(result))
    
def _execute_arithmetic_expansion(self, expr: str) -> int:
    """Execute arithmetic expansion and return result"""
    # Remove $(( and ))
    if expr.startswith('$((') and expr.endswith('))'):
        arith_expr = expr[3:-2]
    else:
        return 0
    
    from .arithmetic import ArithmeticParser, ArithmeticEvaluator
    
    try:
        # Parse arithmetic expression
        parser = ArithmeticParser(arith_expr)
        ast = parser.parse()
        
        # Evaluate with access to shell variables
        evaluator = ArithmeticEvaluator(self)
        result = evaluator.evaluate(ast)
        
        return result
    except ArithmeticError as e:
        print(f"Arithmetic error: {e}", file=sys.stderr)
        return 0
```

## Alternative: Integrated Parser Approach

While not recommended, here's what integration into the main parser would look like:

### Disadvantages:
1. **Parser Complexity**: Shell parser would need arithmetic expression grammar rules
2. **Mixed Concerns**: Shell and arithmetic syntax in same parser
3. **Harder to Test**: Can't test arithmetic independently
4. **Less Reusable**: Arithmetic logic tied to shell parser

### Implementation Sketch:
```python
# Would require adding arithmetic operators to main tokenizer
# Would need arithmetic expression parsing in main parser
# Makes the educational parser much more complex
```

## Feature Scope

### Phase 1: Basic Arithmetic
- Integer arithmetic only (bash behavior)
- Basic operators: +, -, *, /, %, **
- Parentheses for grouping
- Variable expansion: $((x + 1))

### Phase 2: Comparison and Logic
- Comparison: <, >, <=, >=, ==, !=
- Logical: &&, ||, !
- Ternary: ? :

### Phase 3: Advanced Features
- Bitwise operators: &, |, ^, ~, <<, >>
- Assignment: =, +=, -=, *=, /=, %=
- Increment/decrement: ++, --
- Comma operator: ,

## Testing Strategy

```python
# tests/test_arithmetic.py
def test_basic_arithmetic():
    assert shell.run_command("echo $((2 + 2))") == "4"
    assert shell.run_command("echo $((10 - 3))") == "7"
    assert shell.run_command("echo $((4 * 5))") == "20"
    assert shell.run_command("echo $((20 / 4))") == "5"
    assert shell.run_command("echo $((17 % 5))") == "2"
    assert shell.run_command("echo $((2 ** 8))") == "256"

def test_arithmetic_with_variables():
    shell.run_command("x=10")
    assert shell.run_command("echo $((x + 5))") == "15"
    assert shell.run_command("echo $((x * 2))") == "20"
```

## Integration with Other Features

### C-style For Loops
The arithmetic evaluator will be reused for C-style for loops:
```bash
for ((i=0; i<10; i++)); do
    echo $i
done
```

### Test Command Enhancement
Can enhance test command with arithmetic comparison:
```bash
if [ $((x + 1)) -gt 10 ]; then
    echo "x is greater than 9"
fi
```

## Conclusion

The separate subsystem approach provides the best balance of:
- **Simplicity**: Each component has a single responsibility
- **Maintainability**: Arithmetic logic is isolated and testable
- **Educational Value**: Students can understand each phase independently
- **Extensibility**: Easy to add new operators or features

This architecture follows psh's philosophy of clear, educational code while providing full bash compatibility for arithmetic expressions.