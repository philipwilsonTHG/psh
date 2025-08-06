"""Command and pipeline parsers for the shell parser combinator.

This module provides parsers for simple commands, pipelines, and-or lists,
and statement lists - the core command structures in shell syntax.
"""

from typing import List, Optional, Tuple, Union
from ...token_types import Token, TokenType
from ...ast_nodes import (
    SimpleCommand, Pipeline, AndOrList, CommandList, StatementList,
    Redirect, Word, ASTNode,
    # Control structures for type checking
    IfConditional, WhileLoop, ForLoop, CaseConditional, SelectLoop,
    SubshellGroup, BraceGroup, CStyleForLoop, ArithmeticEvaluation,
    EnhancedTestStatement, FunctionDef, ArrayInitialization, ArrayElementAssignment
)
from ..config import ParserConfig
from .core import (
    Parser, ParseResult, ForwardParser,
    many, many1, optional, sequence, separated_by, token
)
from .tokens import TokenParsers
from .expansions import ExpansionParsers


class CommandParsers:
    """Parsers for shell commands and command structures.
    
    This class provides parsers for building the command hierarchy:
    simple commands -> pipelines -> and-or lists -> statement lists
    """
    
    def __init__(self, config: Optional[ParserConfig] = None,
                 token_parsers: Optional[TokenParsers] = None,
                 expansion_parsers: Optional[ExpansionParsers] = None):
        """Initialize command parsers.
        
        Args:
            config: Parser configuration
            token_parsers: Token parsers to use
            expansion_parsers: Expansion parsers to use
        """
        self.config = config or ParserConfig()
        self.tokens = token_parsers or TokenParsers()
        self.expansions = expansion_parsers or ExpansionParsers(self.config)
        
        # Forward declarations for recursive structures
        self.statement_forward = ForwardParser[Union[AndOrList, FunctionDef]]()
        self.statement_list_forward = ForwardParser[CommandList]()
        
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """Initialize all command-related parsers."""
        # Build redirection parser
        self.redirection = Parser(self._parse_redirection)
        
        # Build simple command parser
        self.simple_command = self._build_simple_command_parser()
        
        # Build pipeline parser
        self.pipeline = self._build_pipeline_parser()
        
        # Build and-or list parser
        self.and_or_list = self._build_and_or_list_parser()
        
        # Build statement parser
        self.statement = self._build_statement_parser()
        
        # Build statement list parser
        self.statement_list = self._build_statement_list_parser()
    
    def _parse_redirection(self, tokens: List[Token], pos: int) -> ParseResult[Redirect]:
        """Parse I/O redirection.
        
        Args:
            tokens: List of tokens
            pos: Current position
            
        Returns:
            ParseResult with Redirect node
        """
        # First try to parse a redirection operator
        op_result = self.tokens.redirect_operator.parse(tokens, pos)
        if not op_result.success:
            return ParseResult(success=False, error=op_result.error, position=pos)
        
        op_token = op_result.value
        pos = op_result.position
        
        # Handle redirect duplication (e.g., 2>&1, >&2, etc.)
        if op_token.type.name == 'REDIRECT_DUP':
            # REDIRECT_DUP tokens contain the full operator (e.g., "2>&1")
            return ParseResult(
                success=True,
                value=Redirect(type=op_token.value, target=''),
                position=pos
            )
        
        # Handle heredoc operators
        if op_token.type.name in ['HEREDOC', 'HEREDOC_STRIP']:
            # Parse delimiter
            if pos >= len(tokens):
                return ParseResult(
                    success=False,
                    error="Expected heredoc delimiter",
                    position=pos
                )
            
            delimiter_token = tokens[pos]
            delimiter = delimiter_token.value
            
            # Check if delimiter is quoted
            # Note: heredoc_quoted and heredoc_key are not part of the AST node
            # They would be handled by a separate heredoc processor
            
            return ParseResult(
                success=True,
                value=Redirect(
                    type=op_token.value,
                    target=delimiter,
                    # heredoc_content will be populated later by heredoc processor
                ),
                position=pos + 1
            )
        
        # Handle here string (<<<)
        if op_token.type.name == 'HERE_STRING':
            # Parse the content
            content_result = self.tokens.word_like.parse(tokens, pos)
            if not content_result.success:
                return ParseResult(
                    success=False,
                    error="Expected content after <<<",
                    position=pos
                )
            
            content_value = content_result.value.value if hasattr(content_result.value, 'value') else str(content_result.value)
            
            # Here strings are always treated as single-quoted (no expansion)
            return ParseResult(
                success=True,
                value=Redirect(
                    type=op_token.value,
                    target=content_value,
                    heredoc_content=content_value
                    # Note: heredoc_quoted would be True but it's not in the AST
                ),
                position=content_result.position
            )
        
        # Normal redirection - needs a target
        target_result = self.tokens.word_like.parse(tokens, pos)
        if not target_result.success:
            return ParseResult(
                success=False,
                error=f"Expected redirection target after {op_token.value}",
                position=pos
            )
        
        target_value = target_result.value.value if hasattr(target_result.value, 'value') else str(target_result.value)
        
        return ParseResult(
            success=True,
            value=Redirect(type=op_token.value, target=target_value),
            position=target_result.position
        )
    
    def _build_simple_command_parser(self) -> Parser[SimpleCommand]:
        """Build parser for simple commands.
        
        Returns:
            Parser that produces SimpleCommand nodes
        """
        def parse_simple_command(tokens: List[Token], pos: int) -> ParseResult[SimpleCommand]:
            """Parse a simple command with words and redirections."""
            # Parse one or more words
            words_result = many1(self.tokens.word_like).parse(tokens, pos)
            if not words_result.success:
                return ParseResult(success=False, error="Expected command", position=pos)
            
            word_tokens = words_result.value
            pos = words_result.position
            
            # Parse optional redirections
            redirects_result = many(self.redirection).parse(tokens, pos)
            redirects = redirects_result.value if redirects_result.success else []
            pos = redirects_result.position if redirects_result.success else pos
            
            # Parse optional background operator
            background_result = optional(self.tokens.ampersand).parse(tokens, pos)
            background = background_result.value is not None
            pos = background_result.position
            
            # Build the simple command
            cmd = self._build_simple_command(word_tokens, redirects, background)
            
            return ParseResult(
                success=True,
                value=cmd,
                position=pos
            )
        
        return Parser(parse_simple_command)
    
    def _build_simple_command(self, word_tokens: List[Token], 
                             redirects: List[Redirect], 
                             background: bool = False) -> SimpleCommand:
        """Build a SimpleCommand with proper token type and quote preservation.
        
        Args:
            word_tokens: List of word tokens
            redirects: List of redirections
            background: Whether command runs in background
            
        Returns:
            SimpleCommand AST node
        """
        cmd = SimpleCommand(redirects=redirects, background=background)
        
        # Build traditional string arguments
        cmd.args = [self.expansions.format_token_value(t) for t in word_tokens]
        
        # Build argument types and quote types (like recursive descent parser)
        cmd.arg_types = []
        cmd.quote_types = []
        for token in word_tokens:
            # Map token types to argument types
            if token.type.name == 'STRING':
                cmd.arg_types.append('STRING')
                cmd.quote_types.append(getattr(token, 'quote_type', None))
            elif token.type.name == 'WORD':
                cmd.arg_types.append('WORD')
                cmd.quote_types.append(None)
            elif token.type.name == 'VARIABLE':
                cmd.arg_types.append('VARIABLE')
                cmd.quote_types.append(None)
            else:
                # Other expansions
                cmd.arg_types.append(token.type.name)
                cmd.quote_types.append(None)
        
        # Build Word AST nodes if enabled
        if self.config.build_word_ast_nodes:
            cmd.words = []
            for token in word_tokens:
                word = self.expansions.build_word_from_token(token)
                cmd.words.append(word)
        
        return cmd
    
    def _build_pipeline_parser(self) -> Parser[Union[Pipeline, ASTNode]]:
        """Build parser for pipelines.
        
        Returns:
            Parser that produces Pipeline or unwrapped command nodes
        """
        # Note: We need a command parser first, but that includes control structures
        # For now, we'll use simple_command and expect control structures to be added later
        
        def build_pipeline(commands):
            """Build pipeline, but don't wrap single control structures."""
            if len(commands) == 1:
                # Single command - check if it's a control structure
                cmd = commands[0]
                if isinstance(cmd, (IfConditional, WhileLoop, ForLoop, CaseConditional, SelectLoop,
                                  SubshellGroup, BraceGroup, CStyleForLoop, ArithmeticEvaluation, 
                                  EnhancedTestStatement)):
                    # Don't wrap control structures in Pipeline when they're standalone
                    return cmd
            # Multiple commands or single simple command - wrap in Pipeline
            return Pipeline(commands=commands) if commands else None
        
        # For initial version, just use simple commands
        # Control structures will be added when we have a command parser that includes them
        pipeline_parser = separated_by(
            self.simple_command,
            self.tokens.pipe
        ).map(build_pipeline)
        
        return pipeline_parser
    
    def _build_and_or_list_parser(self) -> Parser[AndOrList]:
        """Build parser for and-or lists.
        
        Returns:
            Parser that produces AndOrList nodes
        """
        # And-or operator
        and_or_operator = self.tokens.and_if.or_else(self.tokens.or_if)
        
        # Parse pipeline followed by optional and/or operators and more pipelines
        and_or_parser = sequence(
            self.pipeline,
            many(sequence(and_or_operator, self.pipeline))
        ).map(self._build_and_or_list_from_parts)
        
        return and_or_parser
    
    def _build_and_or_list_from_parts(self, parse_result: tuple) -> AndOrList:
        """Build an AndOrList from parsed components.
        
        Args:
            parse_result: Tuple of (first_element, rest_pairs)
            
        Returns:
            AndOrList AST node
        """
        first_element = parse_result[0]
        rest = parse_result[1]  # List of (operator, element) pairs
        
        # Normalize first element to Pipeline if needed
        if isinstance(first_element, Pipeline):
            first_pipeline = first_element
        else:
            # Single command - add directly as pipeline element
            first_pipeline = first_element
        
        if not rest:
            # Single element with no operators - return it directly instead of wrapping
            # This prevents unnecessary AndOrList wrapping for standalone control structures
            if isinstance(first_pipeline, (IfConditional, WhileLoop, ForLoop, CaseConditional, SelectLoop,
                                         SubshellGroup, BraceGroup, CStyleForLoop, ArithmeticEvaluation, 
                                         EnhancedTestStatement)):
                return first_pipeline
            return AndOrList(pipelines=[first_pipeline])
        
        pipelines = [first_pipeline]
        operators = []
        
        for op_token, element in rest:
            operators.append(op_token.value)
            # Normalize element to Pipeline if needed
            if isinstance(element, Pipeline):
                pipelines.append(element)
            else:
                # Single command - add directly as pipeline element
                pipelines.append(element)
        
        return AndOrList(pipelines=pipelines, operators=operators)
    
    def _build_statement_parser(self) -> Parser[Union[AndOrList, FunctionDef]]:
        """Build parser for statements.
        
        Returns:
            Parser that produces statement nodes
        """
        # For now, just use and-or list
        # Function definitions and control structures will be added later
        return self.and_or_list
    
    def _build_statement_list_parser(self) -> Parser[CommandList]:
        """Build parser for statement lists.
        
        Returns:
            Parser that produces CommandList nodes
        """
        # Statement separator
        separator = self.tokens.semicolon.or_else(self.tokens.newline)
        separators = many1(separator)
        
        # Parse optional leading separators, statements separated by separators, and optional trailing separators
        statement_list_parser = sequence(
            optional(separators),  # Allow optional leading separators
            optional(
                separated_by(
                    self.statement,
                    separators
                )
            ),
            optional(separators)  # Allow optional trailing separators
        ).map(lambda triple: CommandList(statements=triple[1] if triple[1] else []))
        
        return statement_list_parser
    
    def set_command_parser(self, command_parser: Parser):
        """Set the command parser (includes control structures).
        
        This is called after control structures are initialized to break circular dependency.
        
        Args:
            command_parser: Parser that handles both simple commands and control structures
        """
        # Update pipeline parser to use full command parser
        def build_pipeline(commands):
            """Build pipeline, but don't wrap single control structures."""
            if len(commands) == 1:
                cmd = commands[0]
                if isinstance(cmd, (IfConditional, WhileLoop, ForLoop, CaseConditional, SelectLoop,
                                  SubshellGroup, BraceGroup, CStyleForLoop, ArithmeticEvaluation, 
                                  EnhancedTestStatement)):
                    return cmd
            return Pipeline(commands=commands) if commands else None
        
        self.pipeline = separated_by(
            command_parser,
            self.tokens.pipe
        ).map(build_pipeline)
        
        # Update and-or list parser
        and_or_element = self.pipeline.or_else(command_parser)
        and_or_operator = self.tokens.and_if.or_else(self.tokens.or_if)
        
        self.and_or_list = sequence(
            and_or_element,
            many(sequence(and_or_operator, and_or_element))
        ).map(self._build_and_or_list_from_parts)


# Convenience functions

def create_command_parsers(config: Optional[ParserConfig] = None,
                          token_parsers: Optional[TokenParsers] = None,
                          expansion_parsers: Optional[ExpansionParsers] = None) -> CommandParsers:
    """Create and return a CommandParsers instance.
    
    Args:
        config: Optional parser configuration
        token_parsers: Optional token parsers
        expansion_parsers: Optional expansion parsers
        
    Returns:
        Initialized CommandParsers object
    """
    return CommandParsers(config, token_parsers, expansion_parsers)


def parse_simple_command(tokens: TokenParsers, 
                         expansions: ExpansionParsers) -> Parser[SimpleCommand]:
    """Create parser for simple commands.
    
    Args:
        tokens: Token parsers
        expansions: Expansion parsers
        
    Returns:
        Parser that matches simple commands
    """
    cmd_parsers = CommandParsers(token_parsers=tokens, expansion_parsers=expansions)
    return cmd_parsers.simple_command


def parse_pipeline(command_parser: Parser) -> Parser[Union[Pipeline, ASTNode]]:
    """Create parser for pipelines.
    
    Args:
        command_parser: Parser for commands
        
    Returns:
        Parser that matches pipelines
    """
    def build_pipeline(commands):
        if len(commands) == 1:
            cmd = commands[0]
            if isinstance(cmd, (IfConditional, WhileLoop, ForLoop, CaseConditional, SelectLoop,
                              SubshellGroup, BraceGroup, CStyleForLoop, ArithmeticEvaluation, 
                              EnhancedTestStatement)):
                return cmd
        return Pipeline(commands=commands) if commands else None
    
    return separated_by(command_parser, token('PIPE')).map(build_pipeline)


def parse_and_or_list(pipeline_parser: Parser) -> Parser[AndOrList]:
    """Create parser for and-or lists.
    
    Args:
        pipeline_parser: Parser for pipelines
        
    Returns:
        Parser that matches and-or lists
    """
    and_or_operator = token('AND_AND').or_else(token('OR_OR'))
    
    def build_and_or(parts):
        first = parts[0]
        rest = parts[1]
        
        if not rest:
            if isinstance(first, (IfConditional, WhileLoop, ForLoop, CaseConditional, SelectLoop,
                                SubshellGroup, BraceGroup, CStyleForLoop, ArithmeticEvaluation, 
                                EnhancedTestStatement)):
                return first
            return AndOrList(pipelines=[first])
        
        pipelines = [first]
        operators = []
        for op, pipeline in rest:
            operators.append(op.value)
            pipelines.append(pipeline)
        
        return AndOrList(pipelines=pipelines, operators=operators)
    
    return sequence(
        pipeline_parser,
        many(sequence(and_or_operator, pipeline_parser))
    ).map(build_and_or)