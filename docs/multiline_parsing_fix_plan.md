# Multi-line Command Substitution Parser Crash Fix Plan

## Problem Analysis

### Root Cause Identified
The multi-line command substitution parser crash occurs because:

1. **Source processor tests command completeness** using `tokenize(test_command)` on line 106 of `source_processor.py`
2. **Default tokenizer uses strict mode** which immediately throws `LexerError` on incomplete constructs
3. **Incomplete command substitutions** like `cmd_sub_result=$(` trigger the error before the source processor can detect them as incomplete
4. **The lexer helpers were already partially fixed** to return `(content, is_closed)` but still error in strict mode

### Error Flow
```
source_processor.py:106 → tokenize(test_command) → StateMachineLexer(default_config) → strict_mode=True → read_balanced_parens() → self._error("Unclosed parenthesis") → LexerError raised
```

### Current State
- ✅ `read_balanced_parens()` and `read_balanced_double_parens()` already return `(content, is_closed)` 
- ✅ Lexer helpers respect `strict_mode` configuration
- ❌ Source processor uses strict mode for completeness testing (should use non-strict)
- ❌ Default `tokenize()` function doesn't support non-strict mode

## Solution Plan

### Phase 1: Modify tokenize() Function (Low Risk)
**Objective**: Add optional non-strict mode to `tokenize()` function

**Changes**:
1. **Update `tokenize()` signature** in `/Users/pwilson/src/psh/psh/lexer/__init__.py`:
   ```python
   def tokenize(input_string: str, strict: bool = True) -> List[Token]:
   ```
2. **Create appropriate lexer config** based on strict parameter:
   ```python
   if strict:
       config = LexerConfig.create_batch_config()  # strict_mode=True  
   else:
       config = LexerConfig.create_interactive_config()  # strict_mode=False
   ```
3. **Pass config to StateMachineLexer**:
   ```python
   lexer = StateMachineLexer(input_string, config=config)
   ```

### Phase 2: Update Source Processor (Medium Risk)
**Objective**: Use non-strict tokenization for completeness testing

**Changes**:
1. **Modify source_processor.py line 106**:
   ```python
   # Before
   tokens = tokenize(test_command)
   
   # After  
   tokens = tokenize(test_command, strict=False)
   ```

2. **Handle LexerError gracefully** as incomplete command indicator:
   ```python
   try:
       tokens = tokenize(test_command, strict=False)
       parse(tokens)
       # Command is complete
   except (ParseError, LexerError) as e:
       if self._is_incomplete_command(e):
           continue  # Incomplete command
       else:
           # Real error
   ```

### Phase 3: Update Error Detection (Low Risk)  
**Objective**: Enhance incomplete command detection

**Changes**:
1. **Update `_is_incomplete_command()`** to handle `LexerError`:
   ```python
   def _is_incomplete_command(self, error: Union[ParseError, LexerError]) -> bool:
       error_msg = str(error)
       
       # Handle lexer errors from incomplete constructs
       lexer_incomplete_patterns = [
           "Unclosed parenthesis",
           "Unclosed double parentheses", 
           "Unclosed brace",
           "Unclosed quote"
       ]
       
       for pattern in lexer_incomplete_patterns:
           if pattern in error_msg:
               return True
               
       # Existing parser error patterns...
   ```

### Phase 4: Testing and Validation
**Objective**: Ensure fix works correctly

**Test Cases**:
1. **Multi-line command substitution**:
   ```bash
   result=$(
   echo test
   )
   ```

2. **Multi-line arithmetic**:
   ```bash
   result=$((
   5 + 3
   ))
   ```

3. **Interactive mode** should handle incomplete commands gracefully
4. **Batch mode** should still error on truly malformed syntax
5. **Existing functionality** should remain unchanged

## Expected Outcomes

### Before Fix
```bash
$ psh -c 'result=$(
echo test
)'
Lexer Error: Unclosed parenthesis [CRASH]
```

### After Fix  
```bash
$ psh -c 'result=$(
echo test
)'
# Works correctly - command executes and assigns result
```

### Benefits
- ✅ **Eliminates parser crashes** on multi-line constructs
- ✅ **Improves POSIX compliance** by supporting standard multi-line syntax
- ✅ **Minimal changes** - only touches tokenizer interface and source processor
- ✅ **Backward compatibility** - existing code unchanged
- ✅ **Interactive improvement** - better multi-line handling in shell

## Risk Assessment

### Low Risk Changes
- Adding optional parameter to `tokenize()`
- Updating error detection patterns
- Test case additions

### Medium Risk Changes  
- Modifying source processor completeness testing
- Changing error handling flow

### Mitigation Strategies
- **Comprehensive testing** of both interactive and batch modes
- **Gradual rollout** - test each phase independently  
- **Fallback plan** - revert to strict mode if issues arise
- **Regression testing** - ensure existing tests pass

## Implementation Timeline

1. **Phase 1**: 30 minutes - Update tokenize() function
2. **Phase 2**: 20 minutes - Update source processor  
3. **Phase 3**: 15 minutes - Enhance error detection
4. **Phase 4**: 30 minutes - Testing and validation

**Total Estimated Time**: 1.5 hours

This plan provides a robust fix for the multi-line parsing crash while maintaining existing functionality and improving PSH's overall stability and POSIX compliance.