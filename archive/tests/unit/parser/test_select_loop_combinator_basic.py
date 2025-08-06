"""Basic tests for select loop parsing in parser combinator."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import SelectLoop, CommandList


class TestSelectLoopBasic:
    """Test basic select loop parsing functionality."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_simple_select_loop(self):
        """Test: select item in a b c; do echo $item; done"""
        cmd = 'select item in a b c; do echo $item; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert isinstance(result, CommandList)
        assert len(result.statements) == 1
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "item"
        assert select_stmt.items == ["a", "b", "c"]
        
        # Check body
        body_stmts = select_stmt.body.statements
        assert len(body_stmts) == 1
        echo_cmd = body_stmts[0].pipelines[0].commands[0]
        assert echo_cmd.args == ["echo", "$item"]
    
    def test_select_with_quoted_items(self):
        """Test: select choice in "option 1" "option 2"; do echo $choice; done"""
        cmd = 'select choice in "option 1" "option 2"; do echo $choice; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "choice"
        assert select_stmt.items == ["option 1", "option 2"]
        
        # Check that quote types are tracked (if token has quote_type attribute)
        assert len(select_stmt.item_quote_types) == 2
    
    def test_select_with_variables(self):
        """Test: select opt in $var1 $var2; do echo $opt; done"""
        cmd = 'select opt in $var1 $var2; do echo $opt; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "opt"
        assert select_stmt.items == ["$var1", "$var2"]
    
    def test_select_empty_body(self):
        """Test: select x in a b; do done"""
        cmd = 'select x in a b; do done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "x"
        assert select_stmt.items == ["a", "b"]
        
        # Body should be empty
        assert len(select_stmt.body.statements) == 0
    
    def test_select_multiline_body(self):
        """Test select with multiple commands in body."""
        cmd = '''select file in *.txt; do
    echo "Processing $file"
    cat "$file"
    echo "Done with $file"
done'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "file"
        assert select_stmt.items == ["*.txt"]
        
        # Body should have multiple statements
        body_stmts = select_stmt.body.statements
        assert len(body_stmts) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])