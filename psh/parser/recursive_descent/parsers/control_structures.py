"""
Control structure parsing for PSH shell.

This module handles parsing of control structures like if, while, for, case, and select.
"""

from typing import Union, Tuple, List, Optional
from ....token_types import Token, TokenType
from ....ast_nodes import (
    UnifiedControlStructure, IfConditional, WhileLoop, ForLoop, CStyleForLoop,
    CaseConditional, SelectLoop, BreakStatement, ContinueStatement, Statement,
    StatementList, ExecutionContext, Redirect, CaseItem, CasePattern
)
from ..helpers import TokenGroups


class ControlStructureParser:
    """Parser for control structure constructs."""
    
    def __init__(self, main_parser):
        """Initialize with reference to main parser."""
        self.parser = main_parser
    
    def parse_control_structure_neutral(self) -> UnifiedControlStructure:
        """Parse control structure without setting execution context."""
        token_type = self.parser.peek().type
        
        if token_type == TokenType.IF:
            return self._parse_if_neutral()
        elif token_type == TokenType.WHILE:
            return self._parse_while_neutral()
        elif token_type == TokenType.FOR:
            return self._parse_for_neutral()
        elif token_type == TokenType.CASE:
            return self._parse_case_neutral()
        elif token_type == TokenType.SELECT:
            return self._parse_select_neutral()
        elif token_type == TokenType.DOUBLE_LPAREN:
            return self.parser.arithmetic._parse_arithmetic_neutral()
        elif token_type in (TokenType.BREAK, TokenType.CONTINUE, TokenType.DOUBLE_LBRACKET):
            # These don't have unified types, fall back to regular parsing
            return self._parse_control_structure()
        else:
            raise self.parser._error(f"Unexpected control structure token: {token_type.name}")
    
    def _parse_control_structure(self) -> Statement:
        """Parse any control structure based on current token."""
        token_type = self.parser.peek().type
        
        if token_type == TokenType.IF:
            return self.parse_if_statement()
        elif token_type == TokenType.WHILE:
            return self.parse_while_statement()
        elif token_type == TokenType.FOR:
            return self.parse_for_statement()
        elif token_type == TokenType.CASE:
            return self.parse_case_statement()
        elif token_type == TokenType.SELECT:
            return self.parse_select_statement()
        elif token_type == TokenType.BREAK:
            return self.parse_break_statement()
        elif token_type == TokenType.CONTINUE:
            return self.parse_continue_statement()
        elif token_type == TokenType.DOUBLE_LBRACKET:
            return self.parser.tests.parse_enhanced_test_statement()
        elif token_type == TokenType.DOUBLE_LPAREN:
            return self.parser.arithmetic.parse_arithmetic_command()
        else:
            raise self.parser._error(f"Unexpected control structure token: {token_type.name}")
    
    # === If Statement Parsing ===
    
    def parse_if_statement(self) -> IfConditional:
        """Parse if/then/else/fi conditional statement."""
        result = self._parse_if_neutral()
        result.execution_context = ExecutionContext.STATEMENT
        return result
    
    def _parse_if_neutral(self) -> IfConditional:
        """Parse if statement without setting execution context."""
        self.parser.expect(TokenType.IF)
        self.parser.skip_newlines()
        
        # Parse main condition and body
        condition, then_part = self._parse_condition_then_block()
        
        # Parse elif clauses
        elif_parts = []
        while self.parser.match(TokenType.ELIF):
            self.parser.advance()
            elif_condition, elif_then = self._parse_condition_then_block()
            elif_parts.append((elif_condition, elif_then))
        
        # Parse optional else
        else_part = None
        if self.parser.match(TokenType.ELSE):
            self.parser.advance()
            self.parser.skip_newlines()
            else_part = self.parser.statements.parse_command_list_until(TokenType.FI)
        
        self.parser.expect(TokenType.FI)
        redirects = self.parser.redirections.parse_redirects()
        
        # Create with default execution_context, caller will update if needed
        return IfConditional(
            condition=condition,
            then_part=then_part,
            elif_parts=elif_parts,
            else_part=else_part,
            redirects=redirects,
            background=False
        )
    
    def _parse_condition_then_block(self) -> Tuple[StatementList, StatementList]:
        """Parse a condition followed by THEN and a command list."""
        self.parser.skip_newlines()
        condition = self.parser.statements.parse_command_list_until(TokenType.THEN)
        self.parser.expect(TokenType.THEN)
        self.parser.skip_newlines()
        body = self.parser.statements.parse_command_list_until(TokenType.ELIF, TokenType.ELSE, TokenType.FI)
        return condition, body
    
    # === While Statement Parsing ===
    
    def parse_while_statement(self) -> WhileLoop:
        """Parse while/do/done loop statement."""
        result = self._parse_while_neutral()
        result.execution_context = ExecutionContext.STATEMENT
        return result
    
    def _parse_while_neutral(self) -> WhileLoop:
        """Parse while loop without setting execution context."""
        condition, body, redirects = self._parse_loop_structure(
            TokenType.WHILE, TokenType.DO, TokenType.DONE
        )
        return WhileLoop(
            condition=condition,
            body=body,
            redirects=redirects,
            background=False
        )
    
    def _parse_loop_structure(self, start: TokenType, body_start: TokenType, 
                            body_end: TokenType) -> Tuple[StatementList, StatementList, List[Redirect]]:
        """Common pattern for while/until loops."""
        self.parser.expect(start)
        self.parser.skip_newlines()
        
        condition = self.parser.statements.parse_command_list_until(body_start)
        
        self.parser.expect(body_start)
        self.parser.skip_newlines()
        
        body = self.parser.statements.parse_command_list_until(body_end)
        
        self.parser.expect(body_end)
        redirects = self.parser.redirections.parse_redirects()
        
        return condition, body, redirects
    
    # === For Statement Parsing ===
    
    def parse_for_statement(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse for loop (traditional or C-style)."""
        result = self._parse_for_neutral()
        result.execution_context = ExecutionContext.STATEMENT
        return result
    
    def _parse_for_neutral(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse for loop without setting execution context."""
        self.parser.expect(TokenType.FOR)
        self.parser.skip_newlines()
        
        # Check if it's a C-style for loop
        if self.parser.peek().type == TokenType.DOUBLE_LPAREN:
            self.parser.advance()  # consume ((
            return self._parse_c_style_for_neutral()
        elif self.parser.peek().type == TokenType.LPAREN:
            saved_pos = self.parser.current
            self.parser.advance()  # consume first (
            
            if self.parser.peek().type == TokenType.LPAREN:
                self.parser.advance()  # consume second (
                return self._parse_c_style_for_neutral()
            else:
                self.parser.current = saved_pos
        
        # Traditional for loop
        variable = self.parser.expect(TokenType.WORD).value
        self.parser.skip_newlines()
        self.parser.expect(TokenType.IN)
        self.parser.skip_newlines()
        
        items, quote_types = self._parse_for_iterable()
        self.parser.skip_separators()
        self.parser.expect(TokenType.DO)
        self.parser.skip_newlines()
        
        body = self.parser.statements.parse_command_list_until(TokenType.DONE)
        self.parser.expect(TokenType.DONE)
        redirects = self.parser.redirections.parse_redirects()
        
        return ForLoop(
            variable=variable,
            items=items,
            item_quote_types=quote_types,
            body=body,
            redirects=redirects,
            background=False
        )
    
    def _parse_for_iterable(self) -> tuple[List[str], List[Optional[str]]]:
        """Parse the iterable part of a for loop."""
        items = []
        quote_types = []
        
        # Parse items until we hit DO, newline, or semicolon
        while (not self.parser.match(TokenType.DO) and 
               not self.parser.match_any(TokenGroups.STATEMENT_SEPARATORS) and 
               not self.parser.at_end()):
            
            if self.parser.match_any(TokenGroups.WORD_LIKE):
                value, _, quote_type = self.parser.commands.parse_composite_argument()
                items.append(value)
                quote_types.append(quote_type)
            else:
                break
        
        return items, quote_types
    
    def _parse_c_style_for_neutral(self) -> CStyleForLoop:
        """Parse C-style for loop without setting execution context."""
        # Parse initialization
        init = self.parser.arithmetic.parse_arithmetic_section(";")
        if init == "":
            init = None
        
        # Handle semicolon(s) after init
        if self.parser.match(TokenType.SEMICOLON):
            self.parser.advance()  # consume ;
            # Parse condition normally
            condition = self.parser.arithmetic.parse_arithmetic_section(";")
            if condition == "":
                condition = None
            if self.parser.match(TokenType.SEMICOLON):
                self.parser.advance()  # consume ;
        elif self.parser.match(TokenType.DOUBLE_SEMICOLON):
            # Handle ;; case - both init and condition are effectively empty
            self.parser.advance()  # consume ;;
            condition = None
        else:
            # No semicolon, something's wrong
            raise self.parser._error("Expected ';' after for loop initialization")
        
        # Parse increment
        increment = self.parser.arithmetic.parse_arithmetic_section_until_double_rparen()
        
        # Skip optional semicolon and newlines before DO (or body)
        self.parser.skip_separators()
        
        # DO keyword is optional in C-style for loops
        if self.parser.match(TokenType.DO):
            self.parser.advance()
            self.parser.skip_newlines()
        
        body = self.parser.statements.parse_command_list_until(TokenType.DONE)
        self.parser.expect(TokenType.DONE)
        redirects = self.parser.redirections.parse_redirects()
        
        return CStyleForLoop(
            init_expr=init,
            condition_expr=condition,
            update_expr=increment if increment else None,
            body=body,
            redirects=redirects,
            background=False
        )
    
    
    # === Case Statement Parsing ===
    
    def parse_case_statement(self) -> CaseConditional:
        """Parse case/esac statement."""
        result = self._parse_case_neutral()
        result.execution_context = ExecutionContext.STATEMENT
        return result
    
    def _parse_case_neutral(self) -> CaseConditional:
        """Parse case statement without setting execution context."""
        self.parser.expect(TokenType.CASE)
        self.parser.skip_newlines()
        
        expr = self._parse_case_expression()
        self.parser.expect(TokenType.IN)
        self.parser.skip_newlines()
        
        items = []
        while not self.parser.match(TokenType.ESAC) and not self.parser.at_end():
            if self.parser.match_any(TokenGroups.WORD_LIKE | TokenGroups.CASE_PATTERN_KEYWORDS):
                item = self.parse_case_item()
                items.append(item)
            else:
                self.parser.skip_newlines()
        
        self.parser.expect(TokenType.ESAC)
        redirects = self.parser.redirections.parse_redirects()
        
        return CaseConditional(
            expr=expr,
            items=items,
            redirects=redirects,
            background=False
        )
    
    def _parse_case_expression(self) -> str:
        """Parse the expression part of a case statement."""
        parts = []
        while (not self.parser.match(TokenType.IN) and 
               not self.parser.match_any(TokenGroups.STATEMENT_SEPARATORS) and 
               not self.parser.at_end()):
            if self.parser.match_any(TokenGroups.WORD_LIKE):
                value, _, _ = self.parser.commands.parse_composite_argument()
                parts.append(value)
            else:
                break
        return ' '.join(parts)
    
    def parse_case_item(self) -> CaseItem:
        """Parse a single case item."""
        patterns = []
        
        # Parse first pattern
        with self.parser.context:
            self.parser.context.in_case_pattern = True
            pattern_str = self.parser._parse_case_pattern()
            patterns.append(CasePattern(pattern=pattern_str))
        
        # Parse additional patterns separated by |
        while self.parser.match(TokenType.PIPE):
            self.parser.advance()
            with self.parser.context:
                self.parser.context.in_case_pattern = True
                pattern_str = self.parser._parse_case_pattern()
                patterns.append(CasePattern(pattern=pattern_str))
        
        self.parser.expect(TokenType.RPAREN)
        self.parser.skip_newlines()
        
        # Parse commands until case terminator
        commands = self.parser.statements.parse_command_list_until(
            *TokenGroups.CASE_TERMINATORS, TokenType.ESAC
        )
        
        # Consume the terminator
        if self.parser.match_any(TokenGroups.CASE_TERMINATORS):
            self.parser.advance()
        
        self.parser.skip_newlines()
        
        return CaseItem(patterns=patterns, commands=commands)
    
    def _parse_case_pattern(self) -> str:
        """Parse a case pattern."""
        parts = []
        
        while (not self.parser.match(TokenType.PIPE, TokenType.RPAREN) and 
               not self.parser.at_end()):
            
            token = self.parser.peek()
            if self.parser.match_any(TokenGroups.WORD_LIKE | TokenGroups.CASE_PATTERN_KEYWORDS):
                if token.type in TokenGroups.CASE_PATTERN_KEYWORDS:
                    # Keywords can be valid patterns
                    parts.append(token.value)
                    self.parser.advance()
                else:
                    value, _, _ = self.parser.commands.parse_composite_argument()
                    parts.append(value)
            else:
                break
        
        return ''.join(parts)
    
    # === Select Statement Parsing ===
    
    def parse_select_statement(self) -> SelectLoop:
        """Parse select statement."""
        result = self._parse_select_neutral()
        result.execution_context = ExecutionContext.STATEMENT
        return result
    
    def _parse_select_neutral(self) -> SelectLoop:
        """Parse select statement without setting execution context."""
        self.parser.expect(TokenType.SELECT)
        self.parser.skip_newlines()
        
        variable = self.parser.expect(TokenType.WORD).value
        self.parser.skip_newlines()
        self.parser.expect(TokenType.IN)
        self.parser.skip_newlines()
        
        items, quote_types = self._parse_for_iterable()
        self.parser.skip_separators()
        self.parser.expect(TokenType.DO)
        self.parser.skip_newlines()
        
        body = self.parser.statements.parse_command_list_until(TokenType.DONE)
        self.parser.expect(TokenType.DONE)
        redirects = self.parser.redirections.parse_redirects()
        
        return SelectLoop(
            variable=variable,
            items=items,
            item_quote_types=quote_types,
            body=body,
            redirects=redirects,
            background=False
        )
    
    # === Break/Continue Statement Parsing ===
    
    def parse_break_statement(self) -> BreakStatement:
        """Parse break statement with optional level."""
        self.parser.expect(TokenType.BREAK)
        level = self._parse_loop_control_level()
        return BreakStatement(level=level)
    
    def parse_continue_statement(self) -> ContinueStatement:
        """Parse continue statement with optional level."""
        self.parser.expect(TokenType.CONTINUE)
        level = self._parse_loop_control_level()
        return ContinueStatement(level=level)
    
    def _parse_loop_control_level(self) -> int:
        """Parse optional loop control level (default 1)."""
        if self.parser.match(TokenType.WORD) and self.parser.peek().value.isdigit():
            level_token = self.parser.advance()
            return int(level_token.value)
        return 1