"""Test enhanced test expressions ([[ ]]) integration with shell constructs."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import (
    EnhancedTestStatement, BinaryTestExpression, UnaryTestExpression,
    IfConditional, WhileLoop, ForLoop, AndOrList, Pipeline
)


class TestEnhancedTestWithControlStructures:
    """Test enhanced test expressions in control structures."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_enhanced_test_in_if_condition(self):
        """Test enhanced test as if condition."""
        cmd = 'if [[ "$var" == "value" ]]; then echo "match"; fi'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, IfConditional)
        
        # Check condition contains enhanced test
        condition = stmt.condition.statements[0]
        assert isinstance(condition, EnhancedTestStatement)
        
        expr = condition.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '$var'  # Variable preserved, quotes processed
        assert expr.operator == '=='
        assert expr.right == 'value'  # String content after quote processing
    
    def test_enhanced_test_in_while_condition(self):
        """Test enhanced test as while condition."""
        cmd = 'while [[ -f "$file" ]]; do echo "processing"; done'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, WhileLoop)
        
        # Check condition contains enhanced test
        condition = stmt.condition.statements[0]
        assert isinstance(condition, EnhancedTestStatement)
        
        expr = condition.expression
        assert isinstance(expr, UnaryTestExpression)
        assert expr.operator == '-f'
        assert expr.operand == '$file'  # Variable preserved, quotes processed
    
    def test_enhanced_test_with_elif(self):
        """Test enhanced test in elif conditions."""
        cmd = '''if [[ -f "$file" ]]; then
                    echo "file exists"
                 elif [[ -d "$file" ]]; then
                    echo "is directory"
                 fi'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, IfConditional)
        
        # Check if condition
        if_condition = stmt.condition.statements[0]
        assert isinstance(if_condition, EnhancedTestStatement)
        
        # Check elif condition
        assert len(stmt.elif_parts) == 1
        elif_condition = stmt.elif_parts[0][0].statements[0]  # (condition, then_part)
        assert isinstance(elif_condition, EnhancedTestStatement)
    
    def test_enhanced_test_in_case_guard(self):
        """Test enhanced test in case statement patterns."""
        # Note: This tests if enhanced test can be parsed in case context
        # Case statements with enhanced tests aren't standard but should parse
        cmd = '''case "$var" in
                    pattern) [[ -f "$file" ]] && echo "found";;
                 esac'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        # Should parse successfully with enhanced test in case body
        assert len(result.statements) == 1


class TestEnhancedTestWithLogicalOperators:
    """Test enhanced test expressions with shell logical operators."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_enhanced_test_with_and_operator(self):
        """Test enhanced test with && operator."""
        cmd = '[[ -f "$file" ]] && echo "file exists"'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, AndOrList)
        
        # First pipeline should be enhanced test
        first_pipeline = stmt.pipelines[0]
        assert isinstance(first_pipeline, EnhancedTestStatement)
        
        # Should have AND operator
        assert len(stmt.operators) == 1
        assert stmt.operators[0] == '&&'
    
    def test_enhanced_test_with_or_operator(self):
        """Test enhanced test with || operator."""
        cmd = '[[ -f "$file" ]] || echo "file not found"'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, AndOrList)
        
        # First pipeline should be enhanced test
        first_pipeline = stmt.pipelines[0]
        assert isinstance(first_pipeline, EnhancedTestStatement)
        
        # Should have OR operator
        assert len(stmt.operators) == 1
        assert stmt.operators[0] == '||'
    
    def test_enhanced_test_chained_operators(self):
        """Test enhanced test with chained logical operators."""
        cmd = '[[ -f "$file" ]] && [[ -r "$file" ]] && echo "readable file"'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, AndOrList)
        
        # Should have 3 pipelines with 2 AND operators
        assert len(stmt.pipelines) == 3
        assert len(stmt.operators) == 2
        assert all(op == '&&' for op in stmt.operators)
        
        # First two pipelines should be enhanced tests
        assert isinstance(stmt.pipelines[0], EnhancedTestStatement)
        assert isinstance(stmt.pipelines[1], EnhancedTestStatement)


class TestEnhancedTestWithPipelines:
    """Test enhanced test expressions with pipelines."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_enhanced_test_before_pipe(self):
        """Test enhanced test before pipe operator."""
        # This is a bit unusual but should parse
        cmd = '[[ "$var" == "test" ]] | cat'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, AndOrList)
        
        # Should have a pipeline with enhanced test and cat
        pipeline = stmt.pipelines[0]
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.commands) == 2
        
        # First command should be enhanced test
        assert isinstance(pipeline.commands[0], EnhancedTestStatement)
    
    def test_command_before_enhanced_test(self):
        """Test command output piped to enhanced test."""
        # This is unusual but tests parser flexibility
        cmd = 'echo "test" | [[ $(cat) == "test" ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        # Should parse successfully - even if semantically unusual
        assert len(result.statements) == 1


class TestEnhancedTestWithFunctions:
    """Test enhanced test expressions with function definitions."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_enhanced_test_in_function_body(self):
        """Test enhanced test inside function body."""
        cmd = '''check_file() {
                    [[ -f "$1" ]] && echo "file exists"
                 }'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        func_def = result.statements[0]
        
        # Function body should contain enhanced test
        body_stmt = func_def.body.statements[0]
        assert isinstance(body_stmt, AndOrList)
        
        # First pipeline should be enhanced test
        first_pipeline = body_stmt.pipelines[0]
        assert isinstance(first_pipeline, EnhancedTestStatement)
    
    def test_function_call_in_enhanced_test(self):
        """Test function call within enhanced test."""
        cmd = '[[ $(get_value) == "expected" ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        
        # Should parse command substitution as left operand
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '$(get_value)'
        assert expr.operator == '=='
        assert expr.right == 'expected'  # String content after quote processing


class TestEnhancedTestWithRedirection:
    """Test enhanced test expressions with I/O redirection."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_enhanced_test_with_output_redirect(self):
        """Test enhanced test with output redirection."""
        # Enhanced test with redirection is unusual - test that it doesn't parse
        cmd = '[[ -f "$file" ]] > /dev/null'
        tokens = tokenize(cmd)
        
        # This should fail as enhanced tests don't support direct redirection
        with pytest.raises(Exception):
            self.parser.parse(tokens)
    
    def test_enhanced_test_after_redirect(self):
        """Test enhanced test after command with redirection."""
        cmd = 'cat "$file" > /tmp/output && [[ -s /tmp/output ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, AndOrList)
        
        # Second pipeline should be enhanced test
        second_pipeline = stmt.pipelines[1]
        assert isinstance(second_pipeline, EnhancedTestStatement)


class TestEnhancedTestComplexIntegration:
    """Test complex integration scenarios."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
    
    def test_nested_control_structures_with_enhanced_test(self):
        """Test enhanced test in nested control structures."""
        cmd = '''if [[ -d "$dir" ]]; then
                    for file in "$dir"/*; do
                        if [[ -f "$file" ]]; then
                            echo "Processing $file"
                        fi
                    done
                 fi'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        # Should parse successfully with nested structure
        assert len(result.statements) == 1
        outer_if = result.statements[0]
        assert isinstance(outer_if, IfConditional)
        
        # Outer condition should be enhanced test
        outer_condition = outer_if.condition.statements[0]
        assert isinstance(outer_condition, EnhancedTestStatement)
    
    def test_multiple_enhanced_tests_in_sequence(self):
        """Test multiple enhanced tests in sequence."""
        cmd = '''[[ -f "$file1" ]]
                 [[ -f "$file2" ]]
                 [[ -f "$file3" ]]'''
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        # Should parse as three separate statements
        assert len(result.statements) == 3
        for stmt in result.statements:
            assert isinstance(stmt, EnhancedTestStatement)
    
    def test_enhanced_test_with_command_substitution_complex(self):
        """Test enhanced test with complex command substitution."""
        cmd = '[[ "$(date +%Y)" -gt 2020 ]]'
        tokens = tokenize(cmd)
        result = self.parser.parse(tokens)
        
        assert len(result.statements) == 1
        stmt = result.statements[0]
        assert isinstance(stmt, EnhancedTestStatement)
        
        expr = stmt.expression
        assert isinstance(expr, BinaryTestExpression)
        assert expr.left == '$(date +%Y)'  # Command substitution preserved, quotes processed
        assert expr.operator == '-gt'
        assert expr.right == '2020'