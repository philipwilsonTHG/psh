# Implementation Guide: Nested Control Structures

## Step-by-Step Code Changes

### Step 1: Update AST Nodes (ast_nodes.py)

```python
# Add at the top of ast_nodes.py after imports
class Statement(ASTNode):
    """Base class for all executable statements"""
    pass

# Update existing classes to inherit from Statement
@dataclass
class Command(Statement):  # Changed from ASTNode
    args: List[str] = field(default_factory=list)
    arg_types: List[str] = field(default_factory=list)
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False

@dataclass
class Pipeline(Statement):  # Changed from ASTNode
    commands: List[Command] = field(default_factory=list)

@dataclass  
class AndOrList(Statement):  # Changed from ASTNode
    pipelines: List[Pipeline] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)

# Control structures already inherit from ASTNode, change to Statement
@dataclass
class IfStatement(Statement):  # Changed from ASTNode
    condition: 'StatementList'  # Will be updated
    then_part: 'StatementList'  # Will be updated
    else_part: Optional['StatementList'] = None  # Will be updated

@dataclass
class WhileStatement(Statement):  # Changed from ASTNode
    condition: 'StatementList'  # Will be updated
    body: 'StatementList'  # Will be updated

@dataclass
class ForStatement(Statement):  # Changed from ASTNode
    variable: str
    iterable: List[str]
    body: 'StatementList'  # Will be updated

@dataclass
class CaseStatement(Statement):  # Changed from ASTNode
    expr: str
    items: List[CaseItem] = field(default_factory=list)

@dataclass
class BreakStatement(Statement):  # Changed from ASTNode
    pass

@dataclass
class ContinueStatement(Statement):  # Changed from ASTNode
    pass

@dataclass
class FunctionDef(Statement):  # Changed from ASTNode
    name: str
    body: 'StatementList'  # Will be updated

# Add new StatementList class
@dataclass
class StatementList(ASTNode):
    """A list of statements that can contain any type of statement"""
    statements: List[Statement] = field(default_factory=list)
    
    # Compatibility properties for gradual migration
    @property
    def and_or_lists(self):
        """Extract AndOrList items for backward compatibility"""
        result = []
        for stmt in self.statements:
            if isinstance(stmt, AndOrList):
                result.append(stmt)
            elif isinstance(stmt, (BreakStatement, ContinueStatement)):
                # These were stored directly in and_or_lists
                result.append(stmt)
        return result
    
    @and_or_lists.setter
    def and_or_lists(self, value):
        """Set statements from and_or_lists for backward compatibility"""
        self.statements = value
    
    @property
    def pipelines(self):
        """Extract all pipelines for backward compatibility"""
        pipelines = []
        for stmt in self.statements:
            if isinstance(stmt, AndOrList):
                pipelines.extend(stmt.pipelines)
        return pipelines

# Update CaseItem to use StatementList
@dataclass
class CaseItem(ASTNode):
    patterns: List[CasePattern] = field(default_factory=list)
    commands: StatementList = field(default_factory=lambda: StatementList())  # Changed
    terminator: str = ';;'

# Keep CommandList as alias during migration
CommandList = StatementList
```

### Step 2: Add Parser Helper Methods (parser.py)

Add these methods to the Parser class:

```python
def parse_statement(self) -> Statement:
    """Parse any type of statement (unified parsing)"""
    # Skip leading newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    # Check for end conditions
    if self.match(TokenType.EOF):
        # Return empty and-or list to handle empty statements
        return AndOrList()
    
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
        # Parse as and-or list (which includes simple commands and pipelines)
        return self.parse_and_or_list()

def parse_statement_list(self, terminators: List[TokenType] = None) -> StatementList:
    """Parse a list of statements until we hit one of the terminators or EOF"""
    if terminators is None:
        terminators = [TokenType.EOF]
    
    stmt_list = StatementList()
    
    # Skip leading newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    while not self.match(*terminators) and not self.match(TokenType.EOF):
        # Parse a statement
        stmt = self.parse_statement()
        
        # Only add non-empty statements
        if isinstance(stmt, AndOrList) and stmt.pipelines:
            stmt_list.statements.append(stmt)
        elif not isinstance(stmt, AndOrList):
            # Always add non-AndOrList statements
            stmt_list.statements.append(stmt)
        
        # Handle separators
        had_separator = False
        while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
            self.advance()
            had_separator = True
        
        # Check if we've hit a terminator
        if self.match(*terminators) or self.match(TokenType.EOF):
            break
        
        # If no separator and not at terminator, we might have a syntax error
        # unless we just parsed a control structure which doesn't require separators
        if not had_separator and isinstance(stmt, AndOrList):
            # Check if next token is valid continuation
            if not self.match(*terminators) and not self.match(TokenType.EOF):
                # This might be an error, but let the next iteration handle it
                pass
    
    return stmt_list
```

### Step 3: Update Control Structure Parsers

Update each control structure parser to use the new methods:

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

def parse_while_statement(self) -> WhileStatement:
    """Parse while/do/done with support for nested structures"""
    self.expect(TokenType.WHILE)
    
    # Parse condition using statement list
    condition = self.parse_statement_list([TokenType.DO])
    self.expect(TokenType.DO)
    
    # Parse body with full statement support
    body = self.parse_statement_list([TokenType.DONE])
    self.expect(TokenType.DONE)
    
    return WhileStatement(condition, body)

def parse_for_statement(self) -> ForStatement:
    """Parse for/in/do/done with support for nested structures"""
    self.expect(TokenType.FOR)
    
    # Skip newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    # Parse variable name
    var_token = self.expect(TokenType.WORD)
    variable = var_token.value
    
    # Skip newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    self.expect(TokenType.IN)
    
    # Skip newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    # Parse iterable list (words until 'do' or ';')
    iterable = []
    while not self.match(TokenType.DO) and not self.match(TokenType.SEMICOLON) and not self.match(TokenType.NEWLINE) and not self.match(TokenType.EOF):
        if self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE):
            token = self.advance()
            iterable.append(token.value)
        else:
            break
    
    # Handle separators
    while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
        self.advance()
    
    self.expect(TokenType.DO)
    
    # Parse body with full statement support
    body = self.parse_statement_list([TokenType.DONE])
    self.expect(TokenType.DONE)
    
    return ForStatement(variable, iterable, body)

def parse_case_statement(self) -> CaseStatement:
    """Parse case/esac with support for nested structures"""
    self.expect(TokenType.CASE)
    
    # Parse expression
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    if not self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE):
        raise ParseError("Expected expression after 'case'", self.peek())
    
    expr_token = self.advance()
    expr = expr_token.value
    
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    self.expect(TokenType.IN)
    
    # Parse case items
    items = []
    while not self.match(TokenType.ESAC) and not self.match(TokenType.EOF):
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        if self.match(TokenType.ESAC):
            break
        
        item = self.parse_case_item()
        items.append(item)
    
    self.expect(TokenType.ESAC)
    return CaseStatement(expr, items)

def parse_case_item(self) -> CaseItem:
    """Parse a single case item with nested statement support"""
    patterns = []
    
    # Parse first pattern
    pattern = self.parse_case_pattern()
    patterns.append(pattern)
    
    # Parse additional patterns separated by |
    while self.match(TokenType.PIPE):
        self.advance()
        pattern = self.parse_case_pattern()
        patterns.append(pattern)
    
    self.expect(TokenType.RPAREN)
    
    # Skip newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    # Parse commands with full statement support
    commands = self.parse_statement_list([TokenType.CASE_END, TokenType.CASE_FALL, TokenType.CASE_CONT, TokenType.ESAC])
    
    # Parse terminator
    terminator = ';;'  # default
    if self.match(TokenType.CASE_END):
        self.advance()
        terminator = ';;'
    elif self.match(TokenType.CASE_FALL):
        self.advance()
        terminator = ';&'
    elif self.match(TokenType.CASE_CONT):
        self.advance()
        terminator = ';;&'
    
    return CaseItem(patterns, commands, terminator)

def parse_function_def(self) -> FunctionDef:
    """Parse function definition with nested statement support"""
    name = None
    
    # Handle 'function' keyword if present
    if self.match(TokenType.FUNCTION):
        self.advance()
        if not self.match(TokenType.WORD):
            raise ParseError("Expected function name after 'function'", self.peek())
        name = self.advance().value
        
        # Optional parentheses
        if self.match(TokenType.LPAREN):
            self.advance()
            self.expect(TokenType.RPAREN)
    else:
        # POSIX style: name()
        if not self.match(TokenType.WORD):
            raise ParseError("Expected function name", self.peek())
        name = self.advance().value
        self.expect(TokenType.LPAREN)
        self.expect(TokenType.RPAREN)
    
    # Skip newlines before body
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    # Parse body as compound command with full statement support
    body = self.parse_compound_command_new()
    return FunctionDef(name, body)

def parse_compound_command_new(self) -> StatementList:
    """Parse a compound command { ... } with full statement support"""
    if not self.match(TokenType.LBRACE):
        raise ParseError("Expected '{' to start compound command", self.peek())
    
    self.advance()  # consume {
    
    # Parse statements until }
    stmt_list = self.parse_statement_list([TokenType.RBRACE])
    
    self.expect(TokenType.RBRACE)
    return stmt_list
```

### Step 4: Update Main Parse Method

```python
def parse(self) -> Union[StatementList, TopLevel]:
    """Main entry point for parsing"""
    # Check if we should use new parsing approach
    # Start with new approach for better nesting support
    
    top_level = TopLevel()
    
    # Skip leading newlines
    while self.match(TokenType.NEWLINE):
        self.advance()
    
    # Use new unified parsing
    stmt_list = self.parse_statement_list([TokenType.EOF])
    
    # For backward compatibility, check what we got
    if len(stmt_list.statements) == 0:
        return CommandList()  # Empty
    
    # If all statements are AndOrLists, return as CommandList for compatibility
    all_and_or = all(isinstance(s, (AndOrList, BreakStatement, ContinueStatement)) 
                     for s in stmt_list.statements)
    
    if all_and_or:
        # Return as CommandList for backward compatibility
        return stmt_list
    else:
        # We have mixed statements, return as TopLevel
        for stmt in stmt_list.statements:
            top_level.items.append(stmt)
        return top_level
```

### Step 5: Update Execution Engine (shell.py)

Add new execution method:

```python
def execute_statement_list(self, stmt_list: StatementList):
    """Execute a list of statements with full support for all statement types"""
    exit_code = 0
    
    try:
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
                try:
                    self.function_manager.define_function(stmt.name, stmt.body)
                    exit_code = 0
                except ValueError as e:
                    print(f"psh: {e}", file=sys.stderr)
                    exit_code = 1
            
            self.last_exit_code = exit_code
    except FunctionReturn:
        # Only catch FunctionReturn if we're in a function
        if self.function_stack:
            raise
        print("return: can only `return' from a function or sourced script", file=sys.stderr)
        return 1
    
    return exit_code
```

Update existing `execute_command_list` to delegate:

```python
def execute_command_list(self, command_list: CommandList):
    """Execute a command list - now delegates to execute_statement_list"""
    # For backward compatibility, convert and delegate
    if hasattr(command_list, 'statements'):
        return self.execute_statement_list(command_list)
    else:
        # Old-style CommandList with and_or_lists
        stmt_list = StatementList()
        stmt_list.statements = command_list.and_or_lists
        return self.execute_statement_list(stmt_list)
```

### Step 6: Testing Strategy

Create test cases for nested structures:

```python
# test_nested_control_structures.py
def test_if_inside_for():
    """Test if statement inside for loop"""
    shell = Shell()
    script = '''
    for i in 1 2 3; do
        if [ "$i" = "2" ]; then
            echo "Found 2"
        else
            echo "Not 2: $i"
        fi
    done
    '''
    # Expected output: "Not 2: 1\nFound 2\nNot 2: 3\n"

def test_while_inside_if():
    """Test while loop inside if statement"""
    shell = Shell()
    script = '''
    count=3
    if [ "$count" -gt 0 ]; then
        while [ "$count" -gt 0 ]; do
            echo "Count: $count"
            count=$((count - 1))
        done
    fi
    '''
    # Expected output: "Count: 3\nCount: 2\nCount: 1\n"

def test_case_inside_while_inside_for():
    """Test deeply nested control structures"""
    shell = Shell()
    script = '''
    for file in *.txt; do
        count=0
        while read line; do
            case "$line" in
                START*)
                    echo "Found start in $file"
                    ;;
                END*)
                    echo "Found end in $file"
                    break
                    ;;
            esac
            count=$((count + 1))
        done < "$file"
    done
    '''
    # Test with appropriate file setup

def test_function_with_nested_structures():
    """Test function containing nested control structures"""
    shell = Shell()
    script = '''
    process_items() {
        for item in "$@"; do
            if [ -n "$item" ]; then
                case "$item" in
                    *.txt)
                        while [ -f "$item.lock" ]; do
                            sleep 0.1
                        done
                        echo "Processing $item"
                        ;;
                    *)
                        echo "Skipping $item"
                        ;;
                esac
            fi
        done
    }
    
    process_items file1.txt file2.dat file3.txt
    '''
    # Expected: process .txt files, skip .dat file
```

## Migration Plan

### Phase 1: Foundation (Week 1)
1. Add Statement base class to ast_nodes.py
2. Add StatementList with compatibility properties
3. Update all AST nodes to inherit from Statement
4. Run all existing tests to ensure nothing breaks

### Phase 2: Parser Infrastructure (Week 2)
1. Add parse_statement() method
2. Add parse_statement_list() method
3. Add parse_compound_command_new() method
4. Test new methods in isolation

### Phase 3: Control Structure Updates (Week 3)
1. Update parse_if_statement() to use parse_statement_list()
2. Update parse_while_statement()
3. Update parse_for_statement()
4. Update parse_case_statement() and parse_case_item()
5. Update parse_function_def()

### Phase 4: Execution Updates (Week 4)
1. Add execute_statement_list() method
2. Update execute_command_list() to delegate
3. Test execution of nested structures

### Phase 5: Integration Testing (Week 5)
1. Run all existing tests
2. Add comprehensive nested structure tests
3. Fix any compatibility issues

### Phase 6: Cleanup (Week 6)
1. Remove old parsing methods if safe
2. Update documentation
3. Add examples of nested structures

## Backward Compatibility Checklist

- [ ] All existing tests pass without modification
- [ ] CommandList can still be used as before
- [ ] and_or_lists property works correctly
- [ ] pipelines property works correctly
- [ ] Functions defined with old parser work with new executor
- [ ] Scripts using simple commands work unchanged
- [ ] Complex scripts with control structures work unchanged

## Success Criteria

1. All existing functionality preserved
2. Arbitrary nesting of control structures works
3. Performance impact minimal (< 5% slowdown)
4. Code remains clear and educational
5. Error messages remain helpful

This implementation guide provides concrete steps to evolve PSH's architecture to support arbitrarily nested control structures while maintaining full backward compatibility.