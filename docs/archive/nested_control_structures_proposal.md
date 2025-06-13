# Architectural Proposal: Support for Arbitrarily Nested Control Structures

## Current Limitation

The current PSH architecture cannot support nested control structures (e.g., `if` inside `for`, `while` inside `if`) due to fundamental limitations in the AST design. The issue stems from how the parser and AST nodes are structured:

1. **CommandList limitation**: The `CommandList` node only contains `AndOrList` items (plus `BreakStatement` and `ContinueStatement`), which can only contain pipelines of simple commands.

2. **Control structure isolation**: Control structures (`IfStatement`, `WhileStatement`, `ForStatement`, `CaseStatement`) are only parsed at the top level or within function bodies. They cannot appear within the body of other control structures.

3. **Parser restriction**: The parsing methods for control structure bodies (`parse_and_or_list`) only look for simple commands, not other control structures.

## Root Cause Analysis

The core issue is that the current architecture has two separate parsing paths:

1. **Top-level parsing** (in `parse()`): Can handle functions, control structures, and command lists
2. **Command list parsing** (in `parse_command_list()` and within control structures): Can only handle simple commands and pipelines

This separation prevents control structures from being recognized within other control structures.

## Proposed Solution

### 1. Unified Statement Node

Create a new `Statement` type that can represent any executable construct:

```python
@dataclass
class Statement(ASTNode):
    """Base class for all statements"""
    pass

# Make all executable nodes inherit from Statement
class Command(Statement): ...
class Pipeline(Statement): ...
class AndOrList(Statement): ...
class IfStatement(Statement): ...
class WhileStatement(Statement): ...
class ForStatement(Statement): ...
class CaseStatement(Statement): ...
class BreakStatement(Statement): ...
class ContinueStatement(Statement): ...
class FunctionDef(Statement): ...
```

### 2. Enhanced CommandList

Replace the current `CommandList` with a more flexible structure:

```python
@dataclass
class StatementList(ASTNode):
    """A list of statements that can contain any type of statement"""
    statements: List[Statement] = field(default_factory=list)
    
    # For backward compatibility
    @property
    def and_or_lists(self):
        """Extract AndOrList items for backward compatibility"""
        return [s for s in self.statements if isinstance(s, AndOrList)]
    
    @property
    def pipelines(self):
        """Extract all pipelines for backward compatibility"""
        pipelines = []
        for stmt in self.statements:
            if isinstance(stmt, AndOrList):
                pipelines.extend(stmt.pipelines)
        return pipelines

# Keep CommandList as an alias for backward compatibility
CommandList = StatementList
```

### 3. Unified Parser Methods

Replace the multiple parsing methods with a unified approach:

```python
def parse_statement(self) -> Statement:
    """Parse any type of statement"""
    # Skip leading newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    # Check what type of statement this is
    if self._is_function_def():
        return self.parse_function_def()
    elif self.match(TokenType.IF):
        return self.parse_if_statement()
    elif self.match(TokenType.WHILE):
        return self.parse_while_statement()
    elif self.match(TokenType.FOR):
        return self.parse_for_statement()
    elif self.match(TokenType.CASE):
        return self.parse_case_statement()
    elif self.match(TokenType.BREAK):
        return self.parse_break_statement()
    elif self.match(TokenType.CONTINUE):
        return self.parse_continue_statement()
    else:
        # Parse as a command/pipeline/and-or list
        return self.parse_and_or_list()

def parse_statement_list(self, terminators: List[TokenType] = None) -> StatementList:
    """Parse a list of statements until we hit one of the terminators or EOF"""
    if terminators is None:
        terminators = [TokenType.EOF]
    
    stmt_list = StatementList()
    
    while not self.match(*terminators) and not self.match(TokenType.EOF):
        stmt = self.parse_statement()
        stmt_list.statements.append(stmt)
        
        # Handle separators
        while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
            self.advance()
            # Check if we've hit a terminator after separator
            if self.match(*terminators):
                break
    
    return stmt_list
```

### 4. Update Control Structure Parsing

Modify control structure parsing to use the new unified methods:

```python
def parse_if_statement(self) -> IfStatement:
    """Parse if/then/else/fi with support for nested structures"""
    self.expect(TokenType.IF)
    
    # Parse condition using statement list
    condition = self.parse_statement_list([TokenType.THEN])
    self.expect(TokenType.THEN)
    
    # Parse then part with full statement support
    then_part = self.parse_statement_list([TokenType.ELSE, TokenType.FI])
    
    # Parse optional else part
    else_part = None
    if self.match(TokenType.ELSE):
        self.advance()
        else_part = self.parse_statement_list([TokenType.FI])
    
    self.expect(TokenType.FI)
    return IfStatement(condition, then_part, else_part)

# Similar updates for while, for, and case statements
```

### 5. Update Execution Engine

The execution engine needs minor updates to handle the new structure:

```python
def execute_statement_list(self, stmt_list: StatementList):
    """Execute a list of statements"""
    exit_code = 0
    
    for stmt in stmt_list.statements:
        if isinstance(stmt, AndOrList):
            exit_code = self.execute_and_or_list(stmt)
        elif isinstance(stmt, IfStatement):
            exit_code = self.execute_if_statement(stmt)
        elif isinstance(stmt, WhileStatement):
            exit_code = self.execute_while_statement(stmt)
        elif isinstance(stmt, ForStatement):
            exit_code = self.execute_for_statement(stmt)
        elif isinstance(stmt, CaseStatement):
            exit_code = self.execute_case_statement(stmt)
        elif isinstance(stmt, BreakStatement):
            raise LoopBreak()
        elif isinstance(stmt, ContinueStatement):
            raise LoopContinue()
        elif isinstance(stmt, FunctionDef):
            self.function_manager.define_function(stmt.name, stmt.body)
            exit_code = 0
        
        self.last_exit_code = exit_code
    
    return exit_code
```

## Migration Strategy

### Phase 1: Add New Infrastructure
1. Add `Statement` base class
2. Add `StatementList` with compatibility properties
3. Add unified parser methods alongside existing ones

### Phase 2: Update Parsers
1. Update control structure parsers to use `parse_statement_list`
2. Ensure backward compatibility by maintaining the same AST structure

### Phase 3: Update Execution
1. Add `execute_statement_list` method
2. Update existing execution methods to delegate to the new method

### Phase 4: Testing and Validation
1. Ensure all existing tests pass
2. Add new tests for nested control structures
3. Verify backward compatibility

### Phase 5: Cleanup
1. Remove old parsing methods
2. Update documentation

## Benefits

1. **Full nesting support**: Any control structure can contain any other control structure
2. **Cleaner architecture**: Single unified parsing path instead of multiple special cases
3. **Better extensibility**: Easy to add new statement types in the future
4. **Backward compatibility**: Existing code continues to work with compatibility properties

## Example: Nested Control Structures

With this architecture, the following complex nested structures become possible:

```bash
# Nested if inside for
for file in *.txt; do
    if [ -f "$file" ]; then
        while read line; do
            case "$line" in
                error:*)
                    echo "Found error in $file: $line"
                    if [ "$STOP_ON_ERROR" = "true" ]; then
                        break 2  # Break out of both loops
                    fi
                    ;;
                warning:*)
                    echo "Warning in $file: $line"
                    ;;
            esac
        done < "$file"
    fi
done

# Function with nested control structures
process_data() {
    for item in "$@"; do
        if [ -n "$item" ]; then
            case "$item" in
                *.json)
                    while [ -f "$item.lock" ]; do
                        sleep 1
                    done
                    process_json "$item"
                    ;;
                *.xml)
                    if validate_xml "$item"; then
                        process_xml "$item"
                    else
                        return 1
                    fi
                    ;;
            esac
        fi
    done
}
```

## Implementation Timeline

1. **Week 1**: Implement Statement base class and StatementList
2. **Week 2**: Add unified parser methods
3. **Week 3**: Update control structure parsers
4. **Week 4**: Update execution engine
5. **Week 5**: Testing and validation
6. **Week 6**: Documentation and cleanup

## Risks and Mitigation

1. **Risk**: Breaking existing functionality
   - **Mitigation**: Extensive testing, gradual migration, compatibility properties

2. **Risk**: Performance impact
   - **Mitigation**: The new structure is actually simpler and should have minimal impact

3. **Risk**: Complex migration
   - **Mitigation**: Phased approach, keeping old code working during transition

## Conclusion

This architectural change addresses the fundamental limitation preventing nested control structures in PSH. By unifying the parsing and execution of all statement types, we create a more flexible and extensible shell that can handle arbitrarily complex nested structures while maintaining backward compatibility and educational clarity.