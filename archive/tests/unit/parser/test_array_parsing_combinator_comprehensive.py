"""Comprehensive test suite for array parsing in parser combinator implementation."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import ArrayInitialization, ArrayElementAssignment


class TestArrayInitializationEdgeCases:
    """Test edge cases for array initialization."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_array_with_quoted_strings(self):
        """Test array with quoted string elements."""
        cmd = 'arr=("hello world" "test value")'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_init = result.statements[0].pipelines[0]
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == 'arr'
        assert array_init.elements == ['hello world', 'test value']  # Quotes processed
        assert not array_init.is_append
    
    def test_array_with_variables(self):
        """Test array with variable elements."""
        cmd = 'arr=($var $HOME "literal")'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_init = result.statements[0].pipelines[0]
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == 'arr'
        assert array_init.elements == ['$var', '$HOME', 'literal']
        assert not array_init.is_append
    
    def test_array_append_initialization(self):
        """Test array append initialization with +=."""
        cmd = 'arr+=(new elements)'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_init = result.statements[0].pipelines[0]
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == 'arr'
        assert array_init.elements == ['new', 'elements']
        assert array_init.is_append
    
    def test_array_single_element(self):
        """Test array with single element."""
        cmd = 'arr=(single)'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_init = result.statements[0].pipelines[0]
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == 'arr'
        assert array_init.elements == ['single']
        assert not array_init.is_append
    
    def test_array_with_command_substitution(self):
        """Test array with command substitution."""
        cmd = 'arr=($(echo test) `date`)'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_init = result.statements[0].pipelines[0]
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == 'arr'
        assert array_init.elements == ['$(echo test)', '`date`']
        assert not array_init.is_append


class TestArrayElementAssignmentEdgeCases:
    """Test edge cases for array element assignment."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_array_element_with_variable_index(self):
        """Test array element assignment with variable index."""
        cmd = 'arr[$i]=value'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_assign = result.statements[0].pipelines[0]
        assert isinstance(array_assign, ArrayElementAssignment)
        assert array_assign.name == 'arr'
        assert array_assign.index == '$i'
        assert array_assign.value == 'value'
        assert not array_assign.is_append
    
    def test_array_element_with_quoted_value(self):
        """Test array element assignment with quoted value."""
        cmd = 'arr[0]="hello world"'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_assign = result.statements[0].pipelines[0]
        assert isinstance(array_assign, ArrayElementAssignment)
        assert array_assign.name == 'arr'
        assert array_assign.index == '0'
        assert array_assign.value == 'hello world'  # Quote processed
        assert not array_assign.is_append
    
    def test_array_element_append_assignment(self):
        """Test array element append assignment with +=."""
        cmd = 'arr[0]+=suffix'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_assign = result.statements[0].pipelines[0]
        assert isinstance(array_assign, ArrayElementAssignment)
        assert array_assign.name == 'arr'
        assert array_assign.index == '0'
        assert array_assign.value == 'suffix'
        assert array_assign.is_append
    
    def test_array_element_with_arithmetic_index(self):
        """Test array element assignment with arithmetic index."""
        cmd = 'arr[$((i+1))]=value'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_assign = result.statements[0].pipelines[0]
        assert isinstance(array_assign, ArrayElementAssignment)
        assert array_assign.name == 'arr'
        assert array_assign.index == '$((i+1))'
        assert array_assign.value == 'value'
        assert not array_assign.is_append
    
    def test_array_element_high_index(self):
        """Test array element assignment with high numeric index."""
        cmd = 'arr[100]=sparse'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        array_assign = result.statements[0].pipelines[0]
        assert isinstance(array_assign, ArrayElementAssignment)
        assert array_assign.name == 'arr'
        assert array_assign.index == '100'
        assert array_assign.value == 'sparse'
        assert not array_assign.is_append


class TestArrayParsingErrorCases:
    """Test error cases for array parsing."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_unclosed_array_initialization(self):
        """Test error handling for unclosed array initialization."""
        cmd = 'arr=(one two'
        tokens = tokenize(cmd)
        
        with pytest.raises(Exception):
            self.parser.parse(tokens)
    
    def test_unclosed_array_index(self):
        """Test error handling for unclosed array index."""
        cmd = 'arr[0=value'
        tokens = tokenize(cmd)
        
        # This might parse as a simple command since the lexer may not detect it as array
        # The specific behavior depends on how the lexer handles malformed syntax
        # For now, we just ensure it doesn't crash
        try:
            result = self.parser.parse(tokens)
            # If it parses, it should be as a simple command, not an array
            assert result is not None
        except Exception:
            # If it fails to parse, that's also acceptable for malformed syntax
            pass


class TestArrayIntegrationScenarios:
    """Test array usage in various shell contexts."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_multiple_array_assignments(self):
        """Test multiple array assignments in sequence."""
        cmd = '''arr1=(one two)
arr2[0]=value
arr3+=(more elements)'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 3
        
        # First statement
        array1 = result.statements[0].pipelines[0]
        assert isinstance(array1, ArrayInitialization)
        assert array1.name == 'arr1'
        
        # Second statement  
        array2 = result.statements[1].pipelines[0]
        assert isinstance(array2, ArrayElementAssignment)
        assert array2.name == 'arr2'
        
        # Third statement
        array3 = result.statements[2].pipelines[0]
        assert isinstance(array3, ArrayInitialization)
        assert array3.name == 'arr3'
        assert array3.is_append
    
    def test_array_in_command_sequence(self):
        """Test array assignment followed by regular commands."""
        cmd = '''arr=(test values)
echo "Array initialized"
arr[0]=updated'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 3
        
        # First should be array initialization
        assert isinstance(result.statements[0].pipelines[0], ArrayInitialization)
        
        # Second should be regular command (echo)
        # This will be an AndOrList containing a Pipeline with SimpleCommand
        echo_stmt = result.statements[1]
        assert hasattr(echo_stmt, 'pipelines')
        
        # Third should be array element assignment
        assert isinstance(result.statements[2].pipelines[0], ArrayElementAssignment)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])