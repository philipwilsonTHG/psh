from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    WORD = auto()
    PIPE = auto()
    REDIRECT_IN = auto()
    REDIRECT_OUT = auto()
    REDIRECT_APPEND = auto()
    REDIRECT_ERR = auto()
    REDIRECT_ERR_APPEND = auto()
    REDIRECT_DUP = auto()
    HEREDOC = auto()
    HEREDOC_STRIP = auto()
    HERE_STRING = auto()
    SEMICOLON = auto()
    AMPERSAND = auto()
    AND_AND = auto()
    OR_OR = auto()
    NEWLINE = auto()
    EOF = auto()
    STRING = auto()
    VARIABLE = auto()
    COMMAND_SUB = auto()
    COMMAND_SUB_BACKTICK = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    FUNCTION = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    position: int


class Tokenizer:
    def __init__(self, input_string: str):
        self.input = input_string
        self.position = 0
        self.tokens: List[Token] = []
    
    def current_char(self) -> Optional[str]:
        if self.position >= len(self.input):
            return None
        return self.input[self.position]
    
    def peek_char(self, offset: int = 1) -> Optional[str]:
        pos = self.position + offset
        if pos >= len(self.input):
            return None
        return self.input[pos]
    
    def advance(self) -> None:
        self.position += 1
    
    def skip_whitespace(self) -> None:
        while self.current_char() and self.current_char() in ' \t':
            self.advance()
    
    def read_word(self) -> str:
        value = ''
        while self.current_char() and self.current_char() not in ' \t\n|<>;&`(){}':
            if self.current_char() == '\\' and self.peek_char():
                # Skip backslash and add the escaped character
                self.advance()
                if self.current_char():
                    value += self.current_char()
                    self.advance()
            else:
                value += self.current_char()
                self.advance()
        return value
    
    def read_quoted_string(self, quote_char: str) -> str:
        self.advance()  # Skip opening quote
        value = ''
        while self.current_char() and self.current_char() != quote_char:
            if self.current_char() == '\\' and self.peek_char() == quote_char:
                self.advance()  # Skip backslash
                value += self.current_char()
                self.advance()
            else:
                value += self.current_char()
                self.advance()
        
        if self.current_char() == quote_char:
            self.advance()  # Skip closing quote
        else:
            raise SyntaxError(f"Unclosed quote at position {self.position}")
        
        return value
    
    def read_command_substitution(self) -> str:
        """Read $(...) command substitution"""
        self.advance()  # Skip $
        self.advance()  # Skip (
        
        depth = 1
        command = ''
        
        while depth > 0 and self.current_char() is not None:
            char = self.current_char()
            
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    break
            
            command += char
            self.advance()
        
        if self.current_char() == ')':
            self.advance()  # Skip final )
        else:
            raise SyntaxError(f"Unclosed command substitution at position {self.position}")
        
        return f"$({command})"
    
    def read_backtick_substitution(self) -> str:
        """Read `...` backtick command substitution"""
        self.advance()  # Skip opening `
        
        command = ''
        while self.current_char() is not None and self.current_char() != '`':
            if self.current_char() == '\\':
                # Handle escape sequences in backticks
                self.advance()
                if self.current_char() in ['$', '\\', '`']:
                    # For backticks, \$ means literal $ in the output
                    # So we keep the backslash for $ to prevent expansion
                    if self.current_char() == '$':
                        command += '\\$'
                    else:
                        command += self.current_char()
                    self.advance()
                else:
                    # Not a special escape, keep the backslash
                    command += '\\'
            else:
                command += self.current_char()
                self.advance()
        
        if self.current_char() == '`':
            self.advance()  # Skip closing `
        else:
            raise SyntaxError(f"Unclosed backtick at position {self.position}")
        
        return f"`{command}`"
    
    def check_fd_redirect(self) -> bool:
        """Check if current position has a file descriptor redirect like 2>"""
        if not self.current_char() or not self.current_char().isdigit():
            return False
        
        # Save position
        saved_pos = self.position
        
        # Skip digits
        while self.current_char() and self.current_char().isdigit():
            self.advance()
        
        # Check if followed by > or <
        result = self.current_char() in ['>', '<']
        
        # Restore position
        self.position = saved_pos
        return result
    
    def tokenize(self) -> List[Token]:
        while self.current_char() is not None:
            self.skip_whitespace()
            
            if self.current_char() is None:
                break
            
            # Check for comments at word boundary
            if self.current_char() == '#':
                # Skip everything until end of line
                while self.current_char() is not None and self.current_char() != '\n':
                    self.advance()
                continue
            
            start_pos = self.position
            char = self.current_char()
            
            # Check for file descriptor redirects (e.g., 2>, 2>&1)
            if self.check_fd_redirect():
                # Read the file descriptor number
                fd = ''
                while self.current_char() and self.current_char().isdigit():
                    fd += self.current_char()
                    self.advance()
                
                # Now handle the redirect operator
                if self.current_char() == '>':
                    self.advance()
                    if self.current_char() == '>':
                        self.tokens.append(Token(TokenType.REDIRECT_ERR_APPEND, fd + '>>', start_pos))
                        self.advance()
                    elif self.current_char() == '&':
                        # Handle 2>&1 syntax
                        self.advance()  # Skip &
                        dup_target = ''
                        while self.current_char() and self.current_char().isdigit():
                            dup_target += self.current_char()
                            self.advance()
                        self.tokens.append(Token(TokenType.REDIRECT_DUP, fd + '>&' + dup_target, start_pos))
                    else:
                        self.tokens.append(Token(TokenType.REDIRECT_ERR, fd + '>', start_pos))
                elif self.current_char() == '<':
                    self.advance()
                    self.tokens.append(Token(TokenType.REDIRECT_IN, fd + '<', start_pos))
            elif char == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', start_pos))
                self.advance()
            elif char == '|':
                if self.peek_char() == '|':
                    self.tokens.append(Token(TokenType.OR_OR, '||', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.PIPE, '|', start_pos))
                    self.advance()
            elif char == ';':
                self.tokens.append(Token(TokenType.SEMICOLON, ';', start_pos))
                self.advance()
            elif char == '&':
                if self.peek_char() == '&':
                    self.tokens.append(Token(TokenType.AND_AND, '&&', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.AMPERSAND, '&', start_pos))
                    self.advance()
            elif char == '<':
                if self.peek_char() == '<':
                    # Check for <<, <<-, or <<<
                    self.advance()  # Skip first <
                    if self.peek_char() == '<':
                        # This is <<<
                        self.tokens.append(Token(TokenType.HERE_STRING, '<<<', start_pos))
                        self.advance()  # Skip second <
                        self.advance()  # Skip third <
                    elif self.peek_char() == '-':
                        self.tokens.append(Token(TokenType.HEREDOC_STRIP, '<<-', start_pos))
                        self.advance()  # Skip second <
                        self.advance()  # Skip -
                    else:
                        self.tokens.append(Token(TokenType.HEREDOC, '<<', start_pos))
                        self.advance()  # Skip second <
                else:
                    self.tokens.append(Token(TokenType.REDIRECT_IN, '<', start_pos))
                    self.advance()
            elif char == '>':
                if self.peek_char() == '>':
                    self.tokens.append(Token(TokenType.REDIRECT_APPEND, '>>', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.REDIRECT_OUT, '>', start_pos))
                    self.advance()
            elif char in '"\'':
                value = self.read_quoted_string(char)
                self.tokens.append(Token(TokenType.STRING, value, start_pos))
            elif char == '$':
                if self.peek_char() == '(':
                    # Handle $(...) command substitution
                    value = self.read_command_substitution()
                    self.tokens.append(Token(TokenType.COMMAND_SUB, value, start_pos))
                else:
                    self.advance()
                    if self.current_char() == '{':
                        # Handle ${...} syntax
                        self.advance()  # Skip {
                        var_content = ''
                        while self.current_char() and self.current_char() != '}':
                            var_content += self.current_char()
                            self.advance()
                        if self.current_char() == '}':
                            self.advance()  # Skip }
                        self.tokens.append(Token(TokenType.VARIABLE, '{' + var_content + '}', start_pos))
                    else:
                        var_name = self.read_word()
                        self.tokens.append(Token(TokenType.VARIABLE, var_name, start_pos))
            elif char == '`':
                # Handle backtick command substitution
                value = self.read_backtick_substitution()
                self.tokens.append(Token(TokenType.COMMAND_SUB_BACKTICK, value, start_pos))
            elif char == '(':
                self.tokens.append(Token(TokenType.LPAREN, '(', start_pos))
                self.advance()
            elif char == ')':
                self.tokens.append(Token(TokenType.RPAREN, ')', start_pos))
                self.advance()
            elif char == '{':
                self.tokens.append(Token(TokenType.LBRACE, '{', start_pos))
                self.advance()
            elif char == '}':
                self.tokens.append(Token(TokenType.RBRACE, '}', start_pos))
                self.advance()
            else:
                word = self.read_word()
                # Check if word is 'function' keyword
                if word == 'function':
                    self.tokens.append(Token(TokenType.FUNCTION, word, start_pos))
                else:
                    self.tokens.append(Token(TokenType.WORD, word, start_pos))
        
        self.tokens.append(Token(TokenType.EOF, '', self.position))
        return self.tokens


def tokenize(input_string: str) -> List[Token]:
    tokenizer = Tokenizer(input_string)
    return tokenizer.tokenize()