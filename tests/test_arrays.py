"""Comprehensive test suite for array functionality."""

import pytest
from unittest.mock import patch
from io import StringIO
from psh.shell import Shell


class TestArrays:
    """Test array functionality including syntax and expansions."""
    
    @pytest.fixture
    def shell(self):
        """Create a shell instance for testing."""
        return Shell()
    # Array initialization tests
    
    def test_array_initialization_empty(self, shell):
        """Test empty array initialization."""
        exit_code = shell.run_command("arr=()")
        assert exit_code == 0
        # Empty array should exist
        var = shell.state.get_variable("arr")
        assert var is not None
    
    def test_array_initialization_simple(self, shell):
        """Test simple array initialization."""
        exit_code = shell.run_command('arr=(one two three)')
        assert exit_code == 0
        
    def test_array_initialization_quoted(self, shell):
        """Test array initialization with quoted elements."""
        exit_code = shell.run_command('arr=("hello world" "foo bar" baz)')
        assert exit_code == 0
    
    def test_array_initialization_variables(self, shell):
        """Test array initialization with variable expansion."""
        shell.run_command("x=hello")
        shell.run_command("y=world")
        exit_code = shell.run_command('arr=($x $y "literal")')
        assert exit_code == 0
    
    # Array element assignment tests
    
    def test_array_element_assignment_basic(self, shell):
        """Test basic array element assignment."""
        exit_code = shell.run_command('arr[0]=first')
        assert exit_code == 0
        exit_code = shell.run_command('arr[1]=second')
        assert exit_code == 0
    
    def test_array_element_assignment_sparse(self, shell):
        """Test sparse array element assignment."""
        exit_code = shell.run_command('arr[10]=tenth')
        assert exit_code == 0
        exit_code = shell.run_command('arr[100]=hundredth')
        assert exit_code == 0
    
    def test_array_element_assignment_arithmetic(self, shell):
        """Test array element assignment with arithmetic index."""
        shell.run_command("i=5")
        exit_code = shell.run_command('arr[$i]=value')
        assert exit_code == 0
        exit_code = shell.run_command('arr[$((i+1))]=next')
        assert exit_code == 0
    
    # Array element access tests
    
    def test_array_element_access_basic(self, shell):
        """Test basic array element access."""
        shell.run_command('arr=(one two three)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${arr[0]}')
        assert 'one' in ''.join(output)
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${arr[1]}')
        assert 'two' in ''.join(output)
    
    def test_array_element_access_arithmetic(self, shell):
        """Test array element access with arithmetic index."""
        shell.run_command('arr=(zero one two three)')
        shell.run_command('i=2')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${arr[$i]}')
        assert 'two' in ''.join(output)
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${arr[$((i+1))]}')
        assert 'three' in ''.join(output)
    
    def test_array_element_access_negative(self, shell):
        """Test array element access with negative indices."""
        shell.run_command('arr=(first second third last)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${arr[-1]}')
        assert 'last' in ''.join(output)
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${arr[-2]}')
        assert 'third' in ''.join(output)
    
    # Array expansion tests
    
    def test_array_expand_all_at(self, shell):
        """Test ${arr[@]} expansion."""
        shell.run_command('arr=(one "two three" four)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('for x in "${arr[@]}"; do echo "[$x]"; done')
        
        result = ''.join(output)
        assert '[one]' in result
        assert '[two three]' in result
        assert '[four]' in result
    
    def test_array_expand_all_star(self, shell):
        """Test ${arr[*]} expansion."""
        shell.run_command('arr=(one two three)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[*]}"')
        
        assert 'one two three' in ''.join(output)
    
    def test_array_length(self, shell):
        """Test ${#arr[@]} for array length."""
        shell.run_command('arr=(a b c d e)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${#arr[@]}')
        
        assert '5' in ''.join(output)
    
    def test_array_length_sparse(self, shell):
        """Test array length with sparse array."""
        shell.run_command('arr[0]=zero')
        shell.run_command('arr[5]=five')
        shell.run_command('arr[10]=ten')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${#arr[@]}')
        
        assert '3' in ''.join(output)
    
    def test_array_indices(self, shell):
        """Test ${!arr[@]} for array indices."""
        shell.run_command('arr[1]=one')
        shell.run_command('arr[5]=five')
        shell.run_command('arr[9]=nine')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${!arr[@]}')
        
        result = ''.join(output)
        assert '1' in result
        assert '5' in result
        assert '9' in result
    
    # Array slicing tests
    
    def test_array_slice_basic(self, shell):
        """Test basic array slicing ${arr[@]:start:length}."""
        shell.run_command('arr=(zero one two three four five)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[@]:2:3}"')
        
        assert 'two three four' in ''.join(output)
    
    def test_array_slice_from_start(self, shell):
        """Test array slicing from start."""
        shell.run_command('arr=(a b c d e)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[@]:0:3}"')
        
        assert 'a b c' in ''.join(output)
    
    def test_array_slice_to_end(self, shell):
        """Test array slicing to end."""
        shell.run_command('arr=(a b c d e)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[@]:3}"')
        
        assert 'd e' in ''.join(output)
    
    # Array with parameter expansion tests
    
    def test_array_element_length(self, shell):
        """Test ${#arr[index]} for element length."""
        shell.run_command('arr=("hello" "world" "test")')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${#arr[0]}')
        assert '5' in ''.join(output)
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo ${#arr[1]}')
        assert '5' in ''.join(output)
    
    def test_array_element_substitution(self, shell):
        """Test parameter expansion on array elements."""
        shell.run_command('arr=("hello world" "foo bar")')
        
        # Test pattern substitution
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[0]/world/universe}"')
        assert 'hello universe' in ''.join(output)
        
        # Test substring removal
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[1]#foo }"')
        assert 'bar' in ''.join(output)
    
    # Declare -p array tests
    
    def test_declare_p_indexed_array(self, shell):
        """Test declare -p output for indexed arrays."""
        shell.run_command('arr=(one two three)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('declare -p arr')
        
        result = ''.join(output)
        assert 'declare -a arr=' in result
        assert '([0]="one" [1]="two" [2]="three")' in result
    
    def test_declare_p_sparse_array(self, shell):
        """Test declare -p output for sparse arrays."""
        shell.run_command('arr[1]=one')
        shell.run_command('arr[5]=five')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('declare -p arr')
        
        result = ''.join(output)
        assert 'declare -a arr=' in result
        assert '[1]="one"' in result
        assert '[5]="five"' in result
    
    # Array in loops tests
    
    def test_array_in_for_loop(self, shell):
        """Test array expansion in for loops."""
        shell.run_command('arr=(apple banana cherry)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('for fruit in "${arr[@]}"; do echo "Fruit: $fruit"; done')
        
        result = ''.join(output)
        assert 'Fruit: apple' in result
        assert 'Fruit: banana' in result
        assert 'Fruit: cherry' in result
    
    # Array append tests
    
    def test_array_append_element(self, shell):
        """Test appending to array using +=."""
        shell.run_command('arr=(one two)')
        shell.run_command('arr+=(three four)')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[@]}"')
        
        assert 'one two three four' in ''.join(output)
    
    def test_array_append_to_element(self, shell):
        """Test appending to array element."""
        shell.run_command('arr=(hello world)')
        shell.run_command('arr[0]+=" there"')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${arr[0]}"')
        
        assert 'hello there' in ''.join(output)
    
    # Edge cases
    
    def test_array_unset_element(self, shell):
        """Test unsetting array elements."""
        shell.run_command('arr=(one two three four)')
        shell.run_command('unset arr[1]')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "${!arr[@]}"')
        
        result = ''.join(output)
        assert '0' in result
        assert '2' in result
        assert '3' in result
        assert '1' not in result  # Index 1 was unset
    
    def test_array_vs_scalar_context(self, shell):
        """Test array behavior in scalar context."""
        shell.run_command('arr=(first second third)')
        
        # Without index, should return first element
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "$arr"')
        
        assert 'first' in ''.join(output)
    
    def test_empty_array_expansion(self, shell):
        """Test expansion of empty arrays."""
        shell.run_command('arr=()')
        
        # Should expand to nothing
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('echo "count: ${#arr[@]}"')
        assert 'count: 0' in ''.join(output)
        
        # Should produce no output
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command('for x in "${arr[@]}"; do echo "item: $x"; done')
        assert ''.join(output) == ''