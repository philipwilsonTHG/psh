"""Integration tests for parser context management."""

import pytest
from psh.lexer import tokenize
from psh.parser import Parser
from psh.ast_nodes import EnhancedTestStatement, ArithmeticEvaluation, CaseConditional, CommandList


class TestParserContextIntegration:
    """Test parser's use of context management."""
    
    def parse_command(self, input_str: str):
        """Helper to parse a command."""
        tokens = tokenize(input_str)
        parser = Parser(tokens)
        return parser.parse()
    
    def test_enhanced_test_context(self):
        """Test that enhanced test parsing sets context correctly."""
        tokens = tokenize('[[ -f /etc/passwd ]]')
        parser = Parser(tokens)
        
        # Hook into the parser to check context
        original_parse = parser.parse_test_expression
        context_checked = {'in_test': False}
        
        def wrapped_parse():
            context_checked['in_test'] = parser.context.in_test_expr
            return original_parse()
        
        parser.parse_test_expression = wrapped_parse
        ast = parser.parse()
        
        # Verify context was set during test expression parsing
        assert context_checked['in_test'] is True
        
        # Verify context is restored after parsing
        assert parser.context.in_test_expr is False
    
    def test_arithmetic_context(self):
        """Test that arithmetic parsing sets context correctly."""
        tokens = tokenize('((x + 5))')
        parser = Parser(tokens)
        
        # Hook to check context
        original_parse = parser._parse_arithmetic_expression_until_double_rparen
        context_checked = {'in_arithmetic': False}
        
        def wrapped_parse():
            context_checked['in_arithmetic'] = parser.context.in_arithmetic
            return original_parse()
        
        parser._parse_arithmetic_expression_until_double_rparen = wrapped_parse
        ast = parser.parse()
        
        # Verify context was set during arithmetic parsing
        assert context_checked['in_arithmetic'] is True
        
        # Verify context is restored after parsing
        assert parser.context.in_arithmetic is False
    
    def test_case_pattern_context(self):
        """Test that case pattern parsing sets context correctly."""
        tokens = tokenize('case $x in foo) echo bar ;; esac')
        parser = Parser(tokens)
        
        # Hook to check context
        original_parse = parser._parse_case_pattern
        context_checked = {'in_pattern': False}
        
        def wrapped_parse():
            context_checked['in_pattern'] = parser.context.in_case_pattern
            return original_parse()
        
        parser._parse_case_pattern = wrapped_parse
        ast = parser.parse()
        
        # Verify context was set during pattern parsing
        assert context_checked['in_pattern'] is True
        
        # Verify context is restored after parsing
        assert parser.context.in_case_pattern is False
    
    def test_function_body_context(self):
        """Test that function body parsing sets context correctly."""
        tokens = tokenize('foo() { echo hello; }')
        parser = Parser(tokens)
        
        # Hook to check context
        original_parse = parser.parse_command_list_until
        context_checked = {'in_function': False}
        
        def wrapped_parse(end_token):
            if parser.context.in_function_body:
                context_checked['in_function'] = True
            return original_parse(end_token)
        
        parser.parse_command_list_until = wrapped_parse
        ast = parser.parse()
        
        # Verify context was set during function body parsing
        assert context_checked['in_function'] is True
        
        # Verify context is restored after parsing
        assert parser.context.in_function_body is False
    
    def test_nested_contexts(self):
        """Test nested context management works correctly."""
        # Function containing arithmetic command
        tokens = tokenize('foo() { ((x++)); }')
        parser = Parser(tokens)
        
        contexts = {
            'function_during_arithmetic': False,
            'arithmetic_during_function': False
        }
        
        # Hook arithmetic parsing
        original_arith = parser._parse_arithmetic_expression_until_double_rparen
        
        def wrapped_arith():
            contexts['function_during_arithmetic'] = parser.context.in_function_body
            contexts['arithmetic_during_function'] = parser.context.in_arithmetic
            return original_arith()
        
        parser._parse_arithmetic_expression_until_double_rparen = wrapped_arith
        ast = parser.parse()
        
        # Both contexts should be active during nested parsing
        assert contexts['function_during_arithmetic'] is True
        assert contexts['arithmetic_during_function'] is True
        
        # Both should be restored after
        assert parser.context.in_function_body is False
        assert parser.context.in_arithmetic is False
    
    def test_context_with_parse_error(self):
        """Test context is restored even when parsing fails."""
        tokens = tokenize('[[ -f')  # Incomplete test
        parser = Parser(tokens)
        
        # Check initial state
        assert parser.context.in_test_expr is False
        
        # Try to parse, should fail
        with pytest.raises(Exception):  # ParseError
            parser.parse()
        
        # Context should still be restored
        assert parser.context.in_test_expr is False
    
    def test_regex_rhs_context_stack(self):
        """Test context stack usage for regex RHS."""
        tokens = tokenize('[[ $x =~ pattern ]]')
        parser = Parser(tokens)
        
        # The parser already uses push_context for regex_rhs
        context_stack_checked = {'had_regex': False}
        
        original_pop = parser.context.pop_context
        
        def wrapped_pop():
            if 'regex_rhs' in parser.context.context_stack:
                context_stack_checked['had_regex'] = True
            return original_pop()
        
        parser.context.pop_context = wrapped_pop
        ast = parser.parse()
        
        # Verify regex_rhs was on the stack
        assert context_stack_checked['had_regex'] is True
        
        # Stack should be empty after parsing
        assert parser.context.context_stack == []