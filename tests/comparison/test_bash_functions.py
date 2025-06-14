#!/usr/bin/env python3
"""
Test shell functions against bash for compatibility.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestShellFunctions:
    """Test shell function compatibility with bash."""
    
    def test_basic_function_definition(self):
        """Test basic function definition and calling."""
        bash_compare.assert_shells_match("greet() { echo Hello; }; greet")
        bash_compare.assert_shells_match("greet() { echo Hello $1; }; greet World")
    
    def test_function_with_parameters(self):
        """Test functions with positional parameters."""
        bash_compare.assert_shells_match("add() { echo $(($1 + $2)); }; add 5 3")
        bash_compare.assert_shells_match("show() { echo \"$1 and $2\"; }; show first second")
    
    def test_function_return_value(self):
        """Test function return values."""
        bash_compare.assert_shells_match("f() { return 0; }; f; echo $?")
        bash_compare.assert_shells_match("f() { return 42; }; f; echo $?")
        bash_compare.assert_shells_match("f() { return; }; f; echo $?")
    
    def test_function_local_variables(self):
        """Test local variables in functions."""
        bash_compare.assert_shells_match("x=global; f() { local x=local; echo $x; }; f; echo $x")
        bash_compare.assert_shells_match("f() { local x=5 y=10; echo $((x + y)); }; f")
    
    def test_function_variable_scope(self):
        """Test variable scoping in functions."""
        # Without local, variables are global
        bash_compare.assert_shells_match("x=1; f() { x=2; }; f; echo $x")
        # With local, parent scope is preserved
        bash_compare.assert_shells_match("x=1; f() { local x=2; echo $x; }; f; echo $x")
    
    def test_function_command_substitution(self):
        """Test command substitution with functions."""
        bash_compare.assert_shells_match("double() { echo $((2 * $1)); }; echo $(double 5)")
        bash_compare.assert_shells_match("upper() { echo $1 | tr a-z A-Z; }; result=$(upper hello); echo $result")
    
    def test_function_in_pipeline(self):
        """Test functions used in pipelines."""
        bash_compare.assert_shells_match("filter() { grep $1; }; echo -e 'apple\\nbanana' | filter a")
        bash_compare.assert_shells_match("process() { while read x; do echo \"Got: $x\"; done; }; echo test | process")
    
    def test_recursive_function(self):
        """Test recursive function calls."""
        # Simple countdown
        cmd = """
countdown() {
    if [ $1 -eq 0 ]; then
        echo "Done!"
    else
        echo $1
        countdown $(($1 - 1))
    fi
}
countdown 3
"""
        bash_compare.assert_shells_match(cmd)
    
    def test_function_with_redirections(self):
        """Test functions with I/O redirections."""
        bash_compare.assert_shells_match("loud() { echo 'Error!' >&2; }; loud 2>&1")
        bash_compare.assert_shells_match("quiet() { echo 'Hidden' > /dev/null; echo 'Shown'; }; quiet")
    
    def test_function_special_variables(self):
        """Test special variables in functions."""
        bash_compare.assert_shells_match("f() { echo \"Args: $#\"; }; f a b c")
        bash_compare.assert_shells_match("f() { echo \"All: $@\"; }; f one two three")
        bash_compare.assert_shells_match("f() { echo \"Star: $*\"; }; f x y z")
    
    def test_nested_functions(self):
        """Test nested function calls."""
        cmd = """
outer() {
    echo "Outer: $1"
    inner() {
        echo "Inner: $1"
    }
    inner "from outer"
}
outer "test"
"""
        bash_compare.assert_shells_match(cmd)
    
    def test_function_overriding(self):
        """Test function redefinition."""
        bash_compare.assert_shells_match("f() { echo 1; }; f; f() { echo 2; }; f")
    
    def test_function_with_control_structures(self):
        """Test functions containing control structures."""
        cmd = """
check() {
    if [ "$1" -gt 5 ]; then
        echo "Big"
    else
        echo "Small"
    fi
}
check 3
check 10
"""
        bash_compare.assert_shells_match(cmd)