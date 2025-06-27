# Subshell Variable Isolation Implementation Plan

## Problem Analysis

The conformance tests are failing because PSH lacks proper support for **subshell grouping syntax `(...)`** and **subshell variable isolation**. This is a fundamental POSIX shell feature.

### Current Issues Identified

1. **Missing `(...)` subshell syntax**: PSH cannot parse `(command)` constructs
2. **Pipeline variable isolation**: Variables modified in pipeline processes affect parent shell  
3. **Command substitution isolation**: May have similar issues (needs verification)

### Root Cause Analysis

#### 1. Missing Subshell Grouping Support
```bash
# This should work but doesn't:
(echo "test")  # Parse error: Expected command

# This is what the conformance tests expect:
(
    subshell_var="modified in subshell"
    echo "Modified in subshell: $subshell_var"
)
```

**Problem**: No AST node or parser support for parenthetical command grouping.

#### 2. Pipeline Variable Sharing
```python
# In executor_visitor.py lines 254-279:
pid = os.fork()
if pid == 0:
    # Child process uses SAME shell instance
    self.state._in_forked_child = True  # Flag but same state object!
    exit_status = self.visit(command)   # Modifies shared state
```

**Problem**: Pipeline processes share the same `ShellState` object instead of having isolated copies.

#### 3. Command Substitution Implementation
```python
# In command_sub.py lines 66-71:
temp_shell = Shell(
    debug_ast=self.state.debug_ast,
    debug_tokens=self.state.debug_tokens,
    parent_shell=self.shell,  # Creates new Shell with copied variables
    norc=True
)
```

**Good**: Command substitution creates a new Shell instance with copied variables - this is correct.

## Implementation Plan

### Phase 1: Add SubshellGroup AST Node and Parsing Support

#### 1.1 Create SubshellGroup AST Node
Add to `ast_nodes.py`:
```python
@dataclass
class SubshellGroup(Command):
    """Represents a subshell group (...) that executes in an isolated environment."""
    statements: StatementList
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False
```

#### 1.2 Add Parser Support
Modify `parser.py` to handle `LPAREN ... RPAREN` as subshell groups:
```python
def parse_simple_command(self) -> SimpleCommand:
    # Add check for LPAREN at start
    if self.match(TokenType.LPAREN):
        return self.parse_subshell_group()
    # ... existing logic
    
def parse_subshell_group(self) -> SubshellGroup:
    """Parse (commands) subshell group."""
    self.expect(TokenType.LPAREN)
    self.skip_newlines()
    
    statements = self.parse_statement_list()
    
    self.skip_newlines()
    self.expect(TokenType.RPAREN)
    
    # Parse redirections if any
    redirects = self.parse_redirections()
    
    # Check for background operator
    background = self.match(TokenType.AMPERSAND)
    
    return SubshellGroup(statements, redirects, background)
```

#### 1.3 Add Visitor Support
Add to `executor_visitor.py`:
```python
def visit_SubshellGroup(self, node: SubshellGroup) -> int:
    """Execute subshell group in isolated environment."""
    return self._execute_in_subshell(node.statements, node.redirects, node.background)
```

### Phase 2: Implement Proper Subshell Isolation

#### 2.1 Create Subshell Execution Method
```python
def _execute_in_subshell(self, statements: StatementList, redirects: List[Redirect], background: bool) -> int:
    """Execute commands in an isolated subshell environment."""
    # Create pipe for exit status if needed
    if background:
        # Handle background subshell
        return self._execute_background_subshell(statements, redirects)
    else:
        # Foreground subshell
        return self._execute_foreground_subshell(statements, redirects)

def _execute_foreground_subshell(self, statements: StatementList, redirects: List[Redirect]) -> int:
    """Execute subshell in foreground with proper isolation."""
    pid = os.fork()
    
    if pid == 0:
        # Child process - create isolated shell
        try:
            # Create new shell instance with copied environment
            subshell = Shell(
                debug_ast=self.shell.state.debug_ast,
                debug_tokens=self.shell.state.debug_tokens,
                parent_shell=self.shell,  # Copy variables/functions
                norc=True
            )
            subshell.state._in_forked_child = True
            
            # Apply redirections
            if redirects:
                saved_fds = subshell.io_manager.apply_redirections(redirects)
            
            # Execute statements in isolated environment
            exit_code = subshell.execute_command_list(statements)
            os._exit(exit_code)
            
        except Exception as e:
            print(f"psh: subshell error: {e}", file=sys.stderr)
            os._exit(1)
    else:
        # Parent process - wait for child
        _, status = os.waitpid(pid, 0)
        return os.WEXITSTATUS(status) if os.WIFEXITED(status) else 1
```

### Phase 3: Fix Pipeline Variable Isolation

#### 3.1 Modify Pipeline Execution
Update `_execute_pipeline` to create isolated shell instances:
```python
def _execute_pipeline(self, node: Pipeline) -> int:
    # ... existing setup code ...
    
    for i, command in enumerate(node.commands):
        pid = os.fork()
        
        if pid == 0:
            # Child process - create isolated shell
            try:
                # Create new shell instance instead of sharing state
                pipeline_shell = Shell(
                    debug_ast=self.shell.state.debug_ast,
                    debug_tokens=self.shell.state.debug_tokens,
                    parent_shell=self.shell,
                    norc=True
                )
                pipeline_shell.state._in_forked_child = True
                
                # Set up pipeline redirections
                self._setup_pipeline_redirections(i, pipeline_ctx)
                
                # Execute command in isolated environment
                exit_status = pipeline_shell.visit(command)
                os._exit(exit_status)
                
            except Exception as e:
                os._exit(1)
        # ... parent process logic unchanged ...
```

### Phase 4: Testing and Validation

#### 4.1 Create Test Cases
```python
def test_subshell_variable_isolation():
    shell = Shell()
    
    # Test basic isolation
    shell.run_command('var="parent"')
    shell.run_command('(var="modified"; echo "In subshell: $var")')
    result = shell.run_command('echo "After subshell: $var"')
    assert "After subshell: parent" in result
    
def test_subshell_with_redirections():
    shell = Shell()
    shell.run_command('(echo "test" > file.txt)')
    # Verify file created correctly
    
def test_pipeline_variable_isolation():
    shell = Shell()
    shell.run_command('var="parent"')
    shell.run_command('echo "test" | (read input; var="modified"; echo "$var")')
    result = shell.run_command('echo "$var"')
    assert "parent" in result
```

#### 4.2 Conformance Test Validation
Run specific failing tests to verify fixes:
- `test_variable_scoping.input` - subshell variable isolation
- `test_loop_constructs.input` - pipeline variable effects
- Other tests affected by variable scoping issues

## Technical Considerations

### Performance Impact
- **Minimal**: Subshells already require process forking
- **Memory**: Each subshell creates a new Shell instance, but this is expected behavior
- **Compatibility**: No changes to existing functionality

### Edge Cases to Handle
1. **Nested subshells**: `(command1; (command2))`
2. **Subshells with redirections**: `(command) > file`
3. **Background subshells**: `(command) &`
4. **Subshells in pipelines**: `(command1) | command2`
5. **Exit status propagation**: Subshell exit codes must propagate correctly

### Integration with Existing Features
- **Command substitution**: Already works correctly (creates new Shell)
- **Functions**: Local variables should remain isolated from subshells
- **Job control**: Background subshells should integrate with job management
- **Signal handling**: Subshells should have proper signal isolation

## Expected Impact

### POSIX Compliance Improvement
- **High impact**: Subshell support is fundamental POSIX feature
- **Multiple test fixes**: Will resolve several conformance test failures
- **Shell scripting compatibility**: Enables common shell patterns

### User Experience
- **Predictable behavior**: Variables behave as users expect
- **Script portability**: Shell scripts written for bash/POSIX will work
- **Debugging**: Clearer variable scoping makes scripts easier to debug

## Implementation Priority

1. **Phase 1** (High): Parser and AST support for `(...)` syntax
2. **Phase 2** (High): Subshell isolation implementation  
3. **Phase 3** (Medium): Pipeline variable isolation fixes
4. **Phase 4** (Medium): Comprehensive testing and validation

This implementation will significantly improve PSH's POSIX compliance and resolve multiple conformance test failures related to variable scoping and subshell behavior.