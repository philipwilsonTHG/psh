# Visitor Executor Migration Plan

## Overview

This document outlines the migration path from the legacy executor to the visitor-based executor in PSH. The visitor executor provides a cleaner architecture, better maintainability, and enables advanced features like AST optimization and security analysis.

## Current Status

- **Legacy Executor**: Default execution engine, component-based architecture
- **Visitor Executor**: Experimental feature, enabled with `--visitor-executor` flag
- **Test Status**: All 1131 tests pass with legacy executor
- **Performance**: Visitor executor is within 10.9% of legacy performance (goal: 10%)

## Migration Phases

### Phase 1: Test Infrastructure Update (Current)
**Goal**: Ensure all tests pass with visitor executor

**Tasks**:
1. Identify test infrastructure limitations that prevent output capture in forked processes
2. Update test harness to properly capture output from visitor executor
3. Create compatibility layer for tests that rely on legacy executor internals
4. Run full test suite with visitor executor enabled

**Success Criteria**:
- All tests pass with `--visitor-executor` flag
- No behavioral differences between executors
- Test output properly captured

### Phase 2: Performance Optimization
**Goal**: Close the performance gap to within 5%

**Tasks**:
1. Profile hot paths in visitor executor
2. Implement method caching optimizations
3. Reduce object allocation overhead
4. Optimize visitor dispatch mechanism

**Success Criteria**:
- Performance gap < 5% on benchmark suite
- No regression in functionality

### Phase 3: Feature Parity Validation
**Goal**: Ensure complete feature parity

**Tasks**:
1. Create comprehensive feature matrix
2. Test all shell features with both executors
3. Document any behavioral differences
4. Fix any missing functionality

**Success Criteria**:
- 100% feature parity
- No user-visible behavioral changes

### Phase 4: Gradual Rollout
**Goal**: Safely transition users to visitor executor

**Tasks**:
1. Make visitor executor opt-out instead of opt-in:
   - Change default to visitor executor
   - Add `--legacy-executor` flag for fallback
2. Update documentation to reflect new default
3. Add migration warnings for deprecated features
4. Monitor user feedback and issues

**Timeline**:
- Week 1-2: Internal testing with visitor as default
- Week 3-4: Beta release with visitor as default
- Week 5-6: General release

### Phase 5: Legacy Executor Deprecation
**Goal**: Remove legacy executor code

**Tasks**:
1. Add deprecation warnings when `--legacy-executor` is used
2. Update all examples and documentation
3. Remove legacy executor code paths
4. Clean up compatibility layers

**Timeline**:
- 3 months after Phase 4: Deprecation warnings
- 6 months after Phase 4: Remove legacy code

## Implementation Details

### Test Infrastructure Updates

The main issue is that the current test infrastructure uses output capture mechanisms that don't work properly with forked processes in the visitor executor. We need to:

1. Update `CaptureOutput` context manager to handle subprocess output
2. Modify tests that rely on specific executor internals
3. Add test markers for executor-specific tests

### Configuration Management

1. Add shell option: `set -o visitor_executor` (runtime toggle)
2. Environment variable: `PSH_USE_VISITOR_EXECUTOR=1`
3. RC file setting: `visitor_executor=true` in ~/.pshrc

### Compatibility Layer

For smooth migration, we'll maintain a compatibility layer:

```python
class ExecutorCompatibilityMixin:
    """Provides legacy executor API on top of visitor executor."""
    
    def execute_command(self, command):
        # Delegate to visitor
        return self.visitor_executor.visit(command)
    
    def execute_pipeline(self, pipeline):
        # Delegate to visitor
        return self.visitor_executor.visit(pipeline)
```

### Performance Optimizations

1. **Method Cache Warming**: Pre-populate visitor method cache
2. **Object Pooling**: Reuse context objects for pipelines
3. **Lazy Imports**: Defer importing heavy modules
4. **JIT Compilation**: Consider using PyPy for hot paths

## Risk Mitigation

### Risks and Mitigations

1. **Risk**: Test failures with visitor executor
   - **Mitigation**: Fix test infrastructure before making default
   - **Fallback**: Keep legacy executor available

2. **Risk**: Performance regression
   - **Mitigation**: Continuous benchmarking
   - **Fallback**: Performance-critical users can use legacy

3. **Risk**: Behavioral differences
   - **Mitigation**: Comprehensive test coverage
   - **Fallback**: Document any intentional changes

4. **Risk**: User disruption
   - **Mitigation**: Gradual rollout with opt-out
   - **Fallback**: Long deprecation period

## Success Metrics

1. **Test Coverage**: 100% of tests pass with visitor executor
2. **Performance**: < 5% performance difference
3. **User Feedback**: < 1% of users report issues
4. **Code Quality**: 20% reduction in executor code complexity

## Communication Plan

1. **Announcement**: Blog post explaining benefits of visitor pattern
2. **Documentation**: Update all docs with new default
3. **Examples**: Show advanced features enabled by visitor pattern
4. **Support**: FAQ for common migration issues

## Rollback Plan

If critical issues are discovered:

1. Immediate: Flip default back to legacy executor
2. Fix issues in visitor executor
3. Re-attempt migration with fixes

## Conclusion

The visitor executor migration will modernize PSH's execution engine, enabling advanced features while maintaining compatibility. The phased approach ensures a smooth transition with minimal user disruption.