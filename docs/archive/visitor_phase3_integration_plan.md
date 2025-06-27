# Visitor Pattern Phase 3 Integration Plan

## Overview

Phase 3 focuses on refactoring the executor to use the visitor pattern, as outlined in the integration strategy. This is a significant architectural change that will demonstrate how the visitor pattern can handle complex operations like command execution while maintaining clean separation of concerns.

## Current State

- **Phase 1 (Complete)**: Replaced ASTFormatter with DebugASTVisitor for --debug-ast functionality
- **Phase 2 (Complete)**: Enhanced validation with EnhancedValidatorVisitor including:
  - Undefined variable detection with scope tracking
  - Command validation and typo detection
  - Quoting analysis for safety
  - Security vulnerability detection
  - Integration via --validate flag

## Phase 3 Goals

1. **Executor Visitor Architecture**: Design and implement execution using visitor pattern
2. **Gradual Migration**: Create parallel execution path for testing
3. **Feature Parity**: Ensure all execution features work correctly
4. **Performance**: Maintain or improve execution performance
5. **Testability**: Improve test isolation for execution logic

## Proposed Implementation

### 1. ExecutorVisitor Design

Create a comprehensive executor visitor that handles all AST node types:

```python
class ExecutorVisitor(ASTVisitor[int]):
    """Execute AST nodes and return exit status."""
    
    def __init__(self, shell_state: ShellState):
        self.state = shell_state
        self.expansion_manager = ExpansionManager(shell_state)
        self.io_manager = IOManager()
        self.job_manager = JobManager()
        # ... other managers
```

### 2. Execution Contexts

Design execution contexts for different scenarios:

#### CommandExecutionContext
- Handles simple command execution
- Manages builtin vs external commands
- Handles redirections and expansions

#### PipelineExecutionContext
- Manages pipeline setup and teardown
- Handles process creation and pipe management
- Manages job control for pipelines

#### ControlFlowContext
- Handles control structures (if, while, for, etc.)
- Manages loop state (break/continue)
- Handles conditional execution

### 3. Key Components

#### 3.1 Simple Command Execution
```python
def visit_SimpleCommand(self, node: SimpleCommand) -> int:
    # Expand arguments
    expanded_args = self.expansion_manager.expand_all(node.args)
    
    # Apply redirections
    with self.io_manager.apply_redirections(node.redirects):
        # Execute command
        if self.is_builtin(expanded_args[0]):
            return self.execute_builtin(expanded_args)
        else:
            return self.execute_external(expanded_args)
```

#### 3.2 Pipeline Execution
```python
def visit_Pipeline(self, node: Pipeline) -> int:
    if len(node.commands) == 1:
        return self.visit(node.commands[0])
    
    # Create pipeline context
    with PipelineContext(self.job_manager) as pipeline:
        for i, command in enumerate(node.commands):
            pipeline.add_command(command, self)
        return pipeline.execute()
```

#### 3.3 Control Structure Execution
```python
def visit_WhileLoop(self, node: WhileLoop) -> int:
    exit_status = 0
    try:
        while True:
            # Evaluate condition
            condition_status = self.visit(node.condition)
            if condition_status != 0:
                break
            
            # Execute body
            exit_status = self.visit(node.body)
    except LoopBreak:
        pass
    except LoopContinue:
        continue
    
    return exit_status
```

### 4. Integration Strategy

#### 4.1 Parallel Implementation
- Keep existing executor as primary
- Add --visitor-executor flag for testing
- Gradually migrate features

#### 4.2 Testing Approach
- Create comprehensive test suite
- Compare outputs between old and new executors
- Performance benchmarking

#### 4.3 Migration Path
1. Start with simple commands
2. Add pipeline support
3. Implement control structures
4. Add advanced features (job control, functions)
5. Complete feature parity
6. Switch to visitor as default
7. Remove old executor

### 5. Benefits

#### 5.1 Clean Architecture
- Execution logic clearly organized by node type
- Easy to understand flow
- Consistent patterns

#### 5.2 Testability
- Mock individual visit methods
- Test execution contexts independently
- Isolate complex logic

#### 5.3 Extensibility
- Easy to add new node types
- Can create specialized executors
- Plugin architecture possible

#### 5.4 Debugging
- Clear execution trace
- Easy to add logging/profiling
- Can create debugging executor

### 6. Challenges and Solutions

#### 6.1 State Management
**Challenge**: Managing shell state across visitor calls
**Solution**: Pass state through context objects

#### 6.2 Error Handling
**Challenge**: Consistent error handling across node types
**Solution**: Use exception hierarchy with visitor-aware handling

#### 6.3 Performance
**Challenge**: Virtual method call overhead
**Solution**: Profile and optimize hot paths, consider caching

#### 6.4 Backward Compatibility
**Challenge**: Maintaining exact behavior
**Solution**: Comprehensive test suite, gradual migration

### 7. Implementation Steps

1. **Create Base ExecutorVisitor**
   - Basic structure and state management
   - Integration with existing managers

2. **Implement Simple Commands**
   - Builtin execution
   - External command execution
   - Basic expansions

3. **Add Pipeline Support**
   - Process creation
   - Pipe management
   - Job control integration

4. **Implement Control Structures**
   - Conditionals (if/else)
   - Loops (while, for)
   - Case statements

5. **Add Advanced Features**
   - Functions
   - Subshells
   - Command substitution

6. **Testing and Validation**
   - Comprehensive test suite
   - Performance benchmarking
   - Bug fixing

7. **Migration**
   - Enable by default
   - Remove old executor
   - Update documentation

### 8. Success Criteria

- All existing tests pass with ExecutorVisitor
- Performance is comparable or better
- Code is more maintainable and testable
- Clear documentation and examples
- Smooth migration path

### 9. Timeline Estimate

- Base implementation: 2-3 days
- Simple commands: 1-2 days
- Pipelines: 2-3 days
- Control structures: 3-4 days
- Advanced features: 3-4 days
- Testing and migration: 2-3 days

Total: 2-3 weeks for complete implementation

## Conclusion

Phase 3 represents a significant architectural improvement that will make PSH's execution engine more maintainable, testable, and extensible. By using the visitor pattern, we can achieve cleaner separation of concerns while maintaining all existing functionality.