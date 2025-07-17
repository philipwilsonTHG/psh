"""Enhanced control structure parsing using token metadata."""

from typing import Union, List, Optional
from ..token_types import Token, TokenType
from ..token_enhanced import TokenContext, SemanticType
from ..ast_nodes import (
    UnifiedControlStructure, IfConditional, WhileLoop, ForLoop, 
    CaseConditional, SelectLoop, BreakStatement, ContinueStatement,
    Statement, StatementList
)
from .enhanced_base import EnhancedContextBaseParser, EnhancedParserConfig
from .control_structures import ControlStructureParser


class EnhancedControlStructureParser(ControlStructureParser):
    """Enhanced control structure parser leveraging token metadata."""
    
    def __init__(self, main_parser):
        """Initialize enhanced control structure parser."""
        super().__init__(main_parser)
        
        # Check if main parser has enhanced capabilities
        self.enhanced_parser = isinstance(main_parser, EnhancedContextBaseParser)
        self.enhanced_config = getattr(main_parser, 'enhanced_config', None)
    
    def parse_control_structure_enhanced(self) -> Statement:
        """Enhanced control structure parsing using token metadata."""
        if not self.enhanced_parser:
            # Fallback to original implementation
            return self._parse_control_structure()
        
        current_token = self._get_current_enhanced_token()
        
        if not current_token:
            raise self.parser._error("Expected control structure")
        
        # Enhanced context validation
        if (self.enhanced_config and 
            self.enhanced_config.enable_context_validation):
            self._validate_control_structure_context(current_token)
        
        # Enhanced semantic validation
        if (self.enhanced_config and 
            self.enhanced_config.enable_semantic_validation):
            self._validate_control_structure_semantics(current_token)
        
        # Parse based on token type with enhanced features
        token_type = current_token.type
        
        if token_type == TokenType.IF:
            return self._parse_if_enhanced()
        elif token_type == TokenType.WHILE:
            return self._parse_while_enhanced()
        elif token_type == TokenType.FOR:
            return self._parse_for_enhanced()
        elif token_type == TokenType.CASE:
            return self._parse_case_enhanced()
        elif token_type == TokenType.SELECT:
            return self._parse_select_enhanced()
        elif token_type in (TokenType.BREAK, TokenType.CONTINUE):
            return self._parse_break_continue_enhanced()
        else:
            # Fallback to original parsing
            return self._parse_control_structure()
    
    def _get_current_enhanced_token(self) -> Optional[Token]:
        """Get current token as enhanced token."""
        if hasattr(self.parser, 'peek_enhanced'):
            return self.parser.peek_enhanced()
        
        # Fallback: convert basic token to enhanced
        token = self.parser.peek()
        if token and not isinstance(token, Token):
            return Token.from_token(token)
        return token
    
    def _validate_control_structure_context(self, token: Token):
        """Validate control structure appears in correct context."""
        # Control structures should be in command position
        if TokenContext.COMMAND_POSITION not in token.metadata.contexts:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Control structure '{token.value}' not in command position"
                )
    
    def _validate_control_structure_semantics(self, token: Token):
        """Validate control structure semantics."""
        # Verify token is marked as keyword
        if token.metadata.semantic_type != SemanticType.KEYWORD:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"'{token.value}' should be recognized as shell keyword"
                )
    
    def _parse_if_enhanced(self) -> IfConditional:
        """Enhanced if statement parsing."""
        # Use enhanced error context
        if_token = self.parser.advance()  # consume 'if'
        
        try:
            # Parse condition with enhanced context tracking
            condition = self._parse_condition_enhanced()
            
            # Expect 'then' with context validation
            then_token = self._get_current_enhanced_token()
            if (self.enhanced_config and 
                self.enhanced_config.enable_context_validation and
                then_token):
                
                if TokenContext.CONDITIONAL_EXPRESSION not in then_token.metadata.contexts:
                    if hasattr(self.parser.ctx, 'add_warning'):
                        self.parser.ctx.add_warning(
                            "Expected 'then' in conditional context"
                        )
            
            self.parser.expect(TokenType.THEN)
            
            # Parse then body
            then_body = self._parse_statement_list_enhanced()
            
            # Parse elif/else clauses
            elif_clauses = []
            else_body = None
            
            while self.parser.match(TokenType.ELIF):
                self.parser.advance()  # consume 'elif'
                elif_condition = self._parse_condition_enhanced()
                self.parser.expect(TokenType.THEN)
                elif_body = self._parse_statement_list_enhanced()
                elif_clauses.append((elif_condition, elif_body))
            
            if self.parser.match(TokenType.ELSE):
                self.parser.advance()  # consume 'else'
                else_body = self._parse_statement_list_enhanced()
            
            self.parser.expect(TokenType.FI)
            
            return IfConditional(
                condition=condition,
                then_body=then_body,
                elif_clauses=elif_clauses,
                else_body=else_body,
                position=if_token.position
            )
            
        except Exception as e:
            # Enhanced error recovery
            self._attempt_if_error_recovery(if_token, e)
            raise
    
    def _parse_while_enhanced(self) -> WhileLoop:
        """Enhanced while loop parsing."""
        while_token = self.parser.advance()  # consume 'while'
        
        try:
            # Parse condition
            condition = self._parse_condition_enhanced()
            
            # Expect 'do'
            self.parser.expect(TokenType.DO)
            
            # Parse body
            body = self._parse_statement_list_enhanced()
            
            # Expect 'done'
            self.parser.expect(TokenType.DONE)
            
            return WhileLoop(
                condition=condition,
                body=body,
                position=while_token.position
            )
            
        except Exception as e:
            # Enhanced error recovery
            self._attempt_while_error_recovery(while_token, e)
            raise
    
    def _parse_for_enhanced(self) -> Union[ForLoop, 'CStyleForLoop']:
        """Enhanced for loop parsing."""
        for_token = self.parser.advance()  # consume 'for'
        
        try:
            # Check for C-style for loop
            if self.parser.match(TokenType.DOUBLE_LPAREN):
                return self._parse_c_style_for_enhanced()
            
            # Regular for loop
            variable = self.parser.expect(TokenType.WORD).value
            
            # Enhanced variable validation
            if (self.enhanced_config and 
                self.enhanced_config.enable_semantic_validation):
                self._validate_for_variable(variable)
            
            # Optional 'in' clause
            iterable = None
            if self.parser.match(TokenType.IN):
                self.parser.advance()  # consume 'in'
                iterable = self._parse_for_iterable_enhanced()
            
            # Expect 'do'
            self.parser.expect(TokenType.DO)
            
            # Parse body
            body = self._parse_statement_list_enhanced()
            
            # Expect 'done'
            self.parser.expect(TokenType.DONE)
            
            return ForLoop(
                variable=variable,
                iterable=iterable,
                body=body,
                position=for_token.position
            )
            
        except Exception as e:
            # Enhanced error recovery
            self._attempt_for_error_recovery(for_token, e)
            raise
    
    def _parse_case_enhanced(self) -> CaseConditional:
        """Enhanced case statement parsing."""
        case_token = self.parser.advance()  # consume 'case'
        
        try:
            # Parse expression
            expression = self.parser.expect(TokenType.WORD).value
            
            # Expect 'in'
            self.parser.expect(TokenType.IN)
            
            # Parse case items with enhanced pattern validation
            items = []
            while not self.parser.match(TokenType.ESAC):
                item = self._parse_case_item_enhanced()
                items.append(item)
            
            self.parser.expect(TokenType.ESAC)
            
            return CaseConditional(
                expression=expression,
                items=items,
                position=case_token.position
            )
            
        except Exception as e:
            # Enhanced error recovery
            self._attempt_case_error_recovery(case_token, e)
            raise
    
    def _parse_select_enhanced(self) -> SelectLoop:
        """Enhanced select statement parsing."""
        select_token = self.parser.advance()  # consume 'select'
        
        try:
            # Parse variable
            variable = self.parser.expect(TokenType.WORD).value
            
            # Enhanced variable validation
            if (self.enhanced_config and 
                self.enhanced_config.enable_semantic_validation):
                self._validate_select_variable(variable)
            
            # Optional 'in' clause
            items = None
            if self.parser.match(TokenType.IN):
                self.parser.advance()  # consume 'in'
                items = self._parse_select_items_enhanced()
            
            # Expect 'do'
            self.parser.expect(TokenType.DO)
            
            # Parse body
            body = self._parse_statement_list_enhanced()
            
            # Expect 'done'
            self.parser.expect(TokenType.DONE)
            
            return SelectLoop(
                variable=variable,
                items=items,
                body=body,
                position=select_token.position
            )
            
        except Exception as e:
            # Enhanced error recovery
            self._attempt_select_error_recovery(select_token, e)
            raise
    
    def _parse_break_continue_enhanced(self) -> Union[BreakStatement, ContinueStatement]:
        """Enhanced break/continue parsing."""
        token = self.parser.advance()
        
        # Enhanced context validation
        if (self.enhanced_config and 
            self.enhanced_config.enable_context_validation):
            self._validate_break_continue_context(token)
        
        # Optional level argument
        level = 1
        if self.parser.match(TokenType.WORD):
            level_token = self.parser.advance()
            try:
                level = int(level_token.value)
                if level <= 0:
                    raise ValueError("Invalid level")
            except ValueError:
                if hasattr(self.parser.ctx, 'add_warning'):
                    self.parser.ctx.add_warning(
                        f"Invalid {token.value} level: {level_token.value}"
                    )
                level = 1
        
        if token.type == TokenType.BREAK:
            return BreakStatement(level=level, position=token.position)
        else:
            return ContinueStatement(level=level, position=token.position)
    
    def _parse_condition_enhanced(self):
        """Parse condition with enhanced features."""
        # Use existing condition parsing but add enhanced validation
        return self.parser.statements.parse_statement_list()
    
    def _parse_statement_list_enhanced(self) -> StatementList:
        """Parse statement list with enhanced features."""
        # Use existing statement list parsing
        return self.parser.statements.parse_statement_list()
    
    def _parse_for_iterable_enhanced(self) -> List[str]:
        """Parse for loop iterable with enhanced validation."""
        items = []
        while (self.parser.match(TokenType.WORD, TokenType.STRING) and
               not self.parser.match_any([TokenType.DO, TokenType.SEMICOLON, TokenType.NEWLINE])):
            token = self.parser.advance()
            items.append(token.value)
        return items
    
    def _parse_case_item_enhanced(self):
        """Parse case item with enhanced pattern validation."""
        # Use existing case item parsing
        return self.parser.control_structures._parse_case_item()
    
    def _parse_select_items_enhanced(self) -> List[str]:
        """Parse select items with enhanced validation."""
        items = []
        while (self.parser.match(TokenType.WORD, TokenType.STRING) and
               not self.parser.match_any([TokenType.DO, TokenType.SEMICOLON, TokenType.NEWLINE])):
            token = self.parser.advance()
            items.append(token.value)
        return items
    
    def _parse_c_style_for_enhanced(self):
        """Parse C-style for loop with enhanced validation."""
        # Use existing C-style for parsing
        return self.parser.control_structures._parse_c_style_for()
    
    def _validate_for_variable(self, variable: str):
        """Validate for loop variable."""
        if not variable.isidentifier():
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Invalid variable name in for loop: {variable}"
                )
    
    def _validate_select_variable(self, variable: str):
        """Validate select loop variable."""
        if not variable.isidentifier():
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Invalid variable name in select: {variable}"
                )
    
    def _validate_break_continue_context(self, token):
        """Validate break/continue appears in loop context."""
        # This would require loop context tracking, which could be added
        # to the enhanced lexer context in the future
        pass
    
    def _attempt_if_error_recovery(self, if_token, error):
        """Attempt error recovery for if statement."""
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(
                f"Error in if statement starting at position {if_token.position}: {error}"
            )
    
    def _attempt_while_error_recovery(self, while_token, error):
        """Attempt error recovery for while loop."""
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(
                f"Error in while loop starting at position {while_token.position}: {error}"
            )
    
    def _attempt_for_error_recovery(self, for_token, error):
        """Attempt error recovery for for loop."""
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(
                f"Error in for loop starting at position {for_token.position}: {error}"
            )
    
    def _attempt_case_error_recovery(self, case_token, error):
        """Attempt error recovery for case statement."""
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(
                f"Error in case statement starting at position {case_token.position}: {error}"
            )
    
    def _attempt_select_error_recovery(self, select_token, error):
        """Attempt error recovery for select statement."""
        if hasattr(self.parser.ctx, 'add_warning'):
            self.parser.ctx.add_warning(
                f"Error in select statement starting at position {select_token.position}: {error}"
            )


def install_enhanced_control_structure_parser(parser):
    """Install enhanced control structure parser into existing parser."""
    if hasattr(parser, 'control_structures'):
        # Replace with enhanced version
        enhanced_control = EnhancedControlStructureParser(parser)
        
        # Add enhanced method while keeping original
        parser.control_structures.parse_control_structure_enhanced = enhanced_control.parse_control_structure_enhanced
        parser.control_structures._enhanced_parser = enhanced_control
        
        # Optionally replace main methods
        if hasattr(parser, 'enhanced_config') and parser.enhanced_config.use_enhanced_tokens:
            parser.control_structures.parse_control_structure_original = parser.control_structures._parse_control_structure
            parser.control_structures._parse_control_structure = enhanced_control.parse_control_structure_enhanced