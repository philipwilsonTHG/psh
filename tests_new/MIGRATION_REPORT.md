# Test Migration Report

## Summary

Total test files needing attention: 76


## Recommendations by Fixture


### fully_isolated_shell (30 files)


**/Users/pwilson/src/psh/tests_new/conformance/bash/test_bash_compatibility.py**

- Issues found: {'state': 4, 'subprocess': 1, 'filesystem': 1}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/system/interactive/test_basic_spawn.py**

- Issues found: {'subprocess': 1, 'filesystem': 1}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/system/interactive/test_line_editing.py**

- Issues found: {'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/system/interactive/test_working_interactive.py**

- Issues found: {'subprocess': 1, 'filesystem': 1}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/system/interactive/test_simple_commands.py**

- Issues found: {'subprocess': 1, 'filesystem': 1}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/system/interactive/test_subprocess_commands.py**

- Issues found: {'subprocess': 3, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/system/interactive/test_basic_interactive.py**

- Issues found: {'subprocess': 1, 'filesystem': 1}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/subshells/test_subshell_basics.py**

- Issues found: {'state': 4, 'subprocess': 1, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/job_control/test_signal_handling.py**

- Issues found: {'state': 3, 'subprocess': 1, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/job_control/test_background_jobs.py**

- Issues found: {'state': 1, 'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/redirection/test_simple_redirection.py**

- Issues found: {'state': 1, 'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/redirection/test_advanced_redirection.py**

- Issues found: {'state': 3, 'subprocess': 1, 'filesystem': 4}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/command_resolution/test_command_resolution.py**

- Issues found: {'state': 5, 'subprocess': 2, 'filesystem': 5}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/interactive/test_history.py**

- Issues found: {'subprocess': 2, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/interactive/test_completion.py**

- Issues found: {'state': 2, 'subprocess': 2, 'filesystem': 4}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/functions/test_functions_comprehensive.py**

- Issues found: {'state': 3, 'subprocess': 2, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/functions/test_function_advanced.py**

- Issues found: {'state': 4, 'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/control_flow/test_nested_structures_io_conservative.py**

- Issues found: {'state': 1, 'subprocess': 2, 'filesystem': 4}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/parsing/test_quoting_escaping.py**

- Issues found: {'state': 1, 'subprocess': 2, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/parsing/test_error_recovery.py**

- Issues found: {'state': 2, 'subprocess': 2, 'filesystem': 4}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/parsing/test_word_splitting.py**

- Issues found: {'state': 1, 'subprocess': 2, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/aliases/test_alias_expansion.py**

- Issues found: {'state': 2, 'subprocess': 3, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/lexer/test_basic_tokenization.py**

- Issues found: {'subprocess': 1, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/lexer/test_modular_lexer_integration.py**

- Issues found: {'state': 1, 'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/lexer/test_token_recognizers_comprehensive.py**

- Issues found: {'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/lexer/test_lexer_package_api.py**

- Issues found: {'state': 1, 'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/lexer/test_tokenizer_migration.py**

- Issues found: {'subprocess': 1, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/parser/test_parser_basic.py**

- Issues found: {'subprocess': 1, 'filesystem': 3}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/parser/test_parser_migration.py**

- Issues found: {'state': 1, 'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_arithmetic_comprehensive.py**

- Issues found: {'state': 2, 'subprocess': 1, 'filesystem': 2}
- Recommended change: Use `fully_isolated_shell` fixture


### isolated_shell (20 files)


**/Users/pwilson/src/psh/tests_new/conformance/bash/test_basic_commands.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/pipeline/test_pipeline_execution.py**

- Issues found: {'state': 2, 'subprocess': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/builtins/test_declare_comprehensive.py**

- Issues found: {'state': 4}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/control_flow/test_nested_control_structures.py**

- Issues found: {'state': 2}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/control_flow/test_for_loops.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/integration/control_flow/test_case_statements.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/lexer/test_pure_helpers.py**

- Issues found: {'subprocess': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_alias_builtins.py**

- Issues found: {'state': 2}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_command_builtin.py**

- Issues found: {'state': 2}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_job_control_builtins.py**

- Issues found: {'subprocess': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_misc_builtins.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_positional_builtins.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_glob_expansion.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_brace_expansion.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_command_substitution.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_parameter_expansion.py**

- Issues found: {'state': 2}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_variable_expansion_simple.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/executor/test_executor_visitor_functions.py**

- Issues found: {'state': 1}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/executor/test_executor_visitor_basic.py**

- Issues found: {'state': 3}
- Recommended change: Use `isolated_shell` fixture


**/Users/pwilson/src/psh/tests_new/unit/multiline/test_multiline_handler.py**

- Issues found: {'state': 2, 'subprocess': 1}
- Recommended change: Use `isolated_shell` fixture


### isolated_shell with isolated_temp_dir (21 files)


**/Users/pwilson/src/psh/tests_new/conformance/posix/test_posix_compliance.py**

- Issues found: {'state': 1, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/system/initialization/test_rc_file.py**

- Issues found: {'state': 4, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/subshells/test_subshell_implementation.py**

- Issues found: {'state': 2, 'filesystem': 4}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/shell_options/test_shell_options_comprehensive.py**

- Issues found: {'state': 5, 'filesystem': 2}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/redirection/test_heredoc.py**

- Issues found: {'state': 1, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/parameter_expansion/test_parameter_expansion_comprehensive.py**

- Issues found: {'state': 2, 'filesystem': 3}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/variables/test_variable_assignment.py**

- Issues found: {'state': 5, 'filesystem': 3}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/arrays/test_arrays_comprehensive.py**

- Issues found: {'state': 2, 'filesystem': 3}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/functions/test_function_definitions.py**

- Issues found: {'state': 3, 'filesystem': 2}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/control_flow/test_while_loops.py**

- Issues found: {'state': 1, 'filesystem': 2}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/control_flow/test_if_statements.py**

- Issues found: {'state': 1, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/control_flow/test_nested_structures_basic.py**

- Issues found: {'state': 1, 'filesystem': 2}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/multiline/test_multiline_execution.py**

- Issues found: {'state': 1, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/validation/test_enhanced_validator_comprehensive.py**

- Issues found: {'state': 2, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_function_builtins.py**

- Issues found: {'state': 3, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_test_builtin.py**

- Issues found: {'state': 1, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_exec_builtin.py**

- Issues found: {'state': 1, 'filesystem': 2}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_echo_comprehensive.py**

- Issues found: {'state': 1, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_io_builtins.py**

- Issues found: {'state': 1, 'filesystem': 4}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_tilde_expansion.py**

- Issues found: {'state': 1, 'filesystem': 1}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/expansion/test_arithmetic_expansion.py**

- Issues found: {'state': 1, 'filesystem': 2}
- Recommended change: Use `isolated_shell with isolated_temp_dir` fixture


### shell_with_temp_dir (5 files)


**/Users/pwilson/src/psh/tests_new/performance/benchmarks/test_parsing_performance.py**

- Issues found: {'filesystem': 2}
- Recommended change: Use `shell_with_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/integration/parser/test_composite_token_handling.py**

- Issues found: {'filesystem': 1}
- Recommended change: Use `shell_with_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/parser/test_line_continuation.py**

- Issues found: {'filesystem': 1}
- Recommended change: Use `shell_with_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/builtins/test_navigation.py**

- Issues found: {'filesystem': 3}
- Recommended change: Use `shell_with_temp_dir` fixture


**/Users/pwilson/src/psh/tests_new/unit/multiline/test_prompt_expander.py**

- Issues found: {'filesystem': 1}
- Recommended change: Use `shell_with_temp_dir` fixture
