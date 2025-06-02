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
    ARITH_EXPANSION = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    FUNCTION = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    FI = auto()
    ELIF = auto()
    WHILE = auto()
    DO = auto()
    DONE = auto()
    FOR = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    CASE = auto()
    ESAC = auto()
    DOUBLE_SEMICOLON = auto()  # ;;
    SEMICOLON_AMP = auto()     # ;&
    AMP_SEMICOLON = auto()     # ;;&
    PROCESS_SUB_IN = auto()    # <(...)
    PROCESS_SUB_OUT = auto()   # >(...)
    EXCLAMATION = auto()       # !
    DOUBLE_LBRACKET = auto()   # [[
    DOUBLE_RBRACKET = auto()   # ]]
    REGEX_MATCH = auto()       # =~


@dataclass
class Token:
    type: TokenType
    value: str
    position: int
    quote_type: Optional[str] = None  # Track the quote character used (' or " or None)


class Tokenizer:
    def __init__(self, input_string: str):
        self.input = input_string
        self.position = 0
        self.tokens: List[Token] = []
        self.in_double_brackets = 0  # Track nesting level of [[ ]]
    
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
        # Inside [[ ]], we need to stop at ] to avoid consuming ]]
        stop_chars = ' \t\n|<>;&`(){}'
        if self.in_double_brackets > 0:
            stop_chars += ']'
        
        while self.current_char() and self.current_char() not in stop_chars:
            if self.current_char() == '\\' and self.peek_char():
                # Handle escape sequences
                self.advance()  # Skip backslash
                if self.current_char():
                    # For $, keep it escaped to prevent variable expansion
                    if self.current_char() == '$':
                        value += '\\$'
                    elif self.current_char() == '\\':
                        # Escaped backslash becomes single backslash
                        value += '\\'
                    else:
                        value += self.current_char()
                    self.advance()
            elif self.current_char() == '$' and self.peek_char() == '(' and self.peek_char(2) == '(':
                # Handle arithmetic expansion within a word (e.g., c=$((a + b)))
                arith_exp = self.read_arithmetic_expansion()
                value += arith_exp
            elif self.current_char() == '[':
                # Check if this looks like a bracket expression pattern
                # We need to be careful not to consume [[ ]] operators
                if self.in_double_brackets > 0:
                    # Inside [[ ]], don't treat [ as bracket pattern
                    value += self.current_char()
                    self.advance()
                else:
                    # Outside [[ ]], check if this could be a valid bracket pattern
                    # Look ahead to see if there's a closing ] before any ]] sequence
                    saved_pos = self.position
                    found_closing = False
                    temp_pos = self.position + 1
                    
                    while temp_pos < len(self.input):
                        if temp_pos >= len(self.input):
                            break
                        if self.input[temp_pos] == ']':
                            # Found a ], this could be a bracket pattern close
                            found_closing = True
                            break
                        elif self.input[temp_pos] in ' \t\n|<>;&`(){}':
                            # Hit a delimiter, stop looking
                            break
                        temp_pos += 1
                    
                    if found_closing:
                        # Valid bracket pattern, read it
                        value += self.current_char()
                        self.advance()
                        # Read until closing ]
                        while self.current_char() and self.current_char() != ']':
                            if self.current_char() == '\\' and self.peek_char():
                                value += self.current_char()
                                self.advance()
                                if self.current_char():
                                    value += self.current_char()
                                    self.advance()
                            else:
                                value += self.current_char()
                                self.advance()
                        if self.current_char() == ']':
                            value += self.current_char()
                            self.advance()
                    else:
                        # No valid bracket pattern, just a [ character
                        value += self.current_char()
                        self.advance()
            else:
                value += self.current_char()
                self.advance()
        return value
    
    def read_pattern_word(self) -> str:
        """Read a word that may contain pattern characters like [abc] or [a-z]."""
        value = ''
        
        # If we start with [, read the whole bracket expression
        if self.current_char() == '[':
            # Special handling when inside [[ ]]
            if self.in_double_brackets > 0:
                # Inside [[ ]], just read [ as a single character
                value += self.current_char()
                self.advance()
            else:
                # Outside [[ ]], try to read as bracket pattern
                value += self.current_char()
                self.advance()
                
                # Read until we find the closing ] or hit whitespace
                while self.current_char() and self.current_char() != ']' and self.current_char() not in ' \t\n':
                    if self.current_char() == '\\' and self.peek_char():
                        # Handle escape sequences
                        value += self.current_char()
                        self.advance()
                        if self.current_char():
                            value += self.current_char()
                            self.advance()
                    else:
                        value += self.current_char()
                        self.advance()
                
                # Include the closing ] only if we found it without hitting whitespace
                if self.current_char() == ']':
                    value += self.current_char()
                    self.advance()
        
        # Continue reading the rest of the word (e.g., .txt after [12])
        # Inside [[ ]], we need to stop at ] to avoid consuming ]]
        stop_chars = ' \t\n|<>;&`(){}'
        if self.in_double_brackets > 0:
            stop_chars += ']'
            
        while self.current_char() and self.current_char() not in stop_chars:
            if self.current_char() == '\\' and self.peek_char():
                # Handle escape sequences
                self.advance()  # Skip backslash
                if self.current_char():
                    value += self.current_char()
                    self.advance()
            elif self.current_char() == '[':
                # Another bracket expression in the same word
                value += self.current_char()
                self.advance()
                while self.current_char() and self.current_char() != ']':
                    if self.current_char() == '\\' and self.peek_char():
                        value += self.current_char()
                        self.advance()
                        if self.current_char():
                            value += self.current_char()
                            self.advance()
                    else:
                        value += self.current_char()
                        self.advance()
                if self.current_char() == ']':
                    value += self.current_char()
                    self.advance()
            else:
                value += self.current_char()
                self.advance()
        
        return value
    
    def is_command_position(self) -> bool:
        """Check if we're at a position where a command is expected."""
        if not self.tokens:
            return True  # Start of input
        
        # Look at the last non-whitespace token
        last_token = self.tokens[-1]
        
        # Commands come after these tokens
        if last_token.type in (TokenType.SEMICOLON, TokenType.PIPE, TokenType.LPAREN,
                               TokenType.LBRACE, TokenType.AND_AND, TokenType.OR_OR,
                               TokenType.AMPERSAND):
            return True
        
        # After keywords that expect commands
        if last_token.type == TokenType.WORD and last_token.value in ('if', 'elif', 'while', 'then', 'else', 'do'):
            return True
        
        # Also check for keyword tokens
        if last_token.type in (TokenType.IF, TokenType.ELIF, TokenType.WHILE, 
                               TokenType.THEN, TokenType.ELSE, TokenType.DO):
            return True
        
        # After keywords that DON'T expect commands (these are followed by expressions/patterns)
        if last_token.type == TokenType.WORD and last_token.value in ('case', 'in'):
            return False
        
        # Check for pattern context in case statements
        # If we see "case $var in", the next position is for patterns, not commands
        if len(self.tokens) >= 2 and self.tokens[-2].type == TokenType.WORD and self.tokens[-2].value == 'in':
            return False
        
        return False
    
    def is_keyword_context(self, word: str) -> bool:
        """Check if we're in a position where this word should be a keyword."""
        if not self.tokens:
            return True  # Start of input
        
        last_token = self.tokens[-1]
        
        # Special case: don't treat keywords as keywords when they're arguments to echo
        if len(self.tokens) >= 2:
            prev_token = self.tokens[-2] if len(self.tokens) >= 2 else None
            if (last_token.type == TokenType.WORD and last_token.value == 'echo' and
                prev_token and prev_token.type in [TokenType.SEMICOLON, TokenType.NEWLINE, 
                                                  TokenType.AND_AND, TokenType.OR_OR,
                                                  TokenType.PIPE, TokenType.LBRACE, TokenType.THEN, TokenType.ELSE]):
                return False  # Don't treat as keyword when it's an echo argument
        
        # Handle specific keyword contexts
        if word in ['if', 'function', 'case']:
            # 'if', 'function', and 'case' are keywords at command start positions
            return last_token.type in [
                TokenType.SEMICOLON, TokenType.NEWLINE, 
                TokenType.AND_AND, TokenType.OR_OR,
                TokenType.PIPE, TokenType.LBRACE
            ]
        elif word in ['then', 'else', 'elif', 'fi', 'do', 'done', 'in', 'break', 'continue', 'esac']:
            # Control structure keywords - generally always keywords unless they're echo args
            return True
        elif word in ['while', 'for']:
            # 'while' and 'for' are keywords at command start positions (like 'if')
            return last_token.type in [
                TokenType.SEMICOLON, TokenType.NEWLINE, 
                TokenType.AND_AND, TokenType.OR_OR,
                TokenType.PIPE, TokenType.LBRACE, TokenType.THEN, TokenType.ELSE,
                TokenType.DO  # Allow nested loops after 'do'
            ]
        
        return False
    
    def read_quoted_string(self, quote_char: str) -> str:
        self.advance()  # Skip opening quote
        value = ''
        
        # Single quotes: no escape sequences allowed, everything is literal
        if quote_char == "'":
            while self.current_char() and self.current_char() != quote_char:
                value += self.current_char()
                self.advance()
        else:
            # Double quotes: allow escaping of quote char and other special chars
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
    
    def read_arithmetic_expansion(self) -> str:
        """Read $((...)) arithmetic expansion"""
        self.advance()  # Skip $
        self.advance()  # Skip first (
        self.advance()  # Skip second (
        
        expr = ''
        paren_depth = 0  # Track parentheses balance within the expression
        
        while self.current_char() is not None:
            char = self.current_char()
            
            # Check if we've found the closing ))
            if char == ')' and paren_depth == 0 and self.peek_char() == ')':
                # Found the closing ))
                self.advance()  # Skip first )
                self.advance()  # Skip second )
                break
            
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
                if paren_depth < 0:
                    raise SyntaxError(f"Unmatched ) in arithmetic expansion at position {self.position}")
            
            expr += char
            self.advance()
        
        return f"$(({expr}))"
    
    def read_process_substitution(self, direction: str) -> str:
        """Read <(...) or >(...) process substitution"""
        # Skip < or >
        self.advance()
        # Skip (
        self.advance()
        
        paren_count = 1
        content = []
        
        while self.current_char() is not None and paren_count > 0:
            char = self.current_char()
            
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    break
            
            content.append(char)
            self.advance()
        
        if paren_count != 0:
            raise SyntaxError(f"Unclosed process substitution at position {self.position}")
        
        # Skip closing )
        self.advance()
        
        command = ''.join(content)
        return f"{('<' if direction == 'in' else '>')}({command})"
    
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
                if self.peek_char() == ';':
                    # Check for ;;& pattern
                    if self.peek_char(2) == '&':
                        self.tokens.append(Token(TokenType.AMP_SEMICOLON, ';;&', start_pos))
                        self.advance()
                        self.advance()
                        self.advance()
                    else:
                        self.tokens.append(Token(TokenType.DOUBLE_SEMICOLON, ';;', start_pos))
                        self.advance()
                        self.advance()
                elif self.peek_char() == '&':
                    self.tokens.append(Token(TokenType.SEMICOLON_AMP, ';&', start_pos))
                    self.advance()
                    self.advance()
                else:
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
            elif char == '!':
                # Check if this is part of != operator
                if self.peek_char() == '=':
                    # This is !=, treat it as a WORD token
                    self.advance()  # Skip !
                    self.advance()  # Skip =
                    self.tokens.append(Token(TokenType.WORD, '!=', start_pos))
                else:
                    # Stand-alone !, used for pipeline negation
                    self.tokens.append(Token(TokenType.EXCLAMATION, '!', start_pos))
                    self.advance()
            elif char == '<':
                # Inside [[ ]], < is a comparison operator
                if self.in_double_brackets > 0:
                    self.tokens.append(Token(TokenType.WORD, '<', start_pos))
                    self.advance()
                elif self.peek_char() == '(':
                    # Process substitution <(...)
                    value = self.read_process_substitution('in')
                    self.tokens.append(Token(TokenType.PROCESS_SUB_IN, value, start_pos))
                elif self.peek_char() == '<':
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
                # Inside [[ ]], > is a comparison operator
                if self.in_double_brackets > 0:
                    self.tokens.append(Token(TokenType.WORD, '>', start_pos))
                    self.advance()
                elif self.peek_char() == '(':
                    # Process substitution >(...)
                    value = self.read_process_substitution('out')
                    self.tokens.append(Token(TokenType.PROCESS_SUB_OUT, value, start_pos))
                elif self.peek_char() == '>':
                    self.tokens.append(Token(TokenType.REDIRECT_APPEND, '>>', start_pos))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '&':
                    # Handle >&N redirect duplication
                    self.advance()  # Skip >
                    self.advance()  # Skip &
                    dup_target = ''
                    while self.current_char() and self.current_char().isdigit():
                        dup_target += self.current_char()
                        self.advance()
                    if dup_target:
                        self.tokens.append(Token(TokenType.REDIRECT_DUP, f'>&{dup_target}', start_pos))
                    else:
                        # >&- means close the file descriptor
                        if self.current_char() == '-':
                            self.advance()
                            self.tokens.append(Token(TokenType.REDIRECT_DUP, '>&-', start_pos))
                        else:
                            # Invalid syntax, treat as separate tokens
                            self.position = start_pos + 1  # Reset to after >
                            self.tokens.append(Token(TokenType.REDIRECT_OUT, '>', start_pos))
                else:
                    self.tokens.append(Token(TokenType.REDIRECT_OUT, '>', start_pos))
                    self.advance()
            elif char in '"\'':
                value = self.read_quoted_string(char)
                self.tokens.append(Token(TokenType.STRING, value, start_pos, quote_type=char))
            elif char == '$':
                if self.peek_char() == '(':
                    # Check if it's $(( for arithmetic or $( for command substitution
                    if self.peek_char(2) == '(':
                        # Handle $((...)) arithmetic expansion
                        value = self.read_arithmetic_expansion()
                        self.tokens.append(Token(TokenType.ARITH_EXPANSION, value, start_pos))
                    else:
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
            elif char == '[':
                if self.peek_char() == '[' and self.in_double_brackets == 0 and self.is_command_position():
                    # Only treat [[ as special if we're not already inside [[]] and at command position
                    self.tokens.append(Token(TokenType.DOUBLE_LBRACKET, '[[', start_pos))
                    self.advance()
                    self.advance()
                    self.in_double_brackets += 1
                else:
                    # Not [[ or not at command position - read as part of word/pattern
                    word = self.read_pattern_word()
                    self.tokens.append(Token(TokenType.WORD, word, start_pos))
            elif char == ']':
                if self.peek_char() == ']' and self.in_double_brackets > 0:
                    self.tokens.append(Token(TokenType.DOUBLE_RBRACKET, ']]', start_pos))
                    self.advance()
                    self.advance()
                    self.in_double_brackets -= 1
                else:
                    # Regular ] should have been consumed as part of a pattern
                    # If we get here, it's a standalone ]
                    self.tokens.append(Token(TokenType.WORD, ']', start_pos))
                    self.advance()
            elif char == '=' and self.peek_char() == '~' and self.in_double_brackets > 0:
                self.tokens.append(Token(TokenType.REGEX_MATCH, '=~', start_pos))
                self.advance()
                self.advance()
            else:
                # Special check for [[ before reading word
                if char == '[' and self.peek_char() == '[' and self.in_double_brackets == 0 and self.is_command_position():
                    self.tokens.append(Token(TokenType.DOUBLE_LBRACKET, '[[', start_pos))
                    self.advance()
                    self.advance()
                    self.in_double_brackets += 1
                else:
                    word = self.read_word()
                    # Check for keywords based on word and context
                    if word == 'function' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.FUNCTION, word, start_pos))
                    elif word == 'if' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.IF, word, start_pos))
                    elif word == 'then' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.THEN, word, start_pos))
                    elif word == 'else' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.ELSE, word, start_pos))
                    elif word == 'elif' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.ELIF, word, start_pos))
                    elif word == 'fi' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.FI, word, start_pos))
                    elif word == 'while' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.WHILE, word, start_pos))
                    elif word == 'do' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.DO, word, start_pos))
                    elif word == 'done' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.DONE, word, start_pos))
                    elif word == 'for' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.FOR, word, start_pos))
                    elif word == 'in' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.IN, word, start_pos))
                    elif word == 'break' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.BREAK, word, start_pos))
                    elif word == 'continue' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.CONTINUE, word, start_pos))
                    elif word == 'case' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.CASE, word, start_pos))
                    elif word == 'esac' and self.is_keyword_context(word):
                        self.tokens.append(Token(TokenType.ESAC, word, start_pos))
                    else:
                        # Not a keyword or not in keyword context, treat as regular word
                        self.tokens.append(Token(TokenType.WORD, word, start_pos))
        
        self.tokens.append(Token(TokenType.EOF, '', self.position))
        return self.tokens


def tokenize(input_string: str) -> List[Token]:
    """Tokenize input string, with brace expansion preprocessing."""
    from .brace_expansion import BraceExpander, BraceExpansionError
    
    try:
        # Expand braces first
        expander = BraceExpander()
        expanded_string = expander.expand_line(input_string)
    except BraceExpansionError as e:
        # If brace expansion fails (e.g., too many items), 
        # tokenize the original string to maintain backwards compatibility
        # This allows the shell to still process the command, even if
        # brace expansion is not performed
        tokenizer = Tokenizer(input_string)
        return tokenizer.tokenize()
    
    # Then run normal tokenization on expanded string
    tokenizer = Tokenizer(expanded_string)
    return tokenizer.tokenize()