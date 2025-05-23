from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    WORD = auto()
    PIPE = auto()
    REDIRECT_IN = auto()
    REDIRECT_OUT = auto()
    REDIRECT_APPEND = auto()
    HEREDOC = auto()
    HEREDOC_STRIP = auto()
    SEMICOLON = auto()
    AMPERSAND = auto()
    NEWLINE = auto()
    EOF = auto()
    STRING = auto()
    VARIABLE = auto()


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
        while self.current_char() and self.current_char() not in ' \t\n|<>;&':
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
    
    def tokenize(self) -> List[Token]:
        while self.current_char() is not None:
            self.skip_whitespace()
            
            if self.current_char() is None:
                break
            
            start_pos = self.position
            char = self.current_char()
            
            if char == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', start_pos))
                self.advance()
            elif char == '|':
                self.tokens.append(Token(TokenType.PIPE, '|', start_pos))
                self.advance()
            elif char == ';':
                self.tokens.append(Token(TokenType.SEMICOLON, ';', start_pos))
                self.advance()
            elif char == '&':
                self.tokens.append(Token(TokenType.AMPERSAND, '&', start_pos))
                self.advance()
            elif char == '<':
                if self.peek_char() == '<':
                    # Check for << or <<-
                    self.advance()  # Skip first <
                    if self.peek_char() == '-':
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
            else:
                word = self.read_word()
                self.tokens.append(Token(TokenType.WORD, word, start_pos))
        
        self.tokens.append(Token(TokenType.EOF, '', self.position))
        return self.tokens


def tokenize(input_string: str) -> List[Token]:
    tokenizer = Tokenizer(input_string)
    return tokenizer.tokenize()