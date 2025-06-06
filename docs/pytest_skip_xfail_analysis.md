# PSH Pytest Skip/XFail Analysis

## Summary

Analysis of all tests marked with `@pytest.mark.skip` or `@pytest.mark.xfail` in the PSH test suite.

**Total skipped/xfailed tests: 17**

## Tests That Now Pass

After analysis and manual testing, the following tests now pass due to the v0.33.0 for loop variable persistence fix:

1. **test_break_continue.py**:
   - `test_break_in_for_loop` - Now passes ✅
   - `test_continue_in_for_loop` - Now passes ✅
   - Both were skipped with reason "For loop variable persistence not implemented correctly"
   - Fixed in v0.33.0 when for loop variable restoration was removed

## Tests Still Failing/Skipped

### Pipeline Output Capture Issues (8 tests)
These fail due to pytest's inability to capture output from forked processes in pipelines:

1. **test_builtin_refactor.py**: `test_echo_in_pipeline` - Echo in forked process
2. **test_echo_flags.py**: `test_echo_in_pipeline_with_flags` - Echo in pipeline
3. **test_local_builtin.py**: `test_local_variable_in_pipeline` - Local vars in pipeline
4. **test_nested_control_structures.py**: `test_while_read_pattern` - While read conflicts with pytest
5. **test_pipeline.py**: 
   - `test_builtin_in_pipeline` - pwd builtin in pipeline
   - `test_multiple_builtins_in_pipeline` - Multiple builtins
6. **test_stderr_redirect.py**: 
   - `test_builtin_stderr_redirect` - Echo stderr in pipeline
   - `test_mixed_command_stderr_redirect` - Mixed stderr redirect

**Solution**: These tests work fine when run manually or with `pytest -s`. Consider:
- Using temporary files instead of capsys for output capture
- Creating a custom pytest fixture for pipeline tests
- Marking with a custom marker like `@pytest.mark.requires_no_capture`

### Parser/Architecture Limitations (3 tests)

1. **test_break_continue.py**: 
   - `test_break_continue_parsing` - AST structure issue
   - `test_break_continue_with_pipes_and_operators` - `&& break` parsing

2. **test_functions.py**: `test_function_with_arithmetic_expansion` - Arithmetic parser doesn't support command substitution

**Solution**: Would require parser enhancements to support these edge cases.

### Not Yet Implemented Features (3 tests)

1. **test_glob.py**: `test_escaped_glob` - Escaped glob patterns not implemented
2. **test_parameter_expansion.py**: `test_array_length` - Arrays not implemented
3. **test_ps1_exclamation.py**: `test_ps1_history_substitution` - PS1 with `\!` not implemented

### Test Infrastructure Issues (3 tests)

1. **test_command_substitution.py**: `test_syntax_error_missing_paren` - Test isolation issue
2. **test_echo_flags.py**: `test_echo_e_flag_octal` - Shell escape handling issue
3. **test_variables.py**: `test_variable_in_arithmetic_with_spaces` - Test expects feature not implemented

## Recommendations

1. **Update test_break_continue.py**: Remove skip decorators from the two tests that now pass
2. **Create pytest marker**: Add `@pytest.mark.requires_no_capture` for pipeline tests
3. **Document limitations**: Add comments explaining why tests are skipped
4. **Alternative testing**: Use file-based output capture for pipeline tests
5. **Track feature requests**: Create GitHub issues for unimplemented features

## Code Changes Needed

### Remove Skip Decorators
```python
# In test_break_continue.py, remove these lines:
# Line 62: @pytest.mark.skip(reason="For loop variable persistence not implemented correctly")
# Line 89: @pytest.mark.skip(reason="For loop variable persistence not implemented correctly")
```

### Add Custom Marker
```python
# In conftest.py or pytest.ini:
markers =
    requires_no_capture: Test requires running without output capture (pytest -s)
```

This analysis shows that 2 tests can be immediately fixed, 8 are pytest limitations (not PSH bugs), and the remaining require either parser enhancements or new feature implementations.