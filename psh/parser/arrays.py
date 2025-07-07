"""
Array parsing for PSH shell.

This module handles parsing of array assignments and initializations.
"""

from typing import List
from ..token_types import Token, TokenType
from ..ast_nodes import ArrayAssignment, ArrayInitialization, ArrayElementAssignment
from ..token_stream import TokenStream
from .helpers import TokenGroups


class ArrayParser:
    """Parser for array constructs."""
    
    def __init__(self, main_parser):
        """Initialize with reference to main parser."""
        self.parser = main_parser
    
    def is_array_assignment(self) -> bool:
        """Check if current position starts an array assignment."""
        if not self.parser.match(TokenType.WORD):
            return False
        
        saved_pos = self.parser.current
        word_token = self.parser.peek()
        
        # Check for array element assignment first: name[index]=value
        # ModularLexer might tokenize this as "name[index]" "=value" or "name[index]=value"
        if '[' in word_token.value and ']' in word_token.value:
            # This might be array element assignment
            self.parser.advance()  # consume word
            if self.parser.match(TokenType.WORD) and (self.parser.peek().value.startswith('=') or self.parser.peek().value == '+='):
                # Pattern: "arr[0]" "=value" or "arr[0]" "+=" "value"
                self.parser.current = saved_pos
                return True
            self.parser.current = saved_pos
            # Also check if it's all in one token: "arr[0]=value" or "arr[0]+=value"
            if '=' in word_token.value:
                equals_pos = word_token.value.index('+=') if '+=' in word_token.value else word_token.value.index('=')
                if word_token.value.index('[') < equals_pos:
                    return True
        
        # Check for array initialization: name=( or name+=(
        if ('=' in word_token.value or '+=' in word_token.value) and (word_token.value.endswith('=') or word_token.value.endswith('+=')):
            # Word contains equals at the end (e.g., "arr=" or "arr+=")
            self.parser.advance()
            if self.parser.match(TokenType.LPAREN):
                self.parser.current = saved_pos
                return True
        else:
            # Check for separate = token (ModularLexer behavior)
            self.parser.advance()  # consume word
            if self.parser.match(TokenType.WORD) and self.parser.peek().value == '=':
                self.parser.advance()  # consume =
                if self.parser.match(TokenType.LPAREN):
                    self.parser.current = saved_pos
                    return True
            # Also check for += as two tokens
            elif self.parser.match(TokenType.WORD) and self.parser.peek().value == '+=':
                self.parser.advance()  # consume +=
                if self.parser.match(TokenType.LPAREN):
                    self.parser.current = saved_pos
                    return True
            # Reset position to check for array element assignment
            self.parser.current = saved_pos
        
        # Check for array element assignment: name[
        self.parser.advance()  # consume word
        if self.parser.match(TokenType.LBRACKET):
            self.parser.current = saved_pos
            return True
        
        self.parser.current = saved_pos
        return False
    
    def parse_array_assignment(self) -> ArrayAssignment:
        """Parse an array assignment (initialization or element)."""
        name_token = self.parser.expect(TokenType.WORD)
        
        # Check for array element assignment: name[index]=value
        # ModularLexer might tokenize this differently
        if '[' in name_token.value and ']' in name_token.value:
            # Extract name and handle ModularLexer patterns
            if '=' in name_token.value:
                # Pattern: "arr[0]=value" or "arr[0]+=value" all in one token
                is_append = False
                if '+=' in name_token.value:
                    equals_pos = name_token.value.index('+=')
                    is_append = True
                else:
                    equals_pos = name_token.value.index('=')
                
                bracket_pos = name_token.value.index('[')
                close_bracket_pos = name_token.value.index(']')
                
                if bracket_pos < equals_pos < close_bracket_pos:
                    raise self.parser._error("Invalid array syntax")
                    
                name = name_token.value[:bracket_pos]
                index_str = name_token.value[bracket_pos+1:close_bracket_pos]
                value = name_token.value[equals_pos+(2 if is_append else 1):]
                
                # Create tokens for the index
                index_tokens = [Token(TokenType.WORD, index_str, 0)]
                
                return ArrayElementAssignment(
                    name=name,
                    index=index_tokens,
                    value=value,
                    value_type='WORD',
                    value_quote_type=None,
                    is_append=is_append
                )
            else:
                # Pattern: "arr[0]" "=value" in separate tokens
                bracket_pos = name_token.value.index('[')
                close_bracket_pos = name_token.value.index(']')
                name = name_token.value[:bracket_pos]
                index_str = name_token.value[bracket_pos+1:close_bracket_pos]
                
                # Next token should be "=value" or "+="
                if not self.parser.match(TokenType.WORD):
                    raise self.parser._error("Expected '=' after array index")
                    
                equals_token = self.parser.advance()
                if not (equals_token.value.startswith('=') or equals_token.value == '+='):
                    raise self.parser._error("Expected '=' or '+=' after array index")
                
                is_append = equals_token.value == '+=' or equals_token.value.startswith('+=')
                
                # Extract value
                if equals_token.value == '=' or equals_token.value == '+=':
                    # Value is in next token
                    if not self.parser.match_any(TokenGroups.WORD_LIKE):
                        raise self.parser._error("Expected value after '='")
                    value, value_type, quote_type = self.parser.commands.parse_composite_argument()
                else:
                    # Value is part of equals token (e.g., "=value")
                    value = equals_token.value[2:] if is_append else equals_token.value[1:]
                    value_type = 'WORD'
                    quote_type = None
                
                # Create tokens for the index
                index_tokens = [Token(TokenType.WORD, index_str, 0)]
                
                return ArrayElementAssignment(
                    name=name,
                    index=index_tokens,
                    value=value,
                    value_type=value_type,
                    value_quote_type=quote_type,
                    is_append=is_append
                )
        
        # Check for array element assignment with separate bracket: name[index]=value
        if self.parser.match(TokenType.LBRACKET):
            name = name_token.value
            return self._parse_array_element_assignment(name)
        
        # Otherwise it's array initialization: name=(elements) or name+=(elements)
        # The name token might end with '=' or '+=' (old lexer) or be followed by separate tokens (new lexer)
        name = name_token.value
        is_append = False
        
        if name_token.value.endswith('+='):
            name = name_token.value[:-2]  # Remove the trailing '+='
            is_append = True
        elif name_token.value.endswith('='):
            name = name_token.value[:-1]  # Remove the trailing '='
            is_append = False
        else:
            # Check for separate = or += token (ModularLexer)
            if self.parser.match(TokenType.WORD):
                eq_token = self.parser.peek()
                if eq_token.value == '+=':
                    self.parser.advance()  # consume +=
                    is_append = True
                elif eq_token.value == '=':
                    self.parser.advance()  # consume =
                    is_append = False
                else:
                    raise self.parser._error("Expected '=' or '+=' in array initialization")
            else:
                raise self.parser._error("Expected '=' or '+=' in array initialization")
        
        return self._parse_array_initialization(name, is_append)
    
    def _parse_array_key_tokens(self) -> List[Token]:
        """Parse array key as list of tokens for later evaluation.
        
        This implements the late binding approach where we collect tokens
        without evaluation, allowing the executor to determine whether to
        evaluate as arithmetic (indexed arrays) or string (associative arrays).
        """
        # Create a TokenStream from current position
        stream = TokenStream(self.parser.tokens, self.parser.current)
        
        # Collect tokens until balanced RBRACKET
        tokens = stream.collect_until_balanced(
            TokenType.LBRACKET, 
            TokenType.RBRACKET,
            respect_quotes=True,
            include_delimiters=False
        )
        
        # Validate tokens
        valid_key_tokens = {
            TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
            TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
            TokenType.ARITH_EXPANSION, TokenType.LPAREN, TokenType.RPAREN
        }
        
        for token in tokens:
            if token.type not in valid_key_tokens:
                raise self.parser._error(f"Invalid token in array key: {token.type}")
        
        # Update parser position
        self.parser.current = stream.pos
        
        return tokens
    
    def _parse_array_element_assignment(self, name: str) -> ArrayElementAssignment:
        """Parse array element assignment: name[index]=value"""
        self.parser.expect(TokenType.LBRACKET)
        
        # Parse index as list of tokens for late binding (associative vs indexed array evaluation)
        index_tokens = self._parse_array_key_tokens()
        
        # Note: _parse_array_key_tokens already consumed the RBRACKET
        
        # Next token should be a WORD starting with '='
        if not self.parser.match(TokenType.WORD):
            raise self.parser._error("Expected '=' after array index")
        
        equals_token = self.parser.peek()
        if not (equals_token.value.startswith('=') or equals_token.value.startswith('+=')):
            raise self.parser._error("Expected '=' or '+=' after array index")
        
        self.parser.advance()  # consume the equals token
        
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
            if not self.parser.match_any(TokenGroups.WORD_LIKE):
                raise self.parser._error("Expected value after '=' in array element assignment")
            value, value_type, quote_type = self.parser.commands.parse_composite_argument()
        
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
        self.parser.expect(TokenType.LPAREN)
        
        elements = []
        element_types = []
        element_quote_types = []
        
        # Parse array elements
        while not self.parser.match(TokenType.RPAREN) and not self.parser.at_end():
            if self.parser.match_any(TokenGroups.WORD_LIKE):
                value, arg_type, quote_type = self.parser.commands.parse_composite_argument()
                elements.append(value)
                element_types.append(arg_type)
                element_quote_types.append(quote_type)
            else:
                break
        
        self.parser.expect(TokenType.RPAREN)
        
        return ArrayInitialization(
            name=name,
            elements=elements,
            element_types=element_types,
            element_quote_types=element_quote_types,
            is_append=is_append
        )