from typing import List, Optional, Union
from .tokenizer import Token, TokenType
from .ast_nodes import Command, Pipeline, CommandList, StatementList, AndOrList, Redirect, FunctionDef, TopLevel, IfStatement, WhileStatement, ForStatement, BreakStatement, ContinueStatement, CaseStatement, CaseItem, CasePattern, ProcessSubstitution


class ParseError(Exception):
    def __init__(self, message: str, token: Optional[Token] = None):
        self.message = message
        self.token = token
        super().__init__(self.format_error())
    
    def format_error(self) -> str:
        if self.token:
            return f"Parse error at position {self.token.position}: {self.message}"
        return f"Parse error: {self.message}"


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
    
    def peek(self) -> Token:
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        return self.tokens[-1]  # Return EOF token
    
    def advance(self) -> Token:
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token
    
    def expect(self, token_type: TokenType) -> Token:
        token = self.peek()
        if token.type != token_type:
            raise ParseError(f"Expected {token_type.name}, got {token.type.name}", token)
        return self.advance()
    
    def match(self, *token_types: TokenType) -> bool:
        return self.peek().type in token_types
    
    def parse(self) -> Union[CommandList, TopLevel]:
        """Parse input, returning TopLevel if functions present, CommandList otherwise."""
        top_level = TopLevel()
        
        # Skip leading newlines
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        while self.peek().type != TokenType.EOF:
            if self._is_function_def():
                func_def = self.parse_function_def()
                top_level.items.append(func_def)
            elif self.match(TokenType.IF):
                if_stmt = self.parse_if_statement()
                top_level.items.append(if_stmt)
            elif self.match(TokenType.WHILE):
                while_stmt = self.parse_while_statement()
                top_level.items.append(while_stmt)
            elif self.match(TokenType.FOR):
                for_stmt = self.parse_for_statement()
                top_level.items.append(for_stmt)
            elif self.match(TokenType.CASE):
                case_stmt = self.parse_case_statement()
                top_level.items.append(case_stmt)
            elif self.match(TokenType.BREAK):
                break_stmt = self.parse_break_statement()
                top_level.items.append(break_stmt)
            elif self.match(TokenType.CONTINUE):
                continue_stmt = self.parse_continue_statement()
                top_level.items.append(continue_stmt)
            else:
                # Parse command list until we hit a function or EOF
                cmd_list = self._parse_command_list_until_function()
                if cmd_list.statements:  # Not empty
                    top_level.items.append(cmd_list)
            
            # Skip trailing separators
            while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                self.advance()
        
        # For backward compatibility, return CommandList if no functions
        if len(top_level.items) == 1 and isinstance(top_level.items[0], CommandList):
            return top_level.items[0]
        elif len(top_level.items) == 1 and isinstance(top_level.items[0], (BreakStatement, ContinueStatement)):
            # Wrap single break/continue in CommandList for backward compatibility
            cmd_list = CommandList()
            cmd_list.statements.append(top_level.items[0])
            return cmd_list
        elif len(top_level.items) == 0:
            return CommandList()
        else:
            return top_level
    
    def parse_command_list(self) -> CommandList:
        command_list = CommandList()
        
        # Skip leading newlines
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        if self.match(TokenType.EOF):
            return command_list
        
        # Parse first statement (could be control structure or and_or_list)
        statement = self.parse_statement()
        if statement:
            command_list.statements.append(statement)
        
        # Parse additional statements separated by semicolons or newlines
        while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
            self.advance()
            
            # Skip multiple separators
            while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                self.advance()
            
            # Check if we've reached the end or a terminator
            if self.match(TokenType.EOF, TokenType.FI, TokenType.DONE, TokenType.ELSE, 
                          TokenType.ESAC, TokenType.RBRACE):
                break
            
            statement = self.parse_statement()
            if statement:
                command_list.statements.append(statement)
        
        return command_list
    
    def parse_statement(self):
        """Parse a single statement (control structure or and_or_list)."""
        # Check for control structures
        if self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            return self.parse_while_statement()
        elif self.match(TokenType.FOR):
            return self.parse_for_statement()
        elif self.match(TokenType.CASE):
            return self.parse_case_statement()
        elif self._is_function_def():
            return self.parse_function_def()
        else:
            # Parse regular and_or_list
            return self.parse_and_or_list()
    
    def parse_command_list_until(self, *end_tokens: TokenType) -> CommandList:
        """Parse a command list until one of the end tokens is encountered."""
        command_list = CommandList()
        
        # Skip leading newlines
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        while not self.match(*end_tokens) and not self.match(TokenType.EOF):
            statement = self.parse_statement()
            if statement:
                command_list.statements.append(statement)
            
            # Handle separators but stop at end tokens
            while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                self.advance()
                if self.match(*end_tokens):
                    break
        
        return command_list
    
    def parse_and_or_list(self) -> Union[AndOrList, BreakStatement, ContinueStatement]:
        # Check for control statements first
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
            
            # Skip newlines after operator (bash allows this)
            while self.match(TokenType.NEWLINE):
                self.advance()
            
            pipeline = self.parse_pipeline()
            and_or_list.pipelines.append(pipeline)
        
        return and_or_list
    
    def parse_pipeline(self) -> Pipeline:
        pipeline = Pipeline()
        
        # Check for leading ! (negation)
        if self.match(TokenType.EXCLAMATION):
            pipeline.negated = True
            self.advance()  # Skip !
        
        # Parse first command
        command = self.parse_command()
        pipeline.commands.append(command)
        
        # Parse additional commands separated by pipes
        while self.match(TokenType.PIPE):
            self.advance()
            command = self.parse_command()
            pipeline.commands.append(command)
        
        return pipeline
    
    def parse_command(self) -> Command:
        command = Command()
        
        # Check if we have at least one word-like token
        if not self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
                         TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
                         TokenType.ARITH_EXPANSION, TokenType.PROCESS_SUB_IN,
                         TokenType.PROCESS_SUB_OUT):
            raise ParseError("Expected command", self.peek())
        
        # Peek at the first token to check if it's a variable assignment
        first_token = self.peek()
        if first_token.type == TokenType.WORD and '=' in first_token.value and not first_token.value.startswith('='):
            # This looks like a variable assignment
            # Parse it as a command anyway - the shell will handle it
            pass
        
        # Parse command arguments and redirections
        while self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
                         TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
                         TokenType.ARITH_EXPANSION, TokenType.PROCESS_SUB_IN,
                         TokenType.PROCESS_SUB_OUT,
                         TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, 
                         TokenType.REDIRECT_APPEND, TokenType.HEREDOC,
                         TokenType.HEREDOC_STRIP, TokenType.HERE_STRING,
                         TokenType.REDIRECT_ERR,
                         TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP):
            
            if self.match(TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, 
                         TokenType.REDIRECT_APPEND, TokenType.HEREDOC,
                         TokenType.HEREDOC_STRIP, TokenType.HERE_STRING,
                         TokenType.REDIRECT_ERR,
                         TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP):
                redirect = self.parse_redirect()
                command.redirects.append(redirect)
            else:
                # It's an argument
                token = self.advance()
                if token.type == TokenType.VARIABLE:
                    # For now, just prepend $ to indicate it's a variable
                    command.args.append(f"${token.value}")
                    command.arg_types.append('VARIABLE')
                    command.quote_types.append(None)
                elif token.type == TokenType.STRING:
                    command.args.append(token.value)
                    command.arg_types.append('STRING')
                    command.quote_types.append(token.quote_type)
                elif token.type == TokenType.COMMAND_SUB:
                    command.args.append(token.value)
                    command.arg_types.append('COMMAND_SUB')
                    command.quote_types.append(None)
                elif token.type == TokenType.COMMAND_SUB_BACKTICK:
                    command.args.append(token.value)
                    command.arg_types.append('COMMAND_SUB_BACKTICK')
                    command.quote_types.append(None)
                elif token.type == TokenType.ARITH_EXPANSION:
                    command.args.append(token.value)
                    command.arg_types.append('ARITH_EXPANSION')
                    command.quote_types.append(None)
                elif token.type == TokenType.PROCESS_SUB_IN:
                    command.args.append(token.value)
                    command.arg_types.append('PROCESS_SUB_IN')
                    command.quote_types.append(None)
                elif token.type == TokenType.PROCESS_SUB_OUT:
                    command.args.append(token.value)
                    command.arg_types.append('PROCESS_SUB_OUT')
                    command.quote_types.append(None)
                else:
                    command.args.append(token.value)
                    command.arg_types.append('WORD')
                    command.quote_types.append(None)
        
        # Check for background execution
        if self.match(TokenType.AMPERSAND):
            self.advance()
            command.background = True
        
        return command
    
    def parse_redirects(self) -> List[Redirect]:
        """Parse zero or more redirections."""
        redirects = []
        while self.match(TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, TokenType.REDIRECT_APPEND,
                         TokenType.HEREDOC, TokenType.HEREDOC_STRIP, TokenType.HERE_STRING,
                         TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP):
            redirects.append(self.parse_redirect())
        return redirects
    
    def parse_redirect(self) -> Redirect:
        redirect_token = self.advance()
        
        # For here documents, the delimiter is the next word
        if redirect_token.type in (TokenType.HEREDOC, TokenType.HEREDOC_STRIP):
            if not self.match(TokenType.WORD):
                raise ParseError("Expected delimiter after here document operator", self.peek())
            
            delimiter_token = self.advance()
            
            return Redirect(
                type=redirect_token.value,
                target=delimiter_token.value,
                heredoc_content=None  # Content will be filled in later
            )
        # For here strings, the content is the next word/string
        elif redirect_token.type == TokenType.HERE_STRING:
            if not self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE):
                raise ParseError("Expected string after here string operator", self.peek())
            
            content_token = self.advance()
            
            return Redirect(
                type=redirect_token.value,
                target=content_token.value,
                heredoc_content=None  # Will be set by shell
            )
        elif redirect_token.type == TokenType.REDIRECT_DUP:
            # Handle 2>&1 syntax - extract fd and dup_fd from the token value
            # Token value is like "2>&1"
            parts = redirect_token.value.split('>&')
            fd = int(parts[0]) if parts[0] else 1  # Default to stdout
            dup_fd = int(parts[1]) if len(parts) > 1 and parts[1] else 1
            
            return Redirect(
                type='>&',
                target='',  # No target file for dup
                fd=fd,
                dup_fd=dup_fd
            )
        elif redirect_token.type in (TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND):
            # Handle 2> and 2>> - extract fd from token value
            # Token value is like "2>" or "2>>"
            fd_part = redirect_token.value.rstrip('>')
            fd = int(fd_part) if fd_part else 2
            
            if not self.match(TokenType.WORD, TokenType.STRING):
                raise ParseError("Expected file name after redirection", self.peek())
            
            target_token = self.advance()
            
            return Redirect(
                type='>>' if redirect_token.type == TokenType.REDIRECT_ERR_APPEND else '>',
                target=target_token.value,
                fd=fd
            )
        else:
            # Regular redirection - the next token should be the target file
            if not self.match(TokenType.WORD, TokenType.STRING, TokenType.PROCESS_SUB_IN, TokenType.PROCESS_SUB_OUT):
                raise ParseError("Expected file name after redirection", self.peek())
            
            target_token = self.advance()
            
            # Extract fd if present (for cases like 0<, 1>, etc.)
            redirect_str = redirect_token.value
            fd = None
            if redirect_str[0].isdigit():
                fd = int(redirect_str[0])
                redirect_type = redirect_str[1:]  # Remove fd part
            else:
                redirect_type = redirect_str
            
            return Redirect(
                type=redirect_type,
                target=target_token.value,
                fd=fd
            )
    
    def _is_function_def(self) -> bool:
        """Check if current position starts a function definition."""
        if not self.peek():
            return False
        
        # Check for 'function' keyword
        if self.peek().type == TokenType.FUNCTION:
            return True
        
        # Check for name() pattern
        if self.peek().type == TokenType.WORD:
            # Need to peek ahead
            saved_pos = self.current
            self.advance()
            
            if self.match(TokenType.LPAREN):
                self.advance()
                result = self.match(TokenType.RPAREN)
                self.current = saved_pos  # Restore position
                return result
            
            self.current = saved_pos  # Restore position
        
        return False
    
    def parse_function_def(self) -> FunctionDef:
        """Parse function definition."""
        name = None
        
        # Handle 'function' keyword if present
        if self.match(TokenType.FUNCTION):
            self.advance()
            if not self.match(TokenType.WORD):
                raise ParseError("Expected function name after 'function'", self.peek())
            name = self.advance().value
            
            # Optional parentheses
            if self.match(TokenType.LPAREN):
                self.advance()
                self.expect(TokenType.RPAREN)
        else:
            # POSIX style: name()
            if not self.match(TokenType.WORD):
                raise ParseError("Expected function name", self.peek())
            name = self.advance().value
            self.expect(TokenType.LPAREN)
            self.expect(TokenType.RPAREN)
        
        # Skip newlines before body
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse body
        body = self.parse_compound_command()
        return FunctionDef(name, body)
    
    def parse_compound_command(self) -> CommandList:
        """Parse a compound command { ... }"""
        if not self.match(TokenType.LBRACE):
            raise ParseError("Expected '{' to start compound command", self.peek())
        
        self.advance()  # consume {
        
        # Skip newlines after {
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse the command list inside
        command_list = self.parse_command_list_until(TokenType.RBRACE)
        
        if not self.match(TokenType.RBRACE):
            raise ParseError("Expected '}' to end compound command", self.peek())
        
        self.advance()  # consume }
        
        return command_list
    
    def _parse_command_list_until_function(self) -> CommandList:
        """Parse commands until we hit a function definition or EOF."""
        command_list = CommandList()
        
        # Skip leading newlines
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        while not self.match(TokenType.EOF) and not self._is_function_def() and not self.match(TokenType.IF) and not self.match(TokenType.WHILE) and not self.match(TokenType.FOR) and not self.match(TokenType.CASE):
            statement = self.parse_statement()
            if statement:
                command_list.statements.append(statement)
            
            # Check for separators
            if self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                # Peek ahead to see if a function or if statement follows
                saved_pos = self.current
                while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                    self.advance()
                
                if self._is_function_def() or self.match(TokenType.EOF) or self.match(TokenType.IF) or self.match(TokenType.WHILE) or self.match(TokenType.FOR):
                    # Stop here, let main parse loop handle the function/if/while/for statement
                    self.current = saved_pos
                    break
                
                # Otherwise continue with more commands
                continue
            else:
                # No separator, we're done
                break
        
        return command_list
    
    def parse_if_statement(self) -> IfStatement:
        """Parse if/then/else/fi conditional statement."""
        # Consume 'if'
        self.expect(TokenType.IF)
        
        # Skip newlines after if
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse condition (command list until 'then')
        condition = self.parse_command_list_until(TokenType.THEN)
        
        # Consume 'then'
        self.expect(TokenType.THEN)
        
        # Skip newlines after then
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse then_part (commands until 'elif', 'else' or 'fi')
        then_part = self.parse_command_list_until(TokenType.ELIF, TokenType.ELSE, TokenType.FI)
        
        # Parse elif clauses
        elif_parts = []
        while self.match(TokenType.ELIF):
            self.advance()  # Consume 'elif'
            
            # Skip newlines after elif
            while self.match(TokenType.NEWLINE):
                self.advance()
            
            # Parse elif condition
            elif_condition = self.parse_command_list_until(TokenType.THEN)
            
            # Consume 'then'
            self.expect(TokenType.THEN)
            
            # Skip newlines after then
            while self.match(TokenType.NEWLINE):
                self.advance()
            
            # Parse elif then_part
            elif_then = self.parse_command_list_until(TokenType.ELIF, TokenType.ELSE, TokenType.FI)
            
            elif_parts.append((elif_condition, elif_then))
        
        # Parse optional else part
        else_part = None
        if self.match(TokenType.ELSE):
            self.advance()  # Consume 'else'
            
            # Skip newlines after else
            while self.match(TokenType.NEWLINE):
                self.advance()
            
            # Parse else_part (commands until 'fi')
            else_part = self.parse_command_list_until(TokenType.FI)
        
        # Consume 'fi'
        self.expect(TokenType.FI)
        
        # Parse optional redirections after 'fi'
        redirects = self.parse_redirects()
        
        # Create IfStatement with elif_parts
        if_stmt = IfStatement(condition, then_part, else_part=else_part, redirects=redirects)
        if_stmt.elif_parts = elif_parts
        return if_stmt
    
    def parse_while_statement(self) -> WhileStatement:
        """Parse while/do/done loop statement."""
        # Consume 'while'
        self.expect(TokenType.WHILE)
        
        # Skip newlines after while
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse condition (command list until 'do')
        condition = self.parse_command_list_until(TokenType.DO)
        
        # Consume 'do'
        self.expect(TokenType.DO)
        
        # Skip newlines after do
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse body (commands until 'done')
        body = self.parse_command_list_until(TokenType.DONE)
        
        # Consume 'done'
        self.expect(TokenType.DONE)
        
        # Parse optional redirections after 'done'
        redirects = self.parse_redirects()
        
        return WhileStatement(condition, body, redirects)
    
    def parse_for_statement(self) -> ForStatement:
        """Parse for/in/do/done loop statement."""
        # Consume 'for'
        self.expect(TokenType.FOR)
        
        # Skip newlines after for
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse variable name
        var_token = self.expect(TokenType.WORD)
        variable = var_token.value
        
        # Skip newlines after variable
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Consume 'in'
        self.expect(TokenType.IN)
        
        # Skip newlines after in
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse iterable list (words until 'do' or ';')
        iterable = []
        while not self.match(TokenType.DO) and not self.match(TokenType.SEMICOLON) and not self.match(TokenType.NEWLINE) and not self.match(TokenType.EOF):
            # Accept WORD, STRING, VARIABLE, and command substitution tokens in the iterable list
            if self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE, 
                         TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK):
                token = self.advance()
                iterable.append(token.value)
            else:
                break
        
        # Handle separators between iterable and 'do'
        while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
            self.advance()
        
        # Consume 'do'
        self.expect(TokenType.DO)
        
        # Skip newlines after do
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse body (commands until 'done')
        body = self.parse_command_list_until(TokenType.DONE)
        
        # Consume 'done'
        self.expect(TokenType.DONE)
        
        # Parse optional redirections after 'done'
        redirects = self.parse_redirects()
        
        return ForStatement(variable, iterable, body, redirects)
    
    def parse_break_statement(self) -> BreakStatement:
        """Parse break statement."""
        self.expect(TokenType.BREAK)
        return BreakStatement()
    
    def parse_continue_statement(self) -> ContinueStatement:
        """Parse continue statement."""
        self.expect(TokenType.CONTINUE)
        return ContinueStatement()
    
    def parse_case_statement(self) -> CaseStatement:
        """Parse case/esac statement."""
        # Consume 'case'
        self.expect(TokenType.CASE)
        
        # Parse expression (word to match against)
        if not self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE):
            raise ParseError("Expected expression after 'case'", self.peek())
        token = self.advance()
        if token.type == TokenType.VARIABLE:
            expr = f"${token.value}"
        else:
            expr = token.value
        
        # Skip newlines
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Consume 'in'
        self.expect(TokenType.IN)
        
        # Skip newlines after 'in'
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse case items
        items = []
        while not self.match(TokenType.ESAC) and not self.match(TokenType.EOF):
            item = self.parse_case_item()
            items.append(item)
            
            # Skip newlines between items
            while self.match(TokenType.NEWLINE):
                self.advance()
        
        # Consume 'esac'
        self.expect(TokenType.ESAC)
        
        # Parse optional redirections after 'esac'
        redirects = self.parse_redirects()
        
        return CaseStatement(expr, items, redirects)
    
    def parse_case_item(self) -> CaseItem:
        """Parse a single case item: patterns) commands terminator"""
        # Parse patterns separated by |
        patterns = []
        patterns.append(CasePattern(self.parse_case_pattern()))
        
        # Parse additional patterns separated by |
        while self.match(TokenType.PIPE):
            self.advance()  # Consume |
            patterns.append(CasePattern(self.parse_case_pattern()))
        
        # Consume )
        self.expect(TokenType.RPAREN)
        
        # Skip newlines after )
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        # Parse commands until terminator
        commands = self.parse_command_list_until(TokenType.DOUBLE_SEMICOLON, TokenType.SEMICOLON_AMP, 
                                                TokenType.AMP_SEMICOLON, TokenType.ESAC)
        
        # Parse terminator (default to ;; if at esac or EOF)
        terminator = ';;'
        if self.match(TokenType.DOUBLE_SEMICOLON):
            terminator = self.advance().value
        elif self.match(TokenType.SEMICOLON_AMP):
            terminator = self.advance().value
        elif self.match(TokenType.AMP_SEMICOLON):
            terminator = self.advance().value
        # If we hit esac or EOF, leave default terminator
        
        return CaseItem(patterns, commands, terminator)
    
    def parse_case_pattern(self) -> str:
        """Parse a case pattern (word, string, or variable)."""
        if not self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE):
            raise ParseError("Expected pattern in case statement", self.peek())
        token = self.advance()
        if token.type == TokenType.VARIABLE:
            return f"${token.value}"
        else:
            return token.value


def parse(tokens: List[Token]) -> Union[CommandList, TopLevel]:
    parser = Parser(tokens)
    return parser.parse()