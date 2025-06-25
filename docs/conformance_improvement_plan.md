# PSH Conformance Improvement Plan

This document outlines areas where PSH legitimately needs improvement based on conformance testing against POSIX (dash) and bash standards. The analysis is based on systematic comparison testing using the conformance test framework.

## Executive Summary

Based on comprehensive conformance testing:
- **PSH vs POSIX (dash)**: 13/61 tests pass (21% compatibility)
- **PSH vs bash**: 17/61 tests pass (28% compatibility)

PSH demonstrates solid foundational compatibility but has specific gaps in core shell functionality that should be addressed for better standards compliance.

## Critical POSIX Compliance Issues

### 1. Command Substitution - High Priority

**Issue**: Backtick command substitution is broken
```bash
# Expected behavior
result=`echo "test"`  # Should set result="test"

# PSH behavior
result=`echo "test"`  # Sets result="`echo "test"`" (literal)
```

**Impact**: Breaks compatibility with legacy scripts using backticks
**Location**: Lexer/expansion system
**Tests affected**: `test_command_substitution.input`, multiple others

### 2. Here Document Processing - High Priority

**Issue**: Command substitution and variable expansion in here documents not working
```bash
# Expected behavior
cat << EOF
Current date: $(date)
User: $USER
EOF

# PSH behavior - no expansion occurs
```

**Impact**: Common scripting pattern fails
**Location**: Here document processor
**Tests affected**: Multiple tests with here docs

### 3. Parameter Expansion Edge Cases - Medium Priority

**Issue**: Some complex parameter expansion patterns fail
```bash
# Issues with nested expansions, array slicing syntax
echo ${array[@]:1:2}  # Array slicing
echo ${var/pattern/replacement}  # Pattern substitution
```

**Impact**: Breaks bash-compatible scripts
**Location**: Parameter expansion engine

### 4. Echo Command Behavior - Medium Priority

**Issue**: `echo -e` flag handling differs from POSIX/bash
```bash
# PSH vs dash/bash differ on echo -e behavior
echo -e "line1\nline2"
```

**Impact**: Script output differences
**Location**: Echo builtin implementation

## Bash Compatibility Gaps

### 1. Enhanced Test Operators - Low Priority (Extension)

**Status**: PSH actually supports `[[ ]]` operators that dash doesn't
**Note**: This is PSH implementing bash extensions beyond POSIX
**Decision**: Keep current implementation (good feature)

### 2. Array Display Format - Low Priority

**Issue**: PSH displays arrays differently than bash
```bash
# Bash: zero two five
# PSH:  [0]=zero [2]=two [5]=five
```

**Impact**: Minor cosmetic difference
**Location**: Array expansion formatting

### 3. Function Name Variable (FUNCNAME) - Low Priority

**Issue**: PSH doesn't support bash's `$FUNCNAME` variable
**Impact**: Some bash scripts rely on this for debugging
**Location**: Function execution context

## Lexer/Parser Issues

### 1. Multi-line Command Parsing - High Priority

**Issue**: Complex multi-line command substitution fails
```bash
# Fails with "Unclosed parenthesis" errors
result=$(
    echo "line1"
    echo "line2"
)
```

**Impact**: Breaks common scripting patterns
**Location**: Lexer balanced parentheses handling

### 2. Brace Expansion Completeness - Medium Priority

**Issue**: Some brace expansion patterns not fully implemented
```bash
# Works: {1..5}
# Doesn't work: {red,green,blue} in some contexts
```

**Impact**: Script compatibility issues
**Location**: Expansion system

### 3. Process Substitution - Low Priority (Extension)

**Issue**: `<(...)` and `>(...)` syntax has limited support
**Note**: This is a bash extension, not POSIX-required
**Impact**: Advanced bash scripts won't work

## Built-in Command Issues

### 1. Local Command with Attributes - Medium Priority

**Issue**: `local -x var=value` syntax not fully supported
```bash
# Bash supports this, PSH has limitations
local -x exported_local="value"
```

**Impact**: Function-scoped environment variables
**Location**: Local builtin implementation

### 2. Set Options Completeness - Medium Priority

**Issue**: Many bash `set` options not implemented
```bash
set -o allexport  # Not supported
set -o braceexpand  # Not supported
```

**Impact**: Shell behavior customization limited
**Location**: Set builtin

### 3. Export Command Output Format - Low Priority

**Issue**: `export` without arguments doesn't show `declare -x` format
**Impact**: Minor compatibility difference
**Location**: Export builtin

## Variable Scoping Issues

### 1. Local Variable Unset Behavior - Medium Priority

**Issue**: `unset` behavior in functions differs from bash
```bash
function test() {
    local var="local"
    unset var
    echo $var  # Should be empty, but inherits global
}
```

**Impact**: Function variable isolation
**Location**: Variable scoping system

### 2. Parameter Restoration - Medium Priority

**Issue**: Positional parameter restoration in functions
```bash
# Saving and restoring $@ doesn't work correctly
```

**Impact**: Function parameter handling
**Location**: Parameter management

## Improvement Priority Matrix

### Immediate (Critical for basic compatibility)
1. **Backtick command substitution** - Core POSIX feature
2. **Here document expansion** - Common scripting pattern  
3. **Multi-line command parsing** - Parser stability

### Short-term (Important for script compatibility)
1. **Echo -e flag handling** - POSIX compliance
2. **Complex parameter expansion** - Script compatibility
3. **Local variable scoping** - Function behavior

### Medium-term (Enhanced compatibility)
1. **Brace expansion completeness** - Bash compatibility
2. **Set options implementation** - Shell customization
3. **Array formatting consistency** - Output compatibility

### Long-term (Advanced features)
1. **Process substitution** - Advanced bash features
2. **FUNCNAME variable** - Debugging support
3. **Advanced built-in options** - Full bash compatibility

## Testing Strategy

### Conformance Test Enhancement
- Add specific tests for each identified issue
- Create regression tests for fixes
- Expand edge case coverage

### Validation Approach
- Test fixes against both dash (POSIX) and bash
- Ensure no regressions in existing functionality
- Validate with real-world scripts

### Success Metrics
- **POSIX compliance target**: 80%+ tests passing vs dash
- **Bash compatibility target**: 60%+ tests passing vs bash
- **No regressions**: Maintain current passing tests

## Implementation Notes

### Code Areas Requiring Attention
1. **Lexer package** (`psh/lexer/`) - Command substitution, multi-line parsing
2. **Expansion manager** (`psh/expansion/`) - Parameter expansion, here docs
3. **Built-ins** (`psh/builtins/`) - Echo, local, set, export
4. **Variable scoping** (`psh/core/state.py`) - Local/global interaction

### Architecture Considerations
- Maintain clean separation of concerns
- Ensure educational code clarity
- Preserve performance characteristics
- Keep visitor pattern consistency

## Conclusion

PSH has a solid foundation with 21-28% compatibility with major shells. The identified improvements focus on core POSIX compliance rather than extensive bash extension implementation. Addressing the high-priority items (backtick substitution, here document processing, multi-line parsing) would significantly improve script compatibility while maintaining PSH's educational clarity and design principles.

The improvement plan balances practical compatibility needs with PSH's educational mission, prioritizing fixes that provide the greatest compatibility improvement for the implementation effort required.