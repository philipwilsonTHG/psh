# Arithmetic Command Syntax Implementation Plan

## Overview

This document outlines the implementation plan for adding arithmetic command syntax `((expression))` to psh. This feature will enable standalone arithmetic evaluation that returns an exit status and performs side effects like variable assignments.

## Current State Analysis

### What Already Works
1. **Arithmetic Expansion** `$((expr))` - fully implemented in `arithmetic.py`
2. **C-style for loops** `for ((init; cond; update))` - uses arithmetic expressions
3. **Tokenizer** - already recognizes `((` when parsing C-style for loops
4. **Arithmetic Evaluator** - complete implementation with all operators

### What's Missing
1. Recognition of `((expr))` as a standalone command
2. AST node for arithmetic commands
3. Executor for arithmetic commands
4. Integration with control flow (if, while, etc.)

## Implementation Architecture

### 1. AST Node Addition

**File**: `psh/ast_nodes.py`

```python
@dataclass
class ArithmeticCommand(Statement):
    """Represents an arithmetic command ((expression))."""
    expression: str
    redirects: List[Redirect] = field(default_factory=list)
```

This node type:
- Extends `Statement` so it can appear anywhere a command can
- Stores the arithmetic expression as a string
- Supports redirects (though rarely used with arithmetic commands)

### 2. Token Recognition

**File**: `psh/token_types.py`

Add new token type:
```python
DOUBLE_LPAREN = auto()  # ((
```

**File**: `psh/state_machine_lexer.py` (or tokenizer)

Modify tokenizer to recognize `((` as a special token when:
- Not already inside a C-style for loop
- At the start of a command position

### 3. Parser Modifications

**File**: `psh/parser.py`

#### 3.1 Add to Statement Parsing

In `parse_statement()` method, add:
```python
if self.match(TokenType.DOUBLE_LPAREN):
    return self.parse_arithmetic_command()
```

#### 3.2 New Parsing Method

```python
def parse_arithmetic_command(self) -> ArithmeticCommand:
    """Parse arithmetic command: ((expression))"""
    # Consume the (( token
    self.expect(TokenType.DOUBLE_LPAREN)
    
    # Parse expression until ))
    expr = self._parse_arithmetic_expression_until_double_rparen()
    
    # Expect ))
    self.expect(TokenType.RPAREN)
    self.expect(TokenType.RPAREN)
    
    # Parse any redirects (rare but allowed)
    redirects = self.parse_redirects()
    
    return ArithmeticCommand(expr, redirects)
```

#### 3.3 Expression Parsing

Reuse existing `_parse_arithmetic_section_until_double_rparen()` or create similar:
```python
def _parse_arithmetic_expression_until_double_rparen(self) -> str:
    """Parse arithmetic expression until )) is found."""
    # Similar to existing C-style for loop parsing
    # Handles nested parentheses correctly
```

### 4. Executor Implementation

**File**: `psh/executor/base.py`

Add ArithmeticCommand to imports and dispatcher:
```python
from ..ast_nodes import ArithmeticCommand

# In ExecutorManager.execute():
elif isinstance(node, ArithmeticCommand):
    return self.arithmetic_executor.execute(node)
```

**New File**: `psh/executor/arithmetic_command.py`

```python
"""Arithmetic command execution."""
from typing import Dict, Any
from ..ast_nodes import ArithmeticCommand
from .base import ExecutorComponent
from ..arithmetic import ArithmeticEvaluator

class ArithmeticCommandExecutor(ExecutorComponent):
    """Executes arithmetic commands ((expression))."""
    
    def execute(self, command: ArithmeticCommand) -> int:
        """Execute arithmetic command and return exit status."""
        try:
            # Create evaluator with current variable context
            evaluator = ArithmeticEvaluator(self._get_variables())
            
            # Evaluate the expression
            result = evaluator.evaluate(command.expression)
            
            # Update variables with any assignments
            self._update_variables(evaluator.variables)
            
            # Return 0 if result is non-zero, 1 if zero
            return 0 if result != 0 else 1
            
        except Exception as e:
            # Print error to stderr
            print(f"psh: arithmetic error: {e}", file=sys.stderr)
            return 1
    
    def _get_variables(self) -> Dict[str, Any]:
        """Get current shell variables for arithmetic context."""
        # Get all variables from shell state
        # Convert to integers where possible
        pass
    
    def _update_variables(self, variables: Dict[str, Any]):
        """Update shell variables from arithmetic assignments."""
        # Update shell state with modified variables
        pass
```

### 5. Integration Points

#### 5.1 Control Flow Integration

The arithmetic command should work seamlessly in:
- If conditions: `if ((x > 5)); then ... fi`
- While loops: `while ((i < 10)); do ... done`
- Until loops: `until ((i >= 10)); do ... done`
- Conditional execution: `((x > 0)) && echo "positive"`

#### 5.2 Variable Scope

- Use current scope for variable lookup
- Assignments affect the current scope
- Special variables like `$?` should be updated

### 6. Testing Strategy

#### 6.1 Unit Tests

Create `tests/test_arithmetic_command.py`:
```python
class TestArithmeticCommand(unittest.TestCase):
    def test_basic_evaluation(self):
        """Test basic arithmetic command evaluation."""
        # ((5 > 3)) should return 0
        # ((0)) should return 1
        
    def test_variable_assignment(self):
        """Test variable assignments in arithmetic."""
        # ((x = 5))
        # Verify x is set to 5
        
    def test_compound_assignments(self):
        """Test +=, -=, etc."""
        # x=5; ((x += 3))
        # Verify x is 8
        
    def test_in_conditionals(self):
        """Test in if/while conditions."""
        # if ((x > 5)); then echo yes; fi
        
    def test_multiple_expressions(self):
        """Test comma operator."""
        # ((a=1, b=2, c=a+b))
```

#### 6.2 Integration Tests

The 5 xfailed tests in `test_c_style_for_loops.py` should pass:
- `test_empty_condition`
- `test_empty_update` 
- `test_all_empty`
- `test_break_in_c_style_for`
- `test_continue_in_c_style_for`

### 7. Implementation Order

1. **Phase 1: Core Implementation**
   - Add ArithmeticCommand AST node
   - Add DOUBLE_LPAREN token type
   - Implement basic parser support
   - Create ArithmeticCommandExecutor

2. **Phase 2: Integration**
   - Update ExecutorManager dispatcher
   - Integrate with shell state for variables
   - Handle error cases gracefully

3. **Phase 3: Testing**
   - Write comprehensive unit tests
   - Remove xfail decorators from C-style for loop tests
   - Add integration tests for complex scenarios

4. **Phase 4: Polish**
   - Ensure proper error messages
   - Update documentation
   - Add examples to demo files

## Potential Challenges

### 1. Token Ambiguity
- Need to distinguish `((` for arithmetic from `(` `(` for subshells
- Solution: Look ahead for valid arithmetic expression patterns

### 2. Parser Complexity
- Nested parentheses in expressions
- Solution: Reuse existing arithmetic parsing logic from C-style for loops

### 3. Variable Type Conversion
- Shell variables are strings, arithmetic needs integers
- Solution: Use existing conversion logic from arithmetic evaluator

### 4. Error Handling
- Invalid expressions should not crash the shell
- Solution: Catch exceptions and return exit code 1 with error message

## Success Criteria

1. All 5 xfailed C-style for loop tests pass
2. Arithmetic commands work in all control structures
3. Variable assignments persist correctly
4. Exit codes match bash behavior (0 for non-zero, 1 for zero)
5. Error messages are clear and helpful

## Estimated Effort

- **Core Implementation**: 2-3 hours
- **Testing & Debugging**: 1-2 hours
- **Documentation**: 30 minutes
- **Total**: 3.5-5.5 hours

## Next Steps

1. Review this plan with the team
2. Create feature branch
3. Implement in phases as outlined
4. Submit PR with comprehensive tests