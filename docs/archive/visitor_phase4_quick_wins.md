# Visitor Pattern Phase 4 - Quick Wins

## Overview

This document outlines immediate, high-impact improvements we can make in Phase 4 that can be completed quickly while providing significant value.

## Quick Win #1: Complete Missing Node Types (1-2 days)

### ArithmeticEvaluation
```python
def visit_ArithmeticEvaluation(self, node: ArithmeticEvaluation) -> int:
    """Execute arithmetic command: ((expression))"""
    from ..arithmetic import ArithmeticEvaluator
    evaluator = ArithmeticEvaluator(self.state)
    try:
        result = evaluator.evaluate(node.expression)
        # Bash behavior: 0 if true (non-zero), 1 if false (zero)
        return 0 if result != 0 else 1
    except Exception as e:
        print(f"psh: ((: {e}", file=sys.stderr)
        return 1
```

### CStyleForLoop
```python
def visit_CStyleForLoop(self, node: CStyleForLoop) -> int:
    """Execute C-style for loop."""
    exit_status = 0
    self._loop_depth += 1
    
    # Evaluate init expression
    if node.init:
        self._evaluate_arithmetic(node.init)
    
    with self._apply_redirections(node.redirects):
        try:
            while True:
                # Evaluate condition
                if node.condition:
                    result = self._evaluate_arithmetic(node.condition)
                    if result == 0:  # Zero means false
                        break
                
                # Execute body
                try:
                    exit_status = self.visit(node.body)
                except LoopContinue as lc:
                    if lc.level > 1:
                        raise LoopContinue(lc.level - 1)
                except LoopBreak as lb:
                    if lb.level > 1:
                        raise LoopBreak(lb.level - 1)
                    break
                
                # Evaluate update
                if node.update:
                    self._evaluate_arithmetic(node.update)
                    
        finally:
            self._loop_depth -= 1
    
    return exit_status
```

### SelectLoop
```python
def visit_SelectLoop(self, node: SelectLoop) -> int:
    """Execute select loop."""
    # For now, delegate to existing implementation
    # This is complex due to interactive nature
    return self.shell.execute_select_loop(node)
```

## Quick Win #2: Fix Case Statement (30 minutes)

Already implemented in Phase 3, just needs the fix for CasePattern.body:

```python
def visit_CaseConditional(self, node: CaseConditional) -> int:
    # ... existing code ...
    # Execute the commands for this case
    exit_status = self.visit(case_item.commands)  # Changed from .body
```

## Quick Win #3: Simple Test Output Capture (1 day)

Create a minimal test helper that doesn't require forking:

```python
class TestExecutorVisitor(ExecutorVisitor):
    """Executor visitor for testing that captures output."""
    
    def __init__(self, shell):
        super().__init__(shell)
        self.test_mode = True
        self.output_buffer = []
    
    def _execute_builtin(self, name: str, args: List[str]) -> int:
        # Temporarily redirect stdout to capture output
        old_stdout = self.shell.stdout
        self.shell.stdout = io.StringIO()
        
        try:
            result = super()._execute_builtin(name, args)
            output = self.shell.stdout.getvalue()
            if output:
                self.output_buffer.append(output)
            return result
        finally:
            self.shell.stdout = old_stdout
    
    def get_output(self) -> str:
        return ''.join(self.output_buffer)
```

## Quick Win #4: Performance Quick Fixes (2-3 hours)

### Method Lookup Cache
```python
class ExecutorVisitor(ASTVisitor[int]):
    def __init__(self, shell: 'Shell'):
        super().__init__()
        self._visit_cache = {}  # Cache method lookups
        # ... rest of init
    
    def visit(self, node: ASTNode) -> int:
        node_class = node.__class__
        if node_class not in self._visit_cache:
            method_name = f'visit_{node_class.__name__}'
            self._visit_cache[node_class] = getattr(
                self, method_name, self.generic_visit
            )
        return self._visit_cache[node_class](node)
```

### Expansion Caching
```python
def _expand_arguments(self, node: SimpleCommand) -> List[str]:
    # Check if we've already expanded these exact arguments
    cache_key = tuple(node.args)  # Simple cache key
    if hasattr(self, '_expansion_cache') and cache_key in self._expansion_cache:
        return self._expansion_cache[cache_key].copy()
    
    result = self.expansion_manager.expand_arguments(node)
    
    # Cache for future use
    if not hasattr(self, '_expansion_cache'):
        self._expansion_cache = {}
    self._expansion_cache[cache_key] = result.copy()
    
    return result
```

## Quick Win #5: Metrics Visitor (1-2 hours)

Simple metrics collection to demonstrate visitor utility:

```python
class MetricsVisitor(ASTVisitor[None]):
    """Collect metrics about shell scripts."""
    
    def __init__(self):
        self.metrics = {
            'total_commands': 0,
            'external_commands': 0,
            'builtin_commands': 0,
            'pipelines': 0,
            'functions': 0,
            'loops': 0,
            'conditionals': 0,
            'max_pipeline_length': 0,
            'max_nesting_depth': 0
        }
        self._current_depth = 0
        self._known_builtins = set([
            'echo', 'cd', 'pwd', 'export', 'unset', 'exit',
            'true', 'false', 'test', '[', 'return', 'break', 'continue'
        ])
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        self.metrics['total_commands'] += 1
        if node.args and node.args[0] in self._known_builtins:
            self.metrics['builtin_commands'] += 1
        else:
            self.metrics['external_commands'] += 1
    
    def visit_Pipeline(self, node: Pipeline) -> None:
        if len(node.commands) > 1:
            self.metrics['pipelines'] += 1
            self.metrics['max_pipeline_length'] = max(
                self.metrics['max_pipeline_length'], 
                len(node.commands)
            )
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        self.metrics['functions'] += 1
        self._with_depth(lambda: self.visit(node.body))
    
    def visit_WhileLoop(self, node: WhileLoop) -> None:
        self.metrics['loops'] += 1
        self._with_depth(lambda: self.generic_visit(node))
    
    def visit_ForLoop(self, node: ForLoop) -> None:
        self.metrics['loops'] += 1
        self._with_depth(lambda: self.generic_visit(node))
    
    def visit_IfConditional(self, node: IfConditional) -> None:
        self.metrics['conditionals'] += 1
        self._with_depth(lambda: self.generic_visit(node))
    
    def _with_depth(self, func):
        self._current_depth += 1
        self.metrics['max_nesting_depth'] = max(
            self.metrics['max_nesting_depth'],
            self._current_depth
        )
        try:
            func()
        finally:
            self._current_depth -= 1
    
    def get_summary(self) -> str:
        return f"""Script Metrics:
  Total Commands: {self.metrics['total_commands']}
    Builtins: {self.metrics['builtin_commands']}
    External: {self.metrics['external_commands']}
  Pipelines: {self.metrics['pipelines']}
  Functions: {self.metrics['functions']}
  Loops: {self.metrics['loops']}
  Conditionals: {self.metrics['conditionals']}
  Max Pipeline Length: {self.metrics['max_pipeline_length']}
  Max Nesting Depth: {self.metrics['max_nesting_depth']}"""
```

## Quick Win #6: Simple Command Linter (2-3 hours)

Demonstrate practical visitor use:

```python
class LinterVisitor(ASTVisitor[None]):
    """Simple shell script linter."""
    
    def __init__(self):
        self.issues = []
        self.current_function = None
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        if not node.args:
            return
        
        cmd = node.args[0]
        
        # Check for useless use of cat
        if self._in_pipeline and cmd == 'cat' and len(node.args) == 1:
            self.issues.append({
                'level': 'warning',
                'message': 'Useless use of cat in pipeline',
                'suggestion': 'Remove cat from pipeline'
            })
        
        # Check for deprecated commands
        deprecated = {
            'egrep': 'grep -E',
            'fgrep': 'grep -F',
        }
        if cmd in deprecated:
            self.issues.append({
                'level': 'info',
                'message': f'{cmd} is deprecated',
                'suggestion': f'Use {deprecated[cmd]} instead'
            })
        
        # Check for missing quotes in test
        if cmd in ['test', '['] and any('$' in arg for arg in node.args):
            if not any(arg.startswith('"') for arg in node.args):
                self.issues.append({
                    'level': 'warning',
                    'message': 'Unquoted variable in test command',
                    'suggestion': 'Quote variables to prevent word splitting'
                })
```

## Implementation Priority

1. **Missing Node Types** (1-2 days) - Essential for completeness
2. **Performance Quick Fixes** (3 hours) - Immediate speed improvements  
3. **Metrics Visitor** (2 hours) - Great demo of visitor pattern value
4. **Test Output Capture** (1 day) - Improves test reliability
5. **Linter Visitor** (3 hours) - Practical tool users will appreciate

## Total Time Estimate

- Core fixes: 2-3 days
- Demo visitors: 1 day
- Testing and documentation: 1 day

**Total: 4-5 days for significant Phase 4 progress**

## Benefits

1. **Immediate Value**: Users get new analysis tools right away
2. **Pattern Demonstration**: Shows practical visitor pattern uses
3. **Test Coverage**: More tests will pass with node implementations
4. **Performance**: Noticeable speed improvements with caching
5. **Educational**: Great examples for learning visitor pattern