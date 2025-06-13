# Skipped Tests Analysis

## Summary
After the v0.28.2 release with the new state machine lexer, we have:
- **597 tests passing** (up from 596)
- **23 tests skipped**
- **2 tests marked as xfail**

## Tests That Can Be Unskipped

### 1. Variable Assignment with Spaces (FIXED)
- `test_variable_assignment_command.py::test_assignment_with_spaces_in_value`
- Status: **Fixed and unskipped**
- The new state machine lexer properly handles `VAR="value with spaces"`

### 2. Break/Continue in For Loops 
- `test_break_continue_simple.py` - All tests are passing
- The break/continue functionality in for loops works correctly

## Remaining Skipped Tests by Category

### 1. Pipeline/Output Capture Conflicts (40% of skipped tests)
These are architectural issues where pytest's output capture interferes with shell's fork/pipe implementation:

- `test_pipeline.py::test_pipeline_with_builtin`
- `test_for_loops.py::test_for_with_pipeline_in_body`
- `test_nested_control_structures.py::test_nested_structures_with_pipes`
- `test_nested_control_structures.py::test_heredoc_in_nested_structure`
- `test_nested_control_structures.py::test_pipelines_still_work`
- `test_builtin_refactor.py::test_builtin_in_pipeline`
- `test_glob.py::test_glob_in_pipeline`
- `test_heredoc.py::test_heredoc_with_external_command`
- `test_heredoc.py::test_heredoc_in_pipeline`
- `test_command_substitution.py::test_command_substitution_in_pipeline`

**Root Cause**: When builtins run in child processes (for pipelines), their output goes directly to file descriptors, bypassing pytest's capture mechanism.

### 2. Nested Control Structures (Architecture Limitation)
- `test_for_loops.py::test_for_with_conditional_commands`
- `test_for_loops.py::test_for_nested_in_other_constructs`

**Root Cause**: AST architecture currently doesn't support arbitrary nesting of control structures.

### 3. Parser/Tokenizer Fundamental Issues
- `test_break_continue.py::test_break_continue_parsing` - Returns statements, not and_or_lists
- `test_break_continue.py::test_break_continue_with_pipes_and_operators` - Parse error with break after &&
- `test_break_continue.py::test_break_in_for_loop` - Variable persistence issue
- `test_break_continue.py::test_continue_in_for_loop` - Variable persistence issue
- `test_break_continue.py::test_variable_scoping_with_break_continue` - Variable restoration issue

### 4. Escape Sequence Handling
- `test_ps1_exclamation.py::test_ps1_with_various_escape_sequences` - PS1 escape in double quotes
- `test_ps1_exclamation.py::test_ps1_heuristic_vs_normal_variables` - PS1 escape in double quotes
- `test_tilde_expansion.py::test_escaped_tilde` - `\~` still expands when it shouldn't
- `test_glob.py::test_escaped_globs` - Escape handling for globs not implemented
- `test_command_substitution.py::test_backtick_escape_sequences` - Backtick escape handling

### 5. Complex Feature Interactions
- `test_heredoc.py::test_heredoc_with_output_redirect` - Multiple redirections
- `test_variables.py::test_special_variable_dollar_exclamation` - Background process handling

### 6. XFail Tests (Expected to fail)
- `test_functions.py::test_function_in_pipeline` - Functions in pipelines have stdout issues
- `test_nested_control_structures.py::test_while_read_pattern` - While read pattern conflicts

## Architectural Issues Summary

1. **Output Capture in Pipelines**: The fundamental conflict between pytest's output capture and the shell's fork/pipe architecture affects ~40% of skipped tests. This is not easily fixable without major architectural changes.

2. **Escape Sequence Context**: Different contexts (PS1, tildes, globs, backticks) need different escape handling rules, requiring more sophisticated tokenization.

3. **Variable Scoping**: Break/continue in for loops have issues with variable persistence and restoration.

4. **Nested Structures**: The current AST doesn't support arbitrary nesting of control structures within pipelines.

## Recommendations

1. **Keep Pipeline Tests Skipped**: These represent a fundamental architectural conflict that's not worth fixing for test purposes alone.

2. **Document Escape Limitations**: The escape sequence handling issues should be documented as known limitations.

3. **Consider Variable Scoping Fix**: The break/continue variable persistence issues might be fixable with better state management.

4. **Update Skip Messages**: Make skip messages more specific about whether issues are architectural limitations or just unimplemented features.