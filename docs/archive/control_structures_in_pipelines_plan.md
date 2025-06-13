# Control Structures in Pipelines Implementation Plan

## Overview

This document outlines a comprehensive plan to enable control structures (while, for, if, case, select) to be used as components within pipelines in psh. Currently, these structures cannot be piped to or from, limiting shell functionality compared to bash.

## Current Limitation

### Problem Statement
Control structures cannot be used in pipelines. The following fail:
```bash
echo "data" | while read line; do echo $line; done
echo "test" | if grep -q "test"; then echo "found"; fi
seq 1 5 | for i in $(cat); do echo $i; done
```

### Root Cause
1. The AST type hierarchy separates `Command` and `Statement` types
2. `Pipeline` nodes only accept `Command` objects
3. Control structures are `Statement` objects, not `Command` objects
4. The parser's `parse_pipeline()` only calls `parse_command()`, not `parse_statement()`

## Proposed Solution: Unified Command Model

### Phase 1: AST Refactoring

#### 1.1 Create New AST Hierarchy
```python
# ast_nodes.py modifications

@dataclass
class Command(ASTNode):
    """Base class for all executable commands."""
    background: bool = False
    redirects: List[Redirect] = field(default_factory=list)

@dataclass
class SimpleCommand(Command):
    """Traditional command with arguments (formerly Command class)."""
    args: List[str] = field(default_factory=list)

@dataclass 
class CompoundCommand(Command):
    """Base class for control structures usable in pipelines."""
    pass

@dataclass
class WhileCommand(CompoundCommand):
    """While loop as a command."""
    condition: CommandList
    body: CommandList

@dataclass
class ForCommand(CompoundCommand):
    """For loop as a command."""
    variable: str
    items: List[str]
    body: CommandList

@dataclass
class IfCommand(CompoundCommand):
    """If statement as a command."""
    condition: CommandList
    then_part: CommandList
    else_part: Optional[CommandList] = None

@dataclass
class CaseCommand(CompoundCommand):
    """Case statement as a command."""
    word: str
    cases: List[CaseItem]

@dataclass
class SelectCommand(CompoundCommand):
    """Select statement as a command."""
    variable: str
    items: List[str]
    body: CommandList
```

#### 1.2 Migration Strategy
1. Keep existing Statement classes temporarily for backward compatibility
2. Create parallel Command versions of control structures
3. Update Pipeline to accept base Command type
4. Gradually migrate executors to use new Command types

### Phase 2: Parser Modifications

#### 2.1 Update Pipeline Parser
```python
# parser.py modifications

def parse_pipeline(self) -> Pipeline:
    """Parse a pipeline of commands."""
    pipeline = Pipeline()
    
    # First component
    component = self.parse_pipeline_component()
    pipeline.commands.append(component)
    
    # Additional components
    while self.match(TokenType.PIPE):
        component = self.parse_pipeline_component()
        pipeline.commands.append(component)
        
    return pipeline

def parse_pipeline_component(self) -> Command:
    """Parse a single component of a pipeline (simple or compound command)."""
    # Save position for potential backtracking
    saved_pos = self.current
    
    # Try parsing as control structure first
    if self.current_token.type == TokenType.WHILE:
        return self.parse_while_command()
    elif self.current_token.type == TokenType.FOR:
        return self.parse_for_command()
    elif self.current_token.type == TokenType.IF:
        return self.parse_if_command()
    elif self.current_token.type == TokenType.CASE:
        return self.parse_case_command()
    elif self.current_token.type == TokenType.SELECT:
        return self.parse_select_command()
    else:
        # Fall back to simple command
        return self.parse_simple_command()

def parse_while_command(self) -> WhileCommand:
    """Parse while loop as a command."""
    self.consume(TokenType.WHILE, "Expected 'while'")
    condition = self.parse_command_list()
    self.consume(TokenType.DO, "Expected 'do'")
    body = self.parse_command_list()
    self.consume(TokenType.DONE, "Expected 'done'")
    
    # Handle redirections
    redirects = self.parse_redirections()
    
    return WhileCommand(
        condition=condition,
        body=body,
        redirects=redirects
    )

# Similar methods for other control structures...
```

#### 2.2 Handle Ambiguity
Some constructs could be ambiguous:
```bash
# Is this a while command or while statement?
while read x; do echo $x; done < file.txt

# Context determines interpretation:
# As statement: while is top-level
# As command in pipeline: echo "data" | while read x; do echo $x; done
```

### Phase 3: Executor Enhancements

#### 3.1 Update Pipeline Executor
```python
# executor/pipeline.py modifications

class PipelineExecutor(ExecutorComponent):
    def execute(self, node: Pipeline) -> int:
        if len(node.commands) == 1:
            # Single command, no pipeline needed
            return self._execute_single_command(node.commands[0])
        
        # Multiple commands, set up pipeline
        return self._execute_pipeline(node)
    
    def _execute_single_command(self, command: Command) -> int:
        """Execute a single command (simple or compound)."""
        if isinstance(command, SimpleCommand):
            return self.shell.executor_manager.execute(command)
        elif isinstance(command, CompoundCommand):
            return self._execute_compound_in_subshell(command)
    
    def _execute_compound_in_subshell(self, command: CompoundCommand) -> int:
        """Execute compound command in a subshell for pipeline compatibility."""
        pid = os.fork()
        if pid == 0:
            # Child process
            try:
                # Set up as pipeline component
                self._setup_pipeline_component()
                
                # Execute the compound command
                if isinstance(command, WhileCommand):
                    executor = WhileCommandExecutor(self.shell)
                elif isinstance(command, ForCommand):
                    executor = ForCommandExecutor(self.shell)
                elif isinstance(command, IfCommand):
                    executor = IfCommandExecutor(self.shell)
                # ... etc
                
                exit_status = executor.execute(command)
                os._exit(exit_status)
            except Exception:
                os._exit(1)
        else:
            # Parent process
            _, status = os.waitpid(pid, 0)
            return os.WEXITSTATUS(status) if os.WIFEXITED(status) else 1
```

#### 3.2 Create Command Executors
```python
# executor/control_flow.py additions

class WhileCommandExecutor(ExecutorComponent):
    """Executor for while loops in pipeline context."""
    
    def execute(self, node: WhileCommand) -> int:
        last_status = 0
        
        # Apply redirections if any
        with self.shell.io_manager.apply_redirections(node.redirects):
            while True:
                # Check condition
                condition_status = self.shell.executor_manager.execute(node.condition)
                if condition_status != 0:
                    break
                
                try:
                    # Execute body
                    last_status = self.shell.executor_manager.execute(node.body)
                except LoopBreak:
                    break
                except LoopContinue:
                    continue
                    
        return last_status

# Similar executors for other control structures...
```

### Phase 4: Handle Edge Cases

#### 4.1 Variable Scoping
```python
# Ensure variables set in piped control structures are in subshell scope
echo "data" | while read x; do
    var="value"  # Should not affect parent shell
done
echo $var  # Should be empty/unchanged
```

#### 4.2 Signal Handling
- Handle SIGPIPE when downstream component closes
- Propagate signals correctly through compound commands

#### 4.3 Job Control
- Each compound command in pipeline gets its own process
- Proper process group management for job control

#### 4.4 Break/Continue Across Process Boundaries
- Break/continue only affect the immediate loop
- Cannot break out of a loop from a piped command

### Phase 5: Testing Strategy

#### 5.1 Basic Pipeline Tests
```python
def test_while_in_pipeline():
    """Test while loop as pipeline component."""
    result = shell.run_command('echo -e "1\\n2\\n3" | while read n; do echo "Number: $n"; done')
    assert result.output == "Number: 1\nNumber: 2\nNumber: 3\n"

def test_for_in_pipeline():
    """Test for loop in pipeline."""
    result = shell.run_command('echo "a b c" | for x in $(cat); do echo "[$x]"; done')
    assert result.output == "[a]\n[b]\n[c]\n"

def test_if_in_pipeline():
    """Test if statement in pipeline."""
    result = shell.run_command('echo "test" | if grep -q test; then echo "found"; else echo "not found"; fi')
    assert result.output == "found\n"
```

#### 5.2 Complex Pipeline Tests
```python
def test_nested_control_structures_in_pipeline():
    """Test nested control structures in pipelines."""
    result = shell.run_command('''
        seq 1 3 | while read n; do
            echo "$n" | if [ $(cat) -gt 1 ]; then
                echo "Greater than 1: $n"
            fi
        done | sort
    ''')
    assert result.output == "Greater than 1: 2\nGreater than 1: 3\n"
```

#### 5.3 Edge Case Tests
- Variable scoping in subshells
- Signal handling (SIGPIPE)
- Break/continue behavior
- Exit status propagation
- Redirections on compound commands

### Phase 6: Implementation Timeline

1. **Week 1-2**: AST Refactoring
   - Create new Command hierarchy
   - Update existing code to use SimpleCommand
   - Ensure backward compatibility

2. **Week 3-4**: Parser Updates
   - Implement parse_pipeline_component()
   - Add command variants of control structures
   - Handle ambiguous cases

3. **Week 5-6**: Executor Implementation
   - Update PipelineExecutor
   - Create compound command executors
   - Handle subshell execution

4. **Week 7**: Edge Cases and Signal Handling
   - Variable scoping fixes
   - SIGPIPE handling
   - Process group management

5. **Week 8**: Testing and Documentation
   - Comprehensive test suite
   - Update user documentation
   - Performance testing

## Alternative Approaches Considered

### 1. Wrapper Approach
Create a StatementCommand wrapper without changing AST hierarchy. Rejected because:
- Less clean architecture
- Harder to maintain long-term
- Doesn't fully integrate control structures

### 2. Grammar-Level Changes
Modify grammar to treat everything as expressions. Rejected because:
- Too radical a departure from traditional shell grammar
- Would break compatibility with existing code
- Harder to understand for educational purposes

## Backward Compatibility

1. Existing Statement classes remain for non-pipeline contexts
2. Parser intelligently chooses Command vs Statement based on context
3. All existing tests should continue to pass
4. Gradual migration path for internal code

## Performance Considerations

1. Each compound command in a pipeline runs in its own process
2. This matches bash behavior but may impact performance for large loops
3. Consider optimization for common cases (e.g., simple while read loops)

## Security Considerations

1. Ensure proper signal masking in pipeline components
2. Prevent resource exhaustion from deeply nested structures
3. Maintain proper process cleanup on errors

## Conclusion

This implementation plan provides a path to full support for control structures in pipelines while maintaining the educational clarity and architectural cleanliness of psh. The phased approach allows for incremental implementation and testing, reducing risk and ensuring quality.