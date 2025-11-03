"""Enhanced statement parsing using token metadata."""

from typing import Optional, Union, List
from ....token_types import TokenType
from ....token_types import Token
from ....token_enhanced import TokenContext, SemanticType
from ....lexer.keyword_defs import matches_keyword
from ....ast_nodes import (
    Statement, CommandList, AndOrList, Pipeline, StatementList,
    BreakStatement, ContinueStatement
)
from .base import EnhancedContextBaseParser, EnhancedParserConfig
from ..parsers.statements import StatementParser


class EnhancedStatementParser(StatementParser):
    """Enhanced statement parser leveraging token metadata."""
    
    def __init__(self, main_parser):
        """Initialize enhanced statement parser."""
        super().__init__(main_parser)
        
        # Check if main parser has enhanced capabilities
        self.enhanced_parser = isinstance(main_parser, EnhancedContextBaseParser)
        self.enhanced_config = getattr(main_parser, 'enhanced_config', None)
    
    def parse_statement_enhanced(self) -> Optional[Statement]:
        """Enhanced statement parsing using token metadata."""
        if not self.enhanced_parser:
            # Fallback to original implementation
            return self.parse_statement()
        
        # Skip whitespace and newlines
        self.parser.skip_newlines()
        
        if self.parser.at_end():
            return None
        
        current_token = self._get_current_enhanced_token()
        
        if not current_token:
            return None
        
        # Enhanced semantic analysis
        if (self.enhanced_config and 
            self.enhanced_config.enable_semantic_analysis and
            self.parser.semantic_analyzer):
            
            self._analyze_statement_context(current_token)
        
        # Check for function definition with enhanced validation
        if self._is_enhanced_function_definition():
            return self.parser.functions.parse_function_def()
        
        # Parse and_or_list with enhanced features
        return self.parse_and_or_list_enhanced()
    
    def parse_and_or_list_enhanced(self) -> Optional[AndOrList]:
        """Enhanced and/or list parsing."""
        if not self.enhanced_parser:
            return self.parse_and_or_list()
        
        # Parse first pipeline
        left = self.parse_pipeline_enhanced()
        if not left:
            return None
        
        # Check for && or || operators
        and_or_ops = []
        
        while self.parser.match(TokenType.AND_AND, TokenType.OR_OR):
            op_token = self._get_current_enhanced_token()
            
            # Enhanced operator validation
            if (self.enhanced_config and 
                self.enhanced_config.enable_context_validation):
                self._validate_and_or_operator(op_token)
            
            operator = self.parser.advance()
            right = self.parse_pipeline_enhanced()
            
            if not right:
                raise self.parser._error(f"Expected pipeline after '{operator.value}'")
            
            and_or_ops.append((operator.value, right))
        
        if not and_or_ops:
            # Single pipeline, not an and_or_list
            return left
        
        return AndOrList(
            left=left,
            operators_and_rights=and_or_ops,
            position=left.position if hasattr(left, 'position') else 0
        )
    
    def parse_pipeline_enhanced(self) -> Optional[Pipeline]:
        """Enhanced pipeline parsing."""
        if not self.enhanced_parser:
            return self.parse_pipeline()
        
        # Optional negation
        negated = False
        if self.parser.match(TokenType.BANG):
            negated_token = self._get_current_enhanced_token()
            
            # Enhanced validation for negation
            if (self.enhanced_config and 
                self.enhanced_config.enable_context_validation):
                self._validate_negation_context(negated_token)
            
            self.parser.advance()
            negated = True
        
        # Parse first command
        commands = []
        command = self._parse_command_or_control_structure_enhanced()
        
        if not command:
            if negated:
                raise self.parser._error("Expected command after '!'")
            return None
        
        commands.append(command)
        
        # Parse pipeline components
        while self.parser.match(TokenType.PIPE):
            pipe_token = self._get_current_enhanced_token()
            
            # Enhanced pipe validation
            if (self.enhanced_config and 
                self.enhanced_config.enable_semantic_validation):
                self._validate_pipe_semantics(pipe_token, commands[-1])
            
            self.parser.advance()  # consume '|'
            
            next_command = self._parse_command_or_control_structure_enhanced()
            if not next_command:
                raise self.parser._error("Expected command after '|'")
            
            commands.append(next_command)
        
        if len(commands) == 1 and not negated:
            # Single command, not a pipeline
            return commands[0]
        
        return Pipeline(
            commands=commands,
            negated=negated,
            position=commands[0].position if hasattr(commands[0], 'position') else 0
        )
    
    def parse_statement_list_enhanced(self) -> StatementList:
        """Enhanced statement list parsing."""
        if not self.enhanced_parser:
            return self.parse_statement_list()
        
        statements = []
        
        self.parser.skip_newlines()
        
        # Parse statements until we hit a terminator
        while not self._at_statement_list_end():
            statement = self.parse_statement_enhanced()
            
            if statement:
                statements.append(statement)
                
                # Enhanced statement analysis
                if (self.enhanced_config and 
                    self.enhanced_config.enable_semantic_analysis):
                    self._analyze_statement_in_context(statement)
            
            # Skip statement separators
            if self.parser.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                self.parser.advance()
                self.parser.skip_newlines()
            elif not self._at_statement_list_end():
                # We should have a separator or be at the end
                break
        
        return StatementList(statements=statements)
    
    def _get_current_enhanced_token(self) -> Optional[Token]:
        """Get current token as enhanced token."""
        if hasattr(self.parser, 'peek_enhanced'):
            return self.parser.peek_enhanced()
        
        # Fallback: convert basic token to enhanced
        token = self.parser.peek()
        if token and not isinstance(token, Token):
            return Token.from_token(token)
        return token
    
    def _is_enhanced_function_definition(self) -> bool:
        """Check for function definition using enhanced metadata."""
        current_token = self._get_current_enhanced_token()
        
        if not current_token:
            return False
        
        # Enhanced function detection using semantic type
        if current_token.metadata.semantic_type == SemanticType.KEYWORD:
            if matches_keyword(current_token, 'function'):
                return True
        
        # Check for pattern: WORD () or function WORD ()
        if current_token.type == TokenType.WORD:
            # Look ahead for parentheses
            if (self.parser.peek(1) and 
                self.parser.peek(1).type == TokenType.LPAREN and
                self.parser.peek(2) and 
                self.parser.peek(2).type == TokenType.RPAREN):
                return True
        
        return False
    
    def _parse_command_or_control_structure_enhanced(self):
        """Parse command or control structure with enhanced features."""
        current_token = self._get_current_enhanced_token()
        
        if not current_token:
            return None
        
        # Check for control structures using enhanced metadata
        if current_token.metadata.semantic_type == SemanticType.KEYWORD:
            control_keywords = {
                TokenType.IF, TokenType.WHILE, TokenType.UNTIL, TokenType.FOR, TokenType.CASE,
                TokenType.SELECT, TokenType.BREAK, TokenType.CONTINUE
            }
            
            if current_token.type in control_keywords:
                if hasattr(self.parser, 'control_structures'):
                    if hasattr(self.parser.control_structures, 'parse_control_structure_enhanced'):
                        return self.parser.control_structures.parse_control_structure_enhanced()
                    else:
                        return self.parser.control_structures._parse_control_structure()
        
        # Enhanced command parsing
        if hasattr(self.parser, 'commands'):
            if hasattr(self.parser.commands, 'parse_command_enhanced'):
                return self.parser.commands.parse_command_enhanced()
            else:
                return self.parser.commands.parse_command()
        
        return None
    
    def _analyze_statement_context(self, token: Token):
        """Analyze statement context for semantic issues."""
        # Check for suspicious patterns
        if token.value in ['rm', 'rmdir'] and token.metadata.semantic_type != SemanticType.BUILTIN:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Potentially destructive command: {token.value}"
                )
        
        # Check for common typos
        common_typos = {
            'ecoh': 'echo',
            'cta': 'cat',
            'sl': 'ls',
            'grpe': 'grep'
        }
        
        if token.value in common_typos:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Possible typo: '{token.value}' - did you mean '{common_typos[token.value]}'?"
                )
    
    def _validate_and_or_operator(self, op_token: Token):
        """Validate && or || operator context."""
        if not op_token:
            return
        
        # Check operator is in correct context
        if op_token.metadata.semantic_type != SemanticType.OPERATOR:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"'{op_token.value}' should be recognized as operator"
                )
    
    def _validate_negation_context(self, negation_token: Token):
        """Validate negation (!) context."""
        if not negation_token:
            return
        
        # Negation should be in command position
        if TokenContext.COMMAND_POSITION not in negation_token.metadata.contexts:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    "Negation '!' not in command position"
                )
    
    def _validate_pipe_semantics(self, pipe_token: Token, left_command):
        """Validate pipe semantics."""
        if not pipe_token:
            return
        
        # Check for pipes to commands that don't read stdin
        if hasattr(left_command, 'args') and left_command.args:
            right_token = self.parser.peek(1)
            if right_token and right_token.value in ['ls', 'echo']:
                if hasattr(self.parser.ctx, 'add_warning'):
                    self.parser.ctx.add_warning(
                        f"Pipe to '{right_token.value}' may not use stdin"
                    )
    
    def _analyze_statement_in_context(self, statement):
        """Analyze statement within its context."""
        # Check for unreachable code patterns
        if isinstance(statement, (BreakStatement, ContinueStatement)):
            # These should be in loop context (would need loop tracking to validate)
            pass
        
        # Check for complex pipeline patterns
        if isinstance(statement, Pipeline) and len(statement.commands) > 5:
            if hasattr(self.parser.ctx, 'add_warning'):
                self.parser.ctx.add_warning(
                    f"Complex pipeline with {len(statement.commands)} commands"
                )
    
    def _at_statement_list_end(self) -> bool:
        """Check if at end of statement list."""
        if self.parser.at_end():
            return True
        
        current = self.parser.peek()
        if not current:
            return True
        
        # Statement list terminators
        terminators = {
            TokenType.FI, TokenType.DONE, TokenType.ESAC, TokenType.RBRACE,
            TokenType.RPAREN, TokenType.EOF, TokenType.THEN, TokenType.ELSE,
            TokenType.ELIF, TokenType.DO
        }
        
        return current.type in terminators


def install_enhanced_statement_parser(parser):
    """Install enhanced statement parser into existing parser."""
    if hasattr(parser, 'statements'):
        # Replace with enhanced version
        enhanced_statements = EnhancedStatementParser(parser)
        
        # Add enhanced methods while keeping originals
        parser.statements.parse_statement_enhanced = enhanced_statements.parse_statement_enhanced
        parser.statements.parse_and_or_list_enhanced = enhanced_statements.parse_and_or_list_enhanced
        parser.statements.parse_pipeline_enhanced = enhanced_statements.parse_pipeline_enhanced
        parser.statements.parse_statement_list_enhanced = enhanced_statements.parse_statement_list_enhanced
        parser.statements._enhanced_parser = enhanced_statements
        
        # Optionally replace main methods
        if hasattr(parser, 'enhanced_config') and parser.enhanced_config.use_enhanced_tokens:
            parser.statements.parse_statement_original = parser.statements.parse_statement
            parser.statements.parse_statement = enhanced_statements.parse_statement_enhanced
