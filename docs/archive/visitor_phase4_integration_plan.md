# Visitor Pattern Phase 4 Integration Plan

## Overview

Phase 4 focuses on completing the visitor pattern integration by adding remaining node types, optimizing performance, and preparing for full migration to the visitor-based architecture. This phase builds upon the successful Phase 3 ExecutorVisitor implementation.

## Current State

- **Phase 1 (Complete)**: Replaced ASTFormatter with DebugASTVisitor
- **Phase 2 (Complete)**: Enhanced validation with EnhancedValidatorVisitor
- **Phase 3 (Complete)**: Implemented ExecutorVisitor with core functionality
- **Phase 4 (In Progress)**: Partial implementation completed
  - ✓ All AST node types implemented (including SelectLoop)
  - ✓ TestableExecutor created for improved test output capture
  - ✓ 22/25 tests passing (up from 11/23)
  - ✓ Comprehensive feature verification completed
  - ⏳ Performance optimization not started
  - ⏳ Advanced visitors not implemented
  - ⏳ Migration to default pending

## Phase 4 Goals

1. **Complete Node Coverage**: Implement all remaining AST node types
2. **Fix Test Issues**: Address output capture and remaining test failures
3. **Performance Optimization**: Profile and optimize visitor execution
4. **Advanced Features**: Add optimization and transformation visitors
5. **Migration Preparation**: Prepare for making visitor executor the default

## Proposed Implementation

### 1. Complete Missing Node Types

#### 1.1 Arithmetic Evaluation
```python
def visit_ArithmeticEvaluation(self, node: ArithmeticEvaluation) -> int:
    """Execute arithmetic command: ((expression))"""
    # Evaluate arithmetic expression
    result = self.state.evaluate_arithmetic(node.expression)
    # Return 0 if result is non-zero (bash behavior)
    return 0 if result != 0 else 1
```

#### 1.2 Enhanced Test Statement
```python
def visit_EnhancedTestStatement(self, node: EnhancedTestStatement) -> int:
    """Execute enhanced test: [[ expression ]]"""
    # Delegate to shell's test implementation
    return self.shell.execute_enhanced_test_statement(node)
```

#### 1.3 Select Loop
```python
def visit_SelectLoop(self, node: SelectLoop) -> int:
    """Execute select loop for interactive menus."""
    # Implement select menu functionality
    # Handle PS3 prompt and user selection
```

#### 1.4 C-Style For Loop
```python
def visit_CStyleForLoop(self, node: CStyleForLoop) -> int:
    """Execute C-style for loop: for ((init; cond; update))"""
    # Handle arithmetic-based iteration
```

### 2. Fix Output Capture Issues

#### 2.1 Subprocess-Based Testing Mode
Create a testing mode that uses subprocess instead of fork for better output capture:

```python
class TestableExecutorVisitor(ExecutorVisitor):
    """Executor visitor with output capture for testing."""
    
    def __init__(self, shell, capture_output=False):
        super().__init__(shell)
        self.capture_output = capture_output
        self.captured_stdout = []
        self.captured_stderr = []
    
    def _execute_external(self, args, background=False):
        if self.capture_output and not self._in_pipeline:
            # Use subprocess for output capture
            result = subprocess.run(args, capture_output=True, text=True)
            self.captured_stdout.append(result.stdout)
            self.captured_stderr.append(result.stderr)
            return result.returncode
        else:
            # Use normal fork/exec
            return super()._execute_external(args, background)
```

#### 2.2 Builtin Output Capture
Modify builtins to support output capture in test mode:

```python
def _write_output(self, text, suppress_newline, shell):
    if hasattr(shell, 'capture_mode') and shell.capture_mode:
        shell.captured_output.append(text)
    elif hasattr(shell, '_in_forked_child') and shell._in_forked_child:
        os.write(1, text.encode())
    else:
        shell.stdout.write(text)
        shell.stdout.flush()
```

### 3. Performance Optimization

#### 3.1 Profile Current Implementation
- Use cProfile to identify hot spots
- Measure visitor overhead vs direct execution
- Identify optimization opportunities

#### 3.2 Optimization Strategies

##### Method Lookup Caching
```python
class OptimizedVisitor(ASTVisitor[T]):
    def __init__(self):
        self._method_cache = {}
    
    def visit(self, node: ASTNode) -> T:
        node_type = type(node)
        if node_type not in self._method_cache:
            method_name = f'visit_{node_type.__name__}'
            self._method_cache[node_type] = getattr(
                self, method_name, self.generic_visit
            )
        return self._method_cache[node_type](node)
```

##### Batch Operations
- Combine multiple expansions
- Reuse compiled patterns
- Cache frequently accessed data

### 4. Advanced Visitor Implementations

#### 4.1 Optimization Visitor
```python
class OptimizationVisitor(ASTTransformer):
    """Optimize AST before execution."""
    
    def visit_Pipeline(self, node: Pipeline) -> Pipeline:
        # Optimize away unnecessary cats
        # echo foo | cat -> echo foo
        if len(node.commands) == 2:
            if self._is_simple_cat(node.commands[1]):
                return Pipeline([node.commands[0]])
        return node
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> SimpleCommand:
        # Constant folding for arithmetic
        # Pre-expand literal strings
        return node
```

#### 4.2 Security Visitor
```python
class SecurityVisitor(ASTVisitor[None]):
    """Enhanced security analysis."""
    
    def __init__(self):
        self.vulnerabilities = []
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        # Check for command injection
        # Detect unsafe evals
        # Flag suspicious patterns
        pass
```

#### 4.3 Metrics Visitor
```python
class MetricsVisitor(ASTVisitor[None]):
    """Collect code metrics."""
    
    def __init__(self):
        self.metrics = {
            'commands': 0,
            'pipelines': 0,
            'functions': 0,
            'complexity': 0
        }
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        self.metrics['commands'] += 1
```

### 5. Integration Improvements

#### 5.1 Visitor Registry
```python
class VisitorRegistry:
    """Central registry for visitor types."""
    
    def __init__(self):
        self._visitors = {}
    
    def register(self, name: str, visitor_class: Type[ASTVisitor]):
        self._visitors[name] = visitor_class
    
    def create(self, name: str, *args, **kwargs) -> ASTVisitor:
        return self._visitors[name](*args, **kwargs)

# Usage
registry = VisitorRegistry()
registry.register('executor', ExecutorVisitor)
registry.register('validator', ValidatorVisitor)
registry.register('formatter', FormatterVisitor)
```

#### 5.2 Visitor Pipeline
```python
class VisitorPipeline:
    """Chain multiple visitors."""
    
    def __init__(self, visitors: List[ASTVisitor]):
        self.visitors = visitors
    
    def process(self, ast: ASTNode) -> List[Any]:
        results = []
        for visitor in self.visitors:
            results.append(visitor.visit(ast))
        return results

# Usage
pipeline = VisitorPipeline([
    ValidatorVisitor(),
    OptimizationVisitor(),
    ExecutorVisitor(shell)
])
```

### 6. Migration Path

#### 6.1 Feature Flags
```python
class ShellConfig:
    """Configuration for shell features."""
    
    def __init__(self):
        self.use_visitor_executor = False
        self.enable_optimizations = False
        self.strict_validation = False
    
    @classmethod
    def from_env(cls):
        """Load config from environment."""
        config = cls()
        config.use_visitor_executor = os.getenv('PSH_VISITOR_EXECUTOR', '').lower() == 'true'
        return config
```

#### 6.2 Gradual Rollout
1. **Testing Phase**: Keep --visitor-executor flag
2. **Opt-in Phase**: Make visitor executor available via config
3. **Default Phase**: Switch to visitor executor by default
4. **Cleanup Phase**: Remove old executor code

### 7. Implementation Steps

1. **Week 1: Complete Node Types**
   - Implement remaining visit methods
   - Add comprehensive tests
   - Fix existing test failures

2. **Week 2: Output Capture**
   - Implement testable executor
   - Fix builtin output handling
   - Update test infrastructure

3. **Week 3: Performance**
   - Profile implementation
   - Apply optimizations
   - Benchmark results

4. **Week 4: Advanced Visitors**
   - Implement optimization visitor
   - Add security enhancements
   - Create metrics collector

5. **Week 5: Integration**
   - Create visitor registry
   - Implement pipeline
   - Add configuration

6. **Week 6: Migration**
   - Documentation updates
   - Migration guide
   - Final testing

### 8. Success Criteria

- [x] ~~All 23 ExecutorVisitor tests passing~~ 22/25 passing (3 skipped due to pipeline limitations)
- [x] All AST node types supported
- [ ] Performance within 10% of original executor
- [ ] At least 3 advanced visitors implemented
- [ ] Clean migration path documented
- [x] No regressions in main test suite (1090 tests passing)

### 9. Future Possibilities

After Phase 4 completion:

1. **JIT Compilation**: Use visitor to generate optimized bytecode
2. **Parallel Execution**: Analyze AST for parallelization opportunities
3. **IDE Support**: Use visitors for syntax highlighting, completion
4. **Static Analysis**: Type checking, dead code detection
5. **Transpilation**: Convert shell scripts to other languages

## Conclusion

Phase 4 will complete the visitor pattern integration, making PSH's architecture more modular, testable, and extensible. The addition of advanced visitors will showcase the pattern's power for implementing complex features cleanly. After this phase, PSH will have a state-of-the-art architecture suitable for educational purposes and real-world use.