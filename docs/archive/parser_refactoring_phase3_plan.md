# Parser Refactoring Phase 3: Unifying Command/Statement Duality

## Current Architecture Analysis

### The Dual-Type System

PSH currently has parallel hierarchies for control structures:

1. **Statement Types** (for standalone execution):
   - `WhileStatement`, `ForStatement`, `IfStatement`, `CaseStatement`, etc.
   - Inherit from `Statement`
   - Executed by `ControlFlowExecutor` in the current shell process
   - Parsed by `parse_*_statement()` methods

2. **Command Types** (for pipeline execution):
   - `WhileCommand`, `ForCommand`, `IfCommand`, `CaseCommand`, etc.
   - Inherit from `CompoundCommand` → `Command`
   - Executed by `PipelineExecutor` in forked subshells
   - Parsed by `parse_*_command()` methods

### Problems with Current Approach

1. **Code Duplication**: Nearly identical parsing logic in statement and command parsers
2. **Type Complexity**: Doubled number of AST node types
3. **Maintenance Burden**: Changes must be made in two places
4. **Conceptual Confusion**: Not immediately clear why two types exist

### Benefits of Current Approach

1. **Clear Execution Context**: Type indicates whether subshell is needed
2. **Type Safety**: Can't accidentally execute pipeline command in wrong context
3. **Backward Compatibility**: Existing code continues to work
4. **Educational Clarity**: Makes execution model explicit

## Proposed Unified Architecture

### Option 1: Single Type with Execution Context (Recommended)

Create unified control structure types with an execution context field:

```python
@dataclass
class WhileLoop(Statement, Command):
    """Unified while loop that can be both Statement and Command."""
    condition: CommandList
    body: CommandList
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: str = "statement"  # "statement" or "pipeline"
    background: bool = False
```

Benefits:
- Single parsing method per control structure
- Execution strategy determined by context field
- Maintains type safety through context checking
- Easier to maintain

Implementation approach:
1. Create new unified types inheriting from both Statement and Command
2. Add execution_context field to track usage
3. Update parser to set context during parsing
4. Update executors to check context field
5. Gradually deprecate old dual types

### Option 2: Composition Over Inheritance

Use composition to avoid duplicate types:

```python
@dataclass
class WhileLoopCore:
    """Core while loop data."""
    condition: CommandList
    body: CommandList
    redirects: List[Redirect] = field(default_factory=list)

@dataclass
class WhileStatement(Statement):
    """Statement wrapper for while loop."""
    core: WhileLoopCore

@dataclass
class WhileCommand(CompoundCommand):
    """Command wrapper for while loop."""
    core: WhileLoopCore
    background: bool = False
```

Benefits:
- Shared core logic
- Clear type separation
- No multiple inheritance

Drawbacks:
- More complex access patterns (`.core.condition`)
- Still requires two types

### Option 3: Runtime Type Adaptation

Keep single type but adapt behavior at runtime:

```python
class WhileLoop(Statement):
    """While loop that adapts to context."""
    def as_command(self) -> Command:
        """Convert to command for pipeline use."""
        return WhileLoopCommand(self)
```

Benefits:
- Single source of truth
- Explicit conversion
- Flexible usage

Drawbacks:
- Runtime type changes can be confusing
- Requires wrapper types

## Recommended Implementation Plan

### Phase 3.1: Create Unified Types

1. Define new unified AST nodes with execution context
2. Update AST node imports to include new types
3. Add deprecation warnings to old types

### Phase 3.2: Update Parser

1. Replace duplicate parsing methods with unified versions
2. Set execution_context based on parsing context
3. Maintain compatibility layer for old types

### Phase 3.3: Update Executors

1. Modify executors to check execution_context field
2. Route to appropriate execution strategy
3. Ensure process isolation for pipeline contexts

### Phase 3.4: Migrate Tests

1. Update tests to use new unified types
2. Add tests for execution context behavior
3. Ensure backward compatibility tests pass

### Phase 3.5: Deprecate Old Types

1. Mark old dual types as deprecated
2. Update documentation
3. Plan removal in future version

## Migration Strategy

1. **Incremental Migration**: Start with one control structure (e.g., WhileLoop)
2. **Compatibility Layer**: Keep old types working during transition
3. **Test Coverage**: Ensure comprehensive tests before and after
4. **Documentation**: Update docs to explain new unified model

## Risk Mitigation

1. **Performance**: Profile to ensure no regression
2. **Compatibility**: Extensive testing of existing code
3. **Clarity**: Clear documentation of new model
4. **Rollback**: Keep old types available initially

## Success Criteria

1. Single parsing method per control structure
2. No functional regression
3. Simplified codebase
4. Clear execution model
5. All tests passing

## Timeline

- Phase 3.1: 2 hours - Create unified types
- Phase 3.2: 3 hours - Update parser
- Phase 3.3: 2 hours - Update executors  
- Phase 3.4: 2 hours - Migrate tests
- Phase 3.5: 1 hour - Deprecation plan

Total estimated time: 10 hours