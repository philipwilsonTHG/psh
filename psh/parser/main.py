"""
Main Parser class for PSH shell.

This module contains the main Parser class that orchestrates parsing by delegating
to specialized parser modules for different language constructs.
"""

import sys
from typing import List, Optional, Union, Tuple, Set

from ..token_types import Token, TokenType
from ..token_stream import TokenStream
from ..composite_processor import CompositeTokenProcessor, CompositeToken
from ..ast_nodes import (
    Command, SimpleCommand, CompoundCommand, Pipeline, CommandList, StatementList, AndOrList, Redirect, 
    FunctionDef, TopLevel, BreakStatement, ContinueStatement, 
    CaseItem, CasePattern, ProcessSubstitution, EnhancedTestStatement, 
    TestExpression, BinaryTestExpression, UnaryTestExpression, 
    CompoundTestExpression, NegatedTestExpression, Statement,
    # Unified types only
    ExecutionContext, UnifiedControlStructure, WhileLoop, ForLoop, CStyleForLoop,
    IfConditional, CaseConditional, SelectLoop, ArithmeticEvaluation,
    # Array assignments
    ArrayAssignment, ArrayInitialization, ArrayElementAssignment
)

from .base import BaseParser
from .helpers import TokenGroups, ParseError, ErrorContext
from .error_collector import ErrorCollector, MultiErrorParseResult, ErrorRecoveryStrategy
from .statements import StatementParser
from .commands import CommandParser
from .control_structures import ControlStructureParser
from .tests import TestParser
from .arithmetic import ArithmeticParser
from .redirections import RedirectionParser
from .arrays import ArrayParser
from .functions import FunctionParser
from .utils import ParserUtils


class Parser(BaseParser):
    """Main parser class that orchestrates parsing by delegating to specialized parsers."""
    
    def __init__(self, tokens: List[Token], use_composite_processor: bool = False, 
                 source_text: Optional[str] = None, collect_errors: bool = False):
        # Optionally process tokens for composites
        if use_composite_processor:
            processor = CompositeTokenProcessor()
            tokens = processor.process(tokens)
        super().__init__(tokens)
        
        # Store source text for error messages
        self.source_text = source_text
        self.source_lines = source_text.splitlines() if source_text else None
        
        # Error collection support
        self.error_collector = ErrorCollector() if collect_errors else None
        
        # Initialize specialized parsers
        self.statements = StatementParser(self)
        self.commands = CommandParser(self)
        self.control_structures = ControlStructureParser(self)
        self.tests = TestParser(self)
        self.arithmetic = ArithmeticParser(self)
        self.redirections = RedirectionParser(self)
        self.arrays = ArrayParser(self)
        self.functions = FunctionParser(self)
        self.utils = ParserUtils(self)
    
    def _error(self, message: str, token: Optional[Token] = None) -> ParseError:
        """Create a ParseError with context."""
        if token is None:
            token = self.peek()
        
        # Get source line if available
        source_line = None
        if self.source_lines and token.line and 0 < token.line <= len(self.source_lines):
            source_line = self.source_lines[token.line - 1]
        
        error_context = ErrorContext(
            token=token,
            message=message,
            position=token.position,
            line=token.line,
            column=token.column,
            source_line=source_line
        )
        return ParseError(error_context)
    
    # === Top-Level Parsing ===
    
    def parse(self) -> Union[CommandList, TopLevel]:
        """Parse input, returning TopLevel if needed, CommandList for simple cases."""
        top_level = TopLevel()
        self.skip_newlines()
        
        while not self.at_end():
            item = self._parse_top_level_item()
            if item:
                top_level.items.append(item)
            self.skip_separators()
        
        return self._simplify_result(top_level)
    
    def parse_with_error_collection(self) -> MultiErrorParseResult:
        """Parse input collecting multiple errors instead of stopping on first error.
        
        Returns:
            MultiErrorParseResult containing AST and any errors encountered
        """
        if not self.error_collector:
            # Enable error collection if not already enabled
            self.error_collector = ErrorCollector()
        
        ast = None
        try:
            ast = self.parse()
        except ParseError as e:
            self.error_collector.add_error(e)
            # Try to recover and continue parsing
            if self.error_collector.should_continue():
                ast = self._parse_with_recovery()
        
        return MultiErrorParseResult(ast, self.error_collector.errors)
    
    def _parse_with_recovery(self) -> Optional[Union[CommandList, TopLevel]]:
        """Continue parsing after error with recovery strategies."""
        top_level = TopLevel()
        
        while not self.at_end() and self.error_collector.should_continue():
            try:
                # Try to find next statement
                if not ErrorRecoveryStrategy.find_next_statement(self):
                    break
                
                # Try to parse next item
                item = self._parse_top_level_item_with_recovery()
                if item:
                    top_level.items.append(item)
                    
            except ParseError as e:
                self.error_collector.add_error(e)
                # Skip to next recovery point
                ErrorRecoveryStrategy.skip_to_statement_end(self)
                
            self.skip_separators()
        
        return self._simplify_result(top_level) if top_level.items else None
    
    def _parse_top_level_item_with_recovery(self):
        """Parse top level item with error recovery."""
        try:
            return self._parse_top_level_item()
        except ParseError as e:
            # Add error but try to recover
            self.error_collector.add_error(e)
            
            # Try different recovery strategies
            if self._try_statement_recovery():
                return self._parse_top_level_item()
            else:
                # Skip this item and continue
                ErrorRecoveryStrategy.skip_to_statement_end(self)
                return None
    
    def _try_statement_recovery(self) -> bool:
        """Try to recover at statement level.
        
        Returns:
            True if recovery successful, False otherwise
        """
        # Look for common missing tokens and try to insert them
        current = self.peek()
        
        # Try to recover from missing semicolon
        if current.type in {TokenType.THEN, TokenType.DO}:
            # Assume missing semicolon, continue parsing
            return True
        
        # Try to recover from missing closing tokens
        if current.type in {TokenType.FI, TokenType.DONE, TokenType.ESAC}:
            # Assume we're at the end of a block, continue
            return True
        
        return False
    
    def parse_with_heredocs(self, heredoc_map: dict) -> Union[CommandList, TopLevel]:
        """Parse tokens with heredoc content."""
        self.heredoc_map = heredoc_map
        ast = self.parse()
        # Populate heredoc content in the AST
        self.utils.populate_heredoc_content(ast, heredoc_map)
        return ast
    
    def _parse_top_level_item(self) -> Optional[Statement]:
        """Parse a single top-level item."""
        if self.functions.is_function_def():
            return self.functions.parse_function_def()
        elif self.match_any(TokenGroups.CONTROL_KEYWORDS):
            # Check if control structure is part of a pipeline
            control_struct = self.control_structures.parse_control_structure_neutral()
            
            # Check if followed by pipe or logical operators
            if self.match(TokenType.PIPE):
                # Parse as pipeline with control structure as first component
                return self.commands.parse_pipeline_with_initial_component(control_struct)
            elif self.match(TokenType.AND_AND, TokenType.OR_OR):
                # Create pipeline with control structure and wrap in and_or_list
                control_struct.execution_context = ExecutionContext.STATEMENT
                pipeline = Pipeline()
                pipeline.commands.append(control_struct)
                
                and_or_list = AndOrList()
                and_or_list.pipelines.append(pipeline)
                
                # Parse the rest of the and_or_list
                while self.match(TokenType.AND_AND, TokenType.OR_OR):
                    operator = self.advance()
                    and_or_list.operators.append(operator.value)
                    self.skip_newlines()
                    pipeline = self.commands.parse_pipeline()
                    and_or_list.pipelines.append(pipeline)
                
                return and_or_list
            else:
                # Set as statement context and return
                control_struct.execution_context = ExecutionContext.STATEMENT
                return control_struct
        else:
            # Parse commands until we hit a function or control structure
            cmd_list = self.statements.parse_command_list_until_top_level()
            return cmd_list if cmd_list.statements else None
    
    def _simplify_result(self, top_level: TopLevel) -> Union[CommandList, TopLevel]:
        """Simplify result for backward compatibility when possible."""
        if len(top_level.items) == 0:
            return CommandList()
        elif len(top_level.items) == 1:
            item = top_level.items[0]
            if isinstance(item, CommandList):
                return item
            elif isinstance(item, (BreakStatement, ContinueStatement)):
                # Convert to CommandList for compatibility
                cmd_list = CommandList()
                cmd_list.statements.append(item)
                return cmd_list
            else:
                # Other single items return TopLevel
                return top_level
        else:
            return top_level
    
    # === Delegation Methods ===
    # These methods delegate to specialized parsers for backward compatibility
    
    def parse_statement(self) -> Optional[Statement]:
        """Parse a statement."""
        return self.statements.parse_statement()
    
    def parse_command_list(self) -> CommandList:
        """Parse a command list."""
        return self.statements.parse_command_list()
    
    def parse_and_or_list(self) -> Union[AndOrList, BreakStatement, ContinueStatement]:
        """Parse an and/or list."""
        return self.statements.parse_and_or_list()
    
    def parse_pipeline(self) -> Pipeline:
        """Parse a pipeline."""
        return self.commands.parse_pipeline()
    
    def parse_command(self) -> SimpleCommand:
        """Parse a command."""
        return self.commands.parse_command()
    
    def parse_composite_argument(self) -> Tuple[str, str, Optional[str]]:
        """Parse a composite argument."""
        return self.commands.parse_composite_argument()
    
    # ===== Additional delegation methods for backward compatibility =====
    
    def parse_test_expression(self):
        """Delegate to test parser.""" 
        return self.tests.parse_test_expression()
    
    def _parse_arithmetic_expression_until_double_rparen(self):
        """Delegate to arithmetic parser."""
        return self.arithmetic._parse_arithmetic_expression_until_double_rparen()
    
    def _parse_case_pattern(self):
        """Delegate to control structures parser."""
        return self.control_structures._parse_case_pattern()
    
    def parse_command_list_until(self, *args):
        """Delegate to statements parser."""
        return self.statements.parse_command_list_until(*args)
    
    def parse_if_statement(self) -> IfConditional:
        """Parse an if statement."""
        return self.control_structures.parse_if_statement()
    
    def parse_while_statement(self) -> WhileLoop:
        """Parse a while statement."""
        return self.control_structures.parse_while_statement()
    
    def parse_for_statement(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse a for statement."""
        return self.control_structures.parse_for_statement()
    
    def parse_case_statement(self) -> CaseConditional:
        """Parse a case statement."""
        return self.control_structures.parse_case_statement()
    
    def parse_select_statement(self) -> SelectLoop:
        """Parse a select statement."""
        return self.control_structures.parse_select_statement()
    
    def parse_break_statement(self) -> BreakStatement:
        """Parse a break statement."""
        return self.control_structures.parse_break_statement()
    
    def parse_continue_statement(self) -> ContinueStatement:
        """Parse a continue statement."""
        return self.control_structures.parse_continue_statement()
    
    def parse_enhanced_test_statement(self) -> EnhancedTestStatement:
        """Parse an enhanced test statement ([[ ... ]])."""
        return self.tests.parse_enhanced_test_statement()
    
    def parse_arithmetic_command(self) -> ArithmeticEvaluation:
        """Parse an arithmetic command ((...)). """
        return self.arithmetic.parse_arithmetic_command()
    
    def parse_function_def(self) -> FunctionDef:
        """Parse a function definition."""
        return self.functions.parse_function_def()
    
    def parse_redirects(self) -> List[Redirect]:
        """Parse redirections."""
        return self.redirections.parse_redirects()
    
    def parse_redirect(self) -> Redirect:
        """Parse a single redirection."""
        return self.redirections.parse_redirect()