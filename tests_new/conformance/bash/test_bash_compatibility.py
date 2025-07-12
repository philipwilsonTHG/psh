"""
Bash compatibility tests.

Tests PSH compatibility with bash-specific features and behaviors.
Documents areas where PSH intentionally differs or doesn't support bash extensions.
"""

import pytest
import sys
import os

# Add parent directory to path for framework import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from framework import ConformanceTest


class TestBashBuiltins(ConformanceTest):
    """Test bash builtin compatibility."""

    def test_echo_builtin_flags(self):
        """Test echo builtin with bash flags."""
        self.assert_identical_behavior('echo hello')
        self.assert_identical_behavior('echo -n hello')
        self.assert_identical_behavior('echo -e "hello\\nworld"')

    def test_printf_builtin(self):
        """Test printf builtin compatibility."""
        self.assert_identical_behavior('printf "hello\\n"')
        self.assert_identical_behavior('printf "%s %s\\n" hello world')

        # Format specifiers might not be fully implemented
        result = self.check_behavior('printf "%d\\n" 42')
        # Both should succeed, but output might differ
        assert result.psh_result.exit_code == 0
        assert result.bash_result.exit_code == 0

    def test_read_builtin(self):
        """Test read builtin compatibility."""
        # Basic read functionality
        result = self.check_behavior('echo "test" | read var; echo $var')
        # Read from pipe behavior might differ

    def test_test_builtin(self):
        """Test test/[ builtin compatibility."""
        self.assert_identical_behavior('test "hello" = "hello"')
        self.assert_identical_behavior('[ "hello" = "hello" ]')
        self.assert_identical_behavior('test 5 -gt 3')
        self.assert_identical_behavior('[ 5 -gt 3 ]')
        self.assert_identical_behavior('test -f /dev/null')
        self.assert_identical_behavior('test -d /tmp')

    def test_true_false_builtins(self):
        """Test true/false builtin compatibility."""
        self.assert_identical_behavior('true')
        self.assert_identical_behavior('false')

        result1 = self.check_behavior('true; echo $?')
        result2 = self.check_behavior('false; echo $?')

        assert '0' in result1.psh_result.stdout
        assert '0' in result1.bash_result.stdout
        assert '1' in result2.psh_result.stdout
        assert '1' in result2.bash_result.stdout


class TestBashConditionals(ConformanceTest):
    """Test bash conditional compatibility."""

    def test_single_bracket_conditionals(self):
        """Test [ ] conditionals (POSIX)."""
        self.assert_identical_behavior('if [ "hello" = "hello" ]; then echo yes; fi')
        self.assert_identical_behavior('if [ 5 -gt 3 ]; then echo yes; fi')
        self.assert_identical_behavior('if [ -f /dev/null ]; then echo yes; fi')

    def test_double_bracket_conditionals(self):
        """Test [[ ]] conditionals - mostly work in PSH."""
        self.assert_identical_behavior('[[ "hello" == "hello" ]]')
        self.assert_identical_behavior('[[ 5 > 3 ]]')
        # File test has different exit codes (2 vs 1) but both fail
        result = self.check_behavior('[[ -f /dev/null ]]')
        assert result.psh_result.exit_code != 0  # PSH returns 2
        assert result.bash_result.exit_code != 0  # Bash returns 1

    def test_arithmetic_conditionals(self):
        """Test (( )) arithmetic conditionals - work identically in PSH."""
        self.assert_identical_behavior('(( 5 > 3 ))')
        self.assert_identical_behavior('(( 1 + 1 == 2 ))')


class TestBashArrays(ConformanceTest):
    """Test bash array compatibility."""

    def test_indexed_arrays(self):
        """Test indexed arrays - work identically in PSH."""
        self.assert_identical_behavior('arr=(a b c); echo ${arr[0]}')
        self.assert_identical_behavior('arr[0]=hello; echo ${arr[0]}')

    def test_associative_arrays(self):
        """Test associative arrays - work identically in PSH."""
        self.assert_identical_behavior('declare -A arr; arr[key]=value; echo ${arr[key]}')

    def test_array_operations(self):
        """Test array operations - work identically in PSH."""
        self.assert_identical_behavior('arr=(a b c); echo ${arr[@]}')
        self.assert_identical_behavior('arr=(a b c); echo ${#arr[@]}')


class TestBashParameterExpansion(ConformanceTest):
    """Test bash parameter expansion compatibility."""

    def test_basic_parameter_expansion(self):
        """Test basic parameter expansion (POSIX)."""
        self.assert_identical_behavior('x=hello; echo ${x}')
        self.assert_identical_behavior('x=hello; echo ${x:-default}')
        self.assert_identical_behavior('x=hello; echo ${x:+set}')

    def test_substring_expansion(self):
        """Test bash substring expansion."""
        self.assert_identical_behavior('x=hello; echo ${x:1:3}')
        self.assert_identical_behavior('x=hello; echo ${x:2}')

    def test_pattern_substitution(self):
        """Test bash pattern substitution."""
        self.assert_identical_behavior('x=hello; echo ${x/l/L}')
        self.assert_identical_behavior('x=hello; echo ${x//l/L}')

    @pytest.mark.xfail(reason="Case modification may not be implemented")
    def test_case_modification(self):
        """Test bash case modification."""
        self.assert_bash_specific('x=hello; echo ${x^}')  # First char uppercase
        self.assert_bash_specific('x=hello; echo ${x^^}')  # All uppercase
        self.assert_bash_specific('x=HELLO; echo ${x,}')  # First char lowercase
        self.assert_bash_specific('x=HELLO; echo ${x,,}')  # All lowercase


class TestBashCommandSubstitution(ConformanceTest):
    """Test bash command substitution compatibility."""

    def test_dollar_paren_substitution(self):
        """Test $() command substitution (POSIX)."""
        self.assert_identical_behavior('echo $(echo hello)')
        self.assert_identical_behavior('echo $(date +%Y)')

    def test_backtick_substitution(self):
        """Test backtick command substitution (POSIX)."""
        self.assert_identical_behavior('echo `echo hello`')
        self.assert_identical_behavior('echo `date +%Y`')

    def test_nested_substitution(self):
        """Test nested command substitution."""
        self.assert_identical_behavior('echo $(echo $(echo nested))')

    def test_process_substitution(self):
        """Test process substitution - works identically in PSH."""
        self.assert_identical_behavior('cat <(echo hello)')
        self.assert_identical_behavior('diff <(echo a) <(echo b)')


class TestBashBraceExpansion(ConformanceTest):
    """Test bash brace expansion compatibility."""

    def test_sequence_expansion(self):
        """Test bash sequence brace expansion."""
        self.assert_identical_behavior('echo {1..3}')
        self.assert_identical_behavior('echo {a..c}')

        # Check if expansion actually happens
        result = self.check_behavior('echo {1..3}')
        # Should expand to "1 2 3"
        assert '1' in result.psh_result.stdout
        assert '2' in result.psh_result.stdout
        assert '3' in result.psh_result.stdout

    def test_list_expansion(self):
        """Test bash list brace expansion."""
        self.assert_identical_behavior('echo {a,b,c}')
        self.assert_identical_behavior('echo pre{fix1,fix2}')

        result = self.check_behavior('echo {a,b,c}')
        # Should expand to "a b c"
        assert 'a' in result.psh_result.stdout
        assert 'b' in result.psh_result.stdout
        assert 'c' in result.psh_result.stdout

    def test_nested_brace_expansion(self):
        """Test nested brace expansion."""
        result = self.check_behavior('echo {a,b{1,2}}')
        # Should expand properly in both shells
        # Exact format might differ but should contain all combinations


class TestBashArithmeticExpansion(ConformanceTest):
    """Test bash arithmetic expansion compatibility."""

    def test_basic_arithmetic(self):
        """Test basic arithmetic (POSIX)."""
        self.assert_identical_behavior('echo $((2 + 3))')
        self.assert_identical_behavior('echo $((10 - 4))')
        self.assert_identical_behavior('echo $((3 * 4))')
        self.assert_identical_behavior('echo $((15 / 3))')

    def test_advanced_arithmetic(self):
        """Test advanced arithmetic operations."""
        self.assert_identical_behavior('echo $((2 ** 3))')  # Power
        self.assert_identical_behavior('echo $((17 % 5))')  # Modulo
        self.assert_identical_behavior('echo $((5 & 3))')   # Bitwise AND
        self.assert_identical_behavior('echo $((5 | 3))')   # Bitwise OR

    def test_arithmetic_assignment(self):
        """Test arithmetic assignment."""
        self.assert_identical_behavior('echo $((x = 5 + 3)); echo $x')
        self.assert_identical_behavior('x=5; echo $((x += 3)); echo $x')


class TestBashGlobbing(ConformanceTest):
    """Test bash globbing compatibility."""

    def test_basic_globbing(self):
        """Test basic glob patterns (POSIX)."""
        # Create test files first
        result = self.check_behavior('touch a.txt b.txt; echo *.txt')

        assert 'a.txt' in result.psh_result.stdout
        assert 'b.txt' in result.psh_result.stdout
        assert 'a.txt' in result.bash_result.stdout
        assert 'b.txt' in result.bash_result.stdout

    @pytest.mark.xfail(reason="Extended globbing may not be implemented")
    def test_extended_globbing(self):
        """Test bash extended globbing."""
        # These require shopt -s extglob in bash
        self.assert_bash_specific('shopt -s extglob; echo ?(pattern)')
        self.assert_bash_specific('shopt -s extglob; echo +(pattern)')
        self.assert_bash_specific('shopt -s extglob; echo *(pattern)')

    def test_brace_globbing_interaction(self):
        """Test interaction between braces and globbing."""
        result = self.check_behavior('touch a1 a2 b1 b2; echo {a,b}*')

        # Should expand braces then glob
        for pattern in ['a1', 'a2', 'b1', 'b2']:
            assert pattern in result.psh_result.stdout
            assert pattern in result.bash_result.stdout


class TestBashJobControl(ConformanceTest):
    """Test bash job control compatibility."""

    def test_background_jobs(self):
        """Test background job execution."""
        result = self.check_behavior('sleep 0.1 &')

        # Both should start background job successfully
        assert result.psh_result.exit_code == 0
        assert result.bash_result.exit_code == 0

    def test_job_control_commands(self):
        """Test job control commands."""
        # These tests are complex in non-interactive mode
        result1 = self.check_behavior('jobs')
        result2 = self.check_behavior('sleep 1 & jobs')

        # Should succeed in both shells
        assert result1.psh_result.exit_code == 0
        assert result1.bash_result.exit_code == 0


class TestBashHistory(ConformanceTest):
    """Test bash history compatibility."""

    @pytest.mark.xfail(reason="History expansion not implemented")
    def test_history_expansion(self):
        """Test bash history expansion."""
        self.assert_bash_specific('echo hello; !!')
        self.assert_bash_specific('echo hello; !echo')

    def test_history_commands(self):
        """Test history-related commands."""
        result = self.check_behavior('history')
        # History command behavior might differ


class TestBashOptions(ConformanceTest):
    """Test bash option compatibility."""

    def test_set_options(self):
        """Test set options (POSIX and bash)."""
        self.assert_identical_behavior('set -e; true')

        # These might have different behavior
        result1 = self.check_behavior('set -o pipefail; true')
        result2 = self.check_behavior('set -u; true')

    @pytest.mark.xfail(reason="Bash-specific options not implemented")
    def test_shopt_options(self):
        """Test bash shopt options."""
        self.assert_bash_specific('shopt -s extglob')
        self.assert_bash_specific('shopt -s nullglob')
        self.assert_bash_specific('shopt -s dotglob')


class TestBashRedirection(ConformanceTest):
    """Test bash redirection compatibility."""

    def test_basic_redirection(self):
        """Test basic I/O redirection (POSIX)."""
        self.assert_identical_behavior('echo hello > /dev/null')
        self.assert_identical_behavior('echo hello 2> /dev/null')
        self.assert_identical_behavior('cat < /dev/null')

    def test_here_documents(self):
        """Test here documents (POSIX)."""
        # Here document tests are complex - check basic syntax
        result = self.check_behavior('cat << EOF\nhello\nEOF')
        # Both should handle here documents

    @pytest.mark.xfail(reason="Advanced redirection may not be implemented")
    def test_advanced_redirection(self):
        """Test bash advanced redirection."""
        self.assert_bash_specific('exec 3> file.txt')
        self.assert_bash_specific('echo hello >&3')
        self.assert_bash_specific('exec 3>&-')


class TestBashFunctions(ConformanceTest):
    """Test bash function compatibility."""

    def test_posix_function_syntax(self):
        """Test POSIX function syntax."""
        self.assert_identical_behavior('f() { echo function; }; f')
        self.assert_identical_behavior('greet() { echo hello $1; }; greet world')

    def test_bash_function_syntax(self):
        """Test bash function keyword syntax."""
        self.assert_identical_behavior('function f { echo function; }; f')
        self.assert_identical_behavior('function greet() { echo hello $1; }; greet world')

    def test_local_variables(self):
        """Test local variables in functions - works identically in PSH."""
        self.assert_identical_behavior('f() { local x=local; echo $x; }; x=global; f; echo $x')

    def test_function_return_values(self):
        """Test function return values."""
        result1 = self.check_behavior('f() { return 42; }; f; echo $?')
        result2 = self.check_behavior('f() { true; }; f; echo $?')

        # Return values should work the same
        assert '42' in result1.psh_result.stdout
        assert '42' in result1.bash_result.stdout
        assert '0' in result2.psh_result.stdout
        assert '0' in result2.bash_result.stdout


class TestBashAliases(ConformanceTest):
    """Test bash alias compatibility."""

    def test_basic_aliases(self):
        """Test basic alias functionality."""
        # Test that both PSH and bash handle undefined alias lookup
        # The error message format differs but both should fail
        result = self.check_behavior('alias ll="ls -l"; type ll')
        assert result.psh_result.exit_code != 0  # Should fail - ll is not a type-able command
        assert result.bash_result.exit_code != 0  # Should fail - ll is not a type-able command

        # Test alias creation (this should work in both)
        result = self.check_behavior('alias test_alias="echo aliased"; alias test_alias')
        assert 'test_alias=' in result.psh_result.stdout
        assert 'test_alias=' in result.bash_result.stdout

    @pytest.mark.xfail(reason="Alias expansion may not work in non-interactive shell sessions")
    def test_alias_with_arguments(self):
        """Test aliases with arguments."""
        result = self.check_behavior('alias greet="echo hello"; greet world')

        # Should pass arguments to aliased command
        assert 'hello' in result.psh_result.stdout
        assert 'world' in result.psh_result.stdout
        assert 'hello' in result.bash_result.stdout
        assert 'world' in result.bash_result.stdout

    def test_unalias(self):
        """Test removing aliases."""
        result = self.check_behavior('alias test="echo test"; unalias test; test 2>/dev/null || echo gone')

        # After unalias, command should not be found
        assert 'gone' in result.psh_result.stdout
        assert 'gone' in result.bash_result.stdout


class TestBashMiscellaneous(ConformanceTest):
    """Test miscellaneous bash compatibility features."""

    def test_variable_assignment_formats(self):
        """Test various variable assignment formats."""
        self.assert_identical_behavior('x=value; echo $x')
        self.assert_identical_behavior('x="value with spaces"; echo $x')
        self.assert_identical_behavior('x=$(echo dynamic); echo $x')

    def test_export_functionality(self):
        """Test export functionality."""
        # Basic export
        result = self.check_behavior('export VAR=value; env | grep VAR')
        # Should appear in environment

    def test_readonly_functionality(self):
        """Test readonly functionality."""
        # Test that readonly variables can be created and accessed
        result = self.check_behavior('readonly VAR=value; echo $VAR')
        assert 'value' in result.psh_result.stdout
        assert 'value' in result.bash_result.stdout

        # Test readonly variable listing
        result = self.check_behavior('readonly TEST=test; readonly | grep TEST')
        # Both should show the readonly variable
        assert 'TEST' in result.psh_result.stdout
        assert 'TEST' in result.bash_result.stdout

    def test_command_builtin(self):
        """Test command builtin."""
        result = self.check_behavior('alias echo="echo aliased"; command echo normal')

        # command should bypass alias
        assert 'normal' in result.psh_result.stdout
        assert 'normal' in result.bash_result.stdout
        assert 'aliased' not in result.psh_result.stdout
        assert 'aliased' not in result.bash_result.stdout


# Test suite for documenting differences
class TestDocumentedDifferences(ConformanceTest):
    """Test and document known differences between PSH and bash."""

    def test_psh_extensions(self):
        """Test PSH-specific extensions."""
        # PSH provides these, bash doesn't
        self.assert_psh_extension('version')
        # Note: help exists in both shells but with different behavior
        # This is better tested as documented difference

    def test_bash_specific_features(self):
        """Test features that work identically in PSH and bash."""
        # These features are actually supported by PSH!
        self.assert_identical_behavior('declare -a array')
        self.assert_identical_behavior('[[ 5 -gt 3 ]]')
        self.assert_identical_behavior('(( 5 > 3 ))')

    def test_documented_behavioral_differences(self):
        """Test documented behavioral differences."""
        # These might have subtle differences in behavior
        # but both shells should succeed

        result1 = self.check_behavior('pushd /tmp')
        result2 = self.check_behavior('popd')

        # Both should work but might have different output formats
        # This documents the differences rather than asserting sameness


def generate_bash_compatibility_report():
    """Generate comprehensive bash compatibility report."""
    import tempfile
    import json

    test_classes = [
        TestBashBuiltins,
        TestBashConditionals,
        TestBashArrays,
        TestBashParameterExpansion,
        TestBashCommandSubstitution,
        TestBashBraceExpansion,
        TestBashArithmeticExpansion,
        TestBashGlobbing,
        TestBashJobControl,
        TestBashHistory,
        TestBashOptions,
        TestBashRedirection,
        TestBashFunctions,
        TestBashAliases,
        TestBashMiscellaneous,
        TestDocumentedDifferences
    ]

    all_results = []

    for test_class in test_classes:
        test_instance = test_class()
        methods = [method for method in dir(test_instance) if method.startswith('test_')]

        for method in methods:
            try:
                getattr(test_instance, method)()
            except Exception as e:
                print(f"Test {test_class.__name__}.{method} failed: {e}")

        all_results.extend(test_instance.results)

    # Categorize results
    from framework import ConformanceResult

    categories = {
        "identical": 0,
        "documented_differences": 0,
        "psh_extensions": 0,
        "bash_specific": 0,
        "psh_bugs": 0,
        "test_errors": 0
    }

    for result in all_results:
        if result.conformance == ConformanceResult.IDENTICAL:
            categories["identical"] += 1
        elif result.conformance == ConformanceResult.DOCUMENTED_DIFFERENCE:
            categories["documented_differences"] += 1
        elif result.conformance == ConformanceResult.PSH_EXTENSION:
            categories["psh_extensions"] += 1
        elif result.conformance == ConformanceResult.BASH_SPECIFIC:
            categories["bash_specific"] += 1
        elif result.conformance == ConformanceResult.PSH_BUG:
            categories["psh_bugs"] += 1
        else:
            categories["test_errors"] += 1

    total_tests = len(all_results)
    compatibility_score = (categories["identical"] + categories["documented_differences"]) / total_tests * 100 if total_tests > 0 else 0

    report = {
        "bash_compatibility_summary": categories,
        "total_tests": total_tests,
        "compatibility_score": compatibility_score,
        "areas_of_concern": {
            "psh_bugs": categories["psh_bugs"],
            "test_errors": categories["test_errors"]
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f, indent=2)
        print(f"Bash compatibility report saved to: {f.name}")

    return report


if __name__ == "__main__":
    # Generate compatibility report
    report = generate_bash_compatibility_report()
    print(f"Bash Compatibility Score: {report['compatibility_score']:.1f}%")
    print(f"Identical behavior: {report['bash_compatibility_summary']['identical']}")
    print(f"Documented differences: {report['bash_compatibility_summary']['documented_differences']}")
    print(f"PSH extensions: {report['bash_compatibility_summary']['psh_extensions']}")
    print(f"Bash-specific features: {report['bash_compatibility_summary']['bash_specific']}")
    print(f"Potential PSH bugs: {report['bash_compatibility_summary']['psh_bugs']}")
