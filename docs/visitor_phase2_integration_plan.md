# Visitor Pattern Phase 2 Integration Plan

## Overview

Phase 2 builds on the successful Phase 1 integration by adding more analysis visitors and enhancing the existing ValidatorVisitor. The focus is on improving shell script quality through better validation, optimization suggestions, and code analysis.

## Goals

1. **Enhanced AST Validation**: Extend ValidatorVisitor with more comprehensive checks
2. **Static Analysis**: Add new analysis visitors for code quality and security
3. **Performance Analysis**: Create visitors that identify performance bottlenecks
4. **Code Metrics**: Implement visitors for complexity and maintainability metrics
5. **Integration**: Wire up visitors into the shell for optional analysis modes

## Proposed Visitors

### 1. Enhanced ValidatorVisitor

Extend the existing validator with:

#### Undefined Variable Detection
- Track variable definitions and usage
- Warn about potentially undefined variables
- Respect parameter expansion defaults (${var:-default})
- Handle special variables ($?, $$, $@, etc.)

#### Command Validation
- Check if commands exist in PATH
- Validate builtin command usage
- Warn about deprecated or non-portable commands
- Validate command argument counts

#### Quoting Issues
- Detect unquoted variables that may need quoting
- Warn about word splitting risks
- Identify glob expansion in unexpected places
- Check for proper quoting in test expressions

#### Security Checks
- Detect potential command injection points
- Warn about unsafe use of eval
- Check for world-writable file operations
- Identify potential race conditions

### 2. OptimizationVisitor

A new visitor that suggests performance improvements:

```python
class OptimizationVisitor(ASTVisitor[List[Optimization]]):
    """Identifies opportunities for performance optimization."""
    
    def visit_Pipeline(self, node: Pipeline) -> List[Optimization]:
        optimizations = []
        
        # Check for useless use of cat
        if self._is_useless_cat(node):
            optimizations.append(UselessCatOptimization(node))
        
        # Check for inefficient grep | awk patterns
        if self._is_grep_awk_pattern(node):
            optimizations.append(GrepAwkOptimization(node))
        
        # Check for multiple sed invocations
        if self._has_multiple_sed(node):
            optimizations.append(MultipleSedOptimization(node))
        
        return optimizations
```

Optimization patterns to detect:
- Useless use of cat (cat file | cmd → cmd < file)
- Inefficient pipelines (grep | awk → awk alone)
- Multiple sed/awk calls that could be combined
- Subshell elimination opportunities
- Loop optimization (avoid calling external commands in tight loops)

### 3. ComplexityVisitor

Analyze code complexity:

```python
class ComplexityVisitor(ASTVisitor[ComplexityMetrics]):
    """Calculate code complexity metrics."""
    
    def __init__(self):
        self.metrics = ComplexityMetrics()
        self.current_function = None
        self.nesting_depth = 0
```

Metrics to calculate:
- Cyclomatic complexity per function
- Maximum nesting depth
- Lines of code (LOC)
- Number of functions
- Average function length
- Number of global variables
- Pipeline complexity

### 4. DependencyVisitor

Track external dependencies:

```python
class DependencyVisitor(ASTVisitor[DependencyInfo]):
    """Identify external command dependencies."""
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        cmd = node.args[0] if node.args else None
        if cmd and not self._is_builtin(cmd):
            self.external_commands.add(cmd)
```

Track:
- External commands used
- Required shell features
- File dependencies
- Environment variable dependencies
- Function dependencies

### 5. SecurityAuditVisitor

Comprehensive security analysis:

```python
class SecurityAuditVisitor(ASTVisitor[List[SecurityIssue]]):
    """Perform security audit of shell scripts."""
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        # Check for dangerous commands
        if node.args and node.args[0] in self.DANGEROUS_COMMANDS:
            self._check_dangerous_command(node)
```

Security checks:
- Unsafe variable expansion
- Command injection vulnerabilities
- Insecure file operations
- Hardcoded credentials
- Unsafe use of eval/source
- World-writable file creation

## Implementation Steps

### Step 1: Enhance ValidatorVisitor (Week 1)

1. Add variable tracking infrastructure
2. Implement undefined variable detection
3. Add command existence checking
4. Implement quoting analysis
5. Add basic security checks
6. Update tests

### Step 2: Create OptimizationVisitor (Week 2)

1. Design optimization rule system
2. Implement common optimization patterns
3. Create suggestion formatting
4. Add configuration for rule severity
5. Write comprehensive tests

### Step 3: Implement Analysis Visitors (Week 3)

1. Create ComplexityVisitor
2. Implement DependencyVisitor
3. Add SecurityAuditVisitor
4. Create unified reporting format
5. Add tests for each visitor

### Step 4: Shell Integration (Week 4)

1. Add command-line flags for analysis modes:
   - `--analyze`: Run all analysis visitors
   - `--validate`: Enhanced validation only
   - `--optimize`: Show optimization suggestions
   - `--security`: Security audit mode
   - `--metrics`: Show complexity metrics

2. Create AnalysisManager to coordinate visitors:
   ```python
   class AnalysisManager:
       def __init__(self, shell):
           self.shell = shell
           self.visitors = {
               'validate': ValidatorVisitor(),
               'optimize': OptimizationVisitor(),
               'complexity': ComplexityVisitor(),
               'dependencies': DependencyVisitor(),
               'security': SecurityAuditVisitor(),
           }
   ```

3. Add analysis output formatting:
   - Console output with color coding
   - JSON output for tooling integration
   - Markdown reports for documentation

4. Integration with existing debug infrastructure

### Step 5: Configuration System (Week 5)

1. Create `.pshanalysis` configuration file format
2. Allow enabling/disabling specific checks
3. Set severity levels for different issues
4. Configure output formats
5. Support project-specific rules

## Testing Strategy

1. **Unit Tests**: Each visitor tested independently
2. **Integration Tests**: Visitors working together
3. **Regression Tests**: Ensure no impact on normal execution
4. **Performance Tests**: Verify minimal overhead
5. **Real-world Tests**: Test on actual shell scripts

## Future Enhancements

1. **IDE Integration**: Language server protocol support
2. **Fix Suggestions**: Automated fixes for common issues
3. **Custom Rules**: User-defined validation rules
4. **Incremental Analysis**: For large codebases
5. **Cross-file Analysis**: Track dependencies across files

## Success Criteria

1. All existing tests continue to pass
2. New visitors have >90% test coverage
3. Analysis overhead < 100ms for typical scripts
4. Clear, actionable output for users
5. Documentation for all new features

## Example Usage

```bash
# Run all analysis
psh --analyze script.sh

# Validate only
psh --validate script.sh

# Get optimization suggestions
psh --optimize script.sh

# Security audit
psh --security script.sh

# Get complexity metrics
psh --metrics script.sh

# Combine with existing debug flags
psh --analyze --debug-ast script.sh

# JSON output for tooling
psh --analyze --output=json script.sh > analysis.json
```

## Benefits

1. **Code Quality**: Catch bugs before runtime
2. **Performance**: Identify bottlenecks
3. **Security**: Find vulnerabilities early
4. **Maintainability**: Track complexity
5. **Education**: Learn best practices
6. **Tool Integration**: Support for CI/CD

This phase 2 integration significantly enhances PSH's value as both a shell and an educational tool for understanding shell script analysis and optimization.