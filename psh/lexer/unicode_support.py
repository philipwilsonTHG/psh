"""Unicode-aware character classification for shell identifiers."""

import string
import unicodedata


def is_identifier_start(char: str, posix_mode: bool = False) -> bool:
    """
    Check if character can start an identifier (variable name).

    Args:
        char: Character to check
        posix_mode: If True, restrict to POSIX ASCII characters

    Returns:
        True if character can start an identifier
    """
    if posix_mode:
        # POSIX mode: ASCII letters and underscore only
        return char in string.ascii_letters or char == '_'
    else:
        # Unicode mode: Unicode letters and underscore
        if char == '_':
            return True
        if len(char) != 1:
            return False
        # Check if it's a Unicode letter
        category = unicodedata.category(char)
        return category.startswith('L')  # L* categories are letters


def is_identifier_char(char: str, posix_mode: bool = False) -> bool:
    """
    Check if character can be part of an identifier (after the first character).

    Args:
        char: Character to check
        posix_mode: If True, restrict to POSIX ASCII characters

    Returns:
        True if character can be part of an identifier
    """
    if posix_mode:
        # POSIX mode: ASCII letters, digits, and underscore
        return char in string.ascii_letters or char in string.digits or char == '_'
    else:
        # Unicode mode: Unicode letters, numbers, marks, and underscore
        if char == '_':
            return True
        if len(char) != 1:
            return False
        # Check Unicode categories
        category = unicodedata.category(char)
        return (category.startswith('L') or    # Letters
                category.startswith('N') or    # Numbers
                category.startswith('M'))      # Marks (combining characters)


def is_whitespace(char: str, posix_mode: bool = False) -> bool:
    """
    Check if character is whitespace.

    Args:
        char: Character to check
        posix_mode: If True, restrict to ASCII whitespace

    Returns:
        True if character is whitespace
    """
    if posix_mode:
        # POSIX mode: ASCII whitespace only
        return char in ' \t\n\r\f\v'
    else:
        # Unicode mode: Unicode whitespace
        if len(char) != 1:
            return False
        # Use Unicode whitespace classification
        category = unicodedata.category(char)
        return category.startswith('Z') or char in '\t\n\r\f\v'


def normalize_identifier(name: str, posix_mode: bool = False, case_sensitive: bool = True) -> str:
    """
    Normalize an identifier name according to configuration.

    Args:
        name: Identifier name to normalize
        posix_mode: If True, don't apply Unicode normalization
        case_sensitive: If False, convert to lowercase

    Returns:
        Normalized identifier name
    """
    if not posix_mode:
        # Apply Unicode normalization (NFC - Canonical Composition)
        name = unicodedata.normalize('NFC', name)

    if not case_sensitive:
        name = name.lower()

    return name


def validate_identifier(name: str, posix_mode: bool = False) -> bool:
    """
    Validate that a string is a valid identifier.

    Args:
        name: Identifier name to validate
        posix_mode: If True, use POSIX validation rules

    Returns:
        True if the name is a valid identifier
    """
    if not name:
        return False

    # Check first character
    if not is_identifier_start(name[0], posix_mode):
        return False

    # Check remaining characters
    for char in name[1:]:
        if not is_identifier_char(char, posix_mode):
            return False

    return True
