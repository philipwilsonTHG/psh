"""Example Parser Combinator implementation for shell parsing.

This module demonstrates how to implement a shell parser using
parser combinators, a functional approach to parsing.
"""

from typing import List, Optional, Union, Tuple, Callable, TypeVar, Generic
from dataclasses import dataclass
from functools import reduce

from ..abstract_parser import (
    AbstractShellParser, ParserCharacteristics, ParserType,
    ParseError
)
from ...ast_nodes import (
    TopLevel, CommandList, SimpleCommand, Pipeline, 
    AndOrList, ASTNode, Redirect, UnifiedControlStructure,
    IfConditional, WhileLoop, ForLoop, CaseConditional, 
    CStyleForLoop, CaseItem, CasePattern, StatementList,
    FunctionDef, Word, LiteralPart, ExpansionPart,
    VariableExpansion, CommandSubstitution, ParameterExpansion,
    ArithmeticExpansion
)
from ...token_types import Token, TokenType
from ..config import ParserConfig
from ..word_builder import WordBuilder


# Type variables for parser combinators
T = TypeVar('T')
U = TypeVar('U')


@dataclass
class ParseResult(Generic[T]):
    """Result of a parse operation."""
    success: bool
    value: Optional[T] = None
    remaining: List[Token] = None
    position: int = 0
    error: Optional[str] = None


class Parser(Generic[T]):
    """A parser combinator that produces values of type T."""
    
    def __init__(self, parse_fn: Callable[[List[Token], int], ParseResult[T]]):
        """Initialize with a parsing function."""
        self.parse_fn = parse_fn
    
    def parse(self, tokens: List[Token], position: int = 0) -> ParseResult[T]:
        """Execute the parser."""
        return self.parse_fn(tokens, position)
    
    def map(self, fn: Callable[[T], U]) -> 'Parser[U]':
        """Transform the result of this parser."""
        def mapped_parse(tokens: List[Token], pos: int) -> ParseResult[U]:
            result = self.parse(tokens, pos)
            if result.success:
                return ParseResult(
                    success=True,
                    value=fn(result.value),
                    remaining=result.remaining,
                    position=result.position
                )
            return ParseResult(success=False, error=result.error, position=pos)
        
        return Parser(mapped_parse)
    
    def then(self, next_parser: 'Parser[U]') -> 'Parser[Tuple[T, U]]':
        """Sequence this parser with another."""
        def sequence_parse(tokens: List[Token], pos: int) -> ParseResult[Tuple[T, U]]:
            first_result = self.parse(tokens, pos)
            if not first_result.success:
                return ParseResult(success=False, error=first_result.error, position=pos)
            
            second_result = next_parser.parse(tokens, first_result.position)
            if not second_result.success:
                return ParseResult(success=False, error=second_result.error, 
                                 position=first_result.position)
            
            return ParseResult(
                success=True,
                value=(first_result.value, second_result.value),
                position=second_result.position
            )
        
        return Parser(sequence_parse)
    
    def or_else(self, alternative: 'Parser[T]') -> 'Parser[T]':
        """Try this parser, or alternative if it fails."""
        def choice_parse(tokens: List[Token], pos: int) -> ParseResult[T]:
            result = self.parse(tokens, pos)
            if result.success:
                return result
            return alternative.parse(tokens, pos)
        
        return Parser(choice_parse)


# Basic combinators
def token(token_type: str) -> Parser[Token]:
    """Parse a specific token type."""
    def parse_token(tokens: List[Token], pos: int) -> ParseResult[Token]:
        if pos < len(tokens) and tokens[pos].type.name == token_type:
            return ParseResult(
                success=True,
                value=tokens[pos],
                position=pos + 1
            )
        error = f"Expected {token_type}"
        if pos < len(tokens):
            error += f", got {tokens[pos].type.name}"
        else:
            error += ", but reached end of input"
        return ParseResult(success=False, error=error, position=pos)
    
    return Parser(parse_token)


def many(parser: Parser[T]) -> Parser[List[T]]:
    """Parse zero or more occurrences."""
    def parse_many(tokens: List[Token], pos: int) -> ParseResult[List[T]]:
        results = []
        current_pos = pos
        
        while True:
            result = parser.parse(tokens, current_pos)
            if not result.success:
                break
            results.append(result.value)
            current_pos = result.position
        
        return ParseResult(
            success=True,
            value=results,
            position=current_pos
        )
    
    return Parser(parse_many)


def many1(parser: Parser[T]) -> Parser[List[T]]:
    """Parse one or more occurrences."""
    return parser.then(many(parser)).map(lambda pair: [pair[0]] + pair[1])


def optional(parser: Parser[T]) -> Parser[Optional[T]]:
    """Parse optionally."""
    def parse_optional(tokens: List[Token], pos: int) -> ParseResult[Optional[T]]:
        result = parser.parse(tokens, pos)
        if result.success:
            return result
        return ParseResult(success=True, value=None, position=pos)
    
    return Parser(parse_optional)


def sequence(*parsers: Parser) -> Parser[tuple]:
    """Parse a sequence of parsers."""
    def parse_sequence(tokens: List[Token], pos: int) -> ParseResult[tuple]:
        results = []
        current_pos = pos
        
        for parser in parsers:
            result = parser.parse(tokens, current_pos)
            if not result.success:
                return ParseResult(success=False, error=result.error, position=pos)
            results.append(result.value)
            current_pos = result.position
        
        return ParseResult(
            success=True,
            value=tuple(results),
            position=current_pos
        )
    
    return Parser(parse_sequence)


def separated_by(parser: Parser[T], separator: Parser) -> Parser[List[T]]:
    """Parse items separated by a separator."""
    def parse_separated(tokens: List[Token], pos: int) -> ParseResult[List[T]]:
        # Parse first item
        first = parser.parse(tokens, pos)
        if not first.success:
            # If we can't parse even one item, fail instead of returning empty list
            return ParseResult(success=False, error=first.error, position=pos)
        
        items = [first.value]
        current_pos = first.position
        
        # Parse remaining items
        while True:
            sep_result = separator.parse(tokens, current_pos)
            if not sep_result.success:
                break
            
            item_result = parser.parse(tokens, sep_result.position)
            if not item_result.success:
                break
            
            items.append(item_result.value)
            current_pos = item_result.position
        
        return ParseResult(
            success=True,
            value=items,
            position=current_pos
        )
    
    return Parser(parse_separated)


# Enhanced combinators for control structures
def lazy(parser_factory: Callable[[], Parser[T]]) -> Parser[T]:
    """Lazy evaluation for recursive grammars."""
    cache = [None]  # Use list for mutability
    
    def parse_lazy(tokens: List[Token], pos: int) -> ParseResult[T]:
        if cache[0] is None:
            cache[0] = parser_factory()
        return cache[0].parse(tokens, pos)
    
    return Parser(parse_lazy)


def between(open_p: Parser, close_p: Parser, content_p: Parser[T]) -> Parser[T]:
    """Parse content between delimiters."""
    def parse_between(tokens: List[Token], pos: int) -> ParseResult[T]:
        # Parse opening delimiter
        open_result = open_p.parse(tokens, pos)
        if not open_result.success:
            return ParseResult(success=False, error=f"Expected opening delimiter: {open_result.error}", position=pos)
        
        # Parse content
        content_result = content_p.parse(tokens, open_result.position)
        if not content_result.success:
            return ParseResult(success=False, error=f"Expected content: {content_result.error}", position=open_result.position)
        
        # Parse closing delimiter
        close_result = close_p.parse(tokens, content_result.position)
        if not close_result.success:
            return ParseResult(success=False, error=f"Expected closing delimiter: {close_result.error}", position=content_result.position)
        
        return ParseResult(
            success=True,
            value=content_result.value,
            position=close_result.position
        )
    
    return Parser(parse_between)


def skip(parser: Parser) -> Parser[None]:
    """Parse but discard result."""
    def parse_skip(tokens: List[Token], pos: int) -> ParseResult[None]:
        result = parser.parse(tokens, pos)
        if result.success:
            return ParseResult(success=True, value=None, position=result.position)
        return ParseResult(success=False, error=result.error, position=pos)
    
    return Parser(parse_skip)


def fail_with(msg: str) -> Parser[None]:
    """Parser that always fails with custom message."""
    def parse_fail(tokens: List[Token], pos: int) -> ParseResult[None]:
        return ParseResult(success=False, error=msg, position=pos)
    
    return Parser(parse_fail)


def try_parse(parser: Parser[T]) -> Parser[Optional[T]]:
    """Backtracking support - try parser without consuming on failure."""
    def parse_try(tokens: List[Token], pos: int) -> ParseResult[Optional[T]]:
        result = parser.parse(tokens, pos)
        if result.success:
            return ParseResult(success=True, value=result.value, position=result.position)
        # Return success with None, keeping original position
        return ParseResult(success=True, value=None, position=pos)
    
    return Parser(parse_try)


def keyword(kw: str) -> Parser[Token]:
    """Parse specific keyword ensuring word boundaries."""
    def parse_keyword(tokens: List[Token], pos: int) -> ParseResult[Token]:
        if pos >= len(tokens):
            return ParseResult(success=False, error=f"Expected keyword '{kw}' but reached end of input", position=pos)
        
        token = tokens[pos]
        # Check if it's a WORD with the keyword value OR a specific keyword token type
        kw_token_type = kw.upper()  # Keywords are uppercase in token types
        if ((token.type.name == 'WORD' and token.value == kw) or 
            (token.type.name == kw_token_type and token.value == kw)):
            return ParseResult(success=True, value=token, position=pos + 1)
        
        return ParseResult(success=False, error=f"Expected keyword '{kw}', got {token.value}", position=pos)
    
    return Parser(parse_keyword)


def literal(lit: str) -> Parser[Token]:
    """Parse specific literal value."""
    def parse_literal(tokens: List[Token], pos: int) -> ParseResult[Token]:
        if pos >= len(tokens):
            return ParseResult(success=False, error=f"Expected '{lit}' but reached end of input", position=pos)
        
        token = tokens[pos]
        if token.value == lit:
            return ParseResult(success=True, value=token, position=pos + 1)
        
        return ParseResult(success=False, error=f"Expected '{lit}', got {token.value}", position=pos)
    
    return Parser(parse_literal)


# Forward declaration support
class ForwardParser(Parser[T], Generic[T]):
    """Parser that can be defined later for handling circular references."""
    
    def __init__(self):
        """Initialize without a parser implementation."""
        self._parser: Optional[Parser[T]] = None
        super().__init__(self._parse_forward)
    
    def _parse_forward(self, tokens: List[Token], pos: int) -> ParseResult[T]:
        """Parse using the defined parser."""
        if self._parser is None:
            raise RuntimeError("ForwardParser used before being defined")
        return self._parser.parse(tokens, pos)
    
    def define(self, parser: Parser[T]) -> None:
        """Define the actual parser implementation."""
        self._parser = parser


def with_error_context(parser: Parser[T], context: str) -> Parser[T]:
    """Add context to parser errors for better debugging."""
    def contextualized_parse(tokens: List[Token], pos: int) -> ParseResult[T]:
        result = parser.parse(tokens, pos)
        if not result.success and result.error:
            result.error = f"{context}: {result.error}"
        return result
    
    return Parser(contextualized_parse)


class ParserCombinatorShellParser(AbstractShellParser):
    """Shell parser implementation using parser combinators.
    
    This demonstrates a functional approach to parsing where complex
    parsers are built by combining simple parsers.
    """
    
    def __init__(self):
        """Initialize the parser combinator implementation."""
        super().__init__()
        self.config = ParserConfig()  # Default config
        self._setup_forward_declarations()
        self._build_grammar()
        self._complete_forward_declarations()
    
    def _setup_forward_declarations(self):
        """Setup forward declarations for recursive grammar rules."""
        # These will be defined later to handle circular dependencies
        self.statement_list_forward = ForwardParser[CommandList]()
        self.command_forward = ForwardParser[Union[SimpleCommand, UnifiedControlStructure, FunctionDef]]()
        self.statement_forward = ForwardParser[Union[AndOrList, FunctionDef]]()
    
    def _complete_forward_declarations(self):
        """Complete the forward declarations after grammar is built."""
        # By this point, all the actual parsers are defined
        # No need to redefine - they're already set in _build_grammar
        pass
    
    def _build_grammar(self):
        """Build the shell grammar using combinators."""
        # Token parsers
        self.word = token('WORD')
        self.string = token('STRING')
        self.pipe = token('PIPE')
        self.semicolon = token('SEMICOLON')
        self.and_if = token('AND_IF').or_else(token('AND_AND'))
        self.or_if = token('OR_IF').or_else(token('OR_OR'))
        self.newline = token('NEWLINE')
        
        # Redirect parsers
        self.redirect_out = token('REDIRECT_OUT')
        self.redirect_in = token('REDIRECT_IN')
        self.redirect_append = token('REDIRECT_APPEND')
        self.redirect_err = token('REDIRECT_ERR')  # 2>
        self.redirect_err_append = token('REDIRECT_ERR_APPEND')  # 2>>
        self.redirect_dup = token('REDIRECT_DUP')  # >&, 2>&1
        
        # Background job parser
        self.ampersand = token('AMPERSAND')
        
        # Word-like tokens (including variables and expansions)
        self.variable = token('VARIABLE')
        self.param_expansion = token('PARAM_EXPANSION')
        self.command_sub = token('COMMAND_SUB')
        self.command_sub_backtick = token('COMMAND_SUB_BACKTICK')
        self.arith_expansion = token('ARITH_EXPANSION')
        
        # All expansion types
        self.expansion = (
            self.variable
            .or_else(self.param_expansion)
            .or_else(self.command_sub)
            .or_else(self.command_sub_backtick)
            .or_else(self.arith_expansion)
        )
        
        # Word-like tokens include words, strings, and all expansions
        self.word_like = (
            self.word
            .or_else(self.string)
            .or_else(self.expansion)
        )
        
        # EOF token
        self.eof = token('EOF')
        
        # Control structure keywords
        self.if_kw = keyword('if')
        self.then_kw = keyword('then')
        self.elif_kw = keyword('elif')
        self.else_kw = keyword('else')
        self.fi_kw = keyword('fi')
        self.while_kw = keyword('while')
        self.for_kw = keyword('for')
        self.in_kw = keyword('in')
        self.do_kw = keyword('do')
        self.done_kw = keyword('done')
        self.case_kw = keyword('case')
        self.esac_kw = keyword('esac')
        
        # Statement terminators
        self.statement_terminator = self.semicolon.or_else(self.newline)
        
        # Helper parsers for control structures
        self.do_separator = sequence(
            self.statement_terminator,
            skip(self.do_kw)
        ).map(lambda _: None)
        
        self.then_separator = sequence(
            self.statement_terminator,
            skip(self.then_kw)
        ).map(lambda _: None)
        
        # Redirection
        self.redirect_operator = (
            self.redirect_out
            .or_else(self.redirect_in)
            .or_else(self.redirect_append)
            .or_else(self.redirect_err)
            .or_else(self.redirect_err_append)
            .or_else(self.redirect_dup)
        )
        
        def parse_redirection(tokens: List[Token], pos: int) -> ParseResult[Redirect]:
            # First try normal redirection
            op_result = self.redirect_operator.parse(tokens, pos)
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
            
            # Normal redirection - needs a target
            target_result = self.word_like.parse(tokens, pos)
            if not target_result.success:
                return ParseResult(success=False, error=f"Expected redirection target after {op_token.value}", position=pos)
            
            return ParseResult(
                success=True,
                value=Redirect(type=op_token.value, target=target_result.value.value if hasattr(target_result.value, 'value') else str(target_result.value)),
                position=target_result.position
            )
        
        self.redirection = Parser(parse_redirection)
        
        # Simple command
        self.simple_command = sequence(
            many1(self.word_like),
            many(self.redirection),
            optional(self.ampersand)
        ).map(lambda triple: self._build_simple_command(triple[0], triple[1], background=triple[2] is not None))
        
        # Build function support
        self.function_name = self._build_function_name()
        self.function_def = with_error_context(
            self._build_function_def(),
            "In function definition"
        )
        
        # Build control structures with error context
        self.if_statement = with_error_context(
            self._build_if_statement(),
            "In if statement"
        )
        self.while_loop = with_error_context(
            self._build_while_loop(),
            "In while loop"
        )
        self.for_loop = with_error_context(
            self._build_for_loops(),
            "In for loop"
        )
        self.case_statement = with_error_context(
            self._build_case_statement(),
            "In case statement"
        )
        
        # Break and continue statements
        self.break_statement = self._build_break_statement()
        self.continue_statement = self._build_continue_statement()
        
        # Control structures
        self.control_structure = (
            self.if_statement
            .or_else(self.while_loop)
            .or_else(self.for_loop)
            .or_else(self.case_statement)
            .or_else(self.break_statement)
            .or_else(self.continue_statement)
        )
        
        # Command is either control structure or simple command (not function definitions)
        # Functions are only allowed at statement level
        self.command = self.control_structure.or_else(self.simple_command)
        
        # Pipeline - now uses command instead of just simple_command
        self.pipeline = separated_by(
            self.command,
            self.pipe
        ).map(lambda commands: 
            Pipeline(commands=commands) if commands 
            else None
        )
        
        # And-or list
        self.and_or_operator = self.and_if.or_else(self.or_if)
        
        self.and_or_list = sequence(
            self.pipeline,
            many(sequence(self.and_or_operator, self.pipeline))
        ).map(self._build_and_or_list)
        
        # Control structure or pipeline (for handling control structures as statements)
        # This allows control structures to appear as standalone statements without pipeline wrapping
        self.control_or_pipeline = (
            # Try control structure first
            self.control_structure.map(lambda cs: AndOrList(pipelines=[cs]))
            # Then try function definition
            .or_else(self.function_def.map(lambda fd: fd))
            # Finally fall back to normal and-or list
            .or_else(self.and_or_list)
        )
        
        # Statement separator
        self.separator = self.semicolon.or_else(self.newline)
        
        # Define the forward references now that all components are ready
        self.command_forward.define(self.command)
        
        # Statement uses control_or_pipeline instead of and_or_list
        self.statement = self.control_or_pipeline
        self.statement_forward.define(self.statement)
        
        # Statement list parser using forward declaration
        # We need to handle multiple separators (e.g., multiple newlines)
        self.separators = many1(self.separator)
        
        statement_list_parser = sequence(
            optional(self.separators),  # Allow optional leading separators
            optional(
                separated_by(
                    self.statement,
                    self.separators
                )
            ),
            optional(self.separators)  # Allow optional trailing separators
        ).map(lambda triple: CommandList(statements=triple[1] if triple[1] else []))
        
        self.statement_list_forward.define(statement_list_parser)
        self.statement_list = self.statement_list_forward
        
        # Top level parser
        self.top_level = self.statement_list
    
    def _build_and_or_list(self, parse_result: tuple) -> AndOrList:
        """Build an AndOrList from parsed components."""
        first_pipeline = parse_result[0]
        rest = parse_result[1]  # List of (operator, pipeline) pairs
        
        if not rest:
            return AndOrList(pipelines=[first_pipeline])
        
        pipelines = [first_pipeline]
        operators = []
        
        for op_token, pipeline in rest:
            operators.append(op_token.value)
            pipelines.append(pipeline)
        
        return AndOrList(pipelines=pipelines, operators=operators)
    
    def _build_if_statement(self) -> Parser[IfConditional]:
        """Build parser for if/then/elif/else/fi statements."""
        # Helper to parse a condition-then pair
        def parse_condition_then(tokens: List[Token], pos: int) -> ParseResult[Tuple[CommandList, CommandList]]:
            # Parse condition (statement list until 'then')
            condition_tokens = []
            current_pos = pos
            
            # Collect tokens until we see 'then'
            saw_separator = False
            while current_pos < len(tokens):
                token = tokens[current_pos]
                
                # Check if this is 'then' keyword (not just the word "then" in the condition)
                if token.value == 'then' and token.type.name in ['THEN', 'WORD']:
                    # 'then' must be preceded by a separator
                    if condition_tokens and not saw_separator:
                        # 'then' without separator is a syntax error
                        return ParseResult(success=False, error="Syntax error: expected ';' or newline before 'then'", position=current_pos)
                    break
                    
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    saw_separator = True
                    # Check if next token is 'then'
                    if (current_pos + 1 < len(tokens) and 
                        tokens[current_pos + 1].value == 'then'):
                        # Don't include the separator in condition tokens
                        break
                        
                condition_tokens.append(token)
                current_pos += 1
            
            if current_pos >= len(tokens):
                return ParseResult(success=False, error="Unexpected end of input: expected 'then' in if statement", position=pos)
            
            # Skip separator if we're at one
            if tokens[current_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                current_pos += 1
            
            # Verify we actually found 'then'
            if current_pos >= len(tokens) or tokens[current_pos].value != 'then':
                return ParseResult(success=False, error=f"Expected 'then' in if statement", position=current_pos)
            
            # Parse the condition
            condition_result = self.statement_list.parse(condition_tokens, 0)
            if not condition_result.success:
                return ParseResult(success=False, error=f"Failed to parse condition: {condition_result.error}", position=pos)
            
            # Skip separator and 'then'
            if tokens[current_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                current_pos += 1
            if current_pos >= len(tokens) or tokens[current_pos].value != 'then':
                return ParseResult(success=False, error="Expected 'then' after condition", position=current_pos)
            current_pos += 1  # Skip 'then'
            
            # Skip optional separator after 'then'
            if current_pos < len(tokens) and tokens[current_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                current_pos += 1
            
            # Parse the body (until elif/else/fi, handling nested if statements)
            body_tokens = []
            nesting_level = 0
            
            while current_pos < len(tokens):
                token = tokens[current_pos]
                
                # Track nested if statements
                if token.value == 'if':
                    nesting_level += 1
                    body_tokens.append(token)
                    current_pos += 1
                    continue
                    
                # Check for keywords that might end this body
                if token.value in ['elif', 'else', 'fi']:
                    if nesting_level == 0:
                        # This ends our current body
                        break
                    elif token.value == 'fi':
                        # This ends a nested if
                        nesting_level -= 1
                    body_tokens.append(token)
                    current_pos += 1
                    continue
                
                body_tokens.append(token)
                current_pos += 1
            
            body_result = self.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, error=f"Failed to parse then body: {body_result.error}", position=current_pos)
            
            return ParseResult(
                success=True,
                value=(condition_result.value, body_result.value),
                position=current_pos
            )
        
        # Main if statement parser
        def parse_if_statement(tokens: List[Token], pos: int) -> ParseResult[IfConditional]:
            # Check for 'if' keyword
            if pos >= len(tokens) or tokens[pos].value != 'if':
                return ParseResult(success=False, error="Expected 'if'", position=pos)
            
            pos += 1  # Skip 'if'
            
            # Parse main condition and then part
            main_result = parse_condition_then(tokens, pos)
            if not main_result.success:
                return ParseResult(success=False, error=main_result.error, position=pos)
            
            condition, then_part = main_result.value
            pos = main_result.position
            
            # Parse elif parts
            elif_parts = []
            while pos < len(tokens) and tokens[pos].value == 'elif':
                pos += 1  # Skip 'elif'
                elif_result = parse_condition_then(tokens, pos)
                if not elif_result.success:
                    return ParseResult(success=False, error=elif_result.error, position=pos)
                elif_parts.append(elif_result.value)
                pos = elif_result.position
            
            # Parse optional else part
            else_part = None
            if pos < len(tokens) and tokens[pos].value == 'else':
                pos += 1  # Skip 'else'
                
                # Skip optional separator after 'else'
                if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    pos += 1
                
                # Parse else body (until 'fi', handling nested if statements)
                else_tokens = []
                nesting_level = 0
                
                while pos < len(tokens):
                    token = tokens[pos]
                    
                    if token.value == 'if':
                        nesting_level += 1
                    elif token.value == 'fi':
                        if nesting_level == 0:
                            break
                        else:
                            nesting_level -= 1
                    
                    else_tokens.append(token)
                    pos += 1
                
                else_result = self.statement_list.parse(else_tokens, 0)
                if not else_result.success:
                    return ParseResult(success=False, error=f"Failed to parse else body: {else_result.error}", position=pos)
                else_part = else_result.value
            
            # Expect 'fi'
            if pos >= len(tokens):
                return ParseResult(success=False, error="Unexpected end of input: expected 'fi' to close if statement", position=pos)
            if tokens[pos].value != 'fi':
                return ParseResult(success=False, error=f"Expected 'fi' to close if statement, got '{tokens[pos].value}'", position=pos)
            
            pos += 1  # Skip 'fi'
            
            return ParseResult(
                success=True,
                value=IfConditional(
                    condition=condition,
                    then_part=then_part,
                    elif_parts=elif_parts,
                    else_part=else_part
                ),
                position=pos
            )
        
        return Parser(parse_if_statement)
    
    def _build_while_loop(self) -> Parser[WhileLoop]:
        """Build parser for while/do/done loops."""
        def parse_while_loop(tokens: List[Token], pos: int) -> ParseResult[WhileLoop]:
            # Check for 'while' keyword
            if pos >= len(tokens) or tokens[pos].value != 'while':
                return ParseResult(success=False, error="Expected 'while'", position=pos)
            
            pos += 1  # Skip 'while'
            
            # Parse condition (until 'do')
            condition_tokens = []
            while pos < len(tokens):
                token = tokens[pos]
                if token.type.name == 'DO' and token.value == 'do':
                    break
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    # Check if next token is 'do'
                    if (pos + 1 < len(tokens) and 
                        tokens[pos + 1].type.name == 'DO'):
                        break
                condition_tokens.append(token)
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'do' in while loop", position=pos)
            
            # Parse the condition
            condition_result = self.statement_list.parse(condition_tokens, 0)
            if not condition_result.success:
                return ParseResult(success=False, error=f"Failed to parse while condition: {condition_result.error}", position=pos)
            
            # Skip separator and 'do'
            if tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' after while condition", position=pos)
            pos += 1  # Skip 'do'
            
            # Skip optional separator after 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse the body (until 'done', handling nested loops)
            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')
            
            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close while loop", position=pos)
            
            body_result = self.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, error=f"Failed to parse while body: {body_result.error}", position=pos)
            
            pos = done_pos + 1  # Skip 'done'
            
            return ParseResult(
                success=True,
                value=WhileLoop(
                    condition=condition_result.value,
                    body=body_result.value
                ),
                position=pos
            )
        
        return Parser(parse_while_loop)
    
    def _build_for_loops(self) -> Parser[Union[ForLoop, CStyleForLoop]]:
        """Build parser for both traditional and C-style for loops."""
        # Try C-style first, then traditional
        return self._build_c_style_for_loop().or_else(self._build_traditional_for_loop())
    
    def _collect_tokens_until_keyword(self, tokens: List[Token], start_pos: int, 
                                     end_keyword: str, start_keyword: Optional[str] = None) -> Tuple[List[Token], int]:
        """Collect tokens until end keyword, handling nested structures.
        
        If start_keyword is provided, counts nesting levels.
        Returns (collected_tokens, position_after_end_keyword).
        """
        collected = []
        pos = start_pos
        nesting_level = 0
        
        while pos < len(tokens):
            token = tokens[pos]
            
            # Check for start keyword (increases nesting)
            if start_keyword and token.value == start_keyword:
                nesting_level += 1
                collected.append(token)
                pos += 1
                continue
            
            # Check for end keyword
            if token.value == end_keyword:
                if nesting_level == 0:
                    # Found our end keyword
                    return collected, pos
                else:
                    # This ends a nested structure
                    nesting_level -= 1
                    collected.append(token)
                    pos += 1
                    continue
            
            # Regular token
            collected.append(token)
            pos += 1
        
        # Reached end without finding end keyword
        return collected, pos
    
    def _build_traditional_for_loop(self) -> Parser[ForLoop]:
        """Build parser for traditional for/in loops."""
        def parse_for_loop(tokens: List[Token], pos: int) -> ParseResult[ForLoop]:
            # Check for 'for' keyword
            if pos >= len(tokens) or (tokens[pos].type.name != 'FOR' and tokens[pos].value != 'for'):
                return ParseResult(success=False, error="Expected 'for'", position=pos)
            
            pos += 1  # Skip 'for'
            
            # Parse variable name
            if pos >= len(tokens) or tokens[pos].type.name != 'WORD':
                return ParseResult(success=False, error="Expected variable name after 'for'", position=pos)
            
            var_name = tokens[pos].value
            pos += 1
            
            # Expect 'in'
            if pos >= len(tokens) or (tokens[pos].type.name != 'IN' and tokens[pos].value != 'in'):
                return ParseResult(success=False, error="Expected 'in' after variable name", position=pos)
            
            pos += 1  # Skip 'in'
            
            # Parse items (words until 'do' or separator+do)
            items = []
            while pos < len(tokens):
                token = tokens[pos]
                if token.type.name == 'DO' and token.value == 'do':
                    break
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    # Check if next token is 'do'
                    if (pos + 1 < len(tokens) and 
                        tokens[pos + 1].type.name == 'DO'):
                        break
                if token.type.name in ['WORD', 'STRING', 'VARIABLE']:
                    items.append(token.value)
                    pos += 1
                else:
                    break
            
            # Skip separator and 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' in for loop", position=pos)
            pos += 1  # Skip 'do'
            
            # Skip optional separator after 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse the body (until 'done', handling nested loops)
            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')
            
            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close for loop", position=pos)
            
            body_result = self.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, error=f"Failed to parse for body: {body_result.error}", position=pos)
            
            pos = done_pos + 1  # Skip 'done'
            
            return ParseResult(
                success=True,
                value=ForLoop(
                    variable=var_name,
                    items=items,
                    body=body_result.value
                ),
                position=pos
            )
        
        return Parser(parse_for_loop)
    
    def _build_c_style_for_loop(self) -> Parser[CStyleForLoop]:
        """Build parser for C-style for loops."""
        def parse_c_style_for(tokens: List[Token], pos: int) -> ParseResult[CStyleForLoop]:
            # Check for 'for' keyword
            if pos >= len(tokens) or (tokens[pos].type.name != 'FOR' and tokens[pos].value != 'for'):
                return ParseResult(success=False, error="Expected 'for'", position=pos)
            
            # Check for '((' after 'for'
            if pos + 1 >= len(tokens) or (tokens[pos + 1].type.name != 'DOUBLE_LPAREN' and tokens[pos + 1].value != '(('):
                return ParseResult(success=False, error="Not a C-style for loop", position=pos)
            
            pos += 2  # Skip 'for' and '(('
            
            # Handle special case of ';;' for empty init and condition
            if pos < len(tokens) and tokens[pos].type.name == 'DOUBLE_SEMICOLON':
                # Empty init and condition
                init_tokens = []
                cond_tokens = []
                pos += 1  # Skip ';;'
            else:
                # Parse init expression (until ';')
                init_tokens = []
                while pos < len(tokens) and tokens[pos].value != ';':
                    init_tokens.append(tokens[pos])
                    pos += 1
                
                if pos >= len(tokens):
                    return ParseResult(success=False, error="Expected ';' after init expression", position=pos)
                pos += 1  # Skip ';'
                
                # Parse condition expression (until ';')
                cond_tokens = []
                while pos < len(tokens) and tokens[pos].value != ';':
                    cond_tokens.append(tokens[pos])
                    pos += 1
                
                if pos >= len(tokens):
                    return ParseResult(success=False, error="Expected ';' after condition expression", position=pos)
                pos += 1  # Skip ';'
            
            # Parse update expression (until '))')
            update_tokens = []
            while pos < len(tokens) and tokens[pos].type.name != 'DOUBLE_RPAREN' and tokens[pos].value != '))':
                update_tokens.append(tokens[pos])
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected '))' to close C-style for", position=pos)
            pos += 1  # Skip '))'
            
            # Skip separator and 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            if pos >= len(tokens) or tokens[pos].value != 'do':
                return ParseResult(success=False, error="Expected 'do' after C-style for header", position=pos)
            pos += 1  # Skip 'do'
            
            # Skip optional separator after 'do'
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse the body (until 'done', handling nested loops)
            body_tokens, done_pos = self._collect_tokens_until_keyword(tokens, pos, 'done', 'do')
            
            if done_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close C-style for loop", position=pos)
            
            body_result = self.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, error=f"Failed to parse for body: {body_result.error}", position=pos)
            
            pos = done_pos + 1  # Skip 'done'
            
            # Convert token lists to strings
            init_expr = ' '.join(t.value for t in init_tokens) if init_tokens else None
            cond_expr = ' '.join(t.value for t in cond_tokens) if cond_tokens else None
            update_expr = ' '.join(t.value for t in update_tokens) if update_tokens else None
            
            return ParseResult(
                success=True,
                value=CStyleForLoop(
                    init_expr=init_expr,
                    condition_expr=cond_expr,
                    update_expr=update_expr,
                    body=body_result.value
                ),
                position=pos
            )
        
        return Parser(parse_c_style_for)
    
    def _build_case_statement(self) -> Parser[CaseConditional]:
        """Build parser for case/esac statements."""
        def parse_case_statement(tokens: List[Token], pos: int) -> ParseResult[CaseConditional]:
            # Check for 'case' keyword
            if pos >= len(tokens) or (tokens[pos].type.name != 'CASE' and tokens[pos].value != 'case'):
                return ParseResult(success=False, error="Expected 'case'", position=pos)
            
            pos += 1  # Skip 'case'
            
            # Parse expression (usually a variable or word)
            if pos >= len(tokens) or tokens[pos].type.name not in ['WORD', 'VARIABLE', 'STRING']:
                return ParseResult(success=False, error="Expected expression after 'case'", position=pos)
            
            # Format the expression appropriately
            token = tokens[pos]
            if token.type.name == 'VARIABLE':
                expr = self._format_token_value(token)
            else:
                expr = token.value
            pos += 1
            
            # Expect 'in'
            if pos >= len(tokens) or (tokens[pos].type.name != 'IN' and tokens[pos].value != 'in'):
                return ParseResult(success=False, error="Expected 'in' after case expression", position=pos)
            
            pos += 1  # Skip 'in'
            
            # Skip optional separator
            if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                pos += 1
            
            # Parse case items until 'esac'
            items = []
            while pos < len(tokens) and tokens[pos].value != 'esac':
                # Parse pattern(s)
                patterns = []
                
                # Parse first pattern
                if pos >= len(tokens) or tokens[pos].type.name not in ['WORD', 'STRING']:
                    break
                
                patterns.append(CasePattern(tokens[pos].value))
                pos += 1
                
                # Parse additional patterns separated by '|'
                while pos < len(tokens) and tokens[pos].value == '|':
                    pos += 1  # Skip '|'
                    if pos >= len(tokens) or tokens[pos].type.name not in ['WORD', 'STRING']:
                        return ParseResult(success=False, error="Expected pattern after '|'", position=pos)
                    patterns.append(CasePattern(tokens[pos].value))
                    pos += 1
                
                # Expect ')'
                if pos >= len(tokens) or tokens[pos].value != ')':
                    return ParseResult(success=False, error="Expected ')' after case pattern(s)", position=pos)
                
                pos += 1  # Skip ')'
                
                # Skip optional separator
                if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    pos += 1
                
                # Parse commands until case terminator
                command_tokens = []
                while pos < len(tokens):
                    token = tokens[pos]
                    # Check for case terminators
                    if token.type.name == 'DOUBLE_SEMICOLON' or token.value == ';;':
                        break
                    if token.value == ';&' or token.value == ';;&':
                        break
                    # Check if next token is a pattern (word followed by ')')
                    if (pos + 1 < len(tokens) and 
                        token.type.name in ['WORD', 'STRING'] and 
                        tokens[pos + 1].value == ')'):
                        break
                    # Check for 'esac'
                    if token.value == 'esac':
                        break
                    command_tokens.append(token)
                    pos += 1
                
                # Parse the commands
                if command_tokens:
                    commands_result = self.statement_list.parse(command_tokens, 0)
                    if not commands_result.success:
                        return ParseResult(success=False, error=f"Failed to parse case commands: {commands_result.error}", position=pos)
                    commands = commands_result.value
                else:
                    commands = CommandList(statements=[])
                
                # Get terminator
                terminator = ';;'  # Default
                if pos < len(tokens):
                    if tokens[pos].type.name == 'DOUBLE_SEMICOLON' or tokens[pos].value == ';;':
                        terminator = ';;'
                        pos += 1
                    elif tokens[pos].value == ';&':
                        terminator = ';&'
                        pos += 1
                    elif tokens[pos].value == ';;&':
                        terminator = ';;&'
                        pos += 1
                
                # Skip optional separator after terminator
                if pos < len(tokens) and tokens[pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    pos += 1
                
                # Create case item
                items.append(CaseItem(
                    patterns=patterns,
                    commands=commands,
                    terminator=terminator
                ))
            
            # Expect 'esac'
            if pos >= len(tokens) or tokens[pos].value != 'esac':
                return ParseResult(success=False, error="Expected 'esac' to close case statement", position=pos)
            
            pos += 1  # Skip 'esac'
            
            return ParseResult(
                success=True,
                value=CaseConditional(
                    expr=expr,
                    items=items
                ),
                position=pos
            )
        
        return Parser(parse_case_statement)
    
    def _build_function_name(self) -> Parser[str]:
        """Parse a valid function name."""
        def parse_function_name(tokens: List[Token], pos: int) -> ParseResult[str]:
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected function name", position=pos)
            
            token = tokens[pos]
            if token.type.name != 'WORD':
                return ParseResult(success=False, error="Expected function name", position=pos)
            
            # Validate function name (must start with letter or underscore)
            name = token.value
            if not name:
                return ParseResult(success=False, error="Empty function name", position=pos)
            
            # First character must be letter or underscore
            if not (name[0].isalpha() or name[0] == '_'):
                return ParseResult(success=False, error=f"Invalid function name: {name} (must start with letter or underscore)", position=pos)
            
            # Rest must be alphanumeric, underscore, or hyphen
            for char in name[1:]:
                if not (char.isalnum() or char in '_-'):
                    return ParseResult(success=False, error=f"Invalid function name: {name} (contains invalid character '{char}')", position=pos)
            
            # Check it's not a reserved word
            reserved = {'if', 'then', 'else', 'elif', 'fi', 'while', 'do', 'done', 
                       'for', 'case', 'esac', 'function', 'in', 'select'}
            if name in reserved:
                return ParseResult(success=False, error=f"Reserved word cannot be function name: {name}", position=pos)
            
            return ParseResult(success=True, value=name, position=pos + 1)
        
        return Parser(parse_function_name)
    
    def _parse_function_body(self, tokens: List[Token], pos: int) -> ParseResult[StatementList]:
        """Parse function body between { }."""
        # Expect {
        if pos >= len(tokens) or tokens[pos].value != '{':
            return ParseResult(success=False, error="Expected '{' to start function body", position=pos)
        outer_pos = pos + 1  # Track position in outer token stream
        
        # Skip optional newline after {
        if outer_pos < len(tokens) and tokens[outer_pos].type.name == 'NEWLINE':
            outer_pos += 1
        
        # Collect tokens until }
        body_tokens = []
        brace_count = 1
        
        while outer_pos < len(tokens) and brace_count > 0:
            token = tokens[outer_pos]
            if token.value == '{':
                brace_count += 1
            elif token.value == '}':
                brace_count -= 1
                if brace_count == 0:
                    break
            body_tokens.append(token)
            outer_pos += 1
        
        if brace_count > 0:
            return ParseResult(success=False, error="Unclosed function body", position=outer_pos)
        
        # Parse the body as a statement list
        if body_tokens:
            # For function bodies, we need stricter parsing that doesn't swallow errors
            # Try to parse statements directly without the optional wrapper
            statements = []
            inner_pos = 0  # Position within body_tokens
            
            # Skip leading separators
            while inner_pos < len(body_tokens) and body_tokens[inner_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                inner_pos += 1
            
            # Parse statements
            while inner_pos < len(body_tokens):
                # Try to parse a statement (which can be a pipeline, control structure, or function)
                stmt_result = self.control_or_pipeline.parse(body_tokens, inner_pos)
                if not stmt_result.success:
                    # Check if this is a real error or just end of statements
                    # If we have unparsed tokens, it's an error
                    if inner_pos < len(body_tokens):
                        error = stmt_result.error
                        if "expected 'fi'" in error.lower():
                            error = "Syntax error in function body: missing 'fi' to close if statement"
                        elif "expected 'done'" in error.lower():
                            error = "Syntax error in function body: missing 'done' to close loop"
                        elif "expected 'esac'" in error.lower():
                            error = "Syntax error in function body: missing 'esac' to close case statement"
                        elif "expected 'then'" in error.lower():
                            error = "Syntax error in function body: missing 'then' in if statement"
                        else:
                            error = f"Invalid function body: {error}"
                        return ParseResult(success=False, error=error, position=outer_pos)
                    break
                
                statements.append(stmt_result.value)
                inner_pos = stmt_result.position
                
                # Skip separators
                while inner_pos < len(body_tokens) and body_tokens[inner_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                    inner_pos += 1
            
            body_result = ParseResult(success=True, value=StatementList(statements=statements), position=inner_pos)
        else:
            # Empty body
            body_result = ParseResult(success=True, value=StatementList(statements=[]), position=0)
        
        outer_pos += 1  # Skip closing }
        
        return ParseResult(
            success=True,
            value=body_result.value,
            position=outer_pos
        )
    
    def _build_posix_function(self) -> Parser[FunctionDef]:
        """Parse POSIX-style function: name() { body }"""
        def parse_posix_function(tokens: List[Token], pos: int) -> ParseResult[FunctionDef]:
            # Parse name
            name_result = self.function_name.parse(tokens, pos)
            if not name_result.success:
                return ParseResult(success=False, error="Not a function definition", position=pos)
            
            name = name_result.value
            pos = name_result.position
            
            # Expect ()
            if pos + 1 >= len(tokens) or tokens[pos].value != '(' or tokens[pos + 1].value != ')':
                return ParseResult(success=False, error="Expected () after function name", position=pos)
            pos += 2
            
            # Skip optional whitespace/newlines
            while pos < len(tokens) and tokens[pos].type.name in ['NEWLINE']:
                pos += 1
            
            # Parse body
            body_result = self._parse_function_body(tokens, pos)
            if not body_result.success:
                return ParseResult(success=False, error=body_result.error, position=pos)
            
            return ParseResult(
                success=True,
                value=FunctionDef(name=name, body=body_result.value),
                position=body_result.position
            )
        
        return Parser(parse_posix_function)
    
    def _build_function_keyword_style(self) -> Parser[FunctionDef]:
        """Parse function keyword style: function name { body }"""
        def parse_function_keyword(tokens: List[Token], pos: int) -> ParseResult[FunctionDef]:
            # Check for 'function' keyword
            if pos >= len(tokens) or tokens[pos].value != 'function':
                return ParseResult(success=False, error="Expected 'function' keyword", position=pos)
            pos += 1
            
            # Parse name
            name_result = self.function_name.parse(tokens, pos)
            if not name_result.success:
                return ParseResult(success=False, error="Expected function name after 'function'", position=pos)
            
            name = name_result.value
            pos = name_result.position
            
            # Skip optional whitespace/newlines
            while pos < len(tokens) and tokens[pos].type.name in ['NEWLINE']:
                pos += 1
            
            # Parse body
            body_result = self._parse_function_body(tokens, pos)
            if not body_result.success:
                return ParseResult(success=False, error=body_result.error, position=pos)
            
            return ParseResult(
                success=True,
                value=FunctionDef(name=name, body=body_result.value),
                position=body_result.position
            )
        
        return Parser(parse_function_keyword)
    
    def _build_function_keyword_with_parens(self) -> Parser[FunctionDef]:
        """Parse function keyword with parentheses: function name() { body }"""
        def parse_function_with_parens(tokens: List[Token], pos: int) -> ParseResult[FunctionDef]:
            # Check for 'function' keyword
            if pos >= len(tokens) or tokens[pos].value != 'function':
                return ParseResult(success=False, error="Expected 'function' keyword", position=pos)
            pos += 1
            
            # Parse name
            name_result = self.function_name.parse(tokens, pos)
            if not name_result.success:
                return ParseResult(success=False, error="Expected function name after 'function'", position=pos)
            
            name = name_result.value
            pos = name_result.position
            
            # Expect ()
            if pos + 1 >= len(tokens) or tokens[pos].value != '(' or tokens[pos + 1].value != ')':
                return ParseResult(success=False, error="Expected () after function name", position=pos)
            pos += 2
            
            # Skip optional whitespace/newlines
            while pos < len(tokens) and tokens[pos].type.name in ['NEWLINE']:
                pos += 1
            
            # Parse body
            body_result = self._parse_function_body(tokens, pos)
            if not body_result.success:
                return ParseResult(success=False, error=body_result.error, position=pos)
            
            return ParseResult(
                success=True,
                value=FunctionDef(name=name, body=body_result.value),
                position=body_result.position
            )
        
        return Parser(parse_function_with_parens)
    
    def _build_function_def(self) -> Parser[FunctionDef]:
        """Build parser for function definitions."""
        # Try all three forms: POSIX first (most specific), then keyword variants
        return (
            self._build_posix_function()
            .or_else(self._build_function_keyword_with_parens())
            .or_else(self._build_function_keyword_style())
        )
    
    def _build_break_statement(self) -> Parser['BreakStatement']:
        """Build parser for break statement."""
        from ...ast_nodes import BreakStatement
        
        def parse_break(tokens: List[Token], pos: int) -> ParseResult[BreakStatement]:
            # Check for 'break' keyword
            if pos >= len(tokens) or tokens[pos].value != 'break':
                return ParseResult(success=False, error="Expected 'break'", position=pos)
            
            pos += 1  # Skip 'break'
            
            # Parse optional level (number)
            level = 1  # Default
            if pos < len(tokens) and tokens[pos].type.name == 'WORD':
                # Check if it's a number
                try:
                    level = int(tokens[pos].value)
                    pos += 1
                except ValueError:
                    pass  # Not a number, leave level as 1
            
            return ParseResult(
                success=True,
                value=BreakStatement(level=level),
                position=pos
            )
        
        return Parser(parse_break)
    
    def _build_continue_statement(self) -> Parser['ContinueStatement']:
        """Build parser for continue statement."""
        from ...ast_nodes import ContinueStatement
        
        def parse_continue(tokens: List[Token], pos: int) -> ParseResult[ContinueStatement]:
            # Check for 'continue' keyword
            if pos >= len(tokens) or tokens[pos].value != 'continue':
                return ParseResult(success=False, error="Expected 'continue'", position=pos)
            
            pos += 1  # Skip 'continue'
            
            # Parse optional level (number)
            level = 1  # Default
            if pos < len(tokens) and tokens[pos].type.name == 'WORD':
                # Check if it's a number
                try:
                    level = int(tokens[pos].value)
                    pos += 1
                except ValueError:
                    pass  # Not a number, leave level as 1
            
            return ParseResult(
                success=True,
                value=ContinueStatement(level=level),
                position=pos
            )
        
        return Parser(parse_continue)
    
    def parse(self, tokens: List[Token]) -> Union[TopLevel, CommandList]:
        """Parse tokens using parser combinators.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            Parsed AST
            
        Raises:
            ParseError: If parsing fails
        """
        self.reset_metrics()
        
        # Filter out EOF tokens
        tokens = [t for t in tokens if t.type.name != 'EOF']
        
        self.metrics.tokens_consumed = len(tokens)
        
        # Handle empty token list
        if not tokens:
            return CommandList(statements=[])
        
        result = self.top_level.parse(tokens, 0)
        
        if result.success:
            # Check if all tokens were consumed
            if result.position < len(tokens):
                token_value = tokens[result.position].value if result.position < len(tokens) else "EOF"
                raise ParseError(
                    f"Unexpected token at position {result.position}: {token_value}"
                )
            return result.value
        else:
            raise ParseError(result.error or "Parse failed")
    
    def parse_partial(self, tokens: List[Token]) -> Tuple[Optional[ASTNode], int]:
        """Parse as much as possible."""
        result = self.top_level.parse(tokens, 0)
        if result.success:
            return result.value, result.position
        return None, 0
    
    def can_parse(self, tokens: List[Token]) -> bool:
        """Check if tokens can be parsed."""
        try:
            result = self.top_level.parse(tokens, 0)
            return result.success and result.position == len(tokens)
        except Exception:
            return False
    
    def get_name(self) -> str:
        """Return parser name."""
        return "parser_combinator"
    
    def get_description(self) -> str:
        """Return parser description."""
        return (
            "Functional parser built from composable combinators. "
            "Demonstrates how complex parsers can be built by combining "
            "simple parsing primitives using functional composition."
        )
    
    def get_characteristics(self) -> ParserCharacteristics:
        """Return parser characteristics."""
        return ParserCharacteristics(
            parser_type=ParserType.PARSER_COMBINATOR,
            complexity="high",
            error_recovery=False,
            backtracking=True,
            memoization=False,  # Could be added
            left_recursion=False,
            ambiguity_handling="first",
            incremental=False,
            streaming=False,
            hand_coded=True,
            generated=False,
            functional=True
        )
    
    def _format_token_value(self, token: Token) -> str:
        """Format token value appropriately based on token type."""
        if token.type.name == 'VARIABLE':
            # Variables need the $ prefix
            return f"${token.value}"
        elif token.type.name in ['COMMAND_SUB', 'COMMAND_SUB_BACKTICK', 
                                 'ARITH_EXPANSION', 'PARAM_EXPANSION']:
            # These already include their delimiters
            return token.value
        else:
            # Everything else uses raw value
            return token.value
    
    def _build_simple_command(self, word_tokens: List[Token], redirects: List[Redirect], background: bool = False) -> SimpleCommand:
        """Build a SimpleCommand, optionally with Word AST nodes."""
        cmd = SimpleCommand(redirects=redirects, background=background)
        
        # Build traditional string arguments
        cmd.args = [self._format_token_value(t) for t in word_tokens]
        
        # Build Word AST nodes if enabled
        if self.config.build_word_ast_nodes:
            cmd.words = []
            for token in word_tokens:
                word = self._build_word_from_token(token)
                cmd.words.append(word)
        
        return cmd
    
    def _parse_command_substitution_content(self, cmd_str: str) -> bool:
        """Parse and validate command substitution content.
        
        Returns True if valid, False if it contains invalid constructs like function definitions.
        """
        try:
            # Re-tokenize the command substitution content
            from psh.lexer import tokenize
            sub_tokens = list(tokenize(cmd_str))
            
            # Check for function definitions at the start
            if len(sub_tokens) >= 2:
                # Check for function keyword
                if sub_tokens[0].type.name == 'FUNCTION':
                    return False
                # Check for name followed by parentheses
                if (sub_tokens[0].type.name == 'WORD' and 
                    len(sub_tokens) > 1 and sub_tokens[1].type.name == 'LPAREN'):
                    # This might be a function definition
                    # Look for closing paren and opening brace
                    for i in range(2, len(sub_tokens)):
                        if sub_tokens[i].type.name == 'RPAREN':
                            if i + 1 < len(sub_tokens) and sub_tokens[i + 1].type.name == 'LBRACE':
                                return False  # Function definition found
                            break
            
            # Parse the content to ensure it's valid
            result = self.statement_list.parse(sub_tokens, 0)
            return result.success
        except:
            # If tokenization or parsing fails, consider it invalid
            return False
    
    def _build_word_from_token(self, token: Token) -> Word:
        """Build a Word AST node from a token."""
        # Use TokenType enum values
        if token.type.name == 'STRING':
            # String token - check for quote type
            quote_type = getattr(token, 'quote_type', None)
            return Word(parts=[LiteralPart(token.value)], quote_type=quote_type)
        elif token.type.name == 'VARIABLE':
            # Variable expansion
            expansion = VariableExpansion(token.value)
            return Word(parts=[ExpansionPart(expansion)])
        elif token.type.name == 'COMMAND_SUB':
            # Command substitution $(...)
            # Extract command from $(...)
            cmd = token.value[2:-1] if token.value.startswith('$(') and token.value.endswith(')') else token.value
            
            # Validate the command substitution content
            if not self._parse_command_substitution_content(cmd):
                raise ParseError(f"Invalid command substitution: {token.value}")
            
            expansion = CommandSubstitution(cmd, backtick_style=False)
            return Word(parts=[ExpansionPart(expansion)])
        elif token.type.name == 'COMMAND_SUB_BACKTICK':
            # Backtick command substitution
            # Extract command from `...`
            cmd = token.value[1:-1] if token.value.startswith('`') and token.value.endswith('`') else token.value
            
            # Validate the command substitution content
            if not self._parse_command_substitution_content(cmd):
                raise ParseError(f"Invalid command substitution: {token.value}")
            
            expansion = CommandSubstitution(cmd, backtick_style=True)
            return Word(parts=[ExpansionPart(expansion)])
        elif token.type.name == 'ARITH_EXPANSION':
            # Arithmetic expansion $((...))]
            # Extract expression from $((...))
            expr = token.value[3:-2] if token.value.startswith('$((') and token.value.endswith('))') else token.value
            expansion = ArithmeticExpansion(expr)
            return Word(parts=[ExpansionPart(expansion)])
        elif token.type.name == 'PARAM_EXPANSION':
            # Parameter expansion - use WordBuilder to parse
            expansion = WordBuilder.parse_expansion_token(token)
            return Word(parts=[ExpansionPart(expansion)])
        else:
            # Regular word token
            return Word(parts=[LiteralPart(token.value)])
    
    def explain_parse(self, tokens: List[Token]) -> str:
        """Explain parser combinator parsing."""
        return """
=== Parser Combinator Parsing ===

Parser combinators build complex parsers from simple ones:

1. Basic parsers recognize tokens:
   - token('WORD') matches a WORD token
   - token('PIPE') matches a pipe operator

2. Combinators combine parsers:
   - sequence(p1, p2) matches p1 then p2
   - p1.or_else(p2) tries p1, then p2 if p1 fails
   - many(p) matches zero or more occurrences
   - separated_by(p, sep) matches p separated by sep

3. Transformers build AST:
   - parser.map(fn) transforms parse results
   - Results are composed into AST nodes

Example for 'echo hello | grep world':
  1. simple_command parses 'echo hello'
  2. pipe token matches '|'
  3. simple_command parses 'grep world'
  4. pipeline combinator builds Pipeline AST

Key advantages:
- Composable and reusable
- Grammar closely matches implementation
- Easy to test individual parsers
- Natural backtracking support
"""