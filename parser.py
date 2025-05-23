from typing import List, Optional
from tokenizer import Token, TokenType
from ast_nodes import Command, Pipeline, CommandList, Redirect


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
    
    def parse(self) -> CommandList:
        command_list = self.parse_command_list()
        if self.peek().type != TokenType.EOF:
            raise ParseError("Unexpected tokens after command list", self.peek())
        return command_list
    
    def parse_command_list(self) -> CommandList:
        command_list = CommandList()
        
        # Skip leading newlines
        while self.match(TokenType.NEWLINE):
            self.advance()
        
        if self.match(TokenType.EOF):
            return command_list
        
        # Parse first pipeline
        pipeline = self.parse_pipeline()
        command_list.pipelines.append(pipeline)
        
        # Parse additional pipelines separated by semicolons or newlines
        while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
            self.advance()
            
            # Skip multiple separators
            while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                self.advance()
            
            # Check if we've reached the end
            if self.match(TokenType.EOF):
                break
            
            pipeline = self.parse_pipeline()
            command_list.pipelines.append(pipeline)
        
        return command_list
    
    def parse_pipeline(self) -> Pipeline:
        pipeline = Pipeline()
        
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
        
        # A command must have at least one word
        if not self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
                         TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK):
            raise ParseError("Expected command", self.peek())
        
        # Parse command arguments and redirections
        while self.match(TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
                         TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
                         TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, 
                         TokenType.REDIRECT_APPEND, TokenType.HEREDOC,
                         TokenType.HEREDOC_STRIP, TokenType.REDIRECT_ERR,
                         TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP):
            
            if self.match(TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, 
                         TokenType.REDIRECT_APPEND, TokenType.HEREDOC,
                         TokenType.HEREDOC_STRIP, TokenType.REDIRECT_ERR,
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
                elif token.type == TokenType.STRING:
                    command.args.append(token.value)
                    command.arg_types.append('STRING')
                elif token.type == TokenType.COMMAND_SUB:
                    command.args.append(token.value)
                    command.arg_types.append('COMMAND_SUB')
                elif token.type == TokenType.COMMAND_SUB_BACKTICK:
                    command.args.append(token.value)
                    command.arg_types.append('COMMAND_SUB_BACKTICK')
                else:
                    command.args.append(token.value)
                    command.arg_types.append('WORD')
        
        # Check for background execution
        if self.match(TokenType.AMPERSAND):
            self.advance()
            command.background = True
        
        return command
    
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
            if not self.match(TokenType.WORD, TokenType.STRING):
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


def parse(tokens: List[Token]) -> CommandList:
    parser = Parser(tokens)
    return parser.parse()