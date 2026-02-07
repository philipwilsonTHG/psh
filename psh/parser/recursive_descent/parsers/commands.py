"""
Command parsing for PSH shell.

This module handles parsing of commands, pipelines, and command arguments.
"""

from typing import Optional, Tuple, Union

from ....ast_nodes import (
    AndOrList,
    ArithmeticEvaluation,
    BraceGroup,
    BreakStatement,
    CaseConditional,
    Command,
    ContinueStatement,
    CStyleForLoop,
    ExecutionContext,
    ForLoop,
    IfConditional,
    Pipeline,
    SelectLoop,
    SimpleCommand,
    Statement,
    SubshellGroup,
    UntilLoop,
    WhileLoop,
)
from ....token_stream import TokenStream
from ....token_types import Token, TokenType
from ..helpers import ErrorContext, ParseError, TokenGroups


class CommandParser:
    """Parser for command-level constructs."""

    def __init__(self, main_parser):
        """Initialize with reference to main parser."""
        self.parser = main_parser

    def _is_fd_duplication(self, value: str) -> bool:
        """Check if a WORD token is actually a file descriptor duplication."""
        import re
        # Patterns: >&N, <&N, N>&M, N<&M, >&-, <&-
        fd_dup_pattern = re.compile(r'^(\d*)[><]&(-|\d+)$')
        return bool(fd_dup_pattern.match(value))

    def _check_for_unclosed_expansions(self, token: Token) -> None:
        """Check if a token contains unclosed expansions and raise appropriate errors."""
        # Check tokens that might contain expansions
        if token.type not in [TokenType.WORD, TokenType.COMPOSITE, TokenType.COMMAND_SUB,
                              TokenType.COMMAND_SUB_BACKTICK, TokenType.ARITH_EXPANSION, TokenType.VARIABLE,
                              TokenType.PARAM_EXPANSION]:
            return

        # Import RichToken to check if token has parts
        from ....lexer.token_parts import RichToken

        # If it's a RichToken, check its parts for unclosed expansions
        if isinstance(token, RichToken) and token.parts:
            for part in token.parts:
                if part.expansion_type and part.expansion_type.endswith('_unclosed'):
                    # Determine the type of unclosed expansion
                    if part.expansion_type == 'parameter_unclosed':
                        error_msg = f"Syntax error: unclosed parameter expansion '${{{part.value[2:]}'"
                    elif part.expansion_type == 'command_unclosed':
                        error_msg = f"Syntax error: unclosed command substitution '$({part.value[2:]}'"
                    elif part.expansion_type == 'arithmetic_unclosed':
                        error_msg = f"Syntax error: unclosed arithmetic expansion '$(({part.value[3:]}'"
                    elif part.expansion_type == 'backtick_unclosed':
                        error_msg = f"Syntax error: unclosed backtick substitution '`{part.value[1:]}'"
                    else:
                        error_msg = f"Syntax error: unclosed expansion '{part.value}'"

                    # Create error context with token position
                    error_context = ErrorContext(
                        token=token,
                        message=error_msg,
                        position=token.position
                    )
                    raise ParseError(error_context)

        # Also check for specific token types that indicate unclosed expansions
        if token.type == TokenType.COMMAND_SUB and not token.value.endswith(')'):
            error_msg = f"Syntax error: unclosed command substitution '{token.value}'"
            error_context = ErrorContext(
                token=token,
                message=error_msg,
                position=token.position
            )
            raise ParseError(error_context)
        elif token.type == TokenType.COMMAND_SUB_BACKTICK and token.value.count('`') == 1:
            error_msg = f"Syntax error: unclosed backtick substitution '{token.value}'"
            error_context = ErrorContext(
                token=token,
                message=error_msg,
                position=token.position
            )
            raise ParseError(error_context)
        elif token.type == TokenType.ARITH_EXPANSION and not token.value.endswith('))'):
            error_msg = f"Syntax error: unclosed arithmetic expansion '{token.value}'"
            error_context = ErrorContext(
                token=token,
                message=error_msg,
                position=token.position
            )
            raise ParseError(error_context)
        elif token.type == TokenType.VARIABLE and token.value.startswith('${') and not token.value.endswith('}'):
            error_msg = f"Syntax error: unclosed parameter expansion '{token.value}'"
            error_context = ErrorContext(
                token=token,
                message=error_msg,
                position=token.position
            )
            raise ParseError(error_context)

    def parse_command(self) -> SimpleCommand:
        """Parse a single command with its arguments and redirections."""
        command = SimpleCommand()
        command.words = []

        # Validate command start
        self._validate_command_start()

        # Parse all arguments and redirections
        self._parse_command_elements(command)

        # Check for background execution
        if self.parser.consume_if_match(TokenType.AMPERSAND):
            command.background = True

        return command

    def _validate_command_start(self) -> None:
        """Validate that we're at a valid command start position."""
        # Check for unexpected tokens
        if self.parser.match_any(TokenGroups.CASE_TERMINATORS):
            error_context = ErrorContext(
                token=self.parser.peek(),
                message=f"Syntax error near unexpected token '{self.parser.peek().value}'",
                position=self.parser.peek().position
            )
            raise ParseError(error_context)

        # Ensure we have at least one word-like token
        if not self.parser.match_any(TokenGroups.WORD_LIKE):
            raise self.parser._error("Expected command")

    def _parse_command_elements(self, command: SimpleCommand) -> None:
        """Parse arguments, redirections, and array assignments for a command."""
        has_parsed_regular_args = False

        while (self.parser.match_any(TokenGroups.WORD_LIKE | TokenGroups.REDIRECTS) or
               (command.args and len(command.args) > 0 and
                command.args[0] in ('test', '[') and
                self.parser.match(TokenType.EXCLAMATION))):

            if self.parser.match_any(TokenGroups.REDIRECTS):
                redirect = self.parser.redirections.parse_redirect()
                command.redirects.append(redirect)

            elif self.parser.match(TokenType.WORD) and self._is_fd_duplication(self.parser.peek().value):
                redirect = self.parser.redirections.parse_fd_dup_word()
                command.redirects.append(redirect)

            elif self.parser.match(TokenType.EXCLAMATION):
                token = self.parser.advance()
                command.args.append(token.value)
                from ....ast_nodes import LiteralPart, Word
                command.words.append(Word(parts=[LiteralPart(token.value)]))
                has_parsed_regular_args = True

            else:
                # Only check for array assignments if no regular args parsed yet
                if not has_parsed_regular_args and self.parser.arrays.is_array_assignment():
                    array_assignment = self.parser.arrays.parse_array_assignment()
                    command.array_assignments.append(array_assignment)
                else:
                    has_parsed_regular_args = self._parse_argument(
                        command, has_parsed_regular_args
                    )

    def _parse_argument(self, command: SimpleCommand,
                       has_parsed_regular_args: bool) -> bool:
        """Parse a single argument, handling array initialization specially.

        Returns:
            True if a regular argument was parsed (updates has_parsed_regular_args)
        """
        # Check for array initialization syntax: arr=(...) or arr = (...)
        is_array_init, word_token = self._check_array_initialization()

        if is_array_init:
            arg_value = self._parse_array_initialization(word_token)
            command.args.append(arg_value)
            from ....ast_nodes import LiteralPart, Word
            command.words.append(Word(parts=[LiteralPart(arg_value)]))
            return True

        # Parse argument as Word AST node
        word = self.parse_argument_as_word()
        command.words.append(word)
        # Use inner content for args (without surrounding quotes)
        inner = ''.join(str(part) for part in word.parts)
        command.args.append(inner)

        return True

    def _check_array_initialization(self) -> Tuple[bool, Optional[Token]]:
        """Check if current position is array initialization syntax.

        Returns:
            Tuple of (is_array_init, word_token)
        """
        if not self.parser.match(TokenType.WORD):
            return False, None

        word_token = self.parser.peek()

        # Old lexer pattern: arr=(...)
        if (word_token.value.endswith('=') and
            self.parser.peek_ahead(1) and
            self.parser.peek_ahead(1).type == TokenType.LPAREN):
            self.parser.advance()
            return True, word_token

        # New lexer pattern: arr = (...)
        if (self.parser.peek_ahead(1) and
            self.parser.peek_ahead(1).type == TokenType.WORD and
            self.parser.peek_ahead(1).value == '=' and
            self.parser.peek_ahead(2) and
            self.parser.peek_ahead(2).type == TokenType.LPAREN):
            word_token = self.parser.advance()
            self.parser.advance()  # consume =
            return True, word_token

        return False, None

    def _parse_array_initialization(self, word_token: Token) -> str:
        """Parse array initialization syntax arr=(...).

        Args:
            word_token: The array variable name token

        Returns:
            Complete array initialization string like "arr=(elem1 elem2)"
        """
        self.parser.advance()  # consume LPAREN

        elements = []
        element_start_pos = self.parser.current

        while not self.parser.match(TokenType.RPAREN) and not self.parser.at_end():
            if self.parser.match_any(TokenGroups.WORD_LIKE):
                self.parse_composite_argument()  # consume element

                # Reconstruct original representation
                element_end_pos = self.parser.current
                original_tokens = self.parser.tokens[element_start_pos:element_end_pos]

                original_repr_parts = []
                for token in original_tokens:
                    if token.type == TokenType.STRING and token.quote_type:
                        original_repr_parts.append(token.quote_type + token.value + token.quote_type)
                    else:
                        original_repr_parts.append(token.value)

                elements.append(''.join(original_repr_parts))
                element_start_pos = self.parser.current
            else:
                raise self.parser._error("Expected array element")

        if not self.parser.consume_if_match(TokenType.RPAREN):
            raise self.parser._error("Expected ')' to close array initialization")

        # Build complete argument
        if word_token.value.endswith('='):
            return word_token.value + '(' + ' '.join(elements) + ')'
        else:
            return word_token.value + '=(' + ' '.join(elements) + ')'

    def parse_pipeline(self) -> Pipeline:
        """Parse a pipeline (commands connected by |)."""
        pipeline = Pipeline()

        # Check for leading ! (negation)
        if self.parser.consume_if_match(TokenType.EXCLAMATION):
            pipeline.negated = True

        # Parse first command (could be simple or compound)
        command = self.parse_pipeline_component()
        pipeline.commands.append(command)

        # Parse additional piped commands
        while self.parser.match(TokenType.PIPE):
            self.parser.advance()
            command = self.parse_pipeline_component()
            pipeline.commands.append(command)

        return pipeline


    def parse_pipeline_with_initial_component(self, initial_component: Command) -> Statement:
        """Parse a pipeline starting with an already-parsed component."""
        # Set the initial component to pipeline context
        initial_component.execution_context = ExecutionContext.PIPELINE

        # Create pipeline and add initial component
        pipeline = Pipeline()
        pipeline.commands.append(initial_component)

        # Must have at least one pipe since we were called due to seeing a pipe
        self.parser.expect(TokenType.PIPE)

        # Parse remaining pipeline components
        while True:
            command = self.parse_pipeline_component()
            pipeline.commands.append(command)

            if not self.parser.match(TokenType.PIPE):
                break
            self.parser.advance()

        # Wrap pipeline in AndOrList for consistency
        and_or_list = AndOrList()
        and_or_list.pipelines.append(pipeline)

        # Check for && or || continuation
        while self.parser.match(TokenType.AND_AND, TokenType.OR_OR):
            operator = self.parser.advance()
            and_or_list.operators.append(operator.value)

            self.parser.skip_newlines()
            pipeline = self.parse_pipeline()
            and_or_list.pipelines.append(pipeline)

        return and_or_list

    def parse_pipeline_component(self) -> Command:
        """Parse a single component of a pipeline (simple or compound command)."""
        # Try parsing as control structure first
        if self.parser.match(TokenType.WHILE):
            return self.parse_while_command()
        elif self.parser.match(TokenType.UNTIL):
            return self.parse_until_command()
        elif self.parser.match(TokenType.FOR):
            return self.parse_for_command()
        elif self.parser.match(TokenType.IF):
            return self.parse_if_command()
        elif self.parser.match(TokenType.CASE):
            return self.parse_case_command()
        elif self.parser.match(TokenType.SELECT):
            return self.parse_select_command()
        elif self.parser.match(TokenType.DOUBLE_LPAREN):
            return self.parse_arithmetic_compound_command()
        elif self.parser.match(TokenType.DOUBLE_LBRACKET):
            return self.parser.tests.parse_enhanced_test_statement()
        elif self.parser.match(TokenType.BREAK):
            return self.parse_break_statement()
        elif self.parser.match(TokenType.CONTINUE):
            return self.parse_continue_statement()
        elif self.parser.match(TokenType.LPAREN):
            # Check for bash-incompatible syntax: escaped dollar followed by parenthesis
            # This is a syntax error in bash: echo \$(echo test), echo \\\$(echo test)
            if self.parser.current > 0:
                prev_token = self.parser.tokens[self.parser.current - 1]
                if (prev_token.type == TokenType.WORD and
                    prev_token.value.endswith('\\$')):
                    # Check if it's truly an escaped dollar (odd number of backslashes before $)
                    # Count trailing backslashes before the $
                    num_backslashes = 0
                    for i in range(len(prev_token.value) - 2, -1, -1):
                        if prev_token.value[i] == '\\':
                            num_backslashes += 1
                        else:
                            break

                    # If odd number of backslashes, the $ is escaped
                    if num_backslashes % 2 == 1:
                        # This matches bash behavior which treats \$( as a syntax error
                        error_context = ErrorContext(
                            token=self.parser.peek(),
                            message="syntax error near unexpected token '('",
                            position=self.parser.peek().position
                        )
                        raise ParseError(error_context)
            return self.parse_subshell_group()
        elif self.parser.match(TokenType.LBRACE):
            return self.parse_brace_group()
        else:
            # Fall back to simple command
            return self.parse_command()

    def parse_composite_argument(self) -> Tuple[str, str, Optional[str]]:
        """Parse a potentially composite argument (concatenated tokens)."""
        # If current token is already a COMPOSITE, just return it
        if self.parser.peek() and self.parser.peek().type == TokenType.COMPOSITE:
            token = self.parser.advance()
            return self._token_to_argument(token)

        # Otherwise, check for adjacent tokens forming a composite
        # Create TokenStream to check for composite
        stream = TokenStream(self.parser.tokens, self.parser.current)
        composite = stream.peek_composite_sequence()

        if composite:
            # Process composite tokens
            parts = []
            has_quoted_part = False

            for token in composite:
                # Check for unclosed expansions in composite parts
                self._check_for_unclosed_expansions(token)

                # Track if any part was quoted
                if token.type == TokenType.STRING:
                    has_quoted_part = True
                    parts.append(token.value)
                elif token.type == TokenType.VARIABLE:
                    parts.append(f"${token.value}")
                elif token.type in (TokenType.LBRACKET, TokenType.RBRACKET):
                    # Include brackets as-is for glob patterns
                    parts.append(token.value)
                else:
                    parts.append(token.value)

            # Advance parser position
            self.parser.current = stream.pos + len(composite)

            # Create composite
            arg_type = 'COMPOSITE_QUOTED' if has_quoted_part else 'COMPOSITE'
            return ''.join(parts), arg_type, None
        else:
            # Single token case - preserve original type info
            if self.parser.match_any(TokenGroups.WORD_LIKE):
                token = self.parser.advance()
                return self._token_to_argument(token)
            else:
                raise self.parser._error("Expected word-like token")

    def _token_to_argument(self, token: Token) -> Tuple[str, str, Optional[str]]:
        """Convert a single token to argument tuple format."""
        # Check for unclosed expansions
        self._check_for_unclosed_expansions(token)

        # Handle composite tokens specially
        if token.type == TokenType.COMPOSITE:
            # Composite tokens already have the merged value
            arg_type = 'COMPOSITE_QUOTED' if token.quote_type == 'mixed' else 'COMPOSITE'
            return token.value, arg_type, None

        type_map = {
            TokenType.VARIABLE: ('VARIABLE', lambda t: self._format_variable(t)),
            TokenType.STRING: ('STRING', lambda t: t.value),
            TokenType.COMMAND_SUB: ('COMMAND_SUB', lambda t: t.value),
            TokenType.COMMAND_SUB_BACKTICK: ('COMMAND_SUB_BACKTICK', lambda t: t.value),
            TokenType.ARITH_EXPANSION: ('ARITH_EXPANSION', lambda t: t.value),
            TokenType.PARAM_EXPANSION: ('PARAM_EXPANSION', lambda t: t.value),
            TokenType.PROCESS_SUB_IN: ('PROCESS_SUB_IN', lambda t: t.value),
            TokenType.PROCESS_SUB_OUT: ('PROCESS_SUB_OUT', lambda t: t.value),
            TokenType.WORD: ('WORD', lambda t: t.value),
            TokenType.LBRACKET: ('WORD', lambda t: t.value),
            TokenType.RBRACKET: ('WORD', lambda t: t.value),
            # Note: LBRACE and RBRACE are now handled as grouping operators, not words
        }

        arg_type, value_fn = type_map.get(token.type, ('WORD', lambda t: t.value))
        value = value_fn(token)
        quote_type = getattr(token, 'quote_type', None)

        return value, arg_type, quote_type

    def _format_variable(self, token: Token) -> str:
        """Format a VARIABLE token, prepending $ if needed."""
        value = token.value
        # Variables from lexer are just the name without $
        # The only case where we don't add $ is for brace expansions ${...}
        # which already include the braces
        if value.startswith('{') and value.endswith('}'):
            return f"${value}"
        else:
            return f"${value}"

    def parse_argument_as_word(self) -> 'Word':
        """Parse an argument as a Word AST node with expansions."""
        from ....token_stream import TokenStream
        from ..support.word_builder import WordBuilder

        # Check for composite tokens
        stream = TokenStream(self.parser.tokens, self.parser.current)
        composite = stream.peek_composite_sequence()

        if composite:
            # Check for unclosed expansions in composite parts
            for token in composite:
                self._check_for_unclosed_expansions(token)
            # Build composite word from multiple tokens.
            # Per-part quote context is handled inside build_composite_word().
            self.parser.current = stream.pos + len(composite)
            return WordBuilder.build_composite_word(composite)
        else:
            # Single token
            if self.parser.match_any(TokenGroups.WORD_LIKE):
                token = self.parser.advance()
                self._check_for_unclosed_expansions(token)
                quote_type = token.quote_type if token.type == TokenType.STRING else None
                return WordBuilder.build_word_from_token(token, quote_type)
            else:
                raise self.parser._error("Expected word-like token")

    # Command variant parsers for use in pipelines

    def parse_while_command(self) -> WhileLoop:
        """Parse while loop as a command for use in pipelines."""
        result = self.parser.control_structures._parse_while_neutral()
        result.execution_context = ExecutionContext.PIPELINE
        return result

    def parse_until_command(self) -> UntilLoop:
        """Parse until loop as a command for use in pipelines."""
        result = self.parser.control_structures._parse_until_neutral()
        result.execution_context = ExecutionContext.PIPELINE
        return result

    def parse_for_command(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse for loop as a command for use in pipelines."""
        result = self.parser.control_structures._parse_for_neutral()
        result.execution_context = ExecutionContext.PIPELINE
        return result

    def parse_if_command(self) -> IfConditional:
        """Parse if command for use in pipelines."""
        result = self.parser.control_structures._parse_if_neutral()
        result.execution_context = ExecutionContext.PIPELINE
        return result

    def parse_case_command(self) -> CaseConditional:
        """Parse case command for use in pipelines."""
        result = self.parser.control_structures._parse_case_neutral()
        result.execution_context = ExecutionContext.PIPELINE
        return result

    def parse_select_command(self) -> SelectLoop:
        """Parse select command for use in pipelines."""
        result = self.parser.control_structures._parse_select_neutral()
        result.execution_context = ExecutionContext.PIPELINE
        return result

    def parse_arithmetic_compound_command(self) -> ArithmeticEvaluation:
        """Parse arithmetic command for use in pipelines."""
        result = self.parser.arithmetic._parse_arithmetic_neutral()
        result.execution_context = ExecutionContext.PIPELINE
        return result

    def parse_break_statement(self) -> BreakStatement:
        """Parse break statement for use in pipelines."""
        return self.parser.control_structures.parse_break_statement()

    def parse_continue_statement(self) -> ContinueStatement:
        """Parse continue statement for use in pipelines."""
        return self.parser.control_structures.parse_continue_statement()

    def parse_subshell_group(self) -> SubshellGroup:
        """Parse subshell group (...) that executes in isolated environment."""
        self.parser.expect(TokenType.LPAREN)
        self.parser.skip_newlines()

        # Parse statements inside the subshell
        statements = self.parser.statements.parse_command_list_until(TokenType.RPAREN)

        self.parser.skip_newlines()
        self.parser.expect(TokenType.RPAREN)

        # Parse any redirections after the subshell
        redirects = self.parser.redirections.parse_redirects()

        # Check for background operator
        background = self.parser.match(TokenType.AMPERSAND)
        if background:
            self.parser.advance()

        return SubshellGroup(
            statements=statements,
            redirects=redirects,
            background=background
        )

    def parse_brace_group(self) -> BraceGroup:
        """Parse brace group {...} that executes in current environment.
        
        POSIX syntax rules:
        - Space required after {
        - Semicolon or newline required before }
        """
        self.parser.expect(TokenType.LBRACE)
        self.parser.skip_newlines()

        # Parse statements inside the brace group
        statements = self.parser.statements.parse_command_list_until(TokenType.RBRACE)

        self.parser.skip_newlines()
        self.parser.expect(TokenType.RBRACE)

        # Parse any redirections after the brace group
        redirects = self.parser.redirections.parse_redirects()

        # Check for background operator
        background = self.parser.match(TokenType.AMPERSAND)
        if background:
            self.parser.advance()

        return BraceGroup(
            statements=statements,
            redirects=redirects,
            background=background
        )
