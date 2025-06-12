# Declare Enhancement Implementation Plan

## Current State

The shell currently stores variables as simple strings in the ScopeManager. The declare builtin has basic functionality but lacks:

1. **Persistent attribute storage** - Attributes are not saved with variables
2. **Integer arithmetic evaluation** - The -i flag doesn't evaluate arithmetic expressions
3. **Array support** - Arrays are stored as strings, not as proper array objects
4. **Attribute transformations** - Uppercase/lowercase conversions don't persist
5. **Proper declare -p output** - Missing attribute flags in output
6. **Attribute removal** - The + prefix to remove attributes isn't implemented

## Test Results Summary

From the comprehensive test suite (32 tests):
- **Passed**: 10 tests (31%)
- **Failed**: 22 tests (69%)

Working features:
- Basic -l and -u transformations on initial assignment
- -a and -A array declarations (creates empty arrays)
- Function listing with -f and -F
- Invalid option detection
- Mutually exclusive option checking (-a vs -A)

## Implementation Plan

### Phase 1: Variable Storage Enhancement

1. **Modify ScopeManager** to store Variable objects instead of strings
   - Update `Scope` class to use `Dict[str, Variable]`
   - Maintain backward compatibility with string access
   - Add methods for attribute management

2. **Update ShellState** methods
   - Modify `get_variable()` to return Variable values
   - Modify `set_variable()` to handle Variable objects
   - Add `get_variable_with_attributes()` method
   - Add `set_variable_attributes()` method

### Phase 2: Declare Builtin Enhancement

1. **Persistent Attributes**
   - Store and retrieve Variable objects with attributes
   - Apply transformations on every assignment
   - Handle attribute combinations properly

2. **Integer Arithmetic**
   - Integrate with ArithmeticEvaluator for -i flag
   - Evaluate expressions on assignment
   - Handle errors gracefully (default to 0)

3. **Array Support**
   - Parse array initialization syntax properly
   - Store IndexedArray and AssociativeArray objects
   - Handle array element access in variable expansion

4. **Attribute Removal**
   - Implement + prefix for removing attributes
   - Handle readonly attribute special case (cannot be removed)

5. **Enhanced declare -p**
   - Show all attributes in output
   - Format arrays properly
   - Handle special character escaping

### Phase 3: Integration

1. **Variable Expansion**
   - Update VariableExpander to handle Variable objects
   - Support array element expansion
   - Apply attribute transformations

2. **Assignment Processing**
   - Update assignment handling to preserve attributes
   - Apply transformations based on attributes
   - Handle readonly checking

3. **Export/Import**
   - Update export builtin to work with attributes
   - Handle environment variable import with attributes

## Priority Order

1. **First**: Variable storage system (Phase 1)
2. **Second**: Basic declare functionality (Phase 2.1-2.2)
3. **Third**: Array support (Phase 2.3)
4. **Fourth**: Full integration (Phase 3)

## Backwards Compatibility

- Existing code using string variables must continue to work
- The scope manager must support both string and Variable access
- Environment variables remain as strings
- Simple assignments without declare should work as before

## Testing Strategy

1. Run existing tests to ensure no regression
2. Incrementally enable declare_enhanced tests as features are implemented
3. Add integration tests for variable usage across different contexts
4. Test performance impact of Variable objects vs strings