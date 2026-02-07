"""
Array parsing for PSH shell.

This module handles parsing of array assignments and initializations.
"""

from typing import List

from ....ast_nodes import ArrayAssignment, ArrayElementAssignment, ArrayInitialization
from ....token_types import Token, TokenType
from ..helpers import TokenGroups


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
        # First verify the word looks like a valid variable name
        if not self._is_valid_variable_name(word_token.value):
            self.parser.current = saved_pos
            return False

        self.parser.advance()  # consume word
        if self.parser.match(TokenType.LBRACKET):
            self.parser.current = saved_pos
            return True
        # Also check for WORD token containing just "[" (from ModularLexer)
        elif self.parser.match(TokenType.WORD) and self.parser.peek().value == '[':
            # Look ahead to verify this is really an array assignment
            # by checking for ] followed by = or +=
            temp_pos = self.parser.current
            self.parser.advance()  # skip [

            # Skip tokens until we find ] or give up
            bracket_count = 1
            found_assignment = False
            while bracket_count > 0 and not self.parser.at_end():
                token = self.parser.peek()
                if token.type == TokenType.WORD:
                    if '[' in token.value:
                        bracket_count += token.value.count('[')
                    if ']' in token.value:
                        bracket_count -= token.value.count(']')
                        if bracket_count == 0:
                            # Check if followed by = or +=
                            self.parser.advance()
                            if not self.parser.at_end():
                                next_token = self.parser.peek()
                                if (next_token.type == TokenType.WORD and
                                    (next_token.value.startswith('=') or next_token.value == '+=')):
                                    found_assignment = True
                            break
                self.parser.advance()

            self.parser.current = saved_pos
            return found_assignment

        self.parser.current = saved_pos
        return False

    def _is_valid_variable_name(self, name: str) -> bool:
        """Check if a string is a valid shell variable name."""
        if not name:
            return False
        # Must start with letter or underscore
        if not (name[0].isalpha() or name[0] == '_'):
            return False
        # Rest must be alphanumeric or underscore
        return all(c.isalnum() or c == '_' for c in name[1:])

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

                # If value is empty, check for value in next token
                value_type = 'WORD'
                quote_type = None
                if not value and self.parser.match_any(TokenGroups.WORD_LIKE):
                    value, value_type, quote_type = self.parser.commands.parse_composite_argument()

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
        # Also check for WORD token containing just "[" (from ModularLexer)
        elif self.parser.match(TokenType.WORD) and self.parser.peek().value == '[':
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
        tokens = []
        bracket_count = 0

        # Collect tokens until we find the closing bracket
        while not self.parser.at_end():
            current_token = self.parser.peek()

            # Handle different token types
            if current_token.type == TokenType.LBRACKET:
                bracket_count += 1
                tokens.append(current_token)
                self.parser.advance()
            elif current_token.type == TokenType.RBRACKET:
                bracket_count -= 1
                if bracket_count < 0:
                    # This is our closing bracket
                    self.parser.advance()
                    break
                else:
                    tokens.append(current_token)
                    self.parser.advance()
            elif current_token.type == TokenType.WORD and ']' in current_token.value:
                # Handle case where ]=value is a single token
                bracket_pos = current_token.value.find(']')
                if bracket_pos == 0:
                    # Token starts with ], this is our closing bracket
                    # DON'T advance here - leave the token for the equals parsing logic
                    break
                else:
                    # ] is in the middle, extract the part before ]
                    index_part = current_token.value[:bracket_pos]
                    if index_part:
                        # Create a token for the index part
                        index_token = Token(TokenType.WORD, index_part, current_token.position)
                        tokens.append(index_token)
                    # DON'T advance here - leave the token for the equals parsing logic
                    break
            else:
                # Regular token, add to index
                valid_key_tokens = {
                    TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
                    TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
                    TokenType.ARITH_EXPANSION, TokenType.LPAREN, TokenType.RPAREN
                }

                if current_token.type not in valid_key_tokens:
                    raise self.parser._error(f"Invalid token in array key: {current_token.type}")

                tokens.append(current_token)
                self.parser.advance()

        return tokens

    def _parse_array_element_assignment(self, name: str) -> ArrayElementAssignment:
        """Parse array element assignment: name[index]=value"""
        # Handle both LBRACKET token and WORD "[" token
        if self.parser.match(TokenType.LBRACKET):
            self.parser.advance()
        elif self.parser.match(TokenType.WORD) and self.parser.peek().value == '[':
            self.parser.advance()
        else:
            raise self.parser._error("Expected '[' after array name")

        # Parse index as list of tokens for late binding (associative vs indexed array evaluation)
        index_tokens = self._parse_array_key_tokens()

        # Note: _parse_array_key_tokens already consumed the RBRACKET

        # Handle different cases for the equals token
        equals_token = None
        if self.parser.match(TokenType.WORD):
            current_token = self.parser.peek()
            if current_token.value.startswith('=') or current_token.value.startswith('+='):
                # Case: separate token starting with = (like "=value")
                equals_token = current_token
            elif current_token.value.startswith(']=') or current_token.value.startswith(']+='):
                # Case: token like "]=value" - extract the part after ]
                bracket_pos = current_token.value.find(']')
                equals_part = current_token.value[bracket_pos + 1:]
                # Create a new token for the equals part
                equals_token = Token(TokenType.WORD, equals_part, current_token.position + bracket_pos + 1)
            else:
                raise self.parser._error("Expected '=' or '+=' after array index")
        else:
            raise self.parser._error("Expected '=' after array index")

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
