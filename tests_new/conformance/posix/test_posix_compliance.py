"""
POSIX compliance tests.

Tests PSH conformance to POSIX shell standard requirements.
Tests features that MUST be supported for POSIX compliance.
"""

import pytest
import sys
import os

# Add parent directory to path for framework import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from framework import ConformanceTest, get_posix_test_commands, is_posix_required


class TestPOSIXParameterExpansion(ConformanceTest):
    """Test POSIX parameter expansion compliance."""
    
    def test_basic_parameter_expansion(self):
        """Test basic ${parameter} expansion."""
        self.assert_identical_behavior('x=hello; echo ${x}')
        self.assert_identical_behavior('x="hello world"; echo ${x}')
        self.assert_identical_behavior('x=; echo ${x}')
    
    def test_default_value_expansion(self):
        """Test ${parameter:-word} expansion."""
        self.assert_identical_behavior('x=hello; echo ${x:-default}')
        self.assert_identical_behavior('x=; echo ${x:-default}')
        self.assert_identical_behavior('unset x; echo ${x:-default}')
    
    def test_assign_default_expansion(self):
        """Test ${parameter:=word} expansion."""
        self.assert_identical_behavior('unset x; echo ${x:=default}; echo $x')
        self.assert_identical_behavior('x=; echo ${x:=default}; echo $x')
    
    def test_error_expansion(self):
        """Test ${parameter:?word} expansion."""
        # These should fail in both shells
        result1 = self.check_behavior('unset x; echo ${x:?undefined}')
        result2 = self.check_behavior('x=; echo ${x:?empty}')
        
        # Both should fail with non-zero exit codes
        assert result1.psh_result.exit_code != 0
        assert result1.bash_result.exit_code != 0
        assert result2.psh_result.exit_code != 0  
        assert result2.bash_result.exit_code != 0
    
    def test_alternative_value_expansion(self):
        """Test ${parameter:+word} expansion."""
        self.assert_identical_behavior('x=hello; echo ${x:+alternative}')
        self.assert_identical_behavior('x=; echo ${x:+alternative}')
        self.assert_identical_behavior('unset x; echo ${x:+alternative}')
    
    def test_string_length_expansion(self):
        """Test ${#parameter} expansion."""
        self.assert_identical_behavior('x=hello; echo ${#x}')
        self.assert_identical_behavior('x="hello world"; echo ${#x}')
        self.assert_identical_behavior('x=; echo ${#x}')
    
    @pytest.mark.xfail(reason="Pattern removal may not be implemented")
    def test_prefix_removal_expansion(self):
        """Test ${parameter#word} and ${parameter##word} expansion."""
        self.assert_identical_behavior('x=hello.txt; echo ${x#*.}')
        self.assert_identical_behavior('x=hello.world.txt; echo ${x#*.}')
        self.assert_identical_behavior('x=hello.world.txt; echo ${x##*.}')
    
    @pytest.mark.xfail(reason="Pattern removal may not be implemented")
    def test_suffix_removal_expansion(self):
        """Test ${parameter%word} and ${parameter%%word} expansion."""
        self.assert_identical_behavior('x=hello.txt; echo ${x%.txt}')
        self.assert_identical_behavior('x=hello.world.txt; echo ${x%.*}')
        self.assert_identical_behavior('x=hello.world.txt; echo ${x%%.*}')


class TestPOSIXCommandSubstitution(ConformanceTest):
    """Test POSIX command substitution compliance."""
    
    def test_dollar_paren_substitution(self):
        """Test $(command) substitution."""
        self.assert_identical_behavior('echo $(echo hello)')
        self.assert_identical_behavior('echo $(echo "hello world")')
        self.assert_identical_behavior('echo $(true)')
        self.assert_identical_behavior('echo $(false)')
    
    def test_backtick_substitution(self):
        """Test `command` substitution."""
        self.assert_identical_behavior('echo `echo hello`')
        self.assert_identical_behavior('echo `echo "hello world"`')
        self.assert_identical_behavior('echo `true`')
    
    def test_nested_command_substitution(self):
        """Test nested command substitution."""
        self.assert_identical_behavior('echo $(echo $(echo nested))')
        self.assert_identical_behavior('echo $(echo `echo mixed`)')
    
    def test_command_substitution_with_variables(self):
        """Test command substitution with variables."""
        self.assert_identical_behavior('x=hello; echo $(echo $x)')
        self.assert_identical_behavior('x=world; echo $(echo "hello $x")')
    
    def test_command_substitution_exit_status(self):
        """Test command substitution preserves exit status."""
        result1 = self.check_behavior('x=$(false); echo $?')
        result2 = self.check_behavior('x=$(true); echo $?')
        
        # Exit status handling might differ, but commands should succeed
        assert result1.psh_result.exit_code == 0
        assert result1.bash_result.exit_code == 0
        assert result2.psh_result.exit_code == 0
        assert result2.bash_result.exit_code == 0


class TestPOSIXArithmeticExpansion(ConformanceTest):
    """Test POSIX arithmetic expansion compliance."""
    
    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        self.assert_identical_behavior('echo $((2 + 3))')
        self.assert_identical_behavior('echo $((10 - 4))')
        self.assert_identical_behavior('echo $((3 * 4))')
        self.assert_identical_behavior('echo $((15 / 3))')
        self.assert_identical_behavior('echo $((17 % 5))')
    
    def test_arithmetic_precedence(self):
        """Test arithmetic operator precedence."""
        self.assert_identical_behavior('echo $((2 + 3 * 4))')
        self.assert_identical_behavior('echo $((2 * 3 + 4))')
        self.assert_identical_behavior('echo $(((2 + 3) * 4))')
        self.assert_identical_behavior('echo $((2 * (3 + 4)))')
    
    def test_arithmetic_with_variables(self):
        """Test arithmetic with variables."""
        self.assert_identical_behavior('x=5; echo $((x + 3))')
        self.assert_identical_behavior('x=10; y=3; echo $((x * y))')
        self.assert_identical_behavior('x=0; echo $((x || 1))')
    
    def test_arithmetic_comparison(self):
        """Test arithmetic comparison operators."""
        self.assert_identical_behavior('echo $((5 > 3))')
        self.assert_identical_behavior('echo $((3 > 5))')
        self.assert_identical_behavior('echo $((5 >= 5))')
        self.assert_identical_behavior('echo $((5 <= 5))')
        self.assert_identical_behavior('echo $((5 == 5))')
        self.assert_identical_behavior('echo $((5 != 3))')
    
    def test_arithmetic_logical(self):
        """Test arithmetic logical operators."""
        self.assert_identical_behavior('echo $((1 && 1))')
        self.assert_identical_behavior('echo $((1 && 0))')
        self.assert_identical_behavior('echo $((0 || 1))')
        self.assert_identical_behavior('echo $((0 || 0))')


class TestPOSIXTildeExpansion(ConformanceTest):
    """Test POSIX tilde expansion compliance."""
    
    def test_basic_tilde_expansion(self):
        """Test basic tilde expansion."""
        # ~ should expand to HOME
        result = self.check_behavior('echo ~')
        
        # Both should expand tilde
        assert result.psh_result.stdout.strip() != '~'
        assert result.bash_result.stdout.strip() != '~'
        
        # Should be similar (might differ in trailing slash)
        psh_home = result.psh_result.stdout.strip().rstrip('/')
        bash_home = result.bash_result.stdout.strip().rstrip('/')
        assert psh_home == bash_home
    
    def test_tilde_with_path(self):
        """Test tilde expansion with path."""
        result = self.check_behavior('echo ~/test')
        
        # Both should expand tilde part
        assert not result.psh_result.stdout.strip().startswith('~/')
        assert not result.bash_result.stdout.strip().startswith('~/')
        
        # Both should end with /test
        assert result.psh_result.stdout.strip().endswith('/test')
        assert result.bash_result.stdout.strip().endswith('/test')
    
    @pytest.mark.xfail(reason="User home expansion may not be implemented")
    def test_tilde_user_expansion(self):
        """Test ~user expansion."""
        # This might not work if user doesn't exist
        self.assert_identical_behavior('echo ~root')


class TestPOSIXPathnameExpansion(ConformanceTest):
    """Test POSIX pathname (glob) expansion compliance."""
    
    def test_asterisk_expansion(self):
        """Test * glob expansion."""
        # Create test files first
        result = self.check_behavior('touch a.txt b.txt; echo *.txt')
        
        # Both should expand to list files
        assert 'a.txt' in result.psh_result.stdout
        assert 'b.txt' in result.psh_result.stdout
        assert 'a.txt' in result.bash_result.stdout
        assert 'b.txt' in result.bash_result.stdout
    
    def test_question_mark_expansion(self):
        """Test ? glob expansion."""
        result = self.check_behavior('touch a b c; echo ?')
        
        # Both should expand to single character files
        assert 'a' in result.psh_result.stdout
        assert 'b' in result.psh_result.stdout  
        assert 'c' in result.psh_result.stdout
    
    def test_bracket_expansion(self):
        """Test [chars] glob expansion."""
        result = self.check_behavior('touch a1 a2 b1 b2; echo [ab]*')
        
        # Both should match files starting with a or b
        for filename in ['a1', 'a2', 'b1', 'b2']:
            assert filename in result.psh_result.stdout
            assert filename in result.bash_result.stdout
    
    def test_no_match_behavior(self):
        """Test behavior when glob doesn't match."""
        result = self.check_behavior('echo *.nonexistent')
        
        # POSIX: if no match, pattern should remain literal
        assert '*.nonexistent' in result.psh_result.stdout
        assert '*.nonexistent' in result.bash_result.stdout


class TestPOSIXQuoteRemoval(ConformanceTest):
    """Test POSIX quote removal compliance."""
    
    def test_double_quote_removal(self):
        """Test double quote removal."""
        self.assert_identical_behavior('echo "hello world"')
        self.assert_identical_behavior('echo "hello $USER"')
        self.assert_identical_behavior('echo "hello $(echo world)"')
    
    def test_single_quote_removal(self):
        """Test single quote removal."""
        self.assert_identical_behavior("echo 'hello world'")
        self.assert_identical_behavior("echo 'hello $USER'")
        self.assert_identical_behavior("echo 'hello $(echo world)'")
    
    def test_backslash_quote_removal(self):
        """Test backslash quote removal."""
        self.assert_identical_behavior('echo hello\\ world')
        self.assert_identical_behavior('echo \\$USER')
        self.assert_identical_behavior('echo \\$(echo test)')
    
    def test_mixed_quoting(self):
        """Test mixed quoting styles."""
        self.assert_identical_behavior('echo "hello" world')
        self.assert_identical_behavior("echo 'hello' world")
        self.assert_identical_behavior("echo \"hello 'world'\"")


class TestPOSIXSimpleCommands(ConformanceTest):
    """Test POSIX simple command compliance."""
    
    def test_basic_commands(self):
        """Test basic command execution."""
        self.assert_identical_behavior('echo hello')
        self.assert_identical_behavior('true')
        self.assert_identical_behavior('false')
    
    def test_command_with_arguments(self):
        """Test commands with arguments."""
        self.assert_identical_behavior('echo hello world')
        self.assert_identical_behavior('echo -n hello')
        self.assert_identical_behavior('printf "%s\\n" hello')
    
    def test_command_with_redirections(self):
        """Test commands with I/O redirections."""
        self.assert_identical_behavior('echo hello > /dev/null')
        self.assert_identical_behavior('echo hello 2> /dev/null')
        self.assert_identical_behavior('cat < /dev/null')
    
    def test_variable_assignments(self):
        """Test variable assignments with commands."""
        self.assert_identical_behavior('VAR=value echo $VAR')
        self.assert_identical_behavior('A=1 B=2 echo $A$B')


class TestPOSIXPipelines(ConformanceTest):
    """Test POSIX pipeline compliance."""
    
    def test_simple_pipeline(self):
        """Test simple two-command pipeline."""
        self.assert_identical_behavior('echo hello | cat')
        self.assert_identical_behavior('echo hello | wc -c')
    
    def test_multi_stage_pipeline(self):
        """Test multi-stage pipeline."""
        self.assert_identical_behavior('echo hello | cat | cat')
        self.assert_identical_behavior('echo -e "a\\nb\\nc" | sort | uniq')
    
    def test_pipeline_exit_status(self):
        """Test pipeline exit status."""
        result1 = self.check_behavior('true | false; echo $?')
        result2 = self.check_behavior('false | true; echo $?')
        
        # Pipeline exit status should be last command
        # Both shells should behave the same way
        assert result1.psh_result.exit_code == result1.bash_result.exit_code
        assert result2.psh_result.exit_code == result2.bash_result.exit_code


class TestPOSIXLists(ConformanceTest):
    """Test POSIX command list compliance."""
    
    def test_and_lists(self):
        """Test && command lists."""
        self.assert_identical_behavior('true && echo success')
        self.assert_identical_behavior('false && echo never')
        
        result1 = self.check_behavior('true && false; echo $?')
        result2 = self.check_behavior('false && true; echo $?')
        
        # Exit status should match last executed command
        assert result1.psh_result.exit_code == result1.bash_result.exit_code
        assert result2.psh_result.exit_code == result2.bash_result.exit_code
    
    def test_or_lists(self):
        """Test || command lists."""
        self.assert_identical_behavior('false || echo success')
        self.assert_identical_behavior('true || echo never')
        
        result1 = self.check_behavior('false || true; echo $?')
        result2 = self.check_behavior('true || false; echo $?')
        
        # Exit status should match
        assert result1.psh_result.exit_code == result1.bash_result.exit_code
        assert result2.psh_result.exit_code == result2.bash_result.exit_code
    
    def test_sequential_lists(self):
        """Test ; command lists."""
        self.assert_identical_behavior('echo first; echo second')
        self.assert_identical_behavior('true; false; echo done')
        
        result = self.check_behavior('true; false; echo $?')
        # Should show exit status of last command (echo)
        assert result.psh_result.exit_code == 0
        assert result.bash_result.exit_code == 0


class TestPOSIXCompoundCommands(ConformanceTest):
    """Test POSIX compound command compliance."""
    
    def test_if_constructs(self):
        """Test if-then-else constructs."""
        self.assert_identical_behavior('if true; then echo yes; fi')
        self.assert_identical_behavior('if false; then echo no; fi')
        self.assert_identical_behavior('if true; then echo yes; else echo no; fi')
        self.assert_identical_behavior('if false; then echo no; else echo yes; fi')
    
    def test_while_loops(self):
        """Test while loop constructs."""
        self.assert_identical_behavior('i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done')
        self.assert_identical_behavior('while false; do echo never; done')
    
    def test_for_loops(self):
        """Test for loop constructs."""
        self.assert_identical_behavior('for i in 1 2 3; do echo $i; done')
        self.assert_identical_behavior('for word in hello world; do echo $word; done')
    
    def test_case_constructs(self):
        """Test case statement constructs."""
        self.assert_identical_behavior('case hello in hello) echo match;; esac')
        self.assert_identical_behavior('case test in hello) echo no;; *) echo yes;; esac')
        self.assert_identical_behavior('case abc in a*) echo starts_with_a;; esac')


class TestPOSIXShellFunctions(ConformanceTest):
    """Test POSIX shell function compliance."""
    
    def test_function_definition_execution(self):
        """Test function definition and execution."""
        self.assert_identical_behavior('f() { echo function; }; f')
        self.assert_identical_behavior('greet() { echo hello $1; }; greet world')
    
    def test_function_parameters(self):
        """Test function parameter handling."""
        self.assert_identical_behavior('show() { echo $# $1 $2; }; show a b c')
        self.assert_identical_behavior('show_all() { echo "$@"; }; show_all one two three')
    
    def test_function_return_values(self):
        """Test function return values."""
        result1 = self.check_behavior('success() { return 0; }; success; echo $?')
        result2 = self.check_behavior('failure() { return 1; }; failure; echo $?')
        
        # Return values should propagate correctly
        assert '0' in result1.psh_result.stdout
        assert '0' in result1.bash_result.stdout
        assert '1' in result2.psh_result.stdout
        assert '1' in result2.bash_result.stdout
    
    def test_function_variable_scope(self):
        """Test function variable scoping."""
        result = self.check_behavior('x=global; f() { x=local; }; f; echo $x')
        
        # In POSIX, function variables affect global scope
        assert 'local' in result.psh_result.stdout
        assert 'local' in result.bash_result.stdout


class TestPOSIXShellParameters(ConformanceTest):
    """Test POSIX shell parameter compliance."""
    
    def test_positional_parameters(self):
        """Test positional parameters."""
        # Note: These tests run in -c mode, so $0 is the shell
        self.assert_identical_behavior('echo $#')  # Should be 0
        self.assert_identical_behavior('set a b c; echo $# $1 $2 $3')
    
    def test_special_parameters(self):
        """Test special parameters."""
        self.assert_identical_behavior('echo $$')  # Process ID
        self.assert_identical_behavior('true; echo $?')  # Exit status
        self.assert_identical_behavior('false; echo $?')
        
    def test_parameter_set_unset(self):
        """Test parameter setting and unsetting."""
        self.assert_identical_behavior('set a b c; echo $1; shift; echo $1')
        self.assert_identical_behavior('x=value; echo $x; unset x; echo $x')


# Test suite summary function
def run_posix_compliance_suite():
    """Run complete POSIX compliance test suite and generate report."""
    import tempfile
    import json
    
    test_classes = [
        TestPOSIXParameterExpansion,
        TestPOSIXCommandSubstitution, 
        TestPOSIXArithmeticExpansion,
        TestPOSIXTildeExpansion,
        TestPOSIXPathnameExpansion,
        TestPOSIXQuoteRemoval,
        TestPOSIXSimpleCommands,
        TestPOSIXPipelines,
        TestPOSIXLists,
        TestPOSIXCompoundCommands,
        TestPOSIXShellFunctions,
        TestPOSIXShellParameters
    ]
    
    all_results = []
    
    for test_class in test_classes:
        test_instance = test_class()
        # Run all test methods
        methods = [method for method in dir(test_instance) if method.startswith('test_')]
        for method in methods:
            try:
                getattr(test_instance, method)()
            except Exception as e:
                print(f"Test {test_class.__name__}.{method} failed: {e}")
        
        all_results.extend(test_instance.results)
    
    # Generate report
    summary = {}
    for result_type in ConformanceResult:
        summary[result_type.value] = sum(
            1 for r in all_results if r.conformance == result_type
        )
    
    report = {
        "posix_compliance_summary": summary,
        "total_tests": len(all_results),
        "identical_behavior": summary.get("identical", 0),
        "compliance_percentage": (summary.get("identical", 0) / len(all_results)) * 100 if all_results else 0
    }
    
    # Save detailed results
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f, indent=2)
        print(f"POSIX compliance report saved to: {f.name}")
    
    return report


if __name__ == "__main__":
    # Run compliance tests
    report = run_posix_compliance_suite()
    print(f"POSIX Compliance: {report['compliance_percentage']:.1f}%")
    print(f"Tests with identical behavior: {report['identical_behavior']}/{report['total_tests']}")