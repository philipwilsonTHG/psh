# NOT Operator (!) Implementation Guide

## Overview

The NOT operator (!) is used to negate command exit status and test conditions. This is a high-impact, low-complexity improvement.

## Two Contexts for NOT

### 1. Command Negation
```bash
! command
# Inverts exit status: 0 becomes 1, non-zero becomes 0

! grep pattern file.txt
# Returns 0 if pattern NOT found, 1 if found

if ! [ -f file.txt ]; then
    echo "File does not exist"
fi
```

### 2. Test Condition Negation
```bash
[ ! -f file.txt ]    # True if file does NOT exist
[ ! -z "$var" ]      # True if var is NOT empty
[ ! "$a" = "$b" ]    # True if a does NOT equal b
```

## Implementation

### 1. Add EXCLAMATION Token

**File**: `psh/tokenizer.py`

```python
# In TokenType enum:
EXCLAMATION = "EXCLAMATION"

# In tokenize() method, add this case:
elif char == '!':
    # Check if it's != (not implemented yet)
    if self.peek_char() == '=':
        # This would be for != operator in [[ ]] (future)
        self.tokens.append(Token(TokenType.EXCLAMATION, '!', start_pos))
        self.advance()
    else:
        self.tokens.append(Token(TokenType.EXCLAMATION, '!', start_pos))
        self.advance()
```

### 2. Extend Pipeline AST

**File**: `psh/ast_nodes.py`

```python
class Pipeline:
    def __init__(self, commands):
        self.commands = commands
        self.negated = False  # Add this field
```

### 3. Update Parser

**File**: `psh/parser.py`

```python
def parse_pipeline(self):
    """Parse a pipeline, possibly prefixed with !"""
    negated = False
    
    # Check for leading !
    if self.current_token and self.current_token.type == TokenType.EXCLAMATION:
        negated = True
        self.advance()  # Skip !
    
    # Parse the actual pipeline
    commands = []
    commands.append(self.parse_command())
    
    while self.current_token and self.current_token.type == TokenType.PIPE:
        self.advance()  # Skip |
        commands.append(self.parse_command())
    
    pipeline = Pipeline(commands)
    pipeline.negated = negated
    return pipeline
```

### 4. Update Execution

**File**: `psh/shell.py`

```python
def execute_pipeline(self, pipeline: Pipeline):
    # ... existing pipeline execution code ...
    
    # Get the exit status
    if len(pipeline.commands) == 1:
        exit_status = self.execute_command(pipeline.commands[0])
    else:
        # ... multi-command pipeline execution ...
        exit_status = last_status
    
    # Apply negation if needed
    if pipeline.negated:
        exit_status = 0 if exit_status != 0 else 1
    
    return exit_status
```

### 5. Update Test Command for ! Inside [ ]

**File**: `psh/builtins/test_command.py`

```python
def execute(self, args: List[str], shell: 'Shell') -> int:
    # ... existing code ...
    
    # After checking for [ and removing ]
    if args[0] == '[':
        args = args[1:]  # Remove [
        if args[-1] == ']':
            args = args[:-1]  # Remove ]
    
    # Check for leading !
    negate = False
    if args and args[0] == '!':
        negate = True
        args = args[1:]  # Remove !
    
    # ... rest of test evaluation ...
    
    # Before returning result
    if negate:
        result = 0 if result != 0 else 1
    
    return result
```

## Testing

### Test Script
```bash
#!/bin/bash
# test_not_operator.sh

echo "Testing command negation:"
! false && echo "PASS: ! false returns 0"
! true || echo "PASS: ! true returns 1"

echo -e "\nTesting with grep:"
echo "hello" > /tmp/test.txt
! grep "world" /tmp/test.txt && echo "PASS: ! grep with no match"
! grep "hello" /tmp/test.txt || echo "PASS: ! grep with match"

echo -e "\nTesting in conditionals:"
if ! [ -f /nonexistent ]; then
    echo "PASS: if ! [ -f ... ]"
fi

if ! false; then
    echo "PASS: if ! false"
fi

echo -e "\nTesting inside [ ]:"
[ ! -f /nonexistent ] && echo "PASS: [ ! -f /nonexistent ]"
[ ! -z "text" ] && echo "PASS: [ ! -z 'text' ]"
[ ! 1 -eq 2 ] && echo "PASS: [ ! 1 -eq 2 ]"

rm -f /tmp/test.txt
```

## Edge Cases

1. **Double Negation**: `! ! command` should work (negating twice)
2. **With Pipelines**: `! cat file | grep pattern` - the ! applies to the entire pipeline
3. **With && and ||**: `! cmd1 && cmd2` - the ! only applies to cmd1
4. **Inside Functions**: Should work normally
5. **With Redirections**: `! command > file` - negation happens after redirections

## Common Mistakes

1. **Spacing**: `!command` vs `! command` - both should work in bash
2. **Precedence**: `! cmd1 | cmd2` negates the entire pipeline, not just cmd1
3. **Exit Status**: Remember that ! makes successful commands fail and vice versa

## Verification

After implementation:
```bash
# Should all print "Success"
! false && echo "Success"
[ ! -f /nonexistent ] && echo "Success"
! echo hello | grep -q world && echo "Success"
```

This implementation is simpler than elif and will immediately fix the "NOT in condition" test failure.