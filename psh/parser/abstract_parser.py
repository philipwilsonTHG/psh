"""Abstract base class for shell parser implementations.

This module provides the interface that all parser implementations must follow,
enabling experimentation with different parsing strategies while maintaining
a consistent API.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..ast_nodes import ASTNode, CommandList, TopLevel
from ..token_types import Token


class ParserType(Enum):
    """Types of parser implementations."""
    RECURSIVE_DESCENT = "recursive_descent"
    PARSER_COMBINATOR = "parser_combinator"
    GRAMMAR_DSL = "grammar_dsl"
    PRATT_PARSER = "pratt_parser"
    PACKRAT = "packrat"
    EARLEY = "earley"
    LR = "lr"
    LL = "ll"
    PEG = "peg"
    CUSTOM = "custom"


@dataclass
class ParserCharacteristics:
    """Characteristics of a parser implementation for comparison."""
    parser_type: ParserType
    complexity: str  # "low", "medium", "high"
    error_recovery: bool = False
    backtracking: bool = False
    memoization: bool = False
    left_recursion: bool = False
    ambiguity_handling: str = "first"  # "first", "all", "error"
    incremental: bool = False
    streaming: bool = False
    hand_coded: bool = True
    generated: bool = False
    functional: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "type": self.parser_type.value,
            "complexity": self.complexity,
            "error_recovery": self.error_recovery,
            "backtracking": self.backtracking,
            "memoization": self.memoization,
            "left_recursion": self.left_recursion,
            "ambiguity_handling": self.ambiguity_handling,
            "incremental": self.incremental,
            "streaming": self.streaming,
            "hand_coded": self.hand_coded,
            "generated": self.generated,
            "functional": self.functional
        }


@dataclass
class ParseMetrics:
    """Metrics collected during parsing for comparison."""
    tokens_consumed: int = 0
    rules_evaluated: int = 0
    backtrack_count: int = 0
    memoization_hits: int = 0
    memoization_misses: int = 0
    max_recursion_depth: int = 0
    error_recovery_attempts: int = 0
    parse_time_ms: float = 0.0
    memory_used_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "tokens_consumed": self.tokens_consumed,
            "rules_evaluated": self.rules_evaluated,
            "backtrack_count": self.backtrack_count,
            "memoization_hits": self.memoization_hits,
            "memoization_misses": self.memoization_misses,
            "max_recursion_depth": self.max_recursion_depth,
            "error_recovery_attempts": self.error_recovery_attempts,
            "parse_time_ms": self.parse_time_ms,
            "memory_used_bytes": self.memory_used_bytes
        }


class ParseError(Exception):
    """Base exception for parser errors."""
    def __init__(self, message: str, position: Optional[int] = None,
                 token: Optional[Token] = None):
        super().__init__(message)
        self.position = position
        self.token = token


class AbstractShellParser(ABC):
    """Abstract base class for all parser implementations.
    
    This class defines the interface that all experimental parser
    implementations must follow. It ensures consistency across different
    parsing strategies while allowing for experimentation.
    """

    def __init__(self):
        """Initialize the parser."""
        self.metrics = ParseMetrics()

    @abstractmethod
    def parse(self, tokens: List[Token]) -> Union[TopLevel, CommandList]:
        """Parse a list of tokens into an AST.
        
        Args:
            tokens: List of tokens from the lexer
            
        Returns:
            The root AST node (either TopLevel or CommandList)
            
        Raises:
            ParseError: If parsing fails
        """
        pass

    @abstractmethod
    def parse_partial(self, tokens: List[Token]) -> Tuple[Optional[ASTNode], int]:
        """Parse as much as possible from the token stream.
        
        This method attempts to parse a prefix of the token stream,
        returning the AST for the successfully parsed portion and
        the position where parsing stopped.
        
        Args:
            tokens: List of tokens from the lexer
            
        Returns:
            Tuple of (AST node or None, position where parsing stopped)
        """
        pass

    @abstractmethod
    def can_parse(self, tokens: List[Token]) -> bool:
        """Check if the tokens can be parsed without actually parsing.
        
        This is useful for quick validation or parser selection.
        
        Args:
            tokens: List of tokens to check
            
        Returns:
            True if the tokens appear to be parseable
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the parser implementation name.
        
        Returns:
            A unique identifier for this parser implementation
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return a human-readable description of the parser.
        
        Returns:
            A description suitable for educational display
        """
        pass

    @abstractmethod
    def get_characteristics(self) -> ParserCharacteristics:
        """Return the characteristics of this parser implementation.
        
        Returns:
            ParserCharacteristics object describing the parser
        """
        pass

    def get_metrics(self) -> ParseMetrics:
        """Return metrics from the last parse operation.
        
        Returns:
            ParseMetrics object with performance data
        """
        return self.metrics

    def reset_metrics(self):
        """Reset metrics for a new parse operation."""
        self.metrics = ParseMetrics()

    def supports_incremental(self) -> bool:
        """Check if this parser supports incremental parsing.
        
        Returns:
            True if the parser can parse incrementally
        """
        return self.get_characteristics().incremental

    def supports_streaming(self) -> bool:
        """Check if this parser supports streaming tokens.
        
        Returns:
            True if the parser can handle tokens as a stream
        """
        return self.get_characteristics().streaming

    def get_configuration_options(self) -> Dict[str, Any]:
        """Return available configuration options for this parser.
        
        Returns:
            Dictionary of option names to their descriptions
        """
        return {}

    def configure(self, **options):
        """Configure the parser with implementation-specific options.
        
        Args:
            **options: Implementation-specific configuration options
        """
        pass

    def validate_grammar(self) -> List[str]:
        """Validate the parser's grammar if applicable.
        
        Returns:
            List of validation warnings or errors
        """
        return []

    def get_grammar_description(self) -> Optional[str]:
        """Return a description of the grammar if applicable.
        
        Returns:
            Grammar description in BNF/EBNF format, or None
        """
        return None

    def explain_parse(self, tokens: List[Token]) -> str:
        """Provide an educational explanation of how parsing works.
        
        This method is for educational purposes, showing step-by-step
        how this parser implementation processes the tokens.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            Multi-line string explaining the parsing process
        """
        return "Parsing explanation not implemented for this parser."


class AbstractIncrementalParser(AbstractShellParser):
    """Extended interface for parsers that support incremental parsing."""

    @abstractmethod
    def parse_incremental(self, tokens: List[Token],
                         previous_ast: Optional[ASTNode] = None,
                         change_position: Optional[int] = None) -> ASTNode:
        """Parse incrementally, reusing previous parse results.
        
        Args:
            tokens: Updated token list
            previous_ast: Previous parse result to reuse
            change_position: Position where tokens changed
            
        Returns:
            Updated AST
        """
        pass

    @abstractmethod
    def get_reusable_nodes(self, ast: ASTNode,
                          change_position: int) -> List[ASTNode]:
        """Identify AST nodes that can be reused in incremental parsing.
        
        Args:
            ast: Current AST
            change_position: Position where change occurred
            
        Returns:
            List of reusable AST nodes
        """
        pass


class AbstractStreamingParser(AbstractShellParser):
    """Extended interface for parsers that support streaming."""

    @abstractmethod
    def start_streaming(self):
        """Initialize streaming parse state."""
        pass

    @abstractmethod
    def feed_token(self, token: Token) -> Optional[ASTNode]:
        """Feed a single token to the streaming parser.
        
        Args:
            token: Next token in the stream
            
        Returns:
            Complete AST if a full construct was parsed, None otherwise
        """
        pass

    @abstractmethod
    def end_streaming(self) -> Optional[ASTNode]:
        """Finalize streaming and return any remaining AST.
        
        Returns:
            Final AST or None if incomplete
        """
        pass
