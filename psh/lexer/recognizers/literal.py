"""Literal token recognizer for strings, numbers, and identifiers."""

from typing import Optional, Tuple, Set
from .base import ContextualRecognizer
from ..state_context import LexerContext
from ...token_types import Token, TokenType
from ..unicode_support import is_identifier_start, is_identifier_char, is_whitespace


class LiteralRecognizer(ContextualRecognizer):
    """Recognizes literal tokens: strings, numbers, identifiers."""
    
    def __init__(self):
        super().__init__()
        self.config = None  # Will be set by ModularLexer
    
    # Characters that can terminate a word
    WORD_TERMINATORS = {
        ' ', '\t', '\n', '\r', '\f', '\v',  # Whitespace
        '|', '&', ';', '(', ')', '{', '}',       # Operators
        '<', '>', '!', '=', '+',                 # More operators  
        '[', ']',                                # Bracket operators
        '$', '`', "'",  '"',                     # Special characters
    }
    
    @property
    def priority(self) -> int:
        """Medium priority for literals."""
        return 70
    
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """Check if current position might be a literal."""
        if pos >= len(input_text):
            return False
        
        char = input_text[pos]
        
        # Skip whitespace and operators (handled by other recognizers)
        # But allow disabled quotes to be part of words
        if char in self.WORD_TERMINATORS:
            # Allow disabled quotes/expansions/operators to be recognized as word chars
            if char == "'" and self.config and not self.config.enable_single_quotes:
                return True  # Can be part of word
            if char == '"' and self.config and not self.config.enable_double_quotes:
                return True  # Can be part of word
            if char == '$' and self.config and not self.config.enable_variable_expansion:
                return True  # Can be part of word
            if char == '$' and self.config and self.config.enable_variable_expansion and not self._can_start_valid_expansion(input_text, pos):
                return True  # Can be part of word (invalid expansion)
            if char == '`' and self.config and not self.config.enable_command_substitution:
                return True  # Can be part of word
            if char == '|' and self.config and not self.config.enable_pipes:
                return True  # Can be part of word
            if char in ['<', '>'] and self.config and not self.config.enable_redirections:
                return True  # Can be part of word
            if char == '&' and self.config and not self.config.enable_background:
                return True  # Can be part of word
            # Inside [[ ]], < and > are comparison operators that should be tokenized as words
            if char in ['<', '>'] and context.bracket_depth > 0:
                return True  # Can be part of word
            return False
        
        # Skip quotes and expansions based on configuration, but only if they can be fully handled
        # For $ and `, we need to check if they can actually form valid expansions
        if char == '$' and self.config and self.config.enable_variable_expansion:
            # Only skip if this can actually start a valid expansion
            # Otherwise, let literal recognizer handle it as a regular character
            if self._can_start_valid_expansion(input_text, pos):
                return False  # Let expansion parser handle it
        if char == '`' and self.config and self.config.enable_command_substitution:
            return False  # Let expansion parser handle it
        if char == "'" and self.config and self.config.enable_single_quotes:
            return False  # Let quote parser handle it
        if char == '"' and self.config and self.config.enable_double_quotes:
            return False  # Let quote parser handle it
        
        # If we get here, it might be a literal
        return True
    
    def recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Recognize literal tokens."""
        if not self.can_recognize(input_text, pos, context):
            return None
        
        # Track whether we saw inline ANSI-C quote segments
        saw_inline_ansi = False

        # Read until we hit a word terminator
        start_pos = pos
        value = ""
        
        while pos < len(input_text):
            char = input_text[pos]
            
            # Special case: if this is a $ that can't start a valid expansion,
            # include it in the word even though it's normally a terminator
            if (char == '$' and self.config and self.config.enable_variable_expansion and 
                not self._can_start_valid_expansion(input_text, pos)):
                value += char
                pos += 1
                continue
            
            # Check for word terminators
            if self._is_word_terminator(char, context):
                # Special case: don't terminate on = if we just collected + for +=
                if char == '=' and value.endswith('+'):
                    # Include the = in +=
                    value += char
                    pos += 1
                    continue
                # Special case: don't terminate on = if this looks like a variable assignment
                elif char == '=' and self._is_variable_assignment_start(value):
                    # Include the = and continue reading the value part
                    value += char
                    pos += 1
                    continue
                # Special case: don't terminate on [ if this looks like start of array assignment
                elif char == '[' and self._is_potential_array_assignment_start(value, input_text, pos):
                    # Include the entire array assignment pattern including quotes
                    # This handles patterns like arr["key"]=value
                    array_part, new_pos = self._collect_array_assignment(input_text, pos)
                    if array_part:
                        value += array_part
                        pos = new_pos
                        continue
                    else:
                        # Fallback to just including the [
                        value += char
                        pos += 1
                        continue
                # Special case: don't terminate on ] if we're inside an array assignment
                elif char == ']' and self._is_inside_array_assignment(value):
                    # Include the ] and continue reading
                    value += char
                    pos += 1
                    continue
                # Special case: don't terminate on + if this looks like array assignment and next char is =
                elif char == '+' and self._looks_like_array_assignment_before_plus_equals(value, input_text, pos):
                    # Include the + and continue (the = will be handled by next iteration)
                    value += char
                    pos += 1
                    continue
                # Special case: don't terminate on $ if we're inside an array assignment
                elif char == '$' and self._is_inside_array_assignment(value):
                    # Include the $ and continue reading the variable inside array assignment
                    value += char
                    pos += 1
                    continue
                # Special case: don't terminate on ( or ) if we're inside an array assignment
                elif char in ['(', ')'] and self._is_inside_array_assignment(value):
                    # Include the parentheses and continue reading (for arithmetic expansion)
                    value += char
                    pos += 1
                    continue
                # Special case: don't terminate on arithmetic operators if we're inside an array assignment
                elif char in ['+', '-', '*', '/', '%'] and self._is_inside_array_assignment(value):
                    # Include the arithmetic operators and continue reading
                    value += char
                    pos += 1
                    continue
                # Special case: don't terminate on $ if this is ANSI-C quote in variable assignment or concatenation
                elif (char == '$' and pos + 1 < len(input_text) and input_text[pos + 1] == "'" and 
                      (self._is_in_variable_assignment_value(value) or self._is_in_string_concatenation(value))):
                    # We're in a variable assignment or string concatenation and found $' - parse the ANSI-C quote inline
                    ansi_c_content, new_pos = self._parse_ansi_c_quote_inline(input_text, pos)
                    if ansi_c_content is not None:
                        value += ansi_c_content
                        pos = new_pos
                        saw_inline_ansi = True
                        continue
                    # If parsing failed, fall through to breaking
                break
            
            # Check for quotes or expansions that would end the word
            # (only if they are enabled in config)
            # EXCEPTION: Don't break on quotes if we're inside an array assignment
            should_break = False
            
            # Special handling for quotes inside array assignments
            # Check if current value suggests we're collecting an array assignment
            if self._is_inside_array_assignment(value):
                # Inside array assignment, include quotes as part of the token
                if char in ["'", '"']:
                    value += char
                    pos += 1
                    continue
                # Also don't break on $ or ` inside array assignments
                elif char in ['$', '`']:
                    value += char
                    pos += 1
                    continue
            
            # Normal quote/expansion handling (outside array assignments)
            if char == '$' and self.config and self.config.enable_variable_expansion:
                # Special case: Check for ANSI-C quotes $'...' within variable assignments
                if (pos + 1 < len(input_text) and input_text[pos + 1] == "'" and 
                    self._is_in_variable_assignment_value(value)):
                    # We're in a variable assignment and found $' - parse the ANSI-C quote inline
                    ansi_c_content, new_pos = self._parse_ansi_c_quote_inline(input_text, pos)
                    if ansi_c_content is not None:
                        value += ansi_c_content
                        pos = new_pos
                        saw_inline_ansi = True
                        continue
                    # If parsing failed, fall through to normal handling
                    should_break = True
                else:
                    should_break = True
            elif char == '`' and self.config and self.config.enable_command_substitution:
                should_break = True
            elif char == "'" and self.config and self.config.enable_single_quotes:
                should_break = True
            elif char == '"' and self.config and self.config.enable_double_quotes:
                should_break = True
            
            if should_break:
                break
            
            # Check if # starts a comment (not part of word)
            if char == '#' and self._is_comment_start(input_text, pos, context):
                break
            
            # Handle escape sequences
            if char == '\\' and pos + 1 < len(input_text):
                next_char = input_text[pos + 1]
                # Include the escaped character (preserve the backslash for later processing)
                value += char + next_char
                pos += 2
                
                # Special case: if we escaped a $, and the next character is (,
                # we need to continue reading to include the ( as part of the word
                # This prevents $(command) from being recognized as command substitution
                if next_char == '$' and pos < len(input_text) and input_text[pos] == '(':
                    # Continue reading - the ( is part of the literal word, not a subshell
                    continue
                
                continue
            
            value += char
            pos += 1
        
        if not value:
            return None
        
        # Determine token type based on content
        token_type = self._classify_literal(value, context)
        
        token = Token(
            token_type,
            value,
            start_pos,
            pos
        )

        if saw_inline_ansi and token.quote_type is None:
            token.quote_type = 'mixed'
        
        return token, pos
    
    def _is_comment_start(self, input_text: str, pos: int, context: LexerContext) -> bool:
        """Check if # at current position starts a comment."""
        if pos == 0:
            return True
        
        prev_char = input_text[pos - 1]
        
        # After whitespace
        if prev_char in [' ', '\t', '\n', '\r']:
            return True
        
        # After operators that can be followed by comments
        comment_preceding_ops = {'|', '&', ';', '(', '{'}
        if prev_char in comment_preceding_ops:
            return True
        
        return False
    
    def _is_word_terminator(self, char: str, context: LexerContext) -> bool:
        """Check if character terminates a word in current context."""
        # In arithmetic context, only semicolon and parentheses are terminators
        if context.arithmetic_depth > 0:
            # Only these characters terminate words in arithmetic
            if char in [';', '(', ')', '\n']:
                return True
            else:
                return False
        
        # Check for Unicode whitespace (which should terminate words)
        if is_whitespace(char, posix_mode=context.posix_mode):
            return True
        
        # Basic word terminators, but check configuration for quotes
        if char in self.WORD_TERMINATORS:
            # Check if quotes/operators should be treated as word characters when disabled
            if char == "'" and self.config and not self.config.enable_single_quotes:
                return False  # Treat as word character
            if char == '"' and self.config and not self.config.enable_double_quotes:
                return False  # Treat as word character
            if char == '$' and self.config and not self.config.enable_variable_expansion:
                return False  # Treat as word character
            if char == '`' and self.config and not self.config.enable_command_substitution:
                return False  # Treat as word character
            if char == '|' and self.config and not self.config.enable_pipes:
                return False  # Treat as word character
            if char in ['<', '>'] and self.config and not self.config.enable_redirections:
                return False  # Treat as word character
            if char == '&' and self.config and not self.config.enable_background:
                return False  # Treat as word character
            # Inside [[ ]], < and > are comparison operators that should be treated as word chars
            if char in ['<', '>'] and context.bracket_depth > 0:
                return False  # Treat as word character
            return True
        
        # Context-specific terminators
        if context.bracket_depth > 0:
            # Inside [[ ]], some characters have special meaning
            if char in ['[', ']']:
                return True
        
        return False
    
    def _classify_literal(self, value: str, context: LexerContext) -> TokenType:
        """Classify a literal value into appropriate token type."""
        # Check if it's a number - for now, treat as WORD since NUMBER doesn't exist
        if self._is_number(value):
            return TokenType.WORD  # Could be TokenType.NUMBER if it existed
        
        # Check if it looks like a file descriptor (single digit)
        if len(value) == 1 and value.isdigit():
            # IO_NUMBER doesn't exist either, use WORD
            return TokenType.WORD
        
        # Check if it's a valid identifier
        if self._is_identifier(value):
            return TokenType.WORD
        
        # Default to word
        return TokenType.WORD
    
    def _is_number(self, value: str) -> bool:
        """Check if value is a number literal."""
        if not value:
            return False
        
        # Simple integer
        if value.isdigit():
            return True
        
        # Negative integer
        if value.startswith('-') and len(value) > 1 and value[1:].isdigit():
            return True
        
        # Hexadecimal (0x...)
        if (len(value) > 2 and 
            value.startswith('0x') and 
            all(c in '0123456789abcdefABCDEF' for c in value[2:])):
            return True
        
        # Octal (0...)
        if (len(value) > 1 and 
            value.startswith('0') and 
            all(c in '01234567' for c in value[1:])):
            return True
        
        return False
    
    def _is_identifier(self, value: str) -> bool:
        """Check if value is a valid identifier."""
        if not value:
            return False
        
        # Get posix_mode from config
        posix_mode = self.config.posix_mode if self.config else False
        
        # Must start with valid identifier start character
        if not is_identifier_start(value[0], posix_mode):
            return False
        
        # Rest must be valid identifier characters
        return all(is_identifier_char(c, posix_mode) for c in value[1:])
    
    def _contains_special_chars(self, value: str) -> bool:
        """Check if value contains shell special characters."""
        special_chars = {'*', '?', '[', ']', '{', '}', '~'}
        return any(c in special_chars for c in value)
    
    def _is_variable_assignment_start(self, value: str) -> bool:
        """Check if value looks like the start of a variable assignment (NAME=... or NAME[INDEX]=...)."""
        if not value:
            return False
        
        # Get posix_mode from config
        posix_mode = self.config.posix_mode if self.config else False
        
        # Check for array assignment pattern: NAME[...]
        if '[' in value:
            return self._is_array_assignment_start(value, posix_mode)
        
        # Variable names must start with letter or underscore
        if not is_identifier_start(value[0], posix_mode):
            return False
        
        # Rest must be valid identifier characters (valid shell variable name)
        return all(is_identifier_char(c, posix_mode) for c in value)
    
    def _is_array_assignment_start(self, value: str, posix_mode: bool) -> bool:
        """Check if value looks like the start of an array assignment (NAME[INDEX])."""
        bracket_pos = value.find('[')
        if bracket_pos == -1:
            return False
        
        # Extract the variable name before the bracket
        var_name = value[:bracket_pos]
        if not var_name:
            return False
        
        # Variable name must be valid
        if not is_identifier_start(var_name[0], posix_mode):
            return False
        if not all(is_identifier_char(c, posix_mode) for c in var_name):
            return False
        
        # The rest after '[' can contain any characters (index expression)
        # We don't validate the index contents here, just that it's an array pattern
        return True
    
    def _can_start_valid_expansion(self, input_text: str, pos: int) -> bool:
        """Check if $ at given position can start a valid expansion."""
        if pos >= len(input_text) or input_text[pos] != '$':
            return False
        
        if pos + 1 >= len(input_text):
            # Lone $ at end cannot start a valid expansion
            return False
        
        next_char = input_text[pos + 1]
        
        # Check for specific expansion patterns
        if next_char == '(':
            # Command substitution $(...) or arithmetic $((...))
            return True
        elif next_char == '{':
            # Parameter expansion ${...}
            return True
        elif next_char == "'":
            # ANSI-C quoting $'...'
            return True
        else:
            # Simple variable $VAR - check if next character can start a variable name
            from ..constants import SPECIAL_VARIABLES
            from ..unicode_support import is_identifier_start
            
            # Special single-character variables
            if next_char in SPECIAL_VARIABLES:
                return True
            
            # Regular variable names
            posix_mode = self.config.posix_mode if self.config else False
            return is_identifier_start(next_char, posix_mode)
    
    def _is_potential_array_assignment_start(self, value: str, input_text: str, pos: int) -> bool:
        """Check if [ at current position starts an array assignment pattern."""
        if not value:
            return False
        
        # Get posix_mode from config
        posix_mode = self.config.posix_mode if self.config else False
        
        # Check if the value so far is a valid variable name
        if not is_identifier_start(value[0], posix_mode):
            return False
        if not all(is_identifier_char(c, posix_mode) for c in value):
            return False
        
        # Look ahead to see if this looks like arr[...]=... pattern
        # We're at position of '[', scan forward to look for ]=
        # This needs to be quote-aware to handle arr["key"]=value correctly
        remaining = input_text[pos:]
        bracket_count = 0
        i = 0
        in_single_quote = False
        in_double_quote = False
        escaped = False
        
        while i < len(remaining):
            char = remaining[i]
            
            # Handle escape sequences
            if escaped:
                escaped = False
                i += 1
                continue
            
            if char == '\\' and not in_single_quote:
                escaped = True
                i += 1
                continue
            
            # Handle quotes - only switch quote state if not in other quote type
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                # Only process brackets and other chars when not in quotes
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        # Found closing bracket, check if followed by = or +=
                        if i + 1 < len(remaining):
                            if remaining[i + 1] == '=':
                                # Array assignment pattern found
                                return True
                            elif i + 2 < len(remaining) and remaining[i + 1:i + 3] == '+=':
                                # Array append assignment pattern found
                                return True
                        return False
                elif char in [' ', '\t', '\n', '\r']:
                    # Whitespace breaks the pattern (outside quotes)
                    return False
            
            i += 1
        
        return False
    
    def _is_inside_array_assignment(self, value: str) -> bool:
        """Check if we're currently inside an array assignment pattern."""
        if not value or '[' not in value:
            return False
        
        # Check if we have unmatched opening bracket and this looks like array pattern
        bracket_count = 0
        has_opening_bracket = False
        in_single_quote = False
        in_double_quote = False
        
        for char in value:
            # Track quotes to ignore brackets inside them
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                if char == '[':
                    bracket_count += 1
                    has_opening_bracket = True
                elif char == ']':
                    bracket_count -= 1
        
        # We're inside array assignment if we have unmatched opening brackets
        return has_opening_bracket and bracket_count > 0
    
    def _looks_like_array_assignment_before_plus_equals(self, value: str, input_text: str, pos: int) -> bool:
        """Check if + at current position is part of array assignment += pattern."""
        if not value or not value.endswith(']'):
            return False
        
        # Check if next character is =
        if pos + 1 >= len(input_text) or input_text[pos + 1] != '=':
            return False
        
        # Check if value looks like array assignment pattern (var[...])
        if '[' not in value:
            return False
        
        # Extract variable name before first [
        bracket_pos = value.find('[')
        var_name = value[:bracket_pos]
        
        if not var_name:
            return False
        
        # Get posix_mode from config
        posix_mode = self.config.posix_mode if self.config else False
        
        # Variable name must be valid
        if not is_identifier_start(var_name[0], posix_mode):
            return False
        if not all(is_identifier_char(c, posix_mode) for c in var_name):
            return False
        
        # Check brackets are balanced
        bracket_count = 0
        for char in value:
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
        
        # Should have balanced brackets ending with ]
        return bracket_count == 0 and value.endswith(']')
    
    def _is_in_variable_assignment_value(self, value: str) -> bool:
        """Check if we are currently reading the value part of a variable assignment."""
        if not value or '=' not in value:
            return False
        
        # Simple case: var= (just found the equals)
        if value.endswith('='):
            return True
        
        # Array assignment case: arr[index]= or arr[index]+= 
        if value.endswith('+=') or (']=' in value and value.endswith('=')):
            return True
        
        # Check if we have found an = and are now reading the value
        equals_pos = value.rfind('=')  # Find last equals in case of multiple
        if equals_pos == -1:
            return False
        
        # Check if what comes before = looks like a valid variable assignment start
        before_equals = value[:equals_pos]
        
        # Handle += case
        if before_equals.endswith('+'):
            before_equals = before_equals[:-1]
        
        # Check if it's a simple variable assignment or array assignment
        return self._is_variable_assignment_start(before_equals) or self._is_array_assignment_start(before_equals, 
                                                                                                    self.config.posix_mode if self.config else False)
    
    def _parse_ansi_c_quote_inline(self, input_text: str, pos: int) -> Tuple[Optional[str], int]:
        """
        Parse an ANSI-C quote $'...' starting at the given position.
        
        Returns (processed_content, new_position) where processed_content is None if parsing failed.
        The processed_content has escape sequences converted to their actual characters.
        """
        if pos + 1 >= len(input_text) or input_text[pos:pos+2] != "$'":
            return None, pos
        
        # Import the pure helpers for ANSI-C quote processing
        from .. import pure_helpers
        
        # Start after the $'
        quote_start = pos + 2
        quote_pos = quote_start
        processed_content = ""
        
        # Find the closing quote and process escape sequences
        while quote_pos < len(input_text):
            char = input_text[quote_pos]
            
            if char == "'":
                # Found closing quote - return the processed content (not the literal $'...')
                return processed_content, quote_pos + 1
            
            if char == '\\' and quote_pos + 1 < len(input_text):
                # Handle escape sequence using existing helper
                escaped_str, new_pos = pure_helpers.handle_escape_sequence(
                    input_text, quote_pos, "$'"
                )
                processed_content += escaped_str
                quote_pos = new_pos
            else:
                processed_content += char
                quote_pos += 1
        
        # Unclosed quote - return None to indicate parsing failure
        return None, pos
    
    def _is_in_string_concatenation(self, value: str) -> bool:
        """Check if we are currently reading a string that could be concatenated with quotes."""
        if not value:
            return False
        
        # If the value contains only valid word characters (no special shell characters),
        # then it's likely a string that could be concatenated with quotes
        # Examples: "prefix", "hello", "path"
        
        # Get posix_mode from config
        posix_mode = self.config.posix_mode if self.config else False
        
        # Check if it's a valid identifier-like string (could be concatenated)
        # This includes simple words that could have quotes appended
        from ..unicode_support import is_identifier_char, is_identifier_start
        
        # Must start with a valid character for word
        if not value:
            return False
        
        # Allow strings that are valid identifiers or contain path-like characters
        allowed_chars = set()
        for i, char in enumerate(value):
            if i == 0:
                if not (is_identifier_start(char, posix_mode) or char in '/.~'):
                    return False
            else:
                if not (is_identifier_char(char, posix_mode) or char in '/.~-'):
                    # If we hit special characters like =, we're probably not in simple concatenation
                    if char in '=[](){}|&;<>!':
                        return False
        
        return True

    def _collect_array_assignment(self, input_text: str, pos: int) -> Tuple[str, int]:
        """Collect the complete array assignment pattern including quotes.

        Starting at a '[', collect until we find ']=', ']+=' or hit a terminator.
        This is quote-aware and will include quoted keys.

        Returns (collected_string, new_position) or ("", pos) if not an array assignment.
        """
        if pos >= len(input_text) or input_text[pos] != '[':
            return "", pos

        start_pos = pos
        result = ""
        bracket_count = 0
        in_single_quote = False
        in_double_quote = False
        escaped = False

        while pos < len(input_text):
            char = input_text[pos]

            # Handle escape sequences
            if escaped:
                result += char
                pos += 1
                escaped = False
                continue

            if char == '\\' and not in_single_quote:
                escaped = True
                result += char
                pos += 1
                continue

            # Track quotes
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                result += char
                pos += 1
                continue
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                result += char
                pos += 1
                continue

            # Process characters based on quote state
            if in_single_quote or in_double_quote:
                # Inside quotes, just collect everything
                result += char
                pos += 1
            else:
                # Outside quotes, track brackets and look for assignment
                if char == '[':
                    bracket_count += 1
                    result += char
                    pos += 1
                elif char == ']':
                    bracket_count -= 1
                    result += char
                    pos += 1

                    # Check if this closes the array index
                    if bracket_count == 0:
                        # Look for = or +=
                        if pos < len(input_text):
                            if input_text[pos] == '=':
                                # Include the = and the value part
                                result += '='
                                pos += 1
                                # Continue collecting the value part until whitespace or operator
                                value_part, value_pos = self._collect_assignment_value(input_text, pos)
                                result += value_part
                                return result, value_pos
                            elif pos + 1 < len(input_text) and input_text[pos:pos+2] == '+=':
                                # Include the += and the value part
                                result += '+='
                                pos += 2
                                # Continue collecting the value part
                                value_part, value_pos = self._collect_assignment_value(input_text, pos)
                                result += value_part
                                return result, value_pos
                        # Not an assignment, return what we have
                        return result, pos
                elif char in ' \t\n\r|&;(){}' and bracket_count == 0:
                    # Hit a terminator outside of brackets
                    return "", start_pos
                else:
                    result += char
                    pos += 1

        # Reached end of input without finding assignment
        if in_single_quote or in_double_quote:
            # Unclosed quote
            return "", start_pos
        return "", start_pos

    def _collect_assignment_value(self, input_text: str, pos: int) -> Tuple[str, int]:
        """Collect the value part of an assignment until a terminator.

        This handles quoted values and continues until it hits whitespace or operators.
        """
        result = ""
        in_single_quote = False
        in_double_quote = False
        escaped = False

        while pos < len(input_text):
            char = input_text[pos]

            # Handle escape sequences
            if escaped:
                result += char
                pos += 1
                escaped = False
                continue

            if char == '\\' and not in_single_quote:
                escaped = True
                result += char
                pos += 1
                continue

            # Track quotes
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                result += char
                pos += 1
                continue
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                result += char
                pos += 1
                continue

            # Check for terminators (only when not in quotes)
            if not in_single_quote and not in_double_quote:
                if char in ' \t\n\r|&;(){}' or (char in '<>' and self.config and self.config.enable_redirections):
                    # Hit a terminator
                    break

            result += char
            pos += 1

        return result, pos
