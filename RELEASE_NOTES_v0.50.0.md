# PSH v0.50.0 Release Notes - Visitor Executor Now Default

## Overview

Version 0.50.0 marks a major milestone for Python Shell (psh) by making the visitor pattern executor the default execution engine. This architectural change provides cleaner code organization, better extensibility, and maintains full backward compatibility.

## Key Changes

### Visitor Executor as Default
- The visitor pattern executor is now the primary execution engine
- Provides cleaner separation of concerns and better code organization
- Enables easier addition of new features without modifying core AST nodes
- All 1165 tests pass with the new default

### Backward Compatibility
- Legacy executor remains available via `--legacy-executor` flag
- Environment variable `PSH_USE_VISITOR_EXECUTOR=0` disables visitor executor
- No breaking changes to shell functionality
- All existing scripts continue to work unchanged

### Performance
- Factorial recursion tested successfully up to factorial(30)
- No performance regressions observed
- Maintains educational clarity while improving architecture

## Usage

### Default Behavior (Visitor Executor)
```bash
psh                           # Interactive shell with visitor executor
psh script.sh                 # Run script with visitor executor
psh -c 'echo "Hello"'        # Execute command with visitor executor
```

### Using Legacy Executor
```bash
psh --legacy-executor                    # Interactive shell with legacy executor
PSH_USE_VISITOR_EXECUTOR=0 psh          # Via environment variable
```

## Technical Details

### Architecture Benefits
1. **Separation of Concerns**: AST nodes are pure data structures; operations are in visitors
2. **Extensibility**: New operations can be added by creating new visitor classes
3. **Maintainability**: Related code is grouped together in visitor implementations
4. **Type Safety**: Visitor pattern provides compile-time guarantees for completeness

### Implementation Phases Completed
- Phase 1: Base visitor infrastructure
- Phase 2: Enhanced validation visitors
- Phase 3: Executor visitor implementation
- Phase 4: Production-ready integration
- Phase 5: Default executor migration (this release)

## Known Limitations

Both executors share these architectural limitations:
- Deep recursion in shell functions may hit Python's stack limit
- Command substitution output capture has issues in pytest environments

## Future Work

With the visitor pattern as default, future enhancements can include:
- Optimization visitors for performance improvements
- Security analysis visitors
- Code transformation visitors
- Enhanced error recovery mechanisms

## Testing

All 1165 tests pass with the visitor executor as default, demonstrating full compatibility and stability.

## Conclusion

Version 0.50.0 represents the successful completion of the visitor pattern migration, providing PSH with a more maintainable and extensible architecture while preserving its educational value and shell compatibility.