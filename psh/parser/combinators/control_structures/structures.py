"""Structure parsers for the shell parser combinator.

This module provides mixin parsers for function definitions, subshell
groups, and brace groups.
"""

from typing import List

from ....ast_nodes import (
    BraceGroup,
    FunctionDef,
    StatementList,
    SubshellGroup,
)
from ....lexer.keyword_defs import matches_keyword
from ....token_types import Token
from ..core import Parser, ParseResult, between, lazy


class StructureParserMixin:
    """Mixin providing structure parsers for ControlStructureParsers."""

    def _build_function_name(self) -> Parser[str]:
        """Parse a valid function name."""
        def parse_function_name(tokens: List[Token], pos: int) -> ParseResult[str]:
            """Parse and validate function name."""
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
                return ParseResult(success=False,
                                 error=f"Invalid function name: {name} (must start with letter or underscore)",
                                 position=pos)

            # Rest must be alphanumeric, underscore, or hyphen
            for char in name[1:]:
                if not (char.isalnum() or char in '_-'):
                    return ParseResult(success=False,
                                     error=f"Invalid function name: {name} (contains invalid character '{char}')",
                                     position=pos)

            # Check it's not a reserved word
            reserved = {'if', 'then', 'else', 'elif', 'fi', 'while', 'do', 'done',
                       'for', 'case', 'esac', 'function', 'in', 'select'}
            if name in reserved:
                return ParseResult(success=False,
                                 error=f"Reserved word cannot be function name: {name}",
                                 position=pos)

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
            # For function bodies, we need stricter parsing
            statements = []
            inner_pos = 0  # Position within body_tokens

            # Skip leading separators
            while inner_pos < len(body_tokens) and body_tokens[inner_pos].type.name in ['SEMICOLON', 'NEWLINE']:
                inner_pos += 1

            # Parse statements
            while inner_pos < len(body_tokens):
                # Try to parse a statement
                stmt_result = self.commands.statement.parse(body_tokens, inner_pos)
                if not stmt_result.success:
                    # Check if this is a real error or just end of statements
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
            """Parse POSIX function."""
            # Parse name
            name_result = self._build_function_name().parse(tokens, pos)
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
            """Parse function with keyword."""
            if pos >= len(tokens) or not matches_keyword(tokens[pos], 'function'):
                return ParseResult(success=False, error="Expected 'function' keyword", position=pos)
            pos += 1

            # Parse name
            name_result = self._build_function_name().parse(tokens, pos)
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
            """Parse function with keyword and parentheses."""
            if pos >= len(tokens) or not matches_keyword(tokens[pos], 'function'):
                return ParseResult(success=False, error="Expected 'function' keyword", position=pos)
            pos += 1

            # Parse name
            name_result = self._build_function_name().parse(tokens, pos)
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

    def _build_subshell_group(self) -> Parser[SubshellGroup]:
        """Build parser for subshell group (...) syntax."""
        return between(
            self.tokens.lparen,
            self.tokens.rparen,
            lazy(lambda: self.commands.statement_list)
        ).map(lambda statements: SubshellGroup(statements=statements))

    def _build_brace_group(self) -> Parser[BraceGroup]:
        """Build parser for brace group {...} syntax."""
        return between(
            self.tokens.lbrace,
            self.tokens.rbrace,
            lazy(lambda: self.commands.statement_list)
        ).map(lambda statements: BraceGroup(statements=statements))
