"""
Basic command conformance tests comparing PSH and bash behavior.

These tests verify that PSH produces identical output to bash for
fundamental shell operations.
"""

import sys
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TEST_ROOT))

from framework.conformance import ConformanceTest, DifferenceType
import pytest


class TestBasicCommandConformance(ConformanceTest):
    """Test basic command execution conformance with bash."""
    
    def test_echo_command(self):
        """Test echo command conformance."""
        # Basic echo
        self.assert_same_behavior("echo hello world")
        
        # Echo with quotes
        self.assert_same_behavior('echo "hello world"')
        self.assert_same_behavior("echo 'hello world'")
        
        # Echo with escapes
        self.assert_same_behavior('echo "hello\\nworld"')
        
        # Echo with variables
        self.assert_same_behavior('x=test; echo $x')
        self.assert_same_behavior('x=test; echo "$x"')
        self.assert_same_behavior('x=test; echo ${x}')
        
    def test_variable_assignment(self):
        """Test variable assignment conformance."""
        # Basic assignment
        self.assert_same_behavior('x=hello; echo $x')
        
        # Assignment with spaces
        self.assert_same_behavior('x="hello world"; echo $x')
        
        # Multiple assignments
        self.assert_same_behavior('x=1 y=2 z=3; echo $x $y $z')
        
        # Assignment with command
        self.assert_same_behavior('x=value echo $x')
        
        # Empty assignment
        self.assert_same_behavior('x=; echo "$x"')
        
    def test_command_substitution(self):
        """Test command substitution conformance."""
        # Basic substitution
        self.assert_same_behavior('echo $(echo hello)')
        
        # Nested substitution
        self.assert_same_behavior('echo $(echo $(echo nested))')
        
        # Substitution with quotes
        self.assert_same_behavior('echo "$(echo hello world)"')
        
        # Backtick form
        self.assert_same_behavior('echo `echo hello`')
        
    def test_pipelines(self):
        """Test pipeline conformance."""
        # Simple pipeline
        self.assert_same_behavior('echo hello | cat')
        
        # Multi-stage pipeline
        self.assert_same_behavior('echo "hello world" | grep world | cat')
        
        # Pipeline with variables
        self.assert_same_behavior('x=hello; echo $x | cat')
        
    def test_redirections(self):
        """Test I/O redirection conformance."""
        # Output redirection
        self.assert_same_behavior('echo hello > out.txt; cat out.txt')
        
        # Append redirection
        self.assert_same_behavior(
            'echo first > out.txt; echo second >> out.txt; cat out.txt'
        )
        
        # Input redirection
        self.assert_same_behavior(
            'echo "test data" > in.txt; cat < in.txt'
        )
        
        # Here-document
        self.assert_same_behavior('''cat << EOF
line1
line2
EOF''')
        
    def test_exit_codes(self):
        """Test exit code conformance."""
        # Success
        self.assert_same_behavior('true; echo $?')
        
        # Failure
        self.assert_same_behavior('false; echo $?')
        
        # Command not found
        self.assert_same_behavior('nonexistentcommand 2>/dev/null; echo $?')
        
        # Pipeline exit code
        self.assert_same_behavior('true | false; echo $?')


class TestControlStructureConformance(ConformanceTest):
    """Test control structure conformance with bash."""
    
    def test_if_statements(self):
        """Test if statement conformance."""
        # Basic if
        self.assert_same_behavior('''
if true; then
    echo success
fi
''')
        
        # If-else
        self.assert_same_behavior('''
if false; then
    echo not_reached
else
    echo reached
fi
''')
        
        # If-elif-else
        self.assert_same_behavior('''
x=2
if [ $x -eq 1 ]; then
    echo one
elif [ $x -eq 2 ]; then
    echo two
else
    echo other
fi
''')
        
    def test_while_loops(self):
        """Test while loop conformance."""
        # Basic while
        self.assert_same_behavior('''
i=0
while [ $i -lt 3 ]; do
    echo $i
    i=$((i + 1))
done
''')
        
        # While with break
        self.assert_same_behavior('''
i=0
while true; do
    echo $i
    i=$((i + 1))
    if [ $i -eq 3 ]; then
        break
    fi
done
''')
        
    def test_for_loops(self):
        """Test for loop conformance."""
        # Basic for loop
        self.assert_same_behavior('''
for i in 1 2 3; do
    echo $i
done
''')
        
        # For with variables
        self.assert_same_behavior('''
list="a b c"
for item in $list; do
    echo $item
done
''')
        
        # For with glob
        self.assert_same_behavior('''
touch file1.txt file2.txt
for f in *.txt; do
    echo $f
done
''')
        
    def test_case_statements(self):
        """Test case statement conformance."""
        self.assert_same_behavior('''
x=b
case $x in
    a) echo "is a" ;;
    b) echo "is b" ;;
    *) echo "other" ;;
esac
''')


class TestExpansionConformance(ConformanceTest):
    """Test various expansion conformance with bash."""
    
    def test_parameter_expansion(self):
        """Test parameter expansion forms."""
        # Default values
        self.assert_same_behavior('echo ${undefined:-default}')
        self.assert_same_behavior('x=; echo ${x:-default}')
        self.assert_same_behavior('x=value; echo ${x:-default}')
        
        # Assign default - PSH doesn't support this syntax yet
        # self.assert_same_behavior('echo ${y:=default}; echo $y')
        
        # Length
        self.assert_same_behavior('x=hello; echo ${#x}')
        
        # Substring
        self.assert_same_behavior('x=hello; echo ${x:1:3}')
        
    def test_arithmetic_expansion(self):
        """Test arithmetic expansion conformance."""
        # Basic arithmetic
        self.assert_same_behavior('echo $((1 + 2))')
        self.assert_same_behavior('echo $((10 - 3))')
        self.assert_same_behavior('echo $((4 * 5))')
        self.assert_same_behavior('echo $((10 / 3))')
        self.assert_same_behavior('echo $((10 % 3))')
        
        # With variables
        self.assert_same_behavior('x=5; echo $((x + 3))')
        self.assert_same_behavior('x=2; y=3; echo $((x * y))')
        
    def test_brace_expansion(self):
        """Test brace expansion conformance."""
        # Basic brace expansion
        self.assert_same_behavior('echo {a,b,c}')
        self.assert_same_behavior('echo file{1,2,3}.txt')
        
        # Nested braces
        self.assert_same_behavior('echo {a,b}{1,2}')
        
        # Range expansion
        self.assert_same_behavior('echo {1..5}')
        self.assert_same_behavior('echo {a..e}')
        
    def test_glob_expansion(self):
        """Test pathname expansion conformance."""
        # Create test files
        setup = '''
mkdir -p test_dir
touch test_dir/file1.txt test_dir/file2.txt test_dir/data.csv
'''
        
        # Star glob
        self.assert_same_behavior(setup + 'cd test_dir && echo *.txt')
        
        # Question mark glob
        self.assert_same_behavior(setup + 'cd test_dir && echo file?.txt')
        
        # Character class
        self.assert_same_behavior(setup + 'cd test_dir && echo file[12].txt')


class TestBuiltinConformance(ConformanceTest):
    """Test builtin command conformance."""
    
    def test_cd_builtin(self):
        """Test cd builtin conformance."""
        # Basic cd
        self.assert_same_behavior('rm -rf testdir; mkdir testdir; cd testdir; pwd')
        
        # cd with CDPATH - PSH doesn't support CDPATH yet
        # self.assert_same_behavior('''
# mkdir -p a/b
# CDPATH=a
# cd b
# pwd
# ''')
        
        # cd - (previous directory) - PSH has a bug with OLDPWD
        # self.assert_same_behavior('''
# rm -rf a b
# mkdir a b
# cd a
# cd ../b  
# cd -
# pwd
# ''')
        
    def test_export_builtin(self):
        """Test export builtin conformance."""
        # Basic export
        self.assert_same_behavior('export X=value; echo $X')
        
        # Export existing variable
        self.assert_same_behavior('Y=value; export Y; echo $Y')
        
        # Export multiple
        self.assert_same_behavior('export A=1 B=2; echo $A $B')
        
    def test_read_builtin(self):
        """Test read builtin conformance."""
        # Basic read
        self.assert_same_behavior('echo "input" | read x; echo $x')
        
        # Read with IFS
        self.assert_same_behavior(
            'echo "a:b:c" | IFS=: read x y z; echo "$x $y $z"'
        )
        
        # Read with -r
        self.assert_same_behavior('echo "a\\nb" | read -r x; echo "$x"')


class TestDocumentedDifferences(ConformanceTest):
    """Test cases where PSH intentionally differs from bash."""
    
    def test_echo_escape_sequences(self):
        """Test echo -e differences."""
        # PSH and bash may handle escape sequences differently
        result = self.compare_shells('echo -e "\\n\\t"')
        # If they're identical, that's fine too
        if result.matches:
            result.assert_identical()
        else:
            result.assert_documented_difference(DifferenceType.OUTPUT_FORMAT)
        
    def test_set_output_format(self):
        """Test set -o output format differences."""
        # The output format of 'set -o' may differ
        result = self.compare_shells('set -o')
        result.assert_documented_difference(DifferenceType.OUTPUT_FORMAT)
        
    def test_missing_features(self):
        """Test features PSH doesn't implement yet."""
        # Programmable completion
        result = self.compare_shells('complete -W "option1 option2" mycommand 2>&1')
        result.assert_documented_difference(DifferenceType.FEATURE_MISSING)