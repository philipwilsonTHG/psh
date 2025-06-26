# PSH Heredoc Implementation Analysis and Improvement Plan

## Current Issues Identified

Based on conformance test analysis, the PSH heredoc implementation has several critical gaps:

### 1. **Quoted Delimiter Support (Critical)**
- **Issue**: Parser only accepts `TokenType.WORD` tokens as heredoc delimiters
- **Problem**: Quoted delimiters like `'EOF'` are tokenized as `TokenType.STRING`, causing parse failures
- **Impact**: Complete failure for quoted heredocs with "Expected delimiter after here document operator" error

### 2. **Variable Expansion Control**
- **Issue**: Missing `heredoc_quoted` flag in AST to track delimiter quoting status
- **Problem**: Cannot properly control variable expansion based on delimiter type
- **Impact**: Variables may expand incorrectly in quoted heredocs

### 3. **Content Collection in Complex Scenarios**
- **Issue**: Heredoc content missing in loops and control structures
- **Problem**: Integration between heredoc collection and loop execution incomplete
- **Impact**: "Here doc line: line1/line2/line3" content not appearing in test output

## Recommended Fixes

### Phase 1: Core Parser Fix (High Priority)
1. **Modify `_parse_heredoc()` in parser.py**:
   - Accept both `TokenType.WORD` and `TokenType.STRING` as valid delimiters
   - Detect quoted delimiters and set `heredoc_quoted` flag
   - Add proper error handling for invalid delimiter types

2. **Enhance AST Redirect node**:
   - Add `heredoc_quoted: bool = False` field to track delimiter quoting
   - Update constructor to handle quoted delimiter detection

### Phase 2: Variable Expansion Enhancement (Medium Priority)
1. **Update IOManager heredoc processing**:
   - Use `heredoc_quoted` flag to control variable expansion
   - Ensure quoted delimiters disable variable expansion
   - Verify unquoted delimiters enable variable expansion

2. **Fix expansion integration**:
   - Ensure proper interaction with ExpansionManager
   - Test all expansion types within heredocs

### Phase 3: Integration Testing (Medium Priority)
1. **Fix heredoc content in control structures**:
   - Verify heredoc collection works in while/for loops
   - Test heredoc processing in if statements and functions
   - Ensure proper content delivery to commands

2. **Update conformance test expectations**:
   - Fix golden files with correct expected output
   - Add comprehensive heredoc test coverage

### Phase 4: Edge Case Handling (Low Priority)
1. **Enhanced error handling**:
   - Better error messages for malformed heredocs
   - Proper handling of nested heredocs
   - EOF handling during heredoc collection

2. **Performance optimization**:
   - Optimize heredoc content collection
   - Reduce memory usage for large heredocs

## Expected Outcomes

- **POSIX Compliance**: Fix quoted heredoc delimiter support (critical POSIX requirement)
- **Test Results**: Improve IO redirection tests from 1/2 to 2/2 passing
- **Functionality**: Complete heredoc support in all contexts (loops, conditionals, functions)
- **Variable Expansion**: Proper control based on delimiter quoting status

This plan addresses the fundamental parser limitation that prevents proper heredoc processing and builds toward full POSIX compliance for heredoc functionality.

## Implementation Priority

1. **Immediate**: Fix quoted delimiter parsing (Phase 1)
2. **Short-term**: Variable expansion control (Phase 2)
3. **Medium-term**: Integration testing and fixes (Phase 3)
4. **Long-term**: Edge cases and optimization (Phase 4)

## Success Metrics

- All conformance tests with heredocs should pass
- Quoted and unquoted delimiters work correctly
- Variable expansion behaves according to POSIX standards
- Heredocs work in all shell contexts (loops, functions, conditionals)