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
        
        # Check for array initialization: name=( or name+=(
        if ('=' in word_token.value or '+=' in word_token.value) and (word_token.value.endswith('=') or word_token.value.endswith('+=')):
            # Word contains equals at the end (e.g., "arr=" or "arr+=")
            self.parser.advance()
            if self.parser.match(TokenType.LPAREN):
                self.parser.current = saved_pos
                return True
        
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
        if self.parser.match(TokenType.LBRACKET):
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