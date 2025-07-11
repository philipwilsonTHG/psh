"""
Test parameter expansion operators (:=, :?, :-, :+).

Tests the POSIX parameter expansion operators for:
- Default value assignment (:=)
- Error on unset (:?)
- Default value without assignment (:-)
- Alternative value when set (:+)
"""

import pytest
import sys
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
PSH_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(PSH_ROOT))


def test_default_value_operator(shell, capsys):
    """Test :- operator (use default if unset)."""
    # Unset variable
    shell.run_command('unset testvar')
    shell.run_command('echo ${testvar:-default}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "default"
    
    # Variable should remain unset
    shell.run_command('echo "var=${testvar:-still_unset}"')
    captured = capsys.readouterr()
    assert captured.out.strip() == "var=still_unset"
    
    # Set variable
    shell.run_command('testvar="value"')
    shell.run_command('echo ${testvar:-default}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "value"
    
    # Empty variable - treated as unset for :-
    shell.run_command('testvar=""')
    shell.run_command('echo ${testvar:-empty_default}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "empty_default"


def test_alternative_value_operator(shell, capsys):
    """Test :+ operator (use alternative if set)."""
    # Unset variable
    shell.run_command('unset testvar')
    shell.run_command('echo "${testvar:+alternative}"')
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    
    # Set variable
    shell.run_command('testvar="value"')
    shell.run_command('echo ${testvar:+alternative}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "alternative"
    
    # Empty variable - treated as unset for :+
    shell.run_command('testvar=""')
    shell.run_command('echo "${testvar:+should_not_appear}"')
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_assign_default_operator(shell, capsys):
    """Test := operator (assign default if unset)."""
    # Unset variable
    shell.run_command('unset testvar')
    shell.run_command('echo ${testvar:=assigned}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "assigned"
    
    # Variable should now be set
    shell.run_command('echo $testvar')
    captured = capsys.readouterr()
    assert captured.out.strip() == "assigned"
    
    # Already set variable - no assignment
    shell.run_command('testvar="existing"')
    shell.run_command('echo ${testvar:=new_value}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "existing"
    
    # Variable should retain original value
    shell.run_command('echo $testvar')
    captured = capsys.readouterr()
    assert captured.out.strip() == "existing"


def test_error_if_unset_operator(shell, capsys):
    """Test :? operator (error if unset)."""
    # Unset variable with custom message
    shell.run_command('unset testvar')
    result = shell.run_command('echo ${testvar:?variable is not set}')
    assert result == 1
    captured = capsys.readouterr()
    assert "testvar: variable is not set" in captured.err
    
    # Unset variable with no message
    result = shell.run_command('echo ${testvar:?}')
    assert result == 1
    captured = capsys.readouterr()
    assert "testvar: parameter null or not set" in captured.err
    
    # Set variable - no error
    shell.run_command('testvar="value"')
    shell.run_command('echo ${testvar:?should not error}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "value"
    
    # Empty variable - treated as unset for :?
    shell.run_command('testvar=""')
    result = shell.run_command('echo ${testvar:?empty variable error}')
    assert result == 1
    captured = capsys.readouterr()
    assert "testvar: empty variable error" in captured.err


def test_expansion_in_default_values(shell, capsys):
    """Test variable expansion within default values."""
    shell.run_command('prefix="DEFAULT"')
    
    # Expansion in := operator
    shell.run_command('unset testvar')
    shell.run_command('echo ${testvar:=${prefix}_VALUE}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "DEFAULT_VALUE"
    
    shell.run_command('echo $testvar')
    captured = capsys.readouterr()
    assert captured.out.strip() == "DEFAULT_VALUE"
    
    # Expansion in :- operator
    shell.run_command('unset testvar2')
    shell.run_command('echo ${testvar2:-${prefix}_TEMP}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "DEFAULT_TEMP"
    
    # Expansion in :? error message
    shell.run_command('error_prefix="ERROR"')
    shell.run_command('unset testvar3')
    result = shell.run_command('echo ${testvar3:?${error_prefix}: variable not set}')
    assert result == 1
    captured = capsys.readouterr()
    assert "testvar3: ERROR: variable not set" in captured.err


def test_operators_with_special_variables(shell, capsys):
    """Test operators with special variables like positional parameters."""
    # Test with $1 when not set
    shell.run_command('set --')  # Clear positional parameters
    shell.run_command('echo ${1:-no_args}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "no_args"
    
    # Test with $1 when set
    shell.run_command('set -- "first" "second"')
    shell.run_command('echo ${1:-no_args}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "first"
    
    shell.run_command('echo ${3:-third_missing}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "third_missing"


def test_nested_expansions(shell, capsys):
    """Test nested parameter expansions."""
    shell.run_command('outer="OUTER"')
    shell.run_command('unset inner')
    
    # Nested expansion in default value
    shell.run_command('echo ${inner:-${outer}_INNER}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "OUTER_INNER"
    
    # More complex nesting
    shell.run_command('unset var1 var2 var3')
    shell.run_command('var3="FOUND"')
    shell.run_command('echo ${var1:-${var2:-${var3:-NOT_FOUND}}}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "FOUND"


@pytest.mark.xfail(reason="Array element parameter expansion operators not yet implemented")
def test_operators_with_arrays(shell, capsys):
    """Test parameter expansion operators with array elements."""
    # Test with array elements
    shell.run_command('arr=(one two three)')
    
    # Existing element
    shell.run_command('echo ${arr[1]:-default}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "two"
    
    # Non-existent element
    shell.run_command('echo ${arr[5]:-missing}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "missing"
    
    # Assignment to array element
    shell.run_command('echo ${arr[5]:=five}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "five"
    
    # Verify assignment
    shell.run_command('echo ${arr[5]}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "five"


def test_positional_parameter_operators(shell, capsys):
    """Test parameter expansion with positional parameters."""
    # Clear positional parameters
    shell.run_command('set --')
    
    # Test default value for unset positional parameter
    shell.run_command('echo ${1:-first_default}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "first_default"
    
    # Set positional parameters
    shell.run_command('set -- "arg1" "arg2"')
    
    # Test with set parameter
    shell.run_command('echo ${1:-not_used}')
    captured = capsys.readouterr()
    assert captured.out.strip() == "arg1"
    
    # Test assignment to positional parameter (should fail in bash)
    # PSH might allow this, but bash doesn't
    # shell.run_command('echo ${3:=third}')  # Would be an error in bash