# Enhanced String Test Operators Implementation Plan

## Overview

This document outlines the architectural changes needed to implement Enhanced String Test Operators in psh, specifically:
- `STRING1 < STRING2` - Lexicographic string comparison
- `STRING1 > STRING2` - Lexicographic string comparison  
- `STRING =~ REGEX` - Pattern matching with regular expressions

These operators will be implemented within the `[[ ]]` enhanced test construct, which provides additional features over the traditional `[` command.

## 1. Tokenizer Changes (psh/tokenizer.py)

### New Token Types
```python
class TokenType(Enum):
    # ... existing tokens ...
    DOUBLE_LBRACKET = auto()  # [[
    DOUBLE_RBRACKET = auto()  # ]]
    REGEX_MATCH = auto()      # =~
```

### Tokenizer Modifications
- Recognize `[[` and `]]` as special tokens (not just two consecutive brackets)
- Add context tracking: when inside `[[ ]]`, treat `<` and `>` as operators, not redirections
- Recognize `=~` as a special operator token

## 2. Parser Changes (psh/parser.py)

### New AST Nodes (psh/ast_nodes.py)

```python
@dataclass
class EnhancedTestStatement(Statement):
    """Enhanced test construct [[ ... ]]."""
    expression: 'TestExpression'  # New type for test expressions
    redirects: List[Redirect] = field(default_factory=list)

# Test expression hierarchy
@dataclass
class TestExpression(ASTNode):
    """Base class for test expressions."""
    pass

@dataclass
class BinaryTestExpression(TestExpression):
    """Binary test expression like STRING1 < STRING2."""
    left: str
    operator: str  # =, !=, <, >, =~, -eq, -ne, etc.
    right: str

@dataclass
class UnaryTestExpression(TestExpression):
    """Unary test expression like -f FILE."""
    operator: str  # -f, -d, -z, -n, etc.
    operand: str

@dataclass
class CompoundTestExpression(TestExpression):
    """Compound test expression with && or ||."""
    left: TestExpression
    operator: str  # && or ||
    right: TestExpression

@dataclass
class NegatedTestExpression(TestExpression):
    """Negated test expression with !."""
    expression: TestExpression
```

### Parser Updates
- Recognize `[[` as the start of an enhanced test statement
- Parse test expressions with proper operator precedence
- Handle the new operators (`<`, `>`, `=~`) within `[[ ]]` context

## 3. Execution Changes (psh/shell.py)

### New Execution Methods

```python
def execute_enhanced_test_statement(self, test_stmt: EnhancedTestStatement) -> int:
    """Execute an enhanced test statement [[...]]."""
    try:
        result = self._evaluate_test_expression(test_stmt.expression)
        return 0 if result else 1
    except Exception as e:
        print(f"psh: [[: {e}", file=sys.stderr)
        return 2  # Syntax error

def _evaluate_test_expression(self, expr: TestExpression) -> bool:
    """Evaluate a test expression to boolean."""
    if isinstance(expr, BinaryTestExpression):
        return self._evaluate_binary_test(expr)
    elif isinstance(expr, UnaryTestExpression):
        return self._evaluate_unary_test(expr)
    elif isinstance(expr, CompoundTestExpression):
        return self._evaluate_compound_test(expr)
    elif isinstance(expr, NegatedTestExpression):
        return not self._evaluate_test_expression(expr.expression)
```

### New Operator Implementation

```python
def _evaluate_binary_test(self, expr: BinaryTestExpression) -> bool:
    """Evaluate binary test expression."""
    left = self._expand_string_variables(expr.left)
    right = self._expand_string_variables(expr.right)
    
    if expr.operator == '<':
        # Lexicographic comparison
        return left < right
    elif expr.operator == '>':
        # Lexicographic comparison
        return left > right
    elif expr.operator == '=~':
        # Regex matching
        import re
        try:
            pattern = re.compile(right)
            return bool(pattern.search(left))
        except re.error as e:
            raise Exception(f"invalid regex: {e}")
    # ... handle other operators ...
```

## 4. Key Features of `[[ ]]` vs `[`

The enhanced test construct provides:
- **No word splitting**: Variables don't need to be quoted
- **Pattern matching**: Right-hand side of `=` and `!=` can use patterns
- **Regex support**: The `=~` operator for regular expression matching
- **Safe empty variable handling**: `[[ -z $var ]]` works even if var is unset
- **Lexicographic string comparison**: `<` and `>` for string ordering

## 5. Implementation Phases

### Phase 1: Basic `[[ ]]` parsing and execution
- Tokenize `[[` and `]]`
- Parse simple expressions (existing operators)
- Execute with enhanced semantics (no word splitting)

### Phase 2: New operators
- Add `<` and `>` for string comparison
- Implement `=~` for regex matching
- Add proper error handling

### Phase 3: Advanced features
- Compound expressions with `&&` and `||`
- Pattern matching on right-hand side of `=` and `!=`
- Parentheses for grouping (optional)

## 6. Testing Requirements

Comprehensive tests should cover:
- Basic string comparisons: `[[ "apple" < "banana" ]]`
- Regex matching: `[[ "hello world" =~ ^hello ]]`
- Variable handling: `[[ $unset_var < "test" ]]`
- Compound expressions: `[[ $var = "test" && -f file.txt ]]`
- Error cases: Invalid regex, syntax errors

## 7. Example Usage

```bash
# String comparison
if [[ "apple" < "banana" ]]; then
    echo "apple comes before banana"
fi

# Regex matching
if [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo "Valid email address"
fi

# Compound expression
if [[ -f "$file" && "$file" =~ \.txt$ ]]; then
    echo "File exists and has .txt extension"
fi

# Safe variable handling (no need for quotes)
if [[ -z $unset_variable ]]; then
    echo "Variable is empty or unset"
fi
```

## 8. Implementation Notes

- The implementation maintains backward compatibility with the existing `[` command
- The `[[ ]]` construct is added as a separate feature following the same pattern as other control structures
- Context-aware tokenization is crucial to distinguish operators from redirections inside `[[ ]]`
- Error handling should provide clear messages for syntax errors and invalid regex patterns