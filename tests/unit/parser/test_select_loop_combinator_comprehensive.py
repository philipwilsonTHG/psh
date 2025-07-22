"""Comprehensive tests for select loop parsing in parser combinator."""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import SelectLoop, CommandList


class TestSelectLoopComprehensive:
    """Test comprehensive select loop parsing functionality."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_select_with_mixed_item_types(self):
        """Test select with word, string, and variable items."""
        cmd = 'select item in word "quoted string" $variable; do echo $item; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "item"
        assert select_stmt.items == ["word", "quoted string", "$variable"]
        
        # Check quote types
        assert len(select_stmt.item_quote_types) == 3
        assert select_stmt.item_quote_types[0] is None  # word
        assert select_stmt.item_quote_types[1] == '"'   # quoted string
        assert select_stmt.item_quote_types[2] is None  # variable
    
    def test_select_with_single_quotes(self):
        """Test select with single-quoted items."""
        cmd = "select opt in 'single quoted' \"double quoted\"; do echo $opt; done"
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert select_stmt.items == ["single quoted", "double quoted"]
        assert select_stmt.item_quote_types[0] == "'"
        assert select_stmt.item_quote_types[1] == '"'
    
    def test_select_with_glob_patterns(self):
        """Test select with glob patterns."""
        cmd = 'select file in *.txt *.log /path/*.conf; do echo $file; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert select_stmt.items == ["*.txt", "*.log", "/path/*.conf"]
    
    def test_select_with_command_substitution_in_items(self):
        """Test select with command substitution in items."""
        cmd = 'select choice in $(ls) `date`; do echo $choice; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert select_stmt.items == ["$(ls)", "`date`"]
    
    def test_select_nested_in_control_structures(self):
        """Test select nested inside other control structures."""
        cmd = '''if true; then
    select option in yes no; do
        echo "You chose: $option"
        break
    done
fi'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        # Should parse the if statement containing a select
        if_stmt = result.statements[0]
        then_stmts = if_stmt.then_part.statements
        
        # Find the select statement in the then part
        select_found = False
        for stmt in then_stmts:
            if isinstance(stmt, SelectLoop):
                select_found = True
                assert stmt.variable == "option"
                assert stmt.items == ["yes", "no"]
                break
            elif hasattr(stmt, 'pipelines'):
                for pipeline in stmt.pipelines:
                    if isinstance(pipeline, SelectLoop):
                        select_found = True
                        assert pipeline.variable == "option"
                        assert pipeline.items == ["yes", "no"]
                        break
        
        # Should have found a select statement
        assert select_found
    
    def test_select_with_complex_body(self):
        """Test select with complex body including control structures."""
        cmd = '''select action in create delete list; do
    case $action in
        create) echo "Creating..." ;;
        delete) echo "Deleting..." ;;
        list) echo "Listing..." ;;
    esac
    if [[ $action == "delete" ]]; then
        echo "Are you sure?"
    fi
done'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "action"
        assert select_stmt.items == ["create", "delete", "list"]
        
        # Body should contain multiple statements
        body_stmts = select_stmt.body.statements
        assert len(body_stmts) >= 2  # At least case and if statements
    
    def test_select_with_break_continue(self):
        """Test select with break/continue statements."""
        cmd = '''select num in 1 2 3 4 5; do
    if [[ $num -eq 3 ]]; then
        continue
    fi
    if [[ $num -eq 5 ]]; then
        break
    fi
    echo "Number: $num"
done'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "num"
        assert select_stmt.items == ["1", "2", "3", "4", "5"]
    
    def test_select_with_pipelines_in_body(self):
        """Test select with pipelines in body."""
        cmd = '''select log in /var/log/*.log; do
    cat "$log" | grep ERROR | head -10
    echo "Found errors in $log"
done'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "log"
        assert select_stmt.items == ["/var/log/*.log"]
        
        # Body should contain pipeline statements
        body_stmts = select_stmt.body.statements
        assert len(body_stmts) >= 2
    
    def test_select_with_functions_in_body(self):
        """Test select with function calls in body."""
        cmd = '''select task in backup restore clean; do
    case $task in
        backup)
            backup_function
            ;;
        restore)
            restore_function "$@"
            ;;
        clean)
            cleanup_function && echo "Cleaned"
            ;;
    esac
done'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "task"
        assert select_stmt.items == ["backup", "restore", "clean"]
    
    def test_select_empty_items_list(self):
        """Test select with empty items list."""
        cmd = 'select empty in; do echo "No items"; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "empty"
        assert select_stmt.items == []
    
    def test_select_with_newlines_and_separators(self):
        """Test select with various newline and separator patterns."""
        cmd = '''select item in\\
    first\\
    second\\
    third
do
    echo $item
done'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "item"
        # Items might include continuation characters, depends on lexer
        assert len(select_stmt.items) >= 3
    
    def test_select_variable_validation(self):
        """Test that valid variable names work in select."""
        # Test various valid variable names
        valid_names = ['var', '_var', 'VAR', 'var123', '_123']
        
        for var_name in valid_names:
            cmd = f'select {var_name} in a b; do echo ${var_name}; done'
            tokens = tokenize(cmd)
            result = self.parser.parse(tokens)
            
            select_stmt = result.statements[0]
            assert select_stmt.variable == var_name
    
    def test_select_with_arithmetic_and_expansions(self):
        """Test select with arithmetic expansions and parameter expansions."""
        cmd = 'select item in $((1+1)) ${var:-default} ${#array[@]}; do echo $item; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        select_stmt = result.statements[0]
        assert isinstance(select_stmt, SelectLoop)
        assert select_stmt.variable == "item"
        # Items should include the expansions
        assert len(select_stmt.items) >= 3
        
    def test_select_error_handling_malformed(self):
        """Test that malformed select statements are handled gracefully."""
        malformed_cases = [
            'select',  # No variable
            'select var',  # No 'in'  
            'select var in',  # No 'do'
            'select var in items do',  # No 'done'
        ]
        
        for cmd in malformed_cases:
            tokens = tokenize(cmd)
            with pytest.raises(Exception):  # Should raise ParseError or similar
                self.parser.parse(tokens)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])