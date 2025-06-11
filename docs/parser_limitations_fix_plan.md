# Parser Limitations Fix Plan

This document outlines plans to fix the real parser limitations identified through bash comparison testing.

## Overview

Bash comparison testing revealed that PSH has far fewer limitations than originally documented in TODO.md. Most quote handling works correctly. However, two real limitations need fixing:

1. **Composite Argument Quote Handling in Redirection** (High Priority)
2. **Backslash Escaping** (Medium Priority)

## 1. Composite Argument Quote Handling in Redirection

### Problem Description
- **Issue**: `echo test > file'name'.txt` creates file named `file` instead of `filename.txt`
- **Root Cause**: Parser loses quote information when processing redirection targets
- **Scope**: Only affects redirection contexts; echo works correctly

### Current Behavior Analysis
```bash
# Works correctly (echo context)
echo file'*'.txt  # Output: file*.txt

# Fails (redirection context)  
echo test > file'name'.txt  # Creates file named 'file', not 'filename.txt'
```

### Technical Investigation Needed

#### Step 1: Locate Redirection Parsing Code
- **File**: `psh/parser.py` - redirection parsing methods
- **File**: `psh/io_redirect/manager.py` - redirection handling
- **Method**: Find where redirection targets are parsed and processed

#### Step 2: Compare with Command Argument Parsing
- Command arguments (for echo) work correctly with quotes
- Redirection targets use different parsing path
- Need to identify why they differ

#### Step 3: Debug Token Processing
```bash
# Debug redirection parsing
python3 -m psh --debug-tokens -c "echo test > file'name'.txt"
python3 -m psh --debug-ast -c "echo test > file'name'.txt"
```

### Implementation Plan

#### Phase 1: Investigation (1-2 hours)
1. **Trace redirection parsing flow**
   - Add debug prints to redirection parsing
   - Compare token processing between echo args and redirection targets
   - Identify where quote information is lost

2. **Analyze AST structure**
   - Check if quotes are preserved in AST for redirection targets
   - Compare AST structure between working and failing cases

#### Phase 2: Fix Implementation (2-3 hours)
1. **Option A: Fix at parser level**
   - Ensure redirection target parsing preserves quote information
   - Apply same quote handling logic used for command arguments

2. **Option B: Fix at execution level**
   - Modify redirection execution to handle quoted composites
   - Process quotes during file path resolution

#### Phase 3: Testing (1 hour)
1. **Add comprehensive tests**
   - Test various quote patterns in redirection
   - Ensure no regression in existing functionality
   - Add to bash comparison framework

### Expected Files to Modify
- `psh/parser.py` - redirection parsing logic
- `psh/io_redirect/manager.py` - redirection execution
- `tests/test_redirection.py` - add regression tests
- `tests/comparison/test_bash_parser_limitations.py` - update tests

### Success Criteria
```bash
# These should work after fix
echo test > file'name'.txt && ls filename.txt     # ✓
echo test > pre'fix'suf.txt && ls prefixsuf.txt   # ✓
echo test > 'quoted file.txt' && ls "quoted file.txt"  # ✓
```

## 2. Backslash Escaping

### Problem Description
- **Issue**: `echo \$variable` outputs empty string instead of `$variable`
- **Root Cause**: PSH doesn't handle backslash escaping like bash
- **Scope**: Affects literal character output

### Current Behavior Analysis
```bash
# Bash behavior
echo \$variable  # Output: $variable
echo \*glob      # Output: *glob

# PSH behavior  
echo \$variable  # Output: (empty)
echo \*glob      # Output: *glob (this works)
```

### Technical Investigation Needed

#### Step 1: Locate Escaping Code
- **File**: `psh/state_machine_lexer.py` - tokenization and escaping
- **File**: `psh/expansion/` - expansion processing
- **Method**: Find where backslash escaping is handled

#### Step 2: Compare with Bash Escaping Rules
- Identify which characters should be escapable
- Understand context-dependent escaping (quotes vs unquoted)
- Document expected behavior

### Implementation Plan

#### Phase 1: Investigation (1-2 hours)
1. **Study bash escaping rules**
   - Document which characters can be escaped
   - Understand context-dependent behavior
   - Create test matrix of escaping scenarios

2. **Trace PSH escaping logic**
   - Find where backslash processing occurs
   - Identify why `\$` fails but `\*` works (partially)

#### Phase 2: Fix Implementation (3-4 hours)
1. **Implement proper escaping logic**
   - Handle backslash escaping in tokenizer
   - Ensure escaped characters are treated literally
   - Handle context-dependent escaping rules

2. **Integration with existing systems**
   - Ensure escaping works with variable expansion
   - Maintain compatibility with existing quote handling
   - Test interaction with glob expansion

#### Phase 3: Testing (1-2 hours)
1. **Comprehensive escaping tests**
   - Test all escapable characters
   - Test in different contexts (quoted, unquoted)
   - Add to bash comparison framework

### Expected Files to Modify
- `psh/state_machine_lexer.py` - tokenization escaping
- `psh/expansion/manager.py` - expansion processing
- `tests/test_escaping.py` - new escaping tests
- `tests/comparison/test_bash_parser_limitations.py` - update tests

### Success Criteria
```bash
# These should work after fix
echo \$variable     # Output: $variable
echo \*no_glob      # Output: *no_glob  
echo \"quoted\"     # Output: "quoted"
echo \\backslash    # Output: \backslash
```

## 3. Implementation Priority

### High Priority: Redirection Quote Handling
- **Effort**: 4-6 hours
- **Impact**: High - breaks file operations with quoted names
- **Risk**: Low - localized to redirection parsing

### Medium Priority: Backslash Escaping  
- **Effort**: 5-7 hours
- **Impact**: Medium - affects literal character output
- **Risk**: Medium - could affect existing functionality

## 4. Testing Strategy

### Regression Testing
- Ensure all existing bash comparison tests continue to pass
- Add specific tests for fixed limitations
- Test edge cases and combinations

### Integration Testing
- Test interaction between fixes
- Ensure compatibility with existing quote handling
- Verify no performance regression

### Documentation Updates
- Update TODO.md when limitations are fixed
- Update bash comparison tests to reflect fixes
- Document any behavior changes

## 5. Long-term Improvements

### Enhanced Bash Compatibility Testing
- Expand bash comparison framework
- Add more edge cases and complex scenarios
- Continuous compatibility verification

### Parser Architecture Review
- Consider parser refactoring for better quote handling
- Evaluate tokenizer improvements
- Plan for future bash compatibility features

## 6. Success Metrics

### Quantitative
- All bash comparison tests pass (currently 56/56)
- New limitation tests pass after fixes
- No regression in existing test suite (850+ tests)

### Qualitative  
- PSH behaves identically to bash for common use cases
- Improved user experience with file operations
- Better scripting compatibility

## Implementation Timeline

**Week 1**: Redirection quote handling fix
- Days 1-2: Investigation and debugging
- Days 3-4: Implementation and testing
- Day 5: Documentation and integration

**Week 2**: Backslash escaping fix  
- Days 1-2: Investigation and bash compatibility study
- Days 3-5: Implementation, testing, and integration

**Total Effort**: ~10-13 hours over 2 weeks