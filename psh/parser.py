from typing import List, Optional, Union, Tuple, Set
from .token_types import Token, TokenType
from .ast_nodes import (
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
from .parser_base import BaseParser
from .parser_helpers import TokenGroups, ParseError, ErrorContext


class Parser(BaseParser):
    def __init__(self, tokens: List[Token]):
        super().__init__(tokens)
    
    def _error(self, message: str, token: Optional[Token] = None) -> ParseError:
        """Create a ParseError with context."""
        if token is None:
            token = self.peek()
        error_context = ErrorContext(
            token=token,
            message=message,
            position=token.position
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
    
    def _parse_top_level_item(self) -> Optional[Statement]:
        """Parse a single top-level item."""
        if self._is_function_def():
            return self.parse_function_def()
        elif self.match_any(TokenGroups.CONTROL_KEYWORDS):
            # Check if control structure is part of a pipeline
            control_struct = self._parse_control_structure_neutral()
            
            # Check if followed by pipe
            if self.match(TokenType.PIPE):
                # Parse as pipeline with control structure as first component
                return self._parse_pipeline_with_initial_component(control_struct)
            else:
                # Set as statement context and return
                control_struct.execution_context = ExecutionContext.STATEMENT
                return control_struct
        else:
            # Parse commands until we hit a function or control structure
            cmd_list = self._parse_command_list_until_top_level()
            return cmd_list if cmd_list.statements else None
    
    def _parse_control_structure(self) -> Statement:
        """Parse any control structure based on current token."""
        token_type = self.peek().type
        
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
            return self.parse_enhanced_test_statement()
        elif token_type == TokenType.DOUBLE_LPAREN:
            return self.parse_arithmetic_command()
        else:
            raise self._error(f"Unexpected control structure token: {token_type.name}")
    
    def _parse_control_structure_neutral(self) -> UnifiedControlStructure:
        """Parse control structure without setting execution context."""
        token_type = self.peek().type
        
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
            return self._parse_arithmetic_neutral()
        elif token_type in (TokenType.BREAK, TokenType.CONTINUE, TokenType.DOUBLE_LBRACKET):
            # These don't have unified types, fall back to regular parsing
            return self._parse_control_structure()
        else:
            raise self._error(f"Unexpected control structure token: {token_type.name}")
    
    def _simplify_result(self, top_level: TopLevel) -> Union[CommandList, TopLevel]:
        """Simplify result for backward compatibility when possible."""
        if len(top_level.items) == 0:
            return CommandList()
        elif len(top_level.items) == 1:
            item = top_level.items[0]
            if isinstance(item, CommandList):
                return item
            elif isinstance(item, (BreakStatement, ContinueStatement)):
                # Wrap single break/continue in CommandList
                cmd_list = CommandList()
                cmd_list.statements.append(item)
                return cmd_list
        
        return top_level
    
    # === Statement Parsing ===
    
    def parse_statement(self) -> Optional[Statement]:
        """Parse a single statement (control structure or and_or_list)."""
        if self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            return self.parse_while_statement()
        elif self.match(TokenType.FOR):
            return self.parse_for_statement()
        elif self.match(TokenType.CASE):
            return self.parse_case_statement()
        elif self.match(TokenType.SELECT):
            return self.parse_select_statement()
        elif self.match(TokenType.DOUBLE_LBRACKET):
            return self.parse_enhanced_test_statement()
        elif self.match(TokenType.DOUBLE_LPAREN):
            return self.parse_arithmetic_command()
        elif self._is_function_def():
            return self.parse_function_def()
        else:
            return self.parse_and_or_list()
    
    def parse_command_list(self) -> CommandList:
        """Parse a command list (statements separated by ; or newline)."""
        command_list = CommandList()
        self.skip_newlines()
        
        if self.at_end():
            return command_list
        
        # Parse first statement
        statement = self.parse_statement()
        if statement:
            command_list.statements.append(statement)
        
        # Parse additional statements
        while self.match_any(TokenGroups.STATEMENT_SEPARATORS):
            self.skip_separators()
            
            # Check for terminators
            if self._at_command_list_end():
                break
            
            statement = self.parse_statement()
            if statement:
                command_list.statements.append(statement)
        
        return command_list
    
    def parse_command_list_until(self, *end_tokens: TokenType) -> CommandList:
        """Parse a command list until one of the end tokens is encountered."""
        command_list = CommandList()
        self.skip_newlines()
        
        while not self.match(*end_tokens) and not self.at_end():
            statement = self.parse_statement()
            if statement:
                command_list.statements.append(statement)
            
            # Handle separators but stop at end tokens
            while self.match_any(TokenGroups.STATEMENT_SEPARATORS):
                self.advance()
                if self.match(*end_tokens):
                    break
        
        return command_list
    
    def _parse_command_list_until_top_level(self) -> CommandList:
        """Parse commands until we hit a top-level construct."""
        command_list = CommandList()
        self.skip_newlines()
        
        while not self._at_top_level_boundary():
            statement = self.parse_statement()
            if statement:
                command_list.statements.append(statement)
            
            # Check for separators
            if self.match_any(TokenGroups.STATEMENT_SEPARATORS):
                saved_pos = self.current
                self.skip_separators()
                
                if self._at_top_level_boundary():
                    self.current = saved_pos
                    break
            else:
                break
        
        return command_list
    
    def _at_command_list_end(self) -> bool:
        """Check if we're at the end of a command list."""
        return self.match(
            TokenType.EOF, TokenType.FI, TokenType.DONE, 
            TokenType.ELSE, TokenType.ELIF, TokenType.ESAC, 
            TokenType.RBRACE
        )
    
    def _at_top_level_boundary(self) -> bool:
        """Check if we're at a top-level construct boundary."""
        return (self.at_end() or 
                self._is_function_def() or 
                self.match_any(TokenGroups.CONTROL_KEYWORDS))
    
    def parse_and_or_list(self) -> Union[AndOrList, BreakStatement, ContinueStatement]:
        """Parse an and-or list (pipelines connected by && or ||)."""
        # Check for loop control statements first
        if self.match(TokenType.BREAK):
            return self.parse_break_statement()
        elif self.match(TokenType.CONTINUE):
            return self.parse_continue_statement()
        
        and_or_list = AndOrList()
        
        # Parse first pipeline
        pipeline = self.parse_pipeline()
        and_or_list.pipelines.append(pipeline)
        
        # Parse additional pipelines connected by && or ||
        while self.match(TokenType.AND_AND, TokenType.OR_OR):
            operator = self.advance()
            and_or_list.operators.append(operator.value)
            
            self.skip_newlines()  # Allow newlines after operators
            
            pipeline = self.parse_pipeline()
            and_or_list.pipelines.append(pipeline)
        
        return and_or_list
    
    # === Command Parsing ===
    
    def parse_pipeline(self) -> Pipeline:
        """Parse a pipeline (commands connected by |)."""
        pipeline = Pipeline()
        
        # Check for leading ! (negation)
        if self.consume_if_match(TokenType.EXCLAMATION):
            pipeline.negated = True
        
        # Parse first command (could be simple or compound)
        command = self.parse_pipeline_component()
        pipeline.commands.append(command)
        
        # Parse additional piped commands
        while self.match(TokenType.PIPE):
            self.advance()
            command = self.parse_pipeline_component()
            pipeline.commands.append(command)
        
        return pipeline
    
    def _parse_pipeline_with_initial_component(self, initial_component: Command) -> Statement:
        """Parse a pipeline starting with an already-parsed component."""
        # Set the initial component to pipeline context
        initial_component.execution_context = ExecutionContext.PIPELINE
        
        # Create pipeline and add initial component
        pipeline = Pipeline()
        pipeline.commands.append(initial_component)
        
        # Must have at least one pipe since we were called due to seeing a pipe
        self.expect(TokenType.PIPE)
        
        # Parse remaining pipeline components
        while True:
            command = self.parse_pipeline_component()
            pipeline.commands.append(command)
            
            if not self.match(TokenType.PIPE):
                break
            self.advance()
        
        # Wrap pipeline in AndOrList for consistency
        and_or_list = AndOrList()
        and_or_list.pipelines.append(pipeline)
        
        # Check for && or || continuation
        while self.match(TokenType.AND_AND, TokenType.OR_OR):
            operator = self.advance()
            and_or_list.operators.append(operator.value)
            
            self.skip_newlines()
            pipeline = self.parse_pipeline()
            and_or_list.pipelines.append(pipeline)
        
        return and_or_list
    
    def parse_pipeline_component(self) -> Command:
        """Parse a single component of a pipeline (simple or compound command)."""
        # Try parsing as control structure first
        if self.match(TokenType.WHILE):
            return self.parse_while_command()
        elif self.match(TokenType.FOR):
            return self.parse_for_command()
        elif self.match(TokenType.IF):
            return self.parse_if_command()
        elif self.match(TokenType.CASE):
            return self.parse_case_command()
        elif self.match(TokenType.SELECT):
            return self.parse_select_command()
        elif self.match(TokenType.DOUBLE_LPAREN):
            return self.parse_arithmetic_compound_command()
        elif self.match(TokenType.BREAK):
            return self.parse_break_statement()
        elif self.match(TokenType.CONTINUE):
            return self.parse_continue_statement()
        else:
            # Fall back to simple command
            return self.parse_command()

    def parse_command(self) -> SimpleCommand:
        """Parse a single command with its arguments and redirections."""
        command = SimpleCommand()
        
        # Check for unexpected tokens
        if self.match_any(TokenGroups.CASE_TERMINATORS):
            error_context = ErrorContext(
                token=self.peek(),
                message=f"Syntax error near unexpected token '{self.peek().value}'",
                position=self.peek().position
            )
            raise ParseError(error_context)
        
        # Ensure we have at least one word-like token
        if not self.match_any(TokenGroups.WORD_LIKE):
            raise self._error("Expected command")
        
        # Track whether we've parsed any regular arguments yet
        has_parsed_regular_args = False
        
        # Parse arguments and redirections
        while self.match_any(TokenGroups.WORD_LIKE | TokenGroups.REDIRECTS):
            if self.match_any(TokenGroups.REDIRECTS):
                redirect = self.parse_redirect()
                command.redirects.append(redirect)
            else:
                # Only check for array assignments if we haven't parsed any regular args yet
                if not has_parsed_regular_args and self._is_array_assignment():
                    array_assignment = self._parse_array_assignment()
                    command.array_assignments.append(array_assignment)
                else:
                    # Special case: check if this is arr=(...) syntax for declare
                    if (self.match(TokenType.WORD) and self.peek().value.endswith('=') and 
                        self.peek_ahead(1) and self.peek_ahead(1).type == TokenType.LPAREN):
                        # This is array initialization syntax like arr=(...)
                        # Parse it as a single argument
                        word_token = self.advance()
                        lparen = self.advance()  # consume LPAREN
                        
                        # Collect elements until RPAREN
                        elements = []
                        while not self.match(TokenType.RPAREN) and not self.at_end():
                            if self.match_any(TokenGroups.WORD_LIKE):
                                elem_value, _, _ = self.parse_composite_argument()
                                elements.append(elem_value)
                            else:
                                raise self._error("Expected array element")
                        
                        if not self.consume_if_match(TokenType.RPAREN):
                            raise self._error("Expected ')' to close array initialization")
                        
                        # Build the complete argument
                        arg_value = word_token.value + '(' + ' '.join(elements) + ')'
                        command.args.append(arg_value)
                        command.arg_types.append('WORD')
                        command.quote_types.append(None)
                        has_parsed_regular_args = True
                    else:
                        # Parse a potentially composite argument
                        arg_value, arg_type, quote_type = self.parse_composite_argument()
                        command.args.append(arg_value)
                        command.arg_types.append(arg_type)
                        command.quote_types.append(quote_type)
                        has_parsed_regular_args = True
        
        # Check for background execution
        if self.consume_if_match(TokenType.AMPERSAND):
            command.background = True
        
        return command
    
    # Command variant parsers for use in pipelines
    
    def parse_while_command(self) -> WhileLoop:
        """Parse while loop as a command for use in pipelines."""
        condition, body, redirects = self._parse_loop_structure(
            TokenType.WHILE, TokenType.DO, TokenType.DONE
        )
        return WhileLoop(
            condition=condition,
            body=body,
            redirects=redirects,
            execution_context=ExecutionContext.PIPELINE,
            background=False
        )
    
    def parse_for_command(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse for loop as a command for use in pipelines."""
        self.expect(TokenType.FOR)
        self.skip_newlines()
        
        # Check if it's a C-style for loop
        if self.peek().type == TokenType.DOUBLE_LPAREN:
            self.advance()  # consume ((
            return self._parse_c_style_for_command()
        elif self.peek().type == TokenType.LPAREN:
            # Check for two consecutive LPAREN tokens
            saved_pos = self.current
            self.advance()  # consume first (
            
            if self.peek().type == TokenType.LPAREN:
                self.advance()  # consume second (
                return self._parse_c_style_for_command()
            else:
                # Not C-style, backtrack
                self.current = saved_pos
        
        # Traditional for loop
        variable = self.expect(TokenType.WORD).value
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        # Parse items using the same method as parse_for_statement
        items = self._parse_for_iterable()
        
        # Handle separators before DO
        self.skip_separators()
        
        self.skip_newlines()
        self.expect(TokenType.DO)
        self.skip_newlines()
        
        body = self.parse_command_list_until(TokenType.DONE)
        self.expect(TokenType.DONE)
        
        redirects = self.parse_redirects()
        
        return ForLoop(
            variable=variable,
            items=items,
            body=body,
            redirects=redirects,
            execution_context=ExecutionContext.PIPELINE,
            background=False
        )
    
    def _parse_c_style_for_command(self) -> CStyleForLoop:
        """Parse C-style for loop as a command."""
        # Parse init expression
        init_expr = self._parse_arithmetic_section(';')
        if init_expr == "":
            init_expr = None
        self.advance()  # consume ;
        
        # Parse condition expression
        condition_expr = self._parse_arithmetic_section(';')
        if condition_expr == "":
            condition_expr = None
        self.advance()  # consume ;
        
        # Parse update expression
        update_expr = self._parse_arithmetic_section_until_double_rparen()
        
        # Consume ))
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.RPAREN)
        
        # Skip any separators after ))
        self.skip_separators()
        
        # Optional DO keyword
        if self.match(TokenType.DO):
            self.advance()
        
        self.skip_newlines()
        
        # Parse loop body
        body = self.parse_command_list_until(TokenType.DONE)
        self.expect(TokenType.DONE)
        
        redirects = self.parse_redirects()
        
        return CStyleForLoop(
            body=body,
            init_expr=init_expr,
            condition_expr=condition_expr,
            update_expr=update_expr,
            redirects=redirects,
            execution_context=ExecutionContext.PIPELINE,
            background=False
        )
    
    def parse_if_command(self) -> IfConditional:
        """Parse if statement as a command for use in pipelines."""
        self.expect(TokenType.IF)
        self.skip_newlines()
        
        # Parse main condition and body
        condition, then_part = self._parse_condition_then_block()
        
        # Parse elif clauses
        elif_parts = []
        while self.match(TokenType.ELIF):
            self.advance()
            elif_condition, elif_then = self._parse_condition_then_block()
            elif_parts.append((elif_condition, elif_then))
        
        # Parse optional else
        else_part = None
        if self.match(TokenType.ELSE):
            self.advance()
            self.skip_newlines()
            else_part = self.parse_command_list_until(TokenType.FI)
        
        self.expect(TokenType.FI)
        redirects = self.parse_redirects()
        
        return IfConditional(
            condition=condition,
            then_part=then_part,
            elif_parts=elif_parts,
            else_part=else_part,
            redirects=redirects,
            execution_context=ExecutionContext.PIPELINE,
            background=False
        )
    
    def parse_case_command(self) -> CaseConditional:
        """Parse case statement as a command for use in pipelines."""
        self.expect(TokenType.CASE)
        self.skip_newlines()
        
        # Use the same expression parser as parse_case_statement
        expr = self._parse_case_expression()
        
        self.skip_newlines()
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        items = []
        while not self.match(TokenType.ESAC):
            item = self.parse_case_item()
            items.append(item)
            self.skip_newlines()
        
        self.expect(TokenType.ESAC)
        redirects = self.parse_redirects()
        
        return CaseConditional(
            expr=expr,
            items=items,
            redirects=redirects,
            execution_context=ExecutionContext.PIPELINE,
            background=False
        )
    
    def parse_select_command(self) -> SelectLoop:
        """Parse select statement as a command for use in pipelines."""
        self.expect(TokenType.SELECT)
        self.skip_newlines()
        
        variable = self.expect(TokenType.WORD).value
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        # Parse items
        items = self._parse_for_iterable()
        
        self.skip_separators()
        self.expect(TokenType.DO)
        self.skip_newlines()
        
        body = self.parse_command_list_until(TokenType.DONE)
        self.expect(TokenType.DONE)
        
        redirects = self.parse_redirects()
        
        return SelectLoop(
            variable=variable,
            items=items,
            body=body,
            redirects=redirects,
            execution_context=ExecutionContext.PIPELINE,
            background=False
        )
    
    def parse_arithmetic_compound_command(self) -> ArithmeticEvaluation:
        """Parse arithmetic command as a compound command for use in pipelines."""
        self.expect(TokenType.DOUBLE_LPAREN)
        
        expression = self._parse_arithmetic_expression_until_double_rparen()
        
        # Consume ))
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.RPAREN)
        
        redirects = self.parse_redirects()
        
        return ArithmeticEvaluation(
            expression=expression,
            redirects=redirects,
            execution_context=ExecutionContext.PIPELINE,
            background=False
        )
    
    def parse_composite_argument(self) -> Tuple[str, str, Optional[str]]:
        """Parse a potentially composite argument (concatenated tokens)."""
        parts = []
        first_token = None
        last_end_pos = None
        has_quoted_part = False
        
        while self.match_any(TokenGroups.WORD_LIKE):
            token = self.peek()
            
            # Check if tokens are adjacent
            if last_end_pos is not None and token.position != last_end_pos:
                break  # Not adjacent
            
            token = self.advance()
            if first_token is None:
                first_token = token
            
            # Track if any part was quoted
            if token.type == TokenType.STRING:
                has_quoted_part = True
            
            # Convert token to string representation
            if token.type == TokenType.VARIABLE:
                parts.append(f"${token.value}")
            elif token.type in (TokenType.LBRACKET, TokenType.RBRACKET):
                # Include brackets as-is for glob patterns
                parts.append(token.value)
            else:
                parts.append(token.value)
            
            last_end_pos = token.end_position
        
        # Single token case - preserve original type info
        if len(parts) == 1:
            return self._token_to_argument(first_token)
        
        # Multiple parts - create composite
        # Use special type to indicate quoted composite
        arg_type = 'COMPOSITE_QUOTED' if has_quoted_part else 'COMPOSITE'
        return ''.join(parts), arg_type, None
    
    def _token_to_argument(self, token: Token) -> Tuple[str, str, Optional[str]]:
        """Convert a single token to argument tuple format."""
        type_map = {
            TokenType.VARIABLE: ('VARIABLE', lambda t: f"${t.value}"),
            TokenType.STRING: ('STRING', lambda t: t.value),
            TokenType.COMMAND_SUB: ('COMMAND_SUB', lambda t: t.value),
            TokenType.COMMAND_SUB_BACKTICK: ('COMMAND_SUB_BACKTICK', lambda t: t.value),
            TokenType.ARITH_EXPANSION: ('ARITH_EXPANSION', lambda t: t.value),
            TokenType.PROCESS_SUB_IN: ('PROCESS_SUB_IN', lambda t: t.value),
            TokenType.PROCESS_SUB_OUT: ('PROCESS_SUB_OUT', lambda t: t.value),
            TokenType.WORD: ('WORD', lambda t: t.value),
            TokenType.LBRACKET: ('WORD', lambda t: t.value),
            TokenType.RBRACKET: ('WORD', lambda t: t.value),
        }
        
        arg_type, value_fn = type_map.get(token.type, ('WORD', lambda t: t.value))
        value = value_fn(token)
        quote_type = token.quote_type if token.type == TokenType.STRING else None
        
        return value, arg_type, quote_type
    
    # === Control Structures ===
    
    def parse_if_statement(self) -> IfConditional:
        """Parse if/then/else/fi conditional statement."""
        self.expect(TokenType.IF)
        self.skip_newlines()
        
        # Parse main condition and body
        condition, then_part = self._parse_condition_then_block()
        
        # Parse elif clauses
        elif_parts = []
        while self.match(TokenType.ELIF):
            self.advance()
            elif_condition, elif_then = self._parse_condition_then_block()
            elif_parts.append((elif_condition, elif_then))
        
        # Parse optional else
        else_part = None
        if self.match(TokenType.ELSE):
            self.advance()
            self.skip_newlines()
            else_part = self.parse_command_list_until(TokenType.FI)
        
        self.expect(TokenType.FI)
        redirects = self.parse_redirects()
        
        return IfConditional(
            condition=condition,
            then_part=then_part,
            elif_parts=elif_parts,
            else_part=else_part,
            redirects=redirects,
            execution_context=ExecutionContext.STATEMENT,
            background=False
        )
    
    def _parse_if_neutral(self) -> IfConditional:
        """Parse if statement without setting execution context."""
        self.expect(TokenType.IF)
        self.skip_newlines()
        
        # Parse main condition and body
        condition, then_part = self._parse_condition_then_block()
        
        # Parse elif clauses
        elif_parts = []
        while self.match(TokenType.ELIF):
            self.advance()
            elif_condition, elif_then = self._parse_condition_then_block()
            elif_parts.append((elif_condition, elif_then))
        
        # Parse optional else
        else_part = None
        if self.match(TokenType.ELSE):
            self.advance()
            self.skip_newlines()
            else_part = self.parse_command_list_until(TokenType.FI)
        
        self.expect(TokenType.FI)
        redirects = self.parse_redirects()
        
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
        self.skip_newlines()
        condition = self.parse_command_list_until(TokenType.THEN)
        self.expect(TokenType.THEN)
        self.skip_newlines()
        body = self.parse_command_list_until(TokenType.ELIF, TokenType.ELSE, TokenType.FI)
        return condition, body
    
    def parse_while_statement(self) -> WhileLoop:
        """Parse while/do/done loop statement."""
        condition, body, redirects = self._parse_loop_structure(
            TokenType.WHILE, TokenType.DO, TokenType.DONE
        )
        return WhileLoop(
            condition=condition,
            body=body,
            redirects=redirects,
            execution_context=ExecutionContext.STATEMENT,
            background=False
        )
    
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
    
    def parse_for_statement(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse for loop (traditional or C-style)."""
        self.expect(TokenType.FOR)
        self.skip_newlines()
        
        # Check if it's a C-style for loop by looking for (( or DOUBLE_LPAREN
        if self.peek().type == TokenType.DOUBLE_LPAREN:
            # It's a C-style for loop with DOUBLE_LPAREN token
            self.advance()  # consume ((
            return self._parse_c_style_for()
        elif self.peek().type == TokenType.LPAREN:
            # Check for two consecutive LPAREN tokens
            saved_pos = self.current
            self.advance()  # consume first (
            
            if self.peek().type == TokenType.LPAREN:
                # It's a C-style for loop
                self.advance()  # consume second (
                return self._parse_c_style_for()
            else:
                # Not C-style, backtrack
                self.current = saved_pos
        
        # Traditional for loop
        # Variable name
        var_token = self.expect(TokenType.WORD)
        variable = var_token.value
        
        self.skip_newlines()
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        # Parse iterable list
        items = self._parse_for_iterable()
        
        # Handle separators before DO
        self.skip_separators()
        
        self.expect(TokenType.DO)
        self.skip_newlines()
        
        # Parse body
        body = self.parse_command_list_until(TokenType.DONE)
        
        self.expect(TokenType.DONE)
        redirects = self.parse_redirects()
        
        return ForLoop(
            variable=variable,
            items=items,
            body=body,
            redirects=redirects,
            execution_context=ExecutionContext.STATEMENT,
            background=False
        )
    
    def _parse_for_neutral(self) -> Union[ForLoop, CStyleForLoop]:
        """Parse for loop without setting execution context."""
        self.expect(TokenType.FOR)
        self.skip_newlines()
        
        # Check if it's a C-style for loop
        if self.peek().type == TokenType.DOUBLE_LPAREN:
            self.advance()  # consume ((
            return self._parse_c_style_for_neutral()
        elif self.peek().type == TokenType.LPAREN:
            saved_pos = self.current
            self.advance()  # consume first (
            
            if self.peek().type == TokenType.LPAREN:
                self.advance()  # consume second (
                return self._parse_c_style_for_neutral()
            else:
                self.current = saved_pos
        
        # Traditional for loop
        variable = self.expect(TokenType.WORD).value
        self.skip_newlines()
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        items = self._parse_for_iterable()
        self.skip_separators()
        self.expect(TokenType.DO)
        self.skip_newlines()
        
        body = self.parse_command_list_until(TokenType.DONE)
        self.expect(TokenType.DONE)
        redirects = self.parse_redirects()
        
        return ForLoop(
            variable=variable,
            items=items,
            body=body,
            redirects=redirects,
            background=False
        )
    
    def _parse_for_iterable(self) -> List[str]:
        """Parse the iterable list in a for statement."""
        iterable = []
        
        while not self.match(TokenType.DO, TokenType.SEMICOLON, TokenType.NEWLINE) and not self.at_end():
            if self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
                         TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK):
                token = self.advance()
                iterable.append(token.value)
            else:
                break
        
        return iterable
    
    def _parse_c_style_for(self) -> CStyleForLoop:
        """Parse C-style for loop: for ((init; condition; update))"""
        # At this point, we've already consumed 'for (('
        
        # Parse initialization expression (until semicolon)
        init_expr = self._parse_arithmetic_section(';')
        if self.peek().type == TokenType.SEMICOLON:
            self.advance()  # consume semicolon
        elif self.peek().type == TokenType.DOUBLE_SEMICOLON:
            # We have ;;, need to handle this specially
            # Skip the ;; and add back a ; for the next section
            self.advance()  # consume ;;
            # Insert a semicolon token for the next parse
            semicolon_token = Token(TokenType.SEMICOLON, ';', self.peek().position)
            self.tokens.insert(self.current, semicolon_token)
        
        # Parse condition expression (until semicolon)
        condition_expr = self._parse_arithmetic_section(';')
        if self.peek().type == TokenType.SEMICOLON:
            self.advance()  # consume semicolon
        
        # Parse update expression (until double rparen)
        update_expr = self._parse_arithmetic_section_until_double_rparen()
        
        # Expect )) - two RPAREN tokens
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.RPAREN)
        
        # Skip any separators after ))
        self.skip_separators()
        
        # Skip optional DO
        if self.peek().type == TokenType.DO:
            self.advance()
        
        self.skip_newlines()
        
        # Parse loop body
        body = self.parse_command_list_until(TokenType.DONE)
        
        self.expect(TokenType.DONE)
        redirects = self.parse_redirects()
        
        return CStyleForLoop(
            body=body,
            init_expr=init_expr,
            condition_expr=condition_expr,
            update_expr=update_expr,
            redirects=redirects,
            execution_context=ExecutionContext.STATEMENT,
            background=False
        )
    
    def _parse_c_style_for_neutral(self) -> CStyleForLoop:
        """Parse C-style for loop without setting execution context."""
        # At this point, we've already consumed 'for (('
        
        # Parse init expression
        init_expr = self._parse_arithmetic_section(';')
        if init_expr == "":
            init_expr = None
        if self.peek().type == TokenType.SEMICOLON:
            self.advance()  # consume ;
        elif self.peek().type == TokenType.DOUBLE_SEMICOLON:
            # Handle ;; case
            self.advance()  # consume ;;
            # Insert a semicolon token for the next section
            semicolon_token = Token(TokenType.SEMICOLON, ';', self.peek().position)
            self.tokens.insert(self.current, semicolon_token)
        
        # Parse condition expression
        condition_expr = self._parse_arithmetic_section(';')
        if condition_expr == "":
            condition_expr = None
        if self.peek().type == TokenType.SEMICOLON:
            self.advance()  # consume ;
        
        # Parse update expression
        update_expr = self._parse_arithmetic_section_until_double_rparen()
        
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.RPAREN)
        
        self.skip_separators()
        
        if self.match(TokenType.DO):
            self.advance()
        
        self.skip_newlines()
        
        body = self.parse_command_list_until(TokenType.DONE)
        self.expect(TokenType.DONE)
        redirects = self.parse_redirects()
        
        return CStyleForLoop(
            body=body,
            init_expr=init_expr,
            condition_expr=condition_expr,
            update_expr=update_expr,
            redirects=redirects,
            background=False
        )
    
    def _parse_arithmetic_section(self, terminator: str) -> Optional[str]:
        """Parse arithmetic expression section until terminator character."""
        expr_parts = []
        paren_depth = 0
        
        while not self.at_end():
            token = self.peek()
            
            # Check for terminator at depth 0
            if paren_depth == 0 and terminator == ';':
                if token.type == TokenType.SEMICOLON:
                    break
                elif token.type == TokenType.DOUBLE_SEMICOLON:
                    # Found ;;, treat first ; as terminator
                    break
            
            # Track parentheses depth
            if token.type == TokenType.LPAREN:
                paren_depth += 1
            elif token.type == TokenType.RPAREN:
                if paren_depth == 0:
                    # This might be the end of the C-style for
                    break
                paren_depth -= 1
            
            # For operators that got tokenized as redirects, use their raw form
            if token.type == TokenType.REDIRECT_IN:
                expr_parts.append('<')
            elif token.type == TokenType.REDIRECT_OUT:
                expr_parts.append('>')
            else:
                expr_parts.append(token.value)
                
            # Add space between tokens if needed
            if len(expr_parts) > 1 and expr_parts[-2][-1].isalnum() and token.value[0].isalnum():
                expr_parts.insert(-1, ' ')
                
            self.advance()
        
        return ''.join(expr_parts).strip() if expr_parts else ""
    
    def _parse_arithmetic_section_until_double_rparen(self) -> Optional[str]:
        """Parse arithmetic expression until we find )) at depth 0."""
        expr_parts = []
        paren_depth = 0
        
        while not self.at_end():
            token = self.peek()
            
            # Check for )) at depth 0
            if paren_depth == 0 and token.type == TokenType.RPAREN:
                # Peek ahead to see if next is also RPAREN
                next_pos = self.current + 1
                if next_pos < len(self.tokens) and self.tokens[next_pos].type == TokenType.RPAREN:
                    # Found ))
                    break
            
            # Track parentheses depth
            if token.type == TokenType.LPAREN:
                paren_depth += 1
            elif token.type == TokenType.RPAREN:
                paren_depth -= 1
            
            # For operators that got tokenized as redirects, use their raw form
            if token.type == TokenType.REDIRECT_IN:
                expr_parts.append('<')
            elif token.type == TokenType.REDIRECT_OUT:
                expr_parts.append('>')
            else:
                expr_parts.append(token.value)
                
            # Add space between tokens if needed
            if len(expr_parts) > 1 and expr_parts[-2] and expr_parts[-2][-1].isalnum() and token.value and token.value[0].isalnum():
                expr_parts.insert(-1, ' ')
                
            self.advance()
        
        return ''.join(expr_parts).strip() if expr_parts else None
    
    def _parse_loop_structure(self, start: TokenType, body_start: TokenType, 
                            body_end: TokenType) -> Tuple[StatementList, StatementList, List[Redirect]]:
        """Common pattern for while/until loops."""
        self.expect(start)
        self.skip_newlines()
        
        condition = self.parse_command_list_until(body_start)
        
        self.expect(body_start)
        self.skip_newlines()
        
        body = self.parse_command_list_until(body_end)
        
        self.expect(body_end)
        redirects = self.parse_redirects()
        
        return condition, body, redirects
    
    def parse_case_statement(self) -> CaseConditional:
        """Parse case/esac statement."""
        self.expect(TokenType.CASE)
        self.skip_newlines()
        
        # Parse expression to match
        expr = self._parse_case_expression()
        
        self.skip_newlines()
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        # Parse case items
        items = []
        while not self.match(TokenType.ESAC) and not self.at_end():
            items.append(self.parse_case_item())
            self.skip_newlines()
        
        self.expect(TokenType.ESAC)
        redirects = self.parse_redirects()
        
        return CaseConditional(
            expr=expr,
            items=items,
            redirects=redirects,
            execution_context=ExecutionContext.STATEMENT,
            background=False
        )
    
    def _parse_case_neutral(self) -> CaseConditional:
        """Parse case statement without setting execution context."""
        self.expect(TokenType.CASE)
        self.skip_newlines()
        
        expr = self._parse_case_expression()
        
        self.skip_newlines()
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        items = []
        while not self.match(TokenType.ESAC):
            items.append(self.parse_case_item())
            self.skip_newlines()
        
        self.expect(TokenType.ESAC)
        redirects = self.parse_redirects()
        
        return CaseConditional(
            expr=expr,
            items=items,
            redirects=redirects,
            background=False
        )
    
    def _parse_case_expression(self) -> str:
        """Parse the expression in a case statement."""
        if not self.match_any(TokenGroups.WORD_LIKE):
            raise self._error("Expected expression after 'case'")
        
        token = self.advance()
        if token.type == TokenType.VARIABLE:
            return f"${token.value}"
        return token.value
    
    def parse_case_item(self) -> CaseItem:
        """Parse a single case item: patterns) commands terminator"""
        # Skip any leading newlines/whitespace
        self.skip_newlines()
        
        # Parse patterns
        patterns = [CasePattern(self._parse_case_pattern())]
        
        while self.match(TokenType.PIPE):
            self.advance()
            patterns.append(CasePattern(self._parse_case_pattern()))
        
        self.expect(TokenType.RPAREN)
        self.skip_newlines()
        
        # Parse commands
        commands = self.parse_command_list_until(
            TokenType.DOUBLE_SEMICOLON, TokenType.SEMICOLON_AMP,
            TokenType.AMP_SEMICOLON, TokenType.ESAC
        )
        
        # Parse terminator
        terminator = ';;'  # Default
        if self.match_any(TokenGroups.CASE_TERMINATORS):
            terminator = self.advance().value
        
        return CaseItem(patterns, commands, terminator)
    
    def _parse_case_pattern(self) -> str:
        """Parse a single case pattern."""
        # Keywords can be valid patterns in bash (e.g., case $x in if) echo "it's if" ;; esac)
        # So we need to accept keyword tokens as patterns too
        keyword_tokens = {
            TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.FI, TokenType.ELIF,
            TokenType.WHILE, TokenType.DO, TokenType.DONE, TokenType.FOR, TokenType.IN,
            TokenType.BREAK, TokenType.CONTINUE, TokenType.CASE, TokenType.ESAC,
            TokenType.SELECT, TokenType.FUNCTION
        }
        
        if not (self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE) or
                self.match_any(keyword_tokens) or self.match(TokenType.LBRACKET, TokenType.RBRACKET)):
            raise self._error("Expected pattern in case statement")
        
        # Build pattern from possibly multiple tokens
        # Handle patterns like [abc] which might be tokenized as WORD + RBRACKET
        pattern_parts = []
        
        # Parse pattern tokens until we hit ) or |
        while not self.match(TokenType.RPAREN, TokenType.PIPE) and not self.at_end():
            if self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE) or \
               self.match_any(keyword_tokens) or self.match(TokenType.LBRACKET, TokenType.RBRACKET):
                token = self.advance()
                if token.type == TokenType.VARIABLE:
                    pattern_parts.append(f"${token.value}")
                else:
                    pattern_parts.append(token.value)
            else:
                break
        
        if not pattern_parts:
            raise self._error("Expected pattern in case statement")
        
        return ''.join(pattern_parts)
    
    def parse_select_statement(self) -> SelectLoop:
        """Parse select statement: select name in words; do commands done"""
        self.expect(TokenType.SELECT)
        self.skip_newlines()
        
        # Parse variable name
        if not self.match(TokenType.WORD):
            raise self._error("Expected variable name after 'select'")
        variable = self.advance().value
        
        self.skip_newlines()
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        # Parse word list (reuse existing method)
        items = self._parse_for_iterable()
        
        # Parse do block
        self.skip_separators()
        self.expect(TokenType.DO)
        self.skip_newlines()
        
        # Parse body
        body = self.parse_command_list_until(TokenType.DONE)
        
        self.expect(TokenType.DONE)
        redirects = self.parse_redirects()
        
        return SelectLoop(
            variable=variable,
            items=items,
            body=body,
            redirects=redirects,
            execution_context=ExecutionContext.STATEMENT,
            background=False
        )
    
    def _parse_select_neutral(self) -> SelectLoop:
        """Parse select statement without setting execution context."""
        self.expect(TokenType.SELECT)
        self.skip_newlines()
        
        variable = self.expect(TokenType.WORD).value
        self.expect(TokenType.IN)
        self.skip_newlines()
        
        items = self._parse_for_iterable()
        
        self.skip_separators()
        self.expect(TokenType.DO)
        self.skip_newlines()
        
        body = self.parse_command_list_until(TokenType.DONE)
        self.expect(TokenType.DONE)
        
        redirects = self.parse_redirects()
        
        return SelectLoop(
            variable=variable,
            items=items,
            body=body,
            redirects=redirects,
            background=False
        )
    
    def _parse_loop_control_level(self) -> int:
        """Parse optional numeric level for break/continue statements."""
        level = 1
        if self.match(TokenType.WORD):
            try:
                level = max(1, int(self.peek().value))
                self.advance()
            except ValueError:
                pass  # Not a number, leave for next parsing
        return level
    
    def parse_break_statement(self) -> BreakStatement:
        """Parse break statement with optional level."""
        self.expect(TokenType.BREAK)
        level = self._parse_loop_control_level()
        return BreakStatement(level=level)
    
    def parse_continue_statement(self) -> ContinueStatement:
        """Parse continue statement with optional level."""
        self.expect(TokenType.CONTINUE)
        level = self._parse_loop_control_level()
        return ContinueStatement(level=level)
    
    # === Functions ===
    
    def _is_function_def(self) -> bool:
        """Check if current position starts a function definition."""
        if self.match(TokenType.FUNCTION):
            return True
        
        # Check for name() pattern
        if self.match(TokenType.WORD):
            word_token = self.peek()
            # Don't consider it a function if the word ends with '=' (array assignment)
            if word_token.value.endswith('='):
                return False
                
            saved_pos = self.current
            self.advance()
            
            if self.match(TokenType.LPAREN):
                self.advance()
                result = self.match(TokenType.RPAREN)
                self.current = saved_pos
                return result
            
            self.current = saved_pos
        
        return False
    
    def parse_function_def(self) -> FunctionDef:
        """Parse function definition."""
        name = None
        
        if self.match(TokenType.FUNCTION):
            self.advance()
            name = self.expect(TokenType.WORD).value
            
            # Optional parentheses
            if self.match(TokenType.LPAREN):
                self.advance()
                self.expect(TokenType.RPAREN)
        else:
            # POSIX style: name()
            name = self.expect(TokenType.WORD).value
            self.expect(TokenType.LPAREN)
            self.expect(TokenType.RPAREN)
        
        self.skip_newlines()
        body = self.parse_compound_command()
        
        return FunctionDef(name, body)
    
    def parse_compound_command(self) -> CommandList:
        """Parse a compound command { ... }"""
        self.expect(TokenType.LBRACE)
        self.skip_newlines()
        
        command_list = self.parse_command_list_until(TokenType.RBRACE)
        
        self.expect(TokenType.RBRACE)
        
        return command_list
    
    # === Enhanced Test ===
    
    def parse_enhanced_test_statement(self) -> EnhancedTestStatement:
        """Parse [[ ... ]] enhanced test statement."""
        self.expect(TokenType.DOUBLE_LBRACKET)
        self.skip_newlines()
        
        expression = self.parse_test_expression()
        
        self.skip_newlines()
        self.expect(TokenType.DOUBLE_RBRACKET)
        
        redirects = self.parse_redirects()
        
        return EnhancedTestStatement(expression, redirects)
    
    def parse_test_expression(self) -> TestExpression:
        """Parse a test expression with proper precedence."""
        return self.parse_test_or_expression()
    
    def parse_test_or_expression(self) -> TestExpression:
        """Parse test expression with || operator."""
        left = self.parse_test_and_expression()
        
        while self.match(TokenType.OR_OR):
            self.advance()
            self.skip_newlines()
            right = self.parse_test_and_expression()
            left = CompoundTestExpression(left, '||', right)
        
        return left
    
    def parse_test_and_expression(self) -> TestExpression:
        """Parse test expression with && operator."""
        left = self.parse_test_unary_expression()
        
        while self.match(TokenType.AND_AND):
            self.advance()
            self.skip_newlines()
            right = self.parse_test_unary_expression()
            left = CompoundTestExpression(left, '&&', right)
        
        return left
    
    def parse_test_unary_expression(self) -> TestExpression:
        """Parse unary test expression (possibly negated)."""
        if self.match(TokenType.EXCLAMATION):
            self.advance()
            self.skip_newlines()
            expr = self.parse_test_unary_expression()
            return NegatedTestExpression(expr)
        
        return self.parse_test_primary_expression()
    
    def parse_test_primary_expression(self) -> TestExpression:
        """Parse primary test expression."""
        self.skip_newlines()
        
        # Empty test
        if self.match(TokenType.DOUBLE_RBRACKET):
            return UnaryTestExpression('-n', '')
        
        # Parenthesized expression
        if self.match(TokenType.LPAREN):
            self.advance()
            expr = self.parse_test_expression()
            self.expect(TokenType.RPAREN)
            return expr
        
        # Check for unary operators
        if self.match(TokenType.WORD) and self._is_unary_test_operator(self.peek().value):
            operator = self.advance().value
            self.skip_newlines()
            operand = self._parse_test_operand()
            return UnaryTestExpression(operator, operand)
        
        # Binary expression or single value
        left = self._parse_test_operand()
        self.skip_newlines()
        
        # Check for binary operators
        if self.match(TokenType.WORD, TokenType.REGEX_MATCH):
            token = self.peek()
            if token.type == TokenType.REGEX_MATCH or self._is_binary_test_operator(token.value):
                operator = self.advance().value
                self.skip_newlines()
                
                # Special handling for regex patterns
                if operator == '=~':
                    self.context.push_context('regex_rhs')
                
                right = self._parse_test_operand()
                
                if operator == '=~':
                    self.context.pop_context()
                
                return BinaryTestExpression(left, operator, right)
        
        # Single value test
        return UnaryTestExpression('-n', left)
    
    def _parse_test_operand(self) -> str:
        """Parse a test operand."""
        if not self.match_any(TokenGroups.WORD_LIKE):
            raise self._error("Expected test operand")
        
        token = self.advance()
        result = f"${token.value}" if token.type == TokenType.VARIABLE else token.value
        
        # Concatenate words for regex patterns
        if self.context.in_context('regex_rhs'):
            while self.match(TokenType.WORD) and not self._is_binary_test_operator(self.peek().value):
                result += self.advance().value
        
        return result
    
    def _is_unary_test_operator(self, value: str) -> bool:
        """Check if a word is a unary test operator."""
        return value in {
            '-a', '-b', '-c', '-d', '-e', '-f', '-g', '-h', '-k', '-p',
            '-r', '-s', '-t', '-u', '-w', '-x', '-G', '-L', '-N', '-O',
            '-S', '-z', '-n', '-o'
        }
    
    def _is_binary_test_operator(self, value: str) -> bool:
        """Check if a word is a binary test operator."""
        return value in {
            '=', '==', '!=', '<', '>', '-eq', '-ne', '-lt', '-le', '-gt', '-ge',
            '-nt', '-ot', '-ef'
        }
    
    # === Arithmetic Command ===
    
    def parse_arithmetic_command(self) -> ArithmeticEvaluation:
        """Parse arithmetic command: ((expression))"""
        # Consume the (( token
        self.expect(TokenType.DOUBLE_LPAREN)
        
        # Parse expression until ))
        expr = self._parse_arithmetic_expression_until_double_rparen()
        
        # Expect ))
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.RPAREN)
        
        # Parse any redirects (rare but allowed)
        redirects = self.parse_redirects()
        
        return ArithmeticEvaluation(
            expression=expr,
            redirects=redirects,
            execution_context=ExecutionContext.STATEMENT,
            background=False
        )
    
    def _parse_arithmetic_neutral(self) -> ArithmeticEvaluation:
        """Parse arithmetic command without setting execution context."""
        self.expect(TokenType.DOUBLE_LPAREN)
        
        expr = self._parse_arithmetic_expression_until_double_rparen()
        
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.RPAREN)
        
        redirects = self.parse_redirects()
        
        return ArithmeticEvaluation(
            expression=expr,
            redirects=redirects,
            background=False
        )
    
    def _parse_arithmetic_expression_until_double_rparen(self) -> str:
        """Parse arithmetic expression until )) is found."""
        expr = ""
        paren_depth = 0
        
        while not self.at_end():
            token = self.peek()
            
            # Check for )) at depth 0
            if token.type == TokenType.RPAREN and paren_depth == 0:
                # Look ahead for another )
                if self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].type == TokenType.RPAREN:
                    break
            
            # Track parentheses depth
            if token.type == TokenType.LPAREN:
                paren_depth += 1
            elif token.type == TokenType.RPAREN:
                paren_depth -= 1
            
            expr += token.value
            self.advance()
            
            # Add space between tokens if needed
            if not self.at_end() and self.peek().type != TokenType.RPAREN:
                next_token = self.peek()
                if token.type == TokenType.WORD and next_token.type == TokenType.WORD:
                    expr += " "
        
        return expr.strip()
    
    # === Redirections ===
    
    def parse_redirects(self) -> List[Redirect]:
        """Parse zero or more redirections."""
        redirects = []
        while self.match_any(TokenGroups.REDIRECTS):
            redirects.append(self.parse_redirect())
        return redirects
    
    def parse_redirect(self) -> Redirect:
        """Parse a single redirection."""
        redirect_token = self.advance()
        
        # Dispatch to specific redirect parser
        if redirect_token.type in (TokenType.HEREDOC, TokenType.HEREDOC_STRIP):
            return self._parse_heredoc(redirect_token)
        elif redirect_token.type == TokenType.HERE_STRING:
            return self._parse_here_string(redirect_token)
        elif redirect_token.type == TokenType.REDIRECT_DUP:
            return self._parse_dup_redirect(redirect_token)
        elif redirect_token.type in (TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND):
            return self._parse_err_redirect(redirect_token)
        else:
            return self._parse_standard_redirect(redirect_token)
    
    def _parse_heredoc(self, token: Token) -> Redirect:
        """Parse here document redirect."""
        if not self.match(TokenType.WORD):
            raise self._error("Expected delimiter after here document operator")
        
        delimiter = self.advance().value
        
        return Redirect(
            type=token.value,
            target=delimiter,
            heredoc_content=None  # Content filled later
        )
    
    def _parse_here_string(self, token: Token) -> Redirect:
        """Parse here string redirect."""
        if not self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE):
            raise self._error("Expected string after here string operator")
        
        content = self.advance().value
        
        return Redirect(
            type=token.value,
            target=content,
            heredoc_content=None
        )
    
    def _parse_dup_redirect(self, token: Token) -> Redirect:
        """Parse file descriptor duplication (2>&1)."""
        # Token value is like "2>&1"
        parts = token.value.split('>&')
        fd = int(parts[0]) if parts[0] else 1
        dup_fd = int(parts[1]) if len(parts) > 1 and parts[1] else 1
        
        return Redirect(
            type='>&',
            target='',
            fd=fd,
            dup_fd=dup_fd
        )
    
    def _parse_err_redirect(self, token: Token) -> Redirect:
        """Parse error redirection (2>, 2>>)."""
        # Extract fd from token value
        fd_part = token.value.rstrip('>')
        fd = int(fd_part) if fd_part else 2
        
        if not self.match(TokenType.WORD, TokenType.STRING):
            raise self._error("Expected file name after redirection")
        
        target = self.advance().value
        redirect_type = '>>' if token.type == TokenType.REDIRECT_ERR_APPEND else '>'
        
        return Redirect(
            type=redirect_type,
            target=target,
            fd=fd
        )
    
    def _parse_standard_redirect(self, token: Token) -> Redirect:
        """Parse standard file redirection."""
        if not self.match_any(TokenGroups.WORD_LIKE):
            raise self._error("Expected file name after redirection")
        
        # Use composite argument parsing to handle quoted composites like file'name'.txt
        target, _, _ = self.parse_composite_argument()
        
        # Extract fd if present
        redirect_str = token.value
        fd = None
        if redirect_str[0].isdigit():
            fd = int(redirect_str[0])
            redirect_type = redirect_str[1:]
        else:
            redirect_type = redirect_str
        
        return Redirect(
            type=redirect_type,
            target=target,
            fd=fd
        )
    
    # === Array Assignment Parsing ===
    
    def _is_array_assignment(self) -> bool:
        """Check if current position starts an array assignment."""
        if not self.match(TokenType.WORD):
            return False
        
        saved_pos = self.current
        word_token = self.peek()
        
        # Check for array initialization: name=( or name+=(
        if ('=' in word_token.value or '+=' in word_token.value) and (word_token.value.endswith('=') or word_token.value.endswith('+=')):
            # Word contains equals at the end (e.g., "arr=" or "arr+=")
            self.advance()
            if self.match(TokenType.LPAREN):
                self.current = saved_pos
                return True
        
        # Check for array element assignment: name[
        self.advance()  # consume word
        if self.match(TokenType.LBRACKET):
            self.current = saved_pos
            return True
        
        self.current = saved_pos
        return False
    
    def _parse_array_assignment(self) -> ArrayAssignment:
        """Parse an array assignment (initialization or element)."""
        name_token = self.expect(TokenType.WORD)
        
        # Check for array element assignment: name[index]=value
        if self.match(TokenType.LBRACKET):
            name = name_token.value
            return self._parse_array_element_assignment(name)
        
        # Otherwise it's array initialization: name=(elements) or name+=(elements)
        # The name token should end with '=' or '+='
        if name_token.value.endswith('+='):
            name = name_token.value[:-2]  # Remove the trailing '+='
            is_append = True
        elif name_token.value.endswith('='):
            name = name_token.value[:-1]  # Remove the trailing '='
            is_append = False
        else:
            raise self._error("Expected '=' or '+=' in array initialization")
        
        return self._parse_array_initialization(name, is_append)
    
    def _parse_array_key_tokens(self) -> List[Token]:
        """Parse array key as list of tokens for later evaluation.
        
        This implements the late binding approach where we collect tokens
        without evaluation, allowing the executor to determine whether to
        evaluate as arithmetic (indexed arrays) or string (associative arrays).
        """
        tokens = []
        bracket_depth = 1
        
        while bracket_depth > 0 and not self.at_end():
            token = self.peek()
            
            if token.type == TokenType.LBRACKET:
                bracket_depth += 1
            elif token.type == TokenType.RBRACKET:
                bracket_depth -= 1
                if bracket_depth == 0:
                    break
            
            # Accept any valid key token for later evaluation
            if token.type in (TokenType.WORD, TokenType.STRING, TokenType.VARIABLE, 
                             TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
                             TokenType.ARITH_EXPANSION, TokenType.LPAREN, TokenType.RPAREN):
                tokens.append(token)
                self.advance()
            else:
                raise self._error(f"Invalid token in array key: {token.type}")
        
        if bracket_depth != 0:
            raise self._error("Unmatched '[' in array element assignment")
        
        return tokens
    
    def _parse_array_element_assignment(self, name: str) -> ArrayElementAssignment:
        """Parse array element assignment: name[index]=value"""
        self.expect(TokenType.LBRACKET)
        
        # Parse index as list of tokens for late binding (associative vs indexed array evaluation)
        index_tokens = self._parse_array_key_tokens()
        
        self.expect(TokenType.RBRACKET)
        
        # Next token should be a WORD starting with '='
        if not self.match(TokenType.WORD):
            raise self._error("Expected '=' after array index")
        
        equals_token = self.peek()
        if not (equals_token.value.startswith('=') or equals_token.value.startswith('+=')):
            raise self._error("Expected '=' or '+=' after array index")
        
        self.advance()  # consume the equals token
        
        # Check if it's an append operation
        is_append = equals_token.value.startswith('+=')
        
        # If the equals token has a value after '=' or '+=', use it
        if is_append and len(equals_token.value) > 2:
            # Value is part of the equals token (e.g., "+=value")
            value = equals_token.value[2:]
            value_type = 'WORD'
            quote_type = None
        elif not is_append and len(equals_token.value) > 1:
            # Value is part of the equals token (e.g., "=value")
            value = equals_token.value[1:]
            value_type = 'WORD'
            quote_type = None
        else:
            # Parse the value as a separate token
            if not self.match_any(TokenGroups.WORD_LIKE):
                raise self._error("Expected value after '=' in array element assignment")
            value, value_type, quote_type = self.parse_composite_argument()
        
        return ArrayElementAssignment(
            name=name,
            index=index_tokens,
            value=value,
            value_type=value_type,
            value_quote_type=quote_type,
            is_append=is_append
        )
    
    def _parse_array_initialization(self, name: str, is_append: bool = False) -> ArrayInitialization:
        """Parse array initialization: name=(elements)"""
        self.expect(TokenType.LPAREN)
        
        elements = []
        element_types = []
        element_quote_types = []
        
        # Parse array elements
        while not self.match(TokenType.RPAREN) and not self.at_end():
            if self.match_any(TokenGroups.WORD_LIKE):
                value, arg_type, quote_type = self.parse_composite_argument()
                elements.append(value)
                element_types.append(arg_type)
                element_quote_types.append(quote_type)
            else:
                break
        
        self.expect(TokenType.RPAREN)
        
        return ArrayInitialization(
            name=name,
            elements=elements,
            element_types=element_types,
            element_quote_types=element_quote_types,
            is_append=is_append
        )


def parse(tokens: List[Token]) -> Union[CommandList, TopLevel]:
    """Parse a list of tokens into an AST."""
    parser = Parser(tokens)
    return parser.parse()