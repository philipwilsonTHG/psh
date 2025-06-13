# C-style For Loop Implementation Plan for PSH

## Overview

This document outlines the implementation plan for adding C-style for loops to PSH. C-style for loops use the syntax `for ((init; condition; update))` and provide arithmetic-based iteration, completing the full set of iteration constructs in PSH.

## Current State

- PSH has traditional for loops: `for var in list; do ...; done`
- PSH has a complete arithmetic expansion system (v0.18.0) that can evaluate complex expressions
- The arithmetic system supports all operators, variable assignment, and increment/decrement
- Break and continue statements are already implemented for loop control

## Requirements

### Syntax Support
```bash
# Basic counter
for ((i=0; i<10; i++)); do echo $i; done

# Multiple variables
for ((i=0, j=10; i<5; i++, j--)); do echo "$i $j"; done

# Using existing variables
n=5; for ((i=0; i<n; i++)); do echo $i; done

# Empty sections
i=0; for ((; i<5; )); do echo $i; ((i++)); done

# Complex expressions
for ((i=1; i<=100; i*=2)); do echo $i; done
```

### Features
1. Three arithmetic expressions: initialization, condition, update
2. Support for empty sections (any or all can be omitted)
3. Multiple comma-separated expressions in each section
4. Integration with existing arithmetic evaluator
5. Support for break/continue statements
6. Support for I/O redirections on the loop
7. Proper variable scoping (bash-compatible)

## Architecture Overview

```mermaid
graph TD
    A[Parser detects 'for'] --> B{Next tokens?}
    B -->|'(('| C[Parse C-style for]
    B -->|WORD 'in'| D[Parse traditional for]
    
    C --> E[Parse init expression]
    E --> F[Parse condition expression]
    F --> G[Parse update expression]
    G --> H[Parse loop body]
    
    H --> I[CStyleForStatement AST]
    I --> J[ControlFlowExecutor]
    
    J --> K[Evaluate init once]
    K --> L{Check condition}
    L -->|true| M[Execute body]
    M --> N[Evaluate update]
    N --> L
    L -->|false| O[Exit loop]
    
    E --> P[ArithmeticEvaluator]
    F --> P
    G --> P
    N --> P
```

## Implementation Details

### 1. AST Node Definition

Create a new AST node in `ast_nodes.py`:

```python
@dataclass
class CStyleForStatement(Statement):
    """C-style for loop: for ((init; condition; update))"""
    init_expr: Optional[str]      # Initialization expression (can be empty)
    condition_expr: Optional[str] # Condition expression (can be empty)  
    update_expr: Optional[str]    # Update expression (can be empty)
    body: StatementList           # Loop body
    redirects: List[Redirect] = field(default_factory=list)
```

### 2. Parser Modifications

#### Update `parse_for_statement` in `parser.py`:

```python
def parse_for_statement(self) -> Union[ForStatement, CStyleForStatement]:
    """Parse for loop (traditional or C-style)."""
    self.expect(TokenType.FOR)
    
    # Check if it's a C-style for loop
    if self.current_token.type == TokenType.DOUBLE_LPAREN:
        return self._parse_c_style_for()
    else:
        return self._parse_traditional_for()
```

#### Add C-style parsing method:

```python
def _parse_c_style_for(self) -> CStyleForStatement:
    """Parse C-style for ((init; condition; update))"""
    self.expect(TokenType.DOUBLE_LPAREN)
    
    # Parse initialization (optional)
    init_expr = self._parse_arithmetic_section(';')
    
    # Parse condition (optional) 
    condition_expr = self._parse_arithmetic_section(';')
    
    # Parse update (optional)
    update_expr = self._parse_arithmetic_section(')')
    
    self.expect(TokenType.DOUBLE_RPAREN)
    
    # Skip optional DO
    if self.current_token.type == TokenType.DO:
        self.advance()
    
    # Parse loop body
    body = self._parse_loop_body()
    
    # Parse redirects
    redirects = self._parse_redirects()
    
    return CStyleForStatement(init_expr, condition_expr, update_expr, body, redirects)

def _parse_arithmetic_section(self, terminator: str) -> Optional[str]:
    """Parse arithmetic expression section until terminator."""
    expr_parts = []
    paren_depth = 0
    
    while self.current_token:
        if paren_depth == 0 and self.current_token.value == terminator:
            break
            
        if self.current_token.type == TokenType.LPAREN:
            paren_depth += 1
        elif self.current_token.type == TokenType.RPAREN:
            if paren_depth == 0 and terminator == ')':
                break
            paren_depth -= 1
            
        expr_parts.append(self.current_token.value)
        self.advance()
    
    return ''.join(expr_parts).strip() if expr_parts else None
```

### 3. Executor Implementation

Add to `ControlFlowExecutor` in `control_flow.py`:

```python
def execute_c_style_for(self, node: CStyleForStatement) -> int:
    """Execute C-style for loop."""
    # Apply redirections
    if node.redirects:
        saved_fds = self.io_manager.apply_redirections(node.redirects)
    else:
        saved_fds = None
    
    try:
        # Execute initialization
        if node.init_expr:
            self._evaluate_arithmetic(node.init_expr)
        
        last_status = 0
        
        while True:
            try:
                # Check condition (empty means true)
                if node.condition_expr:
                    result = self._evaluate_arithmetic(node.condition_expr)
                    if result == 0:
                        break
                
                # Execute body
                last_status = self.shell.execute_command_list(node.body)
                
                # Execute update (except when breaking)
                if node.update_expr:
                    self._evaluate_arithmetic(node.update_expr)
                    
            except LoopBreak as e:
                if e.level > 1:
                    raise LoopBreak(e.level - 1)
                break
            except LoopContinue as e:
                if e.level > 1:
                    raise LoopContinue(e.level - 1)
                # Execute update before continuing
                if node.update_expr:
                    self._evaluate_arithmetic(node.update_expr)
                continue
        
        return last_status
    finally:
        if saved_fds:
            self.io_manager.restore_redirections(saved_fds)

def _evaluate_arithmetic(self, expr: str) -> int:
    """Evaluate arithmetic expression using shell's arithmetic system."""
    from ..arithmetic import ArithmeticEvaluator
    evaluator = ArithmeticEvaluator(self.shell)
    return evaluator.evaluate(expr)
```

### 4. Token Updates

Ensure the tokenizer properly handles `((` after `for` keyword. The state machine lexer should already support this, but we may need to verify context-aware tokenization.

### 5. Integration Points

1. **Arithmetic Evaluator**: Reuse existing `ArithmeticEvaluator` class
2. **Variable Management**: Arithmetic evaluator handles variable assignments
3. **Loop Control**: Existing break/continue exception mechanism
4. **I/O Redirection**: Existing redirection infrastructure
5. **Statement Execution**: Existing `execute_command_list` for body

## Testing Strategy

### Unit Tests

1. **Basic Functionality**
   - Simple counter loops
   - Loops with different operators (++, +=, *=)
   - Empty section handling
   
2. **Complex Expressions**
   - Multiple variables in init/update
   - Complex conditions
   - Nested arithmetic expressions
   
3. **Control Flow**
   - Break at various points
   - Continue with update execution
   - Nested loops
   
4. **Edge Cases**
   - All sections empty
   - Very large iterations
   - Invalid expressions
   
5. **Integration**
   - I/O redirection on loops
   - Variable scoping
   - Mixing with traditional for loops

### Test Examples

```python
def test_basic_c_style_for():
    """Test basic C-style for loop."""
    output = shell.run_command('for ((i=0; i<5; i++)); do echo $i; done')
    assert output == "0\n1\n2\n3\n4\n"

def test_multiple_variables():
    """Test C-style for with multiple variables."""
    output = shell.run_command('for ((i=0, j=10; i<3; i++, j--)); do echo "$i $j"; done')
    assert output == "0 10\n1 9\n2 8\n"

def test_empty_sections():
    """Test C-style for with empty sections."""
    output = shell.run_command('i=0; for ((; i<3; )); do echo $i; ((i++)); done')
    assert output == "0\n1\n2\n"

def test_break_continue():
    """Test break and continue in C-style for."""
    cmd = '''
    for ((i=0; i<10; i++)); do
        if ((i == 3)); then continue; fi
        if ((i == 6)); then break; fi
        echo $i
    done
    '''
    output = shell.run_command(cmd)
    assert output == "0\n1\n2\n4\n5\n"
```

## Implementation Phases

### Phase 1: Basic Implementation
- AST node definition
- Parser modifications for basic syntax
- Simple executor implementation
- Basic tests

### Phase 2: Full Feature Support
- Empty section handling
- Multiple comma-separated expressions
- Complex arithmetic expressions
- Break/continue integration

### Phase 3: Polish and Edge Cases
- I/O redirection support
- Error handling and messages
- Performance optimization
- Comprehensive test coverage

### Phase 4: Documentation
- Update grammar documentation
- Add examples to README
- Update CLAUDE.md and TODO.md
- Create user-facing documentation

## Success Criteria

1. All bash-compatible C-style for loop syntax works correctly
2. Seamless integration with existing arithmetic system
3. Proper handling of break/continue statements
4. No regression in existing for loop functionality
5. Comprehensive test coverage (>95%)
6. Clear error messages for invalid syntax
7. Performance comparable to traditional for loops

## Future Considerations

After implementing C-style for loops, consider:
- Optimization for common patterns (simple counters)
- Integration with future array support
- Enhanced debugging output for loop iterations
- Performance profiling for large iterations

## References

- Bash Reference Manual: Looping Constructs
- PSH Arithmetic System (v0.18.0)
- PSH Control Flow Architecture