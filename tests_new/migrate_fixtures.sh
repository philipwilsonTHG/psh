#!/bin/bash
# Auto-generated fixture migration script


# Files needing isolated_shell with isolated_temp_dir
# Manual update needed for /Users/pwilson/src/psh/tests_new/conformance/posix/test_posix_compliance.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/system/initialization/test_rc_file.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/subshells/test_subshell_implementation.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/shell_options/test_shell_options_comprehensive.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/redirection/test_heredoc.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/parameter_expansion/test_parameter_expansion_comprehensive.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/variables/test_variable_assignment.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/arrays/test_arrays_comprehensive.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/functions/test_function_definitions.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/control_flow/test_while_loops.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/control_flow/test_if_statements.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/control_flow/test_nested_structures_basic.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/multiline/test_multiline_execution.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/integration/validation/test_enhanced_validator_comprehensive.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/unit/builtins/test_function_builtins.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/unit/builtins/test_test_builtin.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/unit/builtins/test_exec_builtin.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/unit/builtins/test_echo_comprehensive.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/unit/builtins/test_io_builtins.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/unit/expansion/test_tilde_expansion.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)
# Manual update needed for /Users/pwilson/src/psh/tests_new/unit/expansion/test_arithmetic_expansion.py
# Change: def test_*(shell) -> def test_*(isolated_shell, isolated_temp_dir)

# Files needing isolated_shell
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/conformance/bash/test_basic_commands.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/pipeline/test_pipeline_execution.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/builtins/test_declare_comprehensive.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/control_flow/test_nested_control_structures.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/control_flow/test_for_loops.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/control_flow/test_case_statements.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/lexer/test_pure_helpers.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/builtins/test_alias_builtins.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/builtins/test_command_builtin.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/builtins/test_job_control_builtins.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/builtins/test_misc_builtins.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/builtins/test_positional_builtins.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/expansion/test_glob_expansion.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/expansion/test_brace_expansion.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/expansion/test_command_substitution.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/expansion/test_parameter_expansion.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/expansion/test_variable_expansion_simple.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/executor/test_executor_visitor_functions.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/executor/test_executor_visitor_basic.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/multiline/test_multiline_handler.py

# Files needing fully_isolated_shell
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/conformance/bash/test_bash_compatibility.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/system/interactive/test_basic_spawn.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/system/interactive/test_line_editing.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/system/interactive/test_working_interactive.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/system/interactive/test_simple_commands.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/system/interactive/test_subprocess_commands.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/system/interactive/test_basic_interactive.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/subshells/test_subshell_basics.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/job_control/test_signal_handling.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/job_control/test_background_jobs.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/redirection/test_simple_redirection.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/redirection/test_advanced_redirection.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/command_resolution/test_command_resolution.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/interactive/test_history.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/interactive/test_completion.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/functions/test_functions_comprehensive.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/functions/test_function_advanced.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/control_flow/test_nested_structures_io_conservative.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/parsing/test_quoting_escaping.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/parsing/test_error_recovery.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/parsing/test_word_splitting.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/integration/aliases/test_alias_expansion.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/lexer/test_basic_tokenization.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/lexer/test_modular_lexer_integration.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/lexer/test_token_recognizers_comprehensive.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/lexer/test_lexer_package_api.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/lexer/test_tokenizer_migration.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/parser/test_parser_basic.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/parser/test_parser_migration.py
sed -i '' 's/def test_\(.*\)(shell)/def test_\1(fully_isolated_shell)/g' /Users/pwilson/src/psh/tests_new/unit/expansion/test_arithmetic_comprehensive.py

# Files needing shell_with_temp_dir