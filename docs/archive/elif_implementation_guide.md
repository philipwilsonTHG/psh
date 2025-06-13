# elif Implementation Guide

## Quick Start

This guide provides step-by-step instructions to implement elif support in psh, which will immediately improve the control structures pass rate.

## Current vs Target Syntax

**Current (working)**:
```bash
if [ condition1 ]; then
    echo "one"
else
    if [ condition2 ]; then
        echo "two"
    else
        echo "three"
    fi
fi
```

**Target (not working)**:
```bash
if [ condition1 ]; then
    echo "one"
elif [ condition2 ]; then
    echo "two"
elif [ condition3 ]; then
    echo "three"
else
    echo "default"
fi
```

## Implementation Steps

### 1. Add ELIF Token

**File**: `psh/tokenizer.py`

```python
# In class TokenType, add:
ELIF = "ELIF"

# In tokenizer's keyword detection (around line 507):
elif word == 'elif' and self.is_keyword_context(word):
    self.tokens.append(Token(TokenType.ELIF, word, start_pos))

# Update is_keyword_context to include elif:
elif word in ['then', 'else', 'elif', 'fi', 'do', 'done', 'in', 'break', 'continue', 'esac']:
    # elif is a keyword after newlines, semicolons, or then/else
    return last_token.type in [
        TokenType.SEMICOLON, TokenType.NEWLINE, 
        TokenType.AND_AND, TokenType.OR_OR,
        TokenType.PIPE, TokenType.LBRACE, 
        TokenType.THEN, TokenType.ELSE
    ]
```

### 2. Extend AST Node

**File**: `psh/ast_nodes.py`

```python
# Current IfStatement:
class IfStatement:
    def __init__(self, condition, then_part, else_part=None):
        self.condition = condition
        self.then_part = then_part
        self.else_part = else_part
        self.redirects = []

# New IfStatement with elif support:
class IfStatement:
    def __init__(self, condition, then_part, elif_parts=None, else_part=None):
        self.condition = condition
        self.then_part = then_part
        self.elif_parts = elif_parts or []  # List of (condition, then_part) tuples
        self.else_part = else_part
        self.redirects = []
```

### 3. Update Parser

**File**: `psh/parser.py`

```python
def parse_if_statement(self):
    self.advance()  # Skip 'if'
    
    # Parse condition
    condition = self.parse_command_list()
    
    # Expect 'then'
    if not self.current_token or self.current_token.type != TokenType.THEN:
        self.error(f"Expected THEN after if condition, got {self.current_token.type if self.current_token else 'EOF'}")
    self.advance()  # Skip 'then'
    
    # Parse then part
    then_part = self.parse_command_list()
    
    # Parse elif clauses
    elif_parts = []
    while self.current_token and self.current_token.type == TokenType.ELIF:
        self.advance()  # Skip 'elif'
        
        # Parse elif condition
        elif_condition = self.parse_command_list()
        
        # Expect 'then'
        if not self.current_token or self.current_token.type != TokenType.THEN:
            self.error(f"Expected THEN after elif condition")
        self.advance()  # Skip 'then'
        
        # Parse elif then part
        elif_then = self.parse_command_list()
        
        elif_parts.append((elif_condition, elif_then))
    
    # Parse optional else
    else_part = None
    if self.current_token and self.current_token.type == TokenType.ELSE:
        self.advance()  # Skip 'else'
        else_part = self.parse_command_list()
    
    # Expect 'fi'
    if not self.current_token or self.current_token.type != TokenType.FI:
        self.error(f"Expected FI to close if statement")
    self.advance()  # Skip 'fi'
    
    return IfStatement(condition, then_part, elif_parts, else_part)
```

### 4. Update Execution

**File**: `psh/shell.py`

```python
def execute_if_statement(self, if_stmt: IfStatement):
    """Execute if/elif/else statement."""
    # Apply any redirections
    saved_fds = self._apply_redirections(if_stmt.redirects)
    
    try:
        # Evaluate main condition
        exit_code = self.execute_command_list(if_stmt.condition)
        
        if exit_code == 0:
            # Condition true - execute then part
            return self.execute_command_list(if_stmt.then_part)
        
        # Check elif conditions in order
        for elif_condition, elif_then in if_stmt.elif_parts:
            exit_code = self.execute_command_list(elif_condition)
            if exit_code == 0:
                # This elif condition is true
                return self.execute_command_list(elif_then)
        
        # All conditions false - execute else part if present
        if if_stmt.else_part:
            return self.execute_command_list(if_stmt.else_part)
        
        return 0  # No else clause, return success
    
    finally:
        self._restore_redirections(saved_fds)
```

### 5. Update AST Formatter (for debugging)

**File**: `psh/shell.py` (in _format_ast method)

```python
elif isinstance(node, IfStatement):
    result = f"{spaces}IfStatement:\n"
    result += f"{spaces}  Condition:\n"
    result += self._format_ast(node.condition, indent + 2)
    result += f"{spaces}  Then:\n"
    result += self._format_ast(node.then_part, indent + 2)
    
    # Format elif clauses
    for i, (elif_cond, elif_then) in enumerate(node.elif_parts):
        result += f"{spaces}  Elif {i+1} Condition:\n"
        result += self._format_ast(elif_cond, indent + 2)
        result += f"{spaces}  Elif {i+1} Then:\n"
        result += self._format_ast(elif_then, indent + 2)
    
    if node.else_part:
        result += f"{spaces}  Else:\n"
        result += self._format_ast(node.else_part, indent + 2)
    return result
```

## Testing

### Basic elif Test
```bash
if [ 1 -eq 2 ]; then
    echo "one"
elif [ 2 -eq 2 ]; then
    echo "two"
else
    echo "three"
fi
# Should output: two
```

### Multiple elif Test
```bash
x=3
if [ $x -eq 1 ]; then
    echo "one"
elif [ $x -eq 2 ]; then
    echo "two"  
elif [ $x -eq 3 ]; then
    echo "three"
elif [ $x -eq 4 ]; then
    echo "four"
else
    echo "other"
fi
# Should output: three
```

### Nested with elif
```bash
if [ -f /etc/passwd ]; then
    if [ -r /etc/passwd ]; then
        echo "readable"
    elif [ -w /etc/passwd ]; then
        echo "writable"
    fi
elif [ -f /etc/group ]; then
    echo "group file"
fi
```

## Common Pitfalls

1. **Token Context**: elif should only be recognized as a keyword after then/else/newline/semicolon
2. **Empty elif_parts**: Make sure to handle if statements with no elif clauses (backward compatibility)
3. **Nested Parsing**: elif can contain complex command lists including nested if statements
4. **Short Circuit**: Only evaluate conditions until one is true

## Verification

After implementation:
1. Run the elif tests from test_control_structures.py
2. Check that existing if/else tests still pass
3. Test with complex conditions (pipelines, &&, ||)
4. Test with redirections on the if statement

This implementation should increase the pass rate by ~4% (2 out of 54 tests).