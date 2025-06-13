# Architectural Changes for `while read` Pattern Support

## Current State

The `while read` pattern partially works in psh:

✅ **Works**: `echo "data" | while read line; do ...; done`
❌ **Fails**: `while read line; do ...; done < file.txt`

## Problem Analysis

### 1. Grammar Limitation
The current grammar defines:
```
while_stmt → 'while' command_list 'do' command_list 'done'
```

This doesn't allow redirections on the while statement itself. In bash, control structures (while, for, if) can have redirections applied to the entire construct.

### 2. Parser Structure
The parser correctly parses `while read line` as:
- `while` keyword
- Command list containing a single command: `read line`
- `do` keyword
- Body commands
- `done` keyword

However, it doesn't expect or handle redirections after `done`.

## Recommended Architecture Changes

### Option 1: Extend Control Structure Grammar (Recommended)

**Grammar Changes:**
```
# Current
while_stmt → 'while' command_list 'do' command_list 'done'
for_stmt   → 'for' WORD 'in' word_list 'do' command_list 'done'
if_stmt    → 'if' command_list 'then' command_list ['else' command_list] 'fi'

# Proposed
while_stmt → 'while' command_list 'do' command_list 'done' redirect*
for_stmt   → 'for' WORD 'in' word_list 'do' command_list 'done' redirect*
if_stmt    → 'if' command_list 'then' command_list ['else' command_list] 'fi' redirect*
```

**Implementation Steps:**

1. **Update AST Nodes** (ast_nodes.py):
```python
@dataclass
class WhileStatement(Statement):
    condition: CommandList
    body: CommandList
    redirections: List[Redirection] = field(default_factory=list)

@dataclass
class ForStatement(Statement):
    variable: str
    iterable: List[str]
    body: CommandList
    redirections: List[Redirection] = field(default_factory=list)

@dataclass 
class IfStatement(Statement):
    condition: CommandList
    then_body: CommandList
    else_body: Optional[CommandList] = None
    redirections: List[Redirection] = field(default_factory=list)
```

2. **Update Parser** (parser.py):
```python
def parse_while_statement(self) -> WhileStatement:
    # ... existing code ...
    
    # Consume 'done'
    self.expect(TokenType.DONE)
    
    # NEW: Parse optional redirections
    redirections = []
    while self.match(TokenType.LESS, TokenType.GREATER, 
                     TokenType.GREATER_GREATER, TokenType.LESS_LESS):
        redirections.append(self.parse_redirection())
    
    return WhileStatement(condition, body, redirections)
```

3. **Update Executor** (shell.py):
```python
def execute_while_statement(self, while_stmt: WhileStatement) -> int:
    # NEW: Setup redirections if present
    if while_stmt.redirections:
        saved_fds = self._apply_redirections(while_stmt.redirections)
    
    try:
        last_exit = 0
        while True:
            # Execute condition
            condition_exit = self.execute_command_list(while_stmt.condition)
            
            if condition_exit != 0:
                break
                
            # Execute body
            try:
                last_exit = self.execute_command_list(while_stmt.body)
            except LoopBreak:
                break
            except LoopContinue:
                continue
                
        return last_exit
    finally:
        # NEW: Restore file descriptors
        if while_stmt.redirections:
            self._restore_fds(saved_fds)
```

### Option 2: Treat Control Structures as Commands

An alternative approach would be to treat control structures as special commands that can have redirections. This is closer to how bash actually implements it internally.

**Pros:**
- More consistent with POSIX shell semantics
- Allows redirections on any compound command
- Enables patterns like `{ cmd1; cmd2; } > output.txt`

**Cons:**
- Requires significant parser refactoring
- More complex AST structure
- Harder to understand for educational purposes

### Option 3: Minimal Change - Special Case in Parser

A quick fix would be to special-case the parsing of control structures to look for redirections after the closing keyword:

```python
def parse_statement(self) -> Optional[Statement]:
    # ... existing code ...
    
    if self.match(TokenType.WHILE):
        stmt = self.parse_while_statement()
        # Check for redirections after statement
        if self.match(TokenType.LESS, TokenType.GREATER, ...):
            # Wrap in a redirected command
            return RedirectedStatement(stmt, self.parse_redirections())
        return stmt
```

**Pros:**
- Minimal code changes
- Doesn't break existing functionality

**Cons:**
- Adds complexity to the parser
- Not as clean architecturally

## Recommendation

**Implement Option 1** - Extend the grammar to allow redirections on control structures. This approach:

1. Maintains educational clarity
2. Follows a clean architectural pattern
3. Enables the common `while read` pattern
4. Can be extended to other control structures (for, if, case)
5. Aligns with how users expect shells to behave

## Testing Strategy

After implementation, ensure these patterns work:

```bash
# Basic while read from file
while read line; do echo "$line"; done < input.txt

# While read with multiple redirections  
while read line; do echo "$line"; done < input.txt > output.txt

# Nested loops with redirections
for i in 1 2; do
    while read line; do 
        echo "Run $i: $line"
    done < data.txt
done > results.txt

# If statement with redirections
if [ -f "test.txt" ]; then
    cat test.txt
else
    echo "File not found"
fi > output.txt 2>&1
```

## Impact on Existing Code

- No breaking changes to existing functionality
- Tests using control structures without redirections continue to work
- New tests can be added for redirected control structures
- The `while read` pattern becomes fully supported

## Implementation Priority

Given that:
- The read builtin is already implemented
- Many shell scripts use the `while read` pattern
- The change is architecturally clean

This should be considered a **high priority** enhancement that would significantly improve psh's bash compatibility and usefulness for real-world scripts.