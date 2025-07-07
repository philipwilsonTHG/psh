"""
Redirection parsing for PSH shell.

This module handles parsing of I/O redirections, heredocs, and here-strings.
"""

from typing import List
from ..token_types import Token, TokenType
from ..ast_nodes import Redirect
from .helpers import TokenGroups


class RedirectionParser:
    """Parser for redirection constructs."""
    
    def __init__(self, main_parser):
        """Initialize with reference to main parser."""
        self.parser = main_parser
    
    def parse_redirects(self) -> List[Redirect]:
        """Parse zero or more redirections."""
        redirects = []
        while self.parser.match_any(TokenGroups.REDIRECTS):
            redirects.append(self.parse_redirect())
        return redirects
    
    def parse_fd_dup_word(self) -> Redirect:
        """Parse file descriptor duplication from a WORD token."""
        # This is called when we have a WORD token like ">&2" or "2>&1"
        token = self.parser.advance()
        value = token.value
        
        import re
        match = re.match(r'^(\d*)([><])&(-|\d+)$', value)
        if not match:
            raise self.parser._error(f"Invalid fd duplication syntax: {value}")
        
        source_fd_str, direction, target = match.groups()
        
        # Default source fd is 1 for > and 0 for <
        if source_fd_str:
            source_fd = int(source_fd_str)
        else:
            source_fd = 1 if direction == '>' else 0
        
        # Handle closing fd with >&- or <&-
        if target == '-':
            return Redirect(
                type=direction + '&-',
                target=None,
                fd=source_fd
            )
        else:
            # Regular fd duplication
            return Redirect(
                type=direction + '&',
                target=None,
                fd=source_fd,
                dup_fd=int(target)
            )
    
    def parse_redirect(self) -> Redirect:
        """Parse a single redirection."""
        redirect_token = self.parser.advance()
        
        # Dispatch to specific redirect parser
        if redirect_token.type in (TokenType.HEREDOC, TokenType.HEREDOC_STRIP):
            return self._parse_heredoc(redirect_token)
        elif redirect_token.type == TokenType.HERE_STRING:
            return self._parse_here_string(redirect_token)
        elif redirect_token.type == TokenType.REDIRECT_DUP:
            return self._parse_dup_redirect(redirect_token)
        elif redirect_token.type in (TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND):
            return self._parse_err_redirect(redirect_token)
        else:
            return self._parse_standard_redirect(redirect_token)
    
    def _parse_heredoc(self, token: Token) -> Redirect:
        """Parse here document redirect."""
        if not self.parser.match(TokenType.WORD, TokenType.STRING):
            raise self.parser._error("Expected delimiter after here document operator")
        
        delimiter_token = self.parser.advance()
        delimiter = delimiter_token.value
        
        # Determine if delimiter was quoted (disables variable expansion)
        heredoc_quoted = delimiter_token.type == TokenType.STRING
        
        return Redirect(
            type=token.value,
            target=delimiter,
            heredoc_content=None,  # Content filled later
            heredoc_quoted=heredoc_quoted
        )
    
    def _parse_here_string(self, token: Token) -> Redirect:
        """Parse here string redirect."""
        if not self.parser.match_any(TokenGroups.WORD_LIKE):
            raise self.parser._error("Expected string after here string operator")
        
        # Use composite argument parsing to handle variables and quotes properly
        content_value, content_type, quote_type = self.parser.commands.parse_composite_argument()
        
        return Redirect(
            type=token.value,
            target=content_value,
            quote_type=quote_type
        )
    
    def _parse_dup_redirect(self, token: Token) -> Redirect:
        """Parse file descriptor duplication redirect."""
        # Handle both "2>&1" (single token) and ">&" "2" (two tokens)
        if token.value == '>&':
            # Two tokens like ">&" "2"
            fd = 1  # Default to stdout
            
            if not self.parser.match(TokenType.WORD):
                raise self.parser._error("Expected file descriptor after >&")
                
            target_token = self.parser.advance()
            dup_part = target_token.value
            
            if dup_part == '-':
                # Close file descriptor
                return Redirect(type='>&', target='-', fd=fd)
            else:
                # Duplicate file descriptor
                dup_fd = int(dup_part) if dup_part.isdigit() else None
                return Redirect(type='>&', target=dup_part, fd=fd, dup_fd=dup_fd)
        elif '>&' in token.value:
            # Single token like "2>&1"
            fd_part, dup_part = token.value.split('>&', 1)
            fd = int(fd_part) if fd_part else 1
            
            if dup_part == '-':
                # Close file descriptor
                return Redirect(type='>&', target='-', fd=fd)
            else:
                # Duplicate file descriptor
                dup_fd = int(dup_part) if dup_part.isdigit() else None
                return Redirect(type='>&', target=dup_part, fd=fd, dup_fd=dup_fd)
        else:
            raise self.parser._error(f"Invalid redirection operator: {token.value}")
    
    def _parse_err_redirect(self, token: Token) -> Redirect:
        """Parse stderr redirection."""
        # Check for file descriptor duplication (2>&1)
        if self.parser.match(TokenType.AMPERSAND):
            self.parser.advance()  # consume &
            if not self.parser.match(TokenType.WORD):
                raise self.parser._error("Expected file descriptor after &")
            
            dup_token = self.parser.advance()
            dup_fd = int(dup_token.value) if dup_token.value.isdigit() else None
            
            # Return as file descriptor duplication
            return Redirect(
                type='>&',
                target=dup_token.value,
                fd=2,  # stderr
                dup_fd=dup_fd
            )
        
        # Regular file redirection
        if not self.parser.match_any(TokenGroups.WORD_LIKE):
            raise self.parser._error("Expected target after stderr redirect")
        
        target_token = self.parser.advance()
        
        # Extract operator without file descriptor (2> -> >, 2>> -> >>)
        operator = token.value[1:]  # Remove the '2' prefix
        
        return Redirect(
            type=operator,
            target=target_token.value,
            fd=2
        )
    
    def _parse_standard_redirect(self, token: Token) -> Redirect:
        """Parse standard redirection (< > >>)."""
        if not self.parser.match_any(TokenGroups.WORD_LIKE):
            raise self.parser._error("Expected file name")
        
        # Use composite argument parsing to handle quoted composites like test'file'.txt
        target_value, _, _ = self.parser.commands.parse_composite_argument()
        
        return Redirect(
            type=token.value,
            target=target_value
        )