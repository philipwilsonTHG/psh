# Comprehensive POSIX Conformance Test Plan for PSH

## Overview

This document outlines a comprehensive plan for adding POSIX conformance tests that exercise all features of PSH. The plan is based on analysis of PSH's extensive feature set as documented in `psh/version.py` (58 versions of features) and the user guide documentation.

## Current Test Coverage Analysis

The existing conformance test framework in `conformance_tests/` currently covers only basic functionality:
- Basic commands (`test_echo`)
- Simple control structures (`test_if`, `test_for`, `test_while`) 
- Command substitution (`test_command_sub`)
- Case statements and quoting (`test_case`, `test_quoting`)

This represents approximately 5% of PSH's total feature set. The following plan addresses the remaining 95% of features.

## Missing Test Categories (Organized by Priority)

### **High Priority - Core POSIX Features**

#### 1. Built-in Commands (24+ builtins implemented)
- `test_cd` - Directory navigation, OLDPWD, cd - functionality
- `test_set` - Shell options (-e errexit, -u nounset, -x xtrace, -o pipefail)
- `test_export_unset` - Environment variable management and export
- `test_shift_getopts` - Positional parameter manipulation and option parsing
- `test_read` - Input processing with flags (-p, -s, -t, -n, -d)
- `test_eval` - Dynamic command execution and variable evaluation
- `test_source` - Script sourcing with PATH search and arguments
- `test_alias_unalias` - Command aliases with recursive expansion
- `test_help` - Self-documentation and builtin information
- `test_declare_typeset` - Variable attributes and function introspection
- `test_exec` - Process replacement and permanent redirections
- `test_kill` - Process signaling and job control integration
- `test_trap` - Signal handling and pseudo-signals (EXIT, DEBUG, ERR)
- `test_wait` - Process synchronization and job waiting

#### 2. Variable Expansions (Advanced parameter expansion)
- `test_parameter_expansion` - `${var:-default}`, `${var:=default}`, `${var:?error}`, `${var:+alt}`
- `test_string_operations` - `${#var}`, `${var#pattern}`, `${var##pattern}`, `${var%pattern}`, `${var%%pattern}`
- `test_pattern_substitution` - `${var/pattern/replacement}`, `${var//pattern/replacement}`, `${var/#pattern/replacement}`, `${var/%pattern/replacement}`
- `test_case_modification` - `${var^}`, `${var^^}`, `${var,}`, `${var,,}` with pattern support
- `test_substring_extraction` - `${var:offset}`, `${var:offset:length}` with negative indices
- `test_variable_indirection` - `${!prefix*}`, `${!prefix@}` for variable name matching

#### 3. Arithmetic Operations
- `test_arithmetic_expansion` - `$((expr))` with all operators (+, -, *, /, %, **, comparison, logical, bitwise)
- `test_arithmetic_commands` - `((expr))` as standalone commands with proper exit status
- `test_arithmetic_assignment` - Assignment operators (=, +=, -=, *=, /=, %=), increment/decrement (++, --)
- `test_arithmetic_variables` - Variable integration, command substitution in arithmetic
- `test_arithmetic_advanced` - Ternary operator (?:), comma operator, parentheses grouping

#### 4. I/O Redirection (Complete redirection system)
- `test_basic_redirections` - `>`, `>>`, `<`, `2>`, `2>>`, `&>`, `&>>`
- `test_fd_operations` - File descriptor duplication (`2>&1`), redirection (`3< file`)
- `test_heredocs` - `<<EOF`, `<<-EOF` with variable expansion and indentation stripping
- `test_here_strings` - `<<<string` with variable expansion and quoting
- `test_redirect_combinations` - Multiple redirections, order independence

### **Medium Priority - Advanced Features**

#### 5. Control Structures Enhancement
- `test_nested_control` - Deeply nested if/while/for combinations
- `test_break_continue` - Loop control statements with nesting levels
- `test_control_redirections` - Redirections on control structures (`while ... done > file`)
- `test_control_pipelines` - Control structures in pipelines (v0.37.0 feature)
- `test_arithmetic_control` - Arithmetic commands in control flow (`while ((i < 10))`)

#### 6. Functions and Scope
- `test_function_definition` - POSIX `name() {}` and bash `function name {}` syntax
- `test_local_variables` - Local variable scoping with `local` builtin
- `test_function_return` - Return values, status codes, and early return
- `test_function_recursion` - Recursive function calls and parameter handling
- `test_function_inheritance` - Function visibility in subshells and command substitution

#### 7. Job Control
- `test_background_jobs` - Background execution with `&`, job completion
- `test_job_control` - `jobs`, `fg`, `bg` commands with job specifications (%1, %+, %-)
- `test_signal_handling` - `trap` builtin with signal names and numbers
- `test_process_groups` - Terminal control and process group management
- `test_wait_builtin` - Waiting for specific processes and jobs

#### 8. Pattern Matching and Expansion
- `test_glob_patterns` - `*`, `?`, `[...]`, `[!...]` wildcards with character classes
- `test_brace_expansion` - List expansion `{a,b,c}`, sequence expansion `{1..10}`, nested braces
- `test_tilde_expansion` - `~`, `~user` expansion in various contexts
- `test_quote_handling` - Single quotes, double quotes, backslash escaping
- `test_word_splitting` - IFS-based splitting and quote protection

### **Medium-Low Priority - Shell Features**

#### 9. Interactive Features
- `test_history_expansion` - `!!`, `!n`, `!-n`, `!string`, `!?string?` patterns
- `test_line_editing` - Vi and emacs key bindings, command editing
- `test_completion` - Tab completion for files, directories, commands
- `test_prompts` - PS1, PS2 customization with escape sequences
- `test_multiline_input` - Multi-line command continuation and editing

#### 10. Advanced Syntax
- `test_case_statements` - Pattern matching with `case/esac`, multiple patterns, fallthrough
- `test_select_statements` - Interactive menus with PS3 prompt
- `test_enhanced_test` - `[[ ]]` operators (=~, <, >, &&, ||, !)
- `test_process_substitution` - `<(...)`, `>(...)` syntax with pipes and file descriptors
- `test_command_substitution` - `$(...)` and backtick syntax with nesting

#### 11. Loop Constructs
- `test_while_loops` - Condition evaluation, complex conditions, I/O redirection
- `test_for_loops` - Iteration over lists, variables, command substitution, glob patterns
- `test_c_style_loops` - `for ((init; condition; update))` with empty sections
- `test_select_loops` - Interactive selection with break/continue

### **Lower Priority - Specialized Features**

#### 12. Script Execution
- `test_shebang_handling` - Script execution with various interpreters
- `test_script_arguments` - Positional parameters ($0, $1, $2, etc.)
- `test_source_path` - PATH-based script sourcing and argument passing
- `test_script_modes` - Interactive vs non-interactive behavior

#### 13. Array Support (Modern bash features)
- `test_indexed_arrays` - `arr[0]=value`, `${arr[@]}`, `${arr[*]}`, sparse arrays
- `test_associative_arrays` - `declare -A`, string keys, complex key expressions
- `test_array_operations` - Slicing `${arr[@]:offset:length}`, pattern operations
- `test_array_assignment` - Array initialization, element assignment, append operations

#### 14. Advanced Variable Features
- `test_variable_attributes` - `declare` flags (-i, -l, -u, -r, -x, -a, -A)
- `test_readonly_vars` - Readonly enforcement and error handling
- `test_variable_scoping` - Global, local, and environment variable interaction
- `test_special_variables` - $?, $!, $$, $0, $#, $*, $@, OPTIND, OPTARG

#### 15. Line Continuation and Preprocessing
- `test_line_continuation` - Backslash-newline sequences in various contexts
- `test_comment_handling` - Comment processing and quote awareness
- `test_input_preprocessing` - Multi-line script processing and command buffering

## Test Implementation Strategy

### Phase 1: Core POSIX Features (Weeks 1-2)
**Goal**: Establish foundation with most critical POSIX features
- Built-in commands (14 test files)
- Basic expansions (6 test files) 
- I/O redirection (5 test files)
- **Total**: 25 test files

### Phase 2: Control & Functions (Week 3)
**Goal**: Validate programming constructs
- Enhanced control structures (5 test files)
- Function features (5 test files)
- Job control basics (5 test files)
- **Total**: 15 test files

### Phase 3: Advanced Features (Week 4)
**Goal**: Cover advanced shell programming
- Pattern matching (4 test files)
- Interactive features (5 test files)
- Advanced syntax (6 test files)
- **Total**: 15 test files

### Phase 4: Specialized Features (Week 5)
**Goal**: Complete coverage of specialized features
- Script execution (4 test files)
- Array support (4 test files)
- Advanced variables (4 test files)
- Line continuation (3 test files)
- **Total**: 15 test files

### Phase 5: Integration & Edge Cases (Week 6)
**Goal**: Comprehensive integration testing
- Feature combinations (5 test files)
- Edge cases and error conditions (5 test files)
- Performance and limits (3 test files)
- **Total**: 13 test files

## Test Organization Structure

```
conformance_tests/
├── posix/
│   ├── builtins/
│   │   ├── test_cd.input/golden
│   │   ├── test_set_options.input/golden
│   │   ├── test_export_unset.input/golden
│   │   ├── test_shift_getopts.input/golden
│   │   ├── test_read_advanced.input/golden
│   │   ├── test_eval.input/golden
│   │   ├── test_source.input/golden
│   │   ├── test_alias_unalias.input/golden
│   │   ├── test_help.input/golden
│   │   ├── test_declare_typeset.input/golden
│   │   ├── test_exec.input/golden
│   │   ├── test_kill.input/golden
│   │   ├── test_trap.input/golden
│   │   └── test_wait.input/golden
│   ├── expansions/
│   │   ├── test_parameter_expansion.input/golden
│   │   ├── test_string_operations.input/golden
│   │   ├── test_pattern_substitution.input/golden
│   │   ├── test_case_modification.input/golden
│   │   ├── test_substring_extraction.input/golden
│   │   └── test_variable_indirection.input/golden
│   ├── arithmetic/
│   │   ├── test_arithmetic_expansion.input/golden
│   │   ├── test_arithmetic_commands.input/golden
│   │   ├── test_arithmetic_assignment.input/golden
│   │   ├── test_arithmetic_variables.input/golden
│   │   └── test_arithmetic_advanced.input/golden
│   ├── io_redirection/
│   │   ├── test_basic_redirections.input/golden
│   │   ├── test_fd_operations.input/golden
│   │   ├── test_heredocs.input/golden
│   │   ├── test_here_strings.input/golden
│   │   └── test_redirect_combinations.input/golden
│   ├── control_structures/
│   │   ├── test_nested_control.input/golden
│   │   ├── test_break_continue.input/golden
│   │   ├── test_control_redirections.input/golden
│   │   ├── test_control_pipelines.input/golden
│   │   └── test_arithmetic_control.input/golden
│   ├── functions/
│   │   ├── test_function_definition.input/golden
│   │   ├── test_local_variables.input/golden
│   │   ├── test_function_return.input/golden
│   │   ├── test_function_recursion.input/golden
│   │   └── test_function_inheritance.input/golden
│   ├── job_control/
│   │   ├── test_background_jobs.input/golden
│   │   ├── test_job_control.input/golden
│   │   ├── test_signal_handling.input/golden
│   │   ├── test_process_groups.input/golden
│   │   └── test_wait_builtin.input/golden
│   ├── patterns/
│   │   ├── test_glob_patterns.input/golden
│   │   ├── test_brace_expansion.input/golden
│   │   ├── test_tilde_expansion.input/golden
│   │   └── test_quote_handling.input/golden
│   ├── interactive/
│   │   ├── test_history_expansion.input/golden
│   │   ├── test_line_editing.input/golden
│   │   ├── test_completion.input/golden
│   │   ├── test_prompts.input/golden
│   │   └── test_multiline_input.input/golden
│   ├── advanced_syntax/
│   │   ├── test_case_statements.input/golden
│   │   ├── test_select_statements.input/golden
│   │   ├── test_enhanced_test.input/golden
│   │   ├── test_process_substitution.input/golden
│   │   ├── test_command_substitution.input/golden
│   │   └── test_loop_constructs.input/golden
│   ├── scripts/
│   │   ├── test_shebang_handling.input/golden
│   │   ├── test_script_arguments.input/golden
│   │   ├── test_source_path.input/golden
│   │   └── test_script_modes.input/golden
│   ├── arrays/
│   │   ├── test_indexed_arrays.input/golden
│   │   ├── test_associative_arrays.input/golden
│   │   ├── test_array_operations.input/golden
│   │   └── test_array_assignment.input/golden
│   ├── variables/
│   │   ├── test_variable_attributes.input/golden
│   │   ├── test_readonly_vars.input/golden
│   │   ├── test_variable_scoping.input/golden
│   │   └── test_special_variables.input/golden
│   └── preprocessing/
│       ├── test_line_continuation.input/golden
│       ├── test_comment_handling.input/golden
│       └── test_input_preprocessing.input/golden
├── bash/
│   └── (Future bash-specific extensions)
└── integration/
    ├── test_feature_combinations.input/golden
    ├── test_edge_cases.input/golden
    └── test_performance_limits.input/golden
```

## Enhanced Test Runner Features

### 1. Test Categories
Add `--category` flag to run specific test groups:
```bash
python run_conformance_tests.py --category builtins
python run_conformance_tests.py --category expansions
python run_conformance_tests.py --category control_structures
```

### 2. Bash Comparison Mode
Add `--compare-bash` flag to validate PSH behavior against bash:
```bash
python run_conformance_tests.py --compare-bash --category arithmetic
```

### 3. Feature Detection
Automatically skip tests for unimplemented features by checking PSH capabilities:
```python
def feature_available(feature_name):
    """Check if a feature is available in current PSH version."""
    # Test for specific functionality
    return True/False
```

### 4. Progress Reporting
Track implementation coverage by feature area:
```bash
python run_conformance_tests.py --coverage-report
# Output:
# Built-ins: 14/14 tests (100%)
# Expansions: 6/6 tests (100%) 
# I/O Redirection: 5/5 tests (100%)
# Control Structures: 3/5 tests (60%)
# Overall: 75/83 tests (90%)
```

### 5. Parallel Execution
Run independent tests in parallel for faster execution:
```bash
python run_conformance_tests.py --parallel --jobs 4
```

## Test Quality Standards

### 1. Input File Standards
- Each `.input` file should be self-contained
- Include setup and cleanup commands where needed
- Use deterministic outputs (avoid timestamps, PIDs)
- Comment complex test scenarios

### 2. Golden File Standards  
- Normalize whitespace and line endings
- Remove environment-specific paths where possible
- Include both stdout and stderr when relevant
- Document expected behavior in comments

### 3. Test Naming Conventions
- Use descriptive names: `test_arithmetic_compound_assignment.input`
- Group related tests: `test_brace_expansion_sequences.input`
- Include feature version when relevant: `test_control_pipelines_v037.input`

### 4. Error Handling Tests
- Include both success and failure scenarios
- Test edge cases and boundary conditions
- Validate proper error messages and exit codes
- Test resource exhaustion scenarios

## Implementation Timeline

**Total Estimated Time**: 6 weeks
**Total Test Files**: ~85 comprehensive tests
**Coverage Goal**: 95% of PSH features

This plan provides comprehensive POSIX compliance validation while serving as a regression test suite for PSH development. The systematic approach ensures thorough coverage of PSH's extensive feature set while maintaining manageable implementation phases.

## Success Metrics

1. **Coverage**: 95% of documented PSH features tested
2. **Quality**: All tests pass consistently across environments  
3. **Maintainability**: Tests are easy to update and extend
4. **Documentation**: Clear test purpose and expected behavior
5. **Performance**: Test suite completes in reasonable time (<5 minutes)
6. **Integration**: Seamless CI/CD integration for regression testing

This comprehensive test plan will establish PSH as a thoroughly validated, POSIX-compliant shell implementation suitable for educational and production use.