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
    CStyleForLoop, CaseItem, CasePattern, StatementList
)
from ...token_types import Token


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
        self._setup_forward_declarations()
        self._build_grammar()
        self._complete_forward_declarations()
    
    def _setup_forward_declarations(self):
        """Setup forward declarations for recursive grammar rules."""
        # These will be defined later to handle circular dependencies
        self.statement_list_forward = ForwardParser[CommandList]()
        self.command_forward = ForwardParser[Union[SimpleCommand, UnifiedControlStructure]]()
        self.statement_forward = ForwardParser[Union[SimpleCommand, UnifiedControlStructure]]()
    
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
        
        # Word-like tokens
        self.word_like = self.word.or_else(self.string)
        
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
        self.redirection = sequence(
            self.redirect_out.or_else(self.redirect_in).or_else(self.redirect_append),
            self.word_like
        ).map(lambda pair: Redirect(
            type=pair[0].value,
            target=pair[1].value
        ))
        
        # Simple command
        self.simple_command = sequence(
            many1(self.word_like),
            many(self.redirection)
        ).map(lambda pair: SimpleCommand(
            args=[t.value for t in pair[0]],
            redirects=pair[1]
        ))
        
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
        
        # Control structures
        self.control_structure = (
            self.if_statement
            .or_else(self.while_loop)
            .or_else(self.for_loop)
            .or_else(self.case_statement)
        )
        
        # Command is either simple command or control structure
        self.command = self.simple_command.or_else(self.control_structure)
        
        # Pipeline - now uses command instead of just simple_command
        self.pipeline = separated_by(
            self.command,
            self.pipe
        ).map(lambda commands: 
            Pipeline(commands=commands) if len(commands) > 1 
            else commands[0] if commands 
            else None
        )
        
        # And-or list
        self.and_or_operator = self.and_if.or_else(self.or_if)
        
        self.and_or_list = sequence(
            self.pipeline,
            many(sequence(self.and_or_operator, self.pipeline))
        ).map(self._build_and_or_list)
        
        # Statement separator
        self.separator = self.semicolon.or_else(self.newline)
        
        # Define the forward references now that all components are ready
        self.command_forward.define(self.command)
        
        # Statement list parser using forward declaration
        statement_list_parser = optional(
            separated_by(
                self.and_or_list,
                self.separator
            )
        ).map(lambda statements: CommandList(statements=statements if statements else []))
        
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
            while current_pos < len(tokens):
                token = tokens[current_pos]
                if token.type.name == 'THEN' and token.value == 'then':
                    break
                if token.type.name in ['SEMICOLON', 'NEWLINE']:
                    # Check if next token is 'then'
                    if (current_pos + 1 < len(tokens) and 
                        tokens[current_pos + 1].type.name == 'THEN'):
                        break
                condition_tokens.append(token)
                current_pos += 1
            
            if current_pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'then' in if statement", position=pos)
            
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
            
            # Parse the body (until elif/else/fi)
            body_tokens = []
            while current_pos < len(tokens):
                token = tokens[current_pos]
                if token.value in ['elif', 'else', 'fi']:
                    break
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
                
                # Parse else body (until 'fi')
                else_tokens = []
                while pos < len(tokens) and tokens[pos].value != 'fi':
                    else_tokens.append(tokens[pos])
                    pos += 1
                
                else_result = self.statement_list.parse(else_tokens, 0)
                if not else_result.success:
                    return ParseResult(success=False, error=f"Failed to parse else body: {else_result.error}", position=pos)
                else_part = else_result.value
            
            # Expect 'fi'
            if pos >= len(tokens) or tokens[pos].value != 'fi':
                return ParseResult(success=False, error="Expected 'fi' to close if statement", position=pos)
            
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
            
            # Parse the body (until 'done')
            body_tokens = []
            while pos < len(tokens) and tokens[pos].value != 'done':
                body_tokens.append(tokens[pos])
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close while loop", position=pos)
            
            body_result = self.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, error=f"Failed to parse while body: {body_result.error}", position=pos)
            
            pos += 1  # Skip 'done'
            
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
            
            # Parse the body (until 'done')
            body_tokens = []
            while pos < len(tokens) and tokens[pos].value != 'done':
                body_tokens.append(tokens[pos])
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close for loop", position=pos)
            
            body_result = self.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, error=f"Failed to parse for body: {body_result.error}", position=pos)
            
            pos += 1  # Skip 'done'
            
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
            
            # Parse the body (until 'done')
            body_tokens = []
            while pos < len(tokens) and tokens[pos].value != 'done':
                body_tokens.append(tokens[pos])
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected 'done' to close C-style for loop", position=pos)
            
            body_result = self.statement_list.parse(body_tokens, 0)
            if not body_result.success:
                return ParseResult(success=False, error=f"Failed to parse for body: {body_result.error}", position=pos)
            
            pos += 1  # Skip 'done'
            
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
            
            expr = tokens[pos].value
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