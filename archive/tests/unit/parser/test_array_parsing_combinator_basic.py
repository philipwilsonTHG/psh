"""Basic test for array parsing in parser combinator implementation."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import ArrayInitialization, ArrayElementAssignment


class TestBasicArrayParsing:
    """Test basic array parsing functionality."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_simple_array_initialization(self):
        """Test simple array initialization."""
        cmd = 'arr=(one two three)'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        
        # Should be wrapped in AndOrList
        assert hasattr(stmt, 'pipelines')
        assert len(stmt.pipelines) == 1
        
        array_init = stmt.pipelines[0]
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == 'arr'
        assert array_init.elements == ['one', 'two', 'three']
        assert not array_init.is_append
    
    def test_empty_array_initialization(self):
        """Test empty array initialization."""
        cmd = 'empty=()'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        array_init = stmt.pipelines[0]
        
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == 'empty'
        assert array_init.elements == []
        assert not array_init.is_append
    
    def test_array_element_assignment(self):
        """Test array element assignment."""
        cmd = 'arr[0]=value'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        array_assign = stmt.pipelines[0]
        
        assert isinstance(array_assign, ArrayElementAssignment)
        assert array_assign.name == 'arr'
        assert array_assign.index == '0'
        assert array_assign.value == 'value'
        assert not array_assign.is_append


if __name__ == '__main__':
    pytest.main([__file__, '-v'])