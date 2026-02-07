"""Constants and character sets for the lexer."""

import string

from ..token_types import TokenType

# Constants for character sets
VARIABLE_START_CHARS = set(string.ascii_letters + '_')
VARIABLE_CHARS = set(string.ascii_letters + string.digits + '_')
SPECIAL_VARIABLES = set('?$!#@*-') | set(string.digits)
VARIABLE_NAME_PATTERN = None  # Will be imported from re module when needed

# Escape sequences in different contexts
# In double quotes, bash only processes: \", \\, \$, \`, and \newline
# Other sequences like \n, \t, \r are preserved literally
DOUBLE_QUOTE_ESCAPES = {
    '\"': '\"',
    '\\': '\\',
    '`': '`',
    # Note: \n, \t, \r are NOT processed in double quotes in bash
    # They are preserved as literal \n, \t, \r
}

# Terminal characters for word boundaries
WORD_TERMINATORS = set(' \t\n|<>;&(){}\'"')  # [ and ] removed - handled specially
WORD_TERMINATORS_IN_BRACKETS = set(' \t\n|<>;&(){}\'"')  # ] handled specially

# Operators organized by length for efficient lookup
OPERATORS_BY_LENGTH = {
    4: {'2>&1': TokenType.REDIRECT_DUP},
    3: {
        '<<<': TokenType.HERE_STRING,
        '2>>': TokenType.REDIRECT_ERR_APPEND,
        ';;&': TokenType.AMP_SEMICOLON,
        '<<-': TokenType.HEREDOC_STRIP,
    },
    2: {
        '((': TokenType.DOUBLE_LPAREN,
        '[[': TokenType.DOUBLE_LBRACKET,
        ']]': TokenType.DOUBLE_RBRACKET,
        '<<': TokenType.HEREDOC,
        '>>': TokenType.REDIRECT_APPEND,
        '&&': TokenType.AND_AND,
        '||': TokenType.OR_OR,
        ';;': TokenType.DOUBLE_SEMICOLON,
        ';&': TokenType.SEMICOLON_AMP,
        '=~': TokenType.REGEX_MATCH,
        '>&': TokenType.REDIRECT_DUP,
        '<&': TokenType.REDIRECT_DUP,
        '2>': TokenType.REDIRECT_ERR,
    },
    1: {
        '|': TokenType.PIPE,
        '<': TokenType.REDIRECT_IN,
        '>': TokenType.REDIRECT_OUT,
        ';': TokenType.SEMICOLON,
        '&': TokenType.AMPERSAND,
        '(': TokenType.LPAREN,
        ')': TokenType.RPAREN,
        '{': TokenType.LBRACE,
        '}': TokenType.RBRACE,
        '[': TokenType.LBRACKET,
        ']': TokenType.RBRACKET,
        '!': TokenType.EXCLAMATION,
        '\n': TokenType.NEWLINE,
    }
}

# Keywords that need context checking
KEYWORDS = {
    'if', 'then', 'else', 'elif', 'fi',
    'while', 'until', 'do', 'done',
    'for', 'in',
    'case', 'esac',
    'select',
    'function',
    'break', 'continue', 'return'
}
