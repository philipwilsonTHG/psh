"""Pure helper functions for lexer operations.

This module contains stateless, pure functions that can be used by the lexer
without coupling to the lexer's internal state. These functions are easier to
test, reuse, and reason about.
"""

from typing import Tuple, Optional, Set, Dict, List
from .constants import DOUBLE_QUOTE_ESCAPES


def read_until_char(
    input_text: str,
    start_pos: int,
    target: str,
    escape: bool = False,
    escape_chars: Set[str] = {'"', '\\', '`', '$'}
) -> Tuple[str, int]:
    """
    Read characters until target is found.
    
    Args:
        input_text: The input string to read from
        start_pos: Starting position in the string
        target: Character to read until
        escape: Whether to handle escape sequences
        escape_chars: Characters that can be escaped
        
    Returns:
        Tuple of (content_read, new_position)
    """
    content = ""
    pos = start_pos
    
    while pos < len(input_text) and input_text[pos] != target:
        if escape and input_text[pos] == '\\' and pos + 1 < len(input_text):
            # Handle escape sequence
            next_char = input_text[pos + 1]
            if next_char in escape_chars:
                pos += 1  # Skip backslash
                if pos < len(input_text):
                    content += input_text[pos]
                    pos += 1
            else:
                # Not an escaped character, include the backslash
                content += input_text[pos]
                pos += 1
        else:
            content += input_text[pos]
            pos += 1
    
    return content, pos


def find_closing_delimiter(
    input_text: str,
    start_pos: int,
    open_delim: str,
    close_delim: str,
    track_quotes: bool = True,
    track_escapes: bool = True
) -> Tuple[int, bool]:
    """
    Find matching closing delimiter, handling nesting and quotes.
    
    Args:
        input_text: The input string to search in
        start_pos: Starting position (after opening delimiter)
        open_delim: Opening delimiter string
        close_delim: Closing delimiter string
        track_quotes: Whether to track quote contexts
        track_escapes: Whether to handle escape sequences
        
    Returns:
        Tuple of (position_after_close, found_closing)
    """
    depth = 1
    pos = start_pos
    in_single_quote = False
    in_double_quote = False
    
    while pos < len(input_text) and depth > 0:
        char = input_text[pos]
        
        # Handle escape sequences if enabled
        if track_escapes and char == '\\' and pos + 1 < len(input_text):
            # Skip the escaped character
            pos += 2
            continue
        
        # Handle quotes if tracking is enabled
        if track_quotes:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                pos += 1
                continue
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                pos += 1
                continue
        
        # Track delimiter depth when not in quotes
        if not (in_single_quote or in_double_quote):
            # Check for opening delimiter
            if (pos + len(open_delim) <= len(input_text) and 
                input_text[pos:pos+len(open_delim)] == open_delim):
                depth += 1
                pos += len(open_delim)
                continue
            
            # Check for closing delimiter
            if (pos + len(close_delim) <= len(input_text) and 
                input_text[pos:pos+len(close_delim)] == close_delim):
                depth -= 1
                if depth == 0:
                    return pos + len(close_delim), True
                pos += len(close_delim)
                continue
        
        pos += 1
    
    return pos, False


def find_balanced_parentheses(
    input_text: str,
    start_pos: int,
    track_quotes: bool = True
) -> Tuple[int, bool]:
    """
    Find balanced parentheses starting from given position.
    
    Args:
        input_text: The input string
        start_pos: Starting position (after opening paren)
        track_quotes: Whether to ignore parens inside quotes
        
    Returns:
        Tuple of (position_after_close_paren, found_closing)
    """
    return find_closing_delimiter(
        input_text, start_pos, '(', ')', track_quotes, True
    )


def find_balanced_double_parentheses(
    input_text: str,
    start_pos: int
) -> Tuple[int, bool]:
    """
    Find balanced double parentheses for arithmetic expressions.
    
    Args:
        input_text: The input string
        start_pos: Starting position (after opening $(()
        
    Returns:
        Tuple of (position_after_close_parens, found_closing)
    """
    # For arithmetic expressions, we need to find ))
    # but track individual ( and ) for internal balance
    depth = 0
    pos = start_pos
    
    while pos < len(input_text):
        # Check for )) first
        if pos + 1 < len(input_text) and input_text[pos:pos+2] == '))':
            if depth == 0:
                # Found the closing )) at the right depth
                return pos + 2, True
            else:
                # This )) but we have unmatched ( so treat as regular )
                depth -= 1
                pos += 1  # Only advance by 1 to check the second ) again
                continue
        
        if input_text[pos] == '(':
            depth += 1
        elif input_text[pos] == ')':
            depth -= 1
        
        pos += 1
    
    return pos, False


def handle_escape_sequence(
    input_text: str,
    pos: int,
    quote_context: Optional[str] = None
) -> Tuple[str, int]:
    """
    Handle escape sequences based on context.
    
    Args:
        input_text: The input string
        pos: Position of the backslash
        quote_context: Current quote context ('"', "'", "$'", or None)
        
    Returns:
        Tuple of (escaped_string, new_position)
    """
    if pos >= len(input_text) or input_text[pos] != '\\':
        return '\\', pos + 1
    
    if pos + 1 >= len(input_text):
        return '\\', pos + 1
    
    next_char = input_text[pos + 1]
    
    if quote_context == "$'":
        # ANSI-C quoting - handle extended escape sequences
        return handle_ansi_c_escape(input_text, pos)
    elif quote_context == '"':
        # In double quotes
        if next_char == '\n':
            # Escaped newline is a line continuation - remove it
            return '', pos + 2
        elif next_char in '"\\`':
            return next_char, pos + 2
        elif next_char == '$':
            # Special case: \$ preserves the backslash in double quotes
            return '\\$', pos + 2
        elif next_char in DOUBLE_QUOTE_ESCAPES:
            return DOUBLE_QUOTE_ESCAPES[next_char], pos + 2
        else:
            # Other characters keep the backslash
            return '\\' + next_char, pos + 2
    elif quote_context is None:
        # Outside quotes - backslash escapes everything
        if next_char == '\n':
            # Escaped newline is a line continuation - remove it
            return '', pos + 2
        elif next_char == '$':
            # Use a special marker for escaped dollar to prevent variable expansion
            return '\x00$', pos + 2  # NULL character followed by $
        else:
            return next_char, pos + 2
    else:
        # Single quotes - no escaping (except for the quote itself in some contexts)
        return '\\' + next_char, pos + 2


def handle_ansi_c_escape(input_text: str, pos: int) -> Tuple[str, int]:
    """
    Handle ANSI-C escape sequences in $'...' strings.
    
    Args:
        input_text: The input string
        pos: Position of the backslash
        
    Returns:
        Tuple of (escaped_string, new_position)
    """
    if pos + 1 >= len(input_text):
        return '\\', pos + 1
    
    next_char = input_text[pos + 1]
    
    # Simple single-character escapes
    simple_escapes = {
        'n': '\n', 't': '\t', 'r': '\r', 'b': '\b',
        'f': '\f', 'v': '\v', 'a': '\a', '\\': '\\',
        "'": "'", '"': '"', '?': '?',
        'e': '\x1b', 'E': '\x1b'  # ANSI escape
    }
    
    if next_char in simple_escapes:
        return simple_escapes[next_char], pos + 2
    
    # Hex escape: \xHH
    if next_char == 'x':
        hex_str = ""
        new_pos = pos + 2
        # Read up to 2 hex digits
        for i in range(2):
            if new_pos < len(input_text) and input_text[new_pos] in '0123456789ABCDEFabcdef':
                hex_str += input_text[new_pos]
                new_pos += 1
            else:
                break
        
        if hex_str:
            try:
                return chr(int(hex_str, 16)), new_pos
            except ValueError:
                return '\\x' + hex_str, new_pos
        else:
            return '\\x', pos + 2
    
    # Octal escape: \0NNN (bash style with leading 0)
    if next_char == '0':
        octal_str = ""
        new_pos = pos + 2
        # Read up to 3 octal digits
        for i in range(3):
            if new_pos < len(input_text) and input_text[new_pos] in '01234567':
                octal_str += input_text[new_pos]
                new_pos += 1
            else:
                break
        
        if octal_str:
            try:
                return chr(int(octal_str, 8)), new_pos
            except ValueError:
                return '\\0' + octal_str, new_pos
        else:
            # Just \0 means null character
            return '\0', pos + 2
    
    # Unicode escape: \uHHHH
    if next_char == 'u':
        hex_str = ""
        new_pos = pos + 2
        # Read exactly 4 hex digits
        for i in range(4):
            if new_pos < len(input_text) and input_text[new_pos] in '0123456789ABCDEFabcdef':
                hex_str += input_text[new_pos]
                new_pos += 1
            else:
                break
        
        if len(hex_str) == 4:
            try:
                return chr(int(hex_str, 16)), new_pos
            except ValueError:
                return '\\u' + hex_str, new_pos
        else:
            return '\\u' + hex_str, new_pos
    
    # Unicode escape: \UHHHHHHHH (8 digits)
    if next_char == 'U':
        hex_str = ""
        new_pos = pos + 2
        # Read exactly 8 hex digits
        for i in range(8):
            if new_pos < len(input_text) and input_text[new_pos] in '0123456789ABCDEFabcdef':
                hex_str += input_text[new_pos]
                new_pos += 1
            else:
                break
        
        if len(hex_str) == 8:
            try:
                return chr(int(hex_str, 16)), new_pos
            except ValueError:
                return '\\U' + hex_str, new_pos
        else:
            return '\\U' + hex_str, new_pos
    
    # For other characters, keep the backslash
    return '\\' + next_char, pos + 2


def find_word_boundary(
    input_text: str,
    start_pos: int,
    terminators: Set[str],
    handle_escapes: bool = True
) -> int:
    """
    Find the end of a word given terminator characters.
    
    Args:
        input_text: The input string
        start_pos: Starting position
        terminators: Set of characters that terminate words
        handle_escapes: Whether to handle escape sequences
        
    Returns:
        Position of the first terminator or end of string
    """
    pos = start_pos
    
    while pos < len(input_text):
        char = input_text[pos]
        
        # Handle escape sequences
        if handle_escapes and char == '\\' and pos + 1 < len(input_text):
            # Skip escaped character
            pos += 2
            continue
        
        # Check for terminators
        if char in terminators:
            break
        
        pos += 1
    
    return pos


def extract_variable_name(
    input_text: str,
    start_pos: int,
    special_vars: Set[str],
    posix_mode: bool = False
) -> Tuple[str, int]:
    """
    Extract a variable name starting from the given position.
    
    Args:
        input_text: The input string
        start_pos: Starting position (after $)
        special_vars: Set of special single-character variables
        posix_mode: Whether to use POSIX-compliant identifier rules
        
    Returns:
        Tuple of (variable_name, new_position)
    """
    from .unicode_support import is_identifier_start, is_identifier_char
    
    if start_pos >= len(input_text):
        return "", start_pos
    
    char = input_text[start_pos]
    
    # Special single-character variables
    if char in special_vars:
        return char, start_pos + 1
    
    # Regular variable names
    var_name = ""
    pos = start_pos
    
    # First character must be letter or underscore (not digit)
    if pos < len(input_text) and is_identifier_start(char, posix_mode):
        var_name += char
        pos += 1
        
        # Subsequent characters can be letters, numbers, marks, or underscore
        while pos < len(input_text):
            char = input_text[pos]
            if is_identifier_char(char, posix_mode):
                var_name += char
                pos += 1
            else:
                break
    
    # Don't return anything for invalid start (like digits)
    return var_name, pos


def is_comment_start(
    input_text: str,
    pos: int
) -> bool:
    """
    Check if # at given position starts a comment.
    
    Args:
        input_text: The input string
        pos: Position to check
        
    Returns:
        True if this starts a comment
    """
    if pos >= len(input_text) or input_text[pos] != '#':
        return False
    
    # Comments start at beginning of input or after whitespace/operators
    if pos == 0:
        return True
    
    prev_char = input_text[pos - 1]
    return prev_char in ' \t\n;|&<>(){}[]'


def scan_whitespace(
    input_text: str,
    start_pos: int,
    unicode_aware: bool = True
) -> int:
    """
    Scan past whitespace characters.
    
    Args:
        input_text: The input string
        start_pos: Starting position
        unicode_aware: Whether to recognize Unicode whitespace
        
    Returns:
        Position after whitespace
    """
    pos = start_pos
    
    while pos < len(input_text):
        char = input_text[pos]
        if unicode_aware:
            # Use Unicode-aware whitespace detection
            from .unicode_support import is_whitespace
            if not is_whitespace(char, not unicode_aware):  # posix_mode = not unicode_aware
                break
        else:
            # Basic ASCII whitespace
            if char not in ' \t\n\r\f\v':
                break
        pos += 1
    
    return pos


def extract_quoted_content(
    input_text: str,
    start_pos: int,
    quote_char: str,
    allow_escapes: bool = True
) -> Tuple[str, int, bool]:
    """
    Extract content from a quoted string.
    
    Args:
        input_text: The input string
        start_pos: Starting position (after opening quote)
        quote_char: The quote character ('"' or "'")
        allow_escapes: Whether to process escape sequences
        
    Returns:
        Tuple of (content, position_after_close_quote, found_closing_quote)
    """
    content = ""
    pos = start_pos
    
    while pos < len(input_text):
        char = input_text[pos]
        
        # Check for closing quote
        if char == quote_char:
            return content, pos + 1, True
        
        # Handle escape sequences if allowed
        if allow_escapes and char == '\\' and pos + 1 < len(input_text):
            escaped_str, new_pos = handle_escape_sequence(
                input_text, pos, quote_char
            )
            content += escaped_str
            pos = new_pos
        else:
            content += char
            pos += 1
    
    # Reached end without finding closing quote
    return content, pos, False


def find_operator_match(
    input_text: str,
    pos: int,
    operators_by_length: Dict[int, Dict[str, object]]
) -> Optional[Tuple[str, object, int]]:
    """
    Find the longest matching operator at the given position.
    
    Args:
        input_text: The input string
        pos: Position to check
        operators_by_length: Dictionary mapping length to operator dictionaries
        
    Returns:
        Tuple of (operator, token_type, new_position) or None if no match
    """
    # Check operators from longest to shortest
    for length in sorted(operators_by_length.keys(), reverse=True):
        if pos + length <= len(input_text):
            candidate = input_text[pos:pos + length]
            if candidate in operators_by_length[length]:
                token_type = operators_by_length[length][candidate]
                return candidate, token_type, pos + length
    
    return None


def validate_brace_expansion(
    input_text: str,
    start_pos: int
) -> Tuple[str, int, bool]:
    """
    Validate and extract a brace expansion ${...}.
    
    Args:
        input_text: The input string
        start_pos: Starting position (after ${)
        
    Returns:
        Tuple of (content, position_after_close_brace, found_closing_brace)
    """
    content = ""
    pos = start_pos
    brace_depth = 1
    
    while pos < len(input_text) and brace_depth > 0:
        char = input_text[pos]
        
        if char == '{':
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1
            if brace_depth == 0:
                return content, pos + 1, True
        
        content += char
        pos += 1
    
    return content, pos, False


def is_inside_expansion(
    input_text: str,
    position: int
) -> bool:
    """
    Check if the position is inside an arithmetic expression or command substitution.
    
    Args:
        input_text: The input string
        position: Position to check
        
    Returns:
        True if position is inside an expansion
    """
    if position >= len(input_text):
        return False
    
    # Simple approach: scan from beginning and track expansion boundaries
    i = 0
    while i <= position and i < len(input_text):
        # Check for arithmetic expansion $((
        if i + 2 < len(input_text) and input_text[i:i+3] == '$((': 
            # Find the closing ))
            end_pos, found = find_balanced_double_parentheses(input_text, i + 3)
            if found and i <= position < end_pos:
                return True
            i = end_pos if found else i + 3
            continue
        
        # Check for command substitution $(
        if i + 1 < len(input_text) and input_text[i:i+2] == '$(':
            # Find the closing )
            end_pos, found = find_balanced_parentheses(input_text, i + 2)
            if found and i <= position < end_pos:
                return True
            i = end_pos if found else i + 2
            continue
        
        # Check for backtick command substitution
        if input_text[i] == '`':
            # Find the closing backtick
            j = i + 1
            while j < len(input_text) and input_text[j] != '`':
                j += 1
            if j < len(input_text):  # Found closing backtick
                if i < position < j:  # Position is inside backticks
                    return True
                i = j + 1
            else:
                i += 1
            continue
        
        i += 1
    
    return False