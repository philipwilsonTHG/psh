"""
Enhanced lexer with heredoc support.

This module provides a lexer that can handle heredoc collection,
building on top of the existing modular lexer.
"""

from typing import Dict, List, Tuple

from ..token_types import Token, TokenType
from .heredoc_collector import HeredocCollector
from .modular_lexer import ModularLexer


class HeredocLexer:
    """
    Lexer with heredoc collection support.

    This lexer wraps the standard lexer and adds multi-line heredoc
    collection capabilities.
    """

    def __init__(self, source: str, config=None):
        """
        Initialize the heredoc lexer.

        Args:
            source: The source code to tokenize
            config: Optional lexer configuration
        """
        self.source = source
        self.lines = source.splitlines(keepends=True)
        self.config = config
        self.heredoc_collector = HeredocCollector()
        self._current_line = 0
        self._tokens_buffer = []
        self._heredoc_mode = False
        self._collected_heredocs = {}

    def tokenize(self) -> List[Token]:
        """
        Tokenize the source code with heredoc support.

        Returns:
            List of tokens with heredoc content collected
        """
        tokens = []

        while self._current_line < len(self.lines):
            line = self.lines[self._current_line]

            # Check if we need to start collecting heredocs after the current line
            pending_before = self.heredoc_collector.has_pending_heredocs()

            if pending_before:
                # We're collecting heredoc content
                completed = self.heredoc_collector.collect_line(line.rstrip('\n'))

                # Update collected heredocs
                for key, _ in completed:
                    content = self.heredoc_collector.get_content(key)
                    if content is not None:
                        self._collected_heredocs[key] = {
                            'content': content,
                            'quoted': self.heredoc_collector.get_heredoc_info(key)['quoted']
                        }

                self._current_line += 1
            else:
                # Normal tokenization
                line_tokens = self._tokenize_line(line)

                # Add tokens
                tokens.extend(line_tokens)

                # Add newline token if the line had a newline
                if line.endswith('\n'):
                    # Calculate position based on line length
                    pos = sum(len(self.lines[i]) for i in range(self._current_line))
                    tokens.append(Token(TokenType.NEWLINE, '\n', position=pos))

                # Check for heredoc operators AFTER we've added the tokens
                # This ensures heredocs start collecting on the NEXT line
                self._process_heredoc_operators(line_tokens, self._current_line)

                self._current_line += 1

        # Add EOF token
        final_pos = sum(len(line) for line in self.lines)
        tokens.append(Token(TokenType.EOF, '', position=final_pos))

        # Check for incomplete heredocs
        incomplete = self.heredoc_collector.get_incomplete_heredocs()
        if incomplete:
            # Create error token for incomplete heredoc
            # Note: We could raise an exception here, but for now we'll just
            # let the parser handle the incomplete heredoc
            pass

        return tokens

    def _tokenize_line(self, line: str) -> List[Token]:
        """Tokenize a single line using the standard lexer."""
        # Remove newline for tokenization
        line_content = line.rstrip('\n')

        # Use the standard lexer for this line
        lexer = ModularLexer(line_content, config=self.config)
        line_tokens = lexer.tokenize()

        # Filter out EOF tokens from line tokenization
        return [t for t in line_tokens if t.type != TokenType.EOF]

    def _process_heredoc_operators(self, tokens: List[Token], line_num: int):
        """Process tokens looking for heredoc operators and their delimiters."""
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type in (TokenType.HEREDOC, TokenType.HEREDOC_STRIP):
                # Found heredoc operator, look for delimiter
                strip_tabs = token.type == TokenType.HEREDOC_STRIP

                # Next token should be the delimiter
                delimiter_idx = i + 1

                if delimiter_idx < len(tokens):
                    delimiter_token = tokens[delimiter_idx]
                    delimiter = delimiter_token.value
                    quoted = delimiter_token.type == TokenType.STRING

                    # STRING tokens already have quotes removed by the lexer

                    # Register heredoc for collection
                    key = self.heredoc_collector.register_heredoc(
                        delimiter=delimiter,
                        strip_tabs=strip_tabs,
                        quoted=quoted,
                        line=line_num,
                        col=token.column if hasattr(token, 'column') else 0
                    )

                    # Store the key in the token for later reference
                    token.heredoc_key = key

            i += 1

    def get_heredoc_map(self) -> Dict[str, Dict[str, any]]:
        """
        Get the collected heredoc content map.

        Returns:
            Dictionary mapping heredoc keys to their content and metadata
        """
        return self._collected_heredocs.copy()

    def tokenize_with_heredocs(self) -> Tuple[List[Token], Dict[str, Dict[str, any]]]:
        """
        Tokenize and return both tokens and heredoc map.

        Returns:
            Tuple of (tokens, heredoc_map)
        """
        tokens = self.tokenize()
        heredoc_map = self.get_heredoc_map()
        return tokens, heredoc_map


def tokenize_with_heredocs(source: str, config=None) -> Tuple[List[Token], Dict[str, Dict[str, any]]]:
    """
    Convenience function to tokenize source with heredoc support.

    Args:
        source: The source code to tokenize
        config: Optional lexer configuration

    Returns:
        Tuple of (tokens, heredoc_map)
    """
    lexer = HeredocLexer(source, config=config)
    return lexer.tokenize_with_heredocs()
