# Deprecated Types Removal Plan

## Overview

This plan outlines the systematic removal of deprecated Statement/Command dual types from the PSH codebase. The deprecated types were marked for removal in v0.38.0 and should be removed for v0.40.0.

## Deprecated Types to Remove

| Deprecated Statement | Deprecated Command | Unified Replacement |
|---------------------|-------------------|---------------------|
| WhileStatement | WhileCommand | WhileLoop |
| ForStatement | ForCommand | ForLoop |
| CStyleForStatement | CStyleForCommand | CStyleForLoop |
| IfStatement | IfCommand | IfConditional |
| CaseStatement | CaseCommand | CaseConditional |
| SelectStatement | SelectCommand | SelectLoop |
| ArithmeticCommand | ArithmeticCompoundCommand | ArithmeticEvaluation |

## Removal Phases

### Phase 1: Update Parser to Use Unified Types Only
**Goal**: Make the parser always create unified types, removing the feature flag

1. **Update psh/parser.py**:
   - Remove `_use_unified_types` flag
   - Update all parse methods to create unified types directly
   - Set appropriate ExecutionContext based on parsing context
   - Remove duplicate parsing logic

2. **Remove psh/parser_refactored.py**:
   - This was a temporary migration file
   - Move any useful code back to parser.py
   - Delete the file entirely

3. **Test Impact**:
   - All existing parser tests should continue to pass
   - Remove tests that specifically test the feature flag

### Phase 2: Update Executors
**Goal**: Remove all handling of deprecated types from executors

1. **Update psh/executor/control_flow.py**:
   - Remove isinstance checks for deprecated types
   - Keep only unified type handling
   - Simplify execute() method

2. **Update psh/executor/pipeline.py**:
   - Remove deprecated type checks from _execute_compound_in_subshell()
   - Keep only unified type handling

3. **Update psh/executor/statement.py**:
   - Remove deprecated type imports and checks
   - Simplify execute_toplevel()

4. **Update psh/executor/arithmetic_command.py**:
   - Update to handle only ArithmeticEvaluation

### Phase 3: Remove Deprecated Type Definitions
**Goal**: Remove all deprecated class definitions

1. **Update psh/ast_nodes.py**:
   - Remove all deprecated Statement/Command classes
   - Remove deprecation imports and decorators
   - Keep only unified types
   - Clean up imports

2. **Update psh/utils/ast_formatter.py**:
   - Update format_node() to handle only unified types
   - Remove deprecated type formatting

### Phase 4: Update All Tests
**Goal**: Migrate all tests to use unified types directly

1. **Update Test Imports**:
   - Remove warning suppressions
   - Import unified types directly
   - Update type assertions

2. **Files to Update**:
   - tests/test_while_loops.py
   - tests/test_for_loops.py
   - tests/test_c_style_for_loops.py
   - tests/test_control_structures.py
   - tests/test_if_statements.py (if exists)
   - tests/test_case_statements.py
   - tests/test_select_statement.py
   - tests/test_arithmetic_command.py
   - tests/test_parser.py
   - tests/test_nested_control_structures.py
   - Any other test files with deprecated imports

3. **Update Test Logic**:
   - Replace deprecated type checks with unified type checks
   - Add execution_context assertions where needed
   - Remove migration-specific test code

### Phase 5: Clean Up Migration Infrastructure
**Goal**: Remove all migration helpers and utilities

1. **Remove Migration Files**:
   - psh/deprecation.py
   - tests/helpers/parser_compat.py
   - tests/helpers/unified_types_helper.py
   - scripts/migrate_test_imports.py
   - tests/test_unified_parser.py
   - tests/test_unified_executor.py
   - tests/test_unified_integration.py
   - tests/test_control_structures_unified.py

2. **Remove Migration Documentation**:
   - Archive but don't delete docs/unified_types_migration.md
   - Update docs/parser_refactoring_phase3_status.md to indicate completion

### Phase 6: Final Verification
**Goal**: Ensure everything works correctly

1. **Run Full Test Suite**:
   - All tests should pass without deprecation warnings
   - No references to deprecated types should remain

2. **Update Documentation**:
   - Update ARCHITECTURE.md to reflect unified types
   - Update any examples or user guides
   - Update development documentation

3. **Code Review**:
   - Search for any remaining references to deprecated types
   - Verify all imports are correct
   - Check for any missed edge cases

## Implementation Order

To minimize risk and ensure smooth transition:

1. **Day 1**: Phase 1 (Parser updates)
2. **Day 2**: Phase 2 (Executor updates)
3. **Day 3**: Phase 3 (Remove deprecated definitions)
4. **Day 4-5**: Phase 4 (Update all tests)
5. **Day 6**: Phase 5 (Clean up migration infrastructure)
6. **Day 7**: Phase 6 (Final verification)

## Testing Strategy

After each phase:
- Run full test suite: `python -m pytest tests/`
- Check for deprecation warnings
- Verify no functionality regression
- Run shell interactively to test common use cases

## Rollback Plan

If issues arise:
1. Git provides full rollback capability
2. Each phase is independent and can be reverted
3. The unified types are already tested and working

## Success Criteria

- All tests pass without deprecation warnings
- No references to deprecated types remain in code
- Parser creates only unified types
- Executors handle only unified types
- Documentation is updated
- Code is cleaner and more maintainable

## Benefits After Removal

1. **Simpler Codebase**: One type per control structure
2. **Cleaner Parser**: No duplicate parsing logic
3. **Easier Maintenance**: Less code to maintain
4. **Better Performance**: Fewer type checks in executors
5. **Clearer Architecture**: Unified type hierarchy

## Version Planning

- **v0.38.0**: Deprecation warnings added ✓
- **v0.39.0**: Internal migration (this removal plan)
- **v0.40.0**: Public release with deprecated types removed