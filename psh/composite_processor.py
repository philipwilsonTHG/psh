"""Composite token processor for PSH.

This module provides a processor that identifies adjacent tokens that should
be treated as a single composite argument. This simplifies the parser by
moving composite detection to a dedicated phase between tokenization and parsing.
"""

from typing import List, Optional, Set
from dataclasses import dataclass
from .token_types import Token, TokenType


class CompositeToken(Token):
    """A token representing merged adjacent tokens."""
    
    def __init__(self, components: List[Token]):
        """Create a composite token from component tokens."""
        if not components:
            raise ValueError("Composite token must have at least one component")
        
        # Merge values
        value = ''.join(self._token_to_string(t) for t in components)
        
        # Position spans from first to last component
        position = components[0].position
        end_position = components[-1].end_position
        
        # Track if any component was quoted
        has_quotes = any(t.type == TokenType.STRING for t in components)
        
        super().__init__(
            type=TokenType.COMPOSITE,
            value=value,
            position=position,
            end_position=end_position,
            quote_type='mixed' if has_quotes else None
        )
        self.components = components
    
    def _token_to_string(self, token: Token) -> str:
        """Convert a token to its string representation for merging."""
        # Special handling for tokens that need their original syntax
        if token.type == TokenType.VARIABLE:
            return f"${token.value}"
        elif token.type in (TokenType.LBRACKET, TokenType.RBRACKET):
            # Preserve brackets for glob patterns
            return token.value
        elif token.type == TokenType.STRING:
            # Mark glob chars from quoted sections as non-globbable
            # using \x00 prefix, but skip chars inside ${...} expansions
            return self._mark_quoted_globs(token.value)
        else:
            return token.value

    @staticmethod
    def _mark_quoted_globs(value: str) -> str:
        """Mark glob characters in quoted strings with \\x00 prefix.

        Skips characters inside ${...} expansions since those are
        part of variable syntax, not glob patterns.
        """
        result = []
        i = 0
        brace_depth = 0
        while i < len(value):
            ch = value[i]
            if ch == '$' and i + 1 < len(value) and value[i + 1] == '{':
                result.append('${')
                brace_depth += 1
                i += 2
                continue
            if ch == '}' and brace_depth > 0:
                brace_depth -= 1
                result.append('}')
                i += 1
                continue
            if brace_depth == 0 and ch in ('*', '?', '['):
                result.append(f'\x00{ch}')
            else:
                result.append(ch)
            i += 1
        return ''.join(result)


class CompositeTokenProcessor:
    """Process token stream to identify and merge composite arguments.
    
    A composite argument is a sequence of adjacent tokens (no spaces between)
    that should be treated as a single argument. For example:
    - file${num}.txt -> composite of WORD, VARIABLE, WORD
    - "hello"world -> composite of STRING, WORD
    - $var[0] -> composite of VARIABLE, LBRACKET, WORD, RBRACKET
    """
    
    # Token types that can participate in composites
    WORD_LIKE: Set[TokenType] = {
        TokenType.WORD,
        TokenType.STRING,
        TokenType.VARIABLE,
        TokenType.COMMAND_SUB,
        TokenType.COMMAND_SUB_BACKTICK,
        TokenType.ARITH_EXPANSION,
        TokenType.PROCESS_SUB_IN,
        TokenType.PROCESS_SUB_OUT,
        TokenType.LBRACKET,
        TokenType.RBRACKET,
    }
    
    # Token types that terminate composites
    COMPOSITE_TERMINATORS: Set[TokenType] = {
        TokenType.PIPE,
        TokenType.SEMICOLON,
        TokenType.AMPERSAND,
        TokenType.AND_AND,
        TokenType.OR_OR,
        TokenType.NEWLINE,
        TokenType.EOF,
        TokenType.LPAREN,
        TokenType.RPAREN,
        TokenType.LBRACE,
        TokenType.RBRACE,
        TokenType.REDIRECT_IN,
        TokenType.REDIRECT_OUT,
        TokenType.REDIRECT_APPEND,
        TokenType.REDIRECT_ERR,
        TokenType.REDIRECT_ERR_APPEND,
        TokenType.REDIRECT_DUP,
        TokenType.HEREDOC,
        TokenType.HEREDOC_STRIP,
        TokenType.HERE_STRING,
        TokenType.DOUBLE_SEMICOLON,
        TokenType.SEMICOLON_AMP,
        TokenType.AMP_SEMICOLON,
    }
    
    def process(self, tokens: List[Token]) -> List[Token]:
        """Process token list and merge adjacent tokens into composites.
        
        Args:
            tokens: Original token list from lexer
            
        Returns:
            New token list with composite tokens where appropriate
        """
        if not tokens:
            return []
        
        result = []
        i = 0
        
        while i < len(tokens):
            if self._is_composite_start(tokens, i):
                composite = self._collect_composite(tokens, i)
                if len(composite) > 1:
                    # Create composite token
                    result.append(CompositeToken(composite))
                    i += len(composite)
                else:
                    # Single token, not really a composite
                    result.append(tokens[i])
                    i += 1
            else:
                result.append(tokens[i])
                i += 1
        
        return result
    
    def _is_composite_start(self, tokens: List[Token], index: int) -> bool:
        """Check if token at index could start a composite."""
        if index >= len(tokens):
            return False
        
        token = tokens[index]
        
        # Must be a word-like token
        if token.type not in self.WORD_LIKE:
            return False
        
        # Keywords generally don't participate in composites
        if token.type == TokenType.WORD and self._is_keyword(token.value):
            return False
        
        return True
    
    def _collect_composite(self, tokens: List[Token], start: int) -> List[Token]:
        """Collect all tokens that form a composite starting at index."""
        composite = []
        i = start
        
        while i < len(tokens):
            token = tokens[i]
            
            # First token is always included (we already checked it can start a composite)
            if i == start:
                composite.append(token)
                i += 1
                continue
            
            # Check if this token is adjacent to the previous one
            prev_token = tokens[i - 1]
            if token.position != prev_token.end_position:
                # Not adjacent, end of composite
                break
            
            # Check if this token can be part of a composite
            if token.type not in self.WORD_LIKE:
                # Not word-like, end of composite
                break
            
            # Check for terminating tokens
            if token.type in self.COMPOSITE_TERMINATORS:
                break
            
            # Add to composite
            composite.append(token)
            i += 1
        
        return composite
    
    def _is_keyword(self, value: str) -> bool:
        """Check if a word is a shell keyword."""
        keywords = {
            'if', 'then', 'else', 'elif', 'fi',
            'while', 'do', 'done', 'for', 'in',
            'case', 'esac', 'select',
            'function', 'break', 'continue',
            'return', 'exit', 'eval',
        }
        return value in keywords