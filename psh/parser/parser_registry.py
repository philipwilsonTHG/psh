"""Parser registry and strategy pattern implementation.

This module provides a registry for parser implementations and a strategy
pattern for selecting and switching between parsers at runtime.
"""

from typing import Dict, Type, Optional, List, Any
import time
import tracemalloc
from contextlib import contextmanager

from .abstract_parser import (
    AbstractShellParser, ParseError, ParseMetrics,
    ParserCharacteristics
)
from ..ast_nodes import TopLevel, CommandList
from ..token_types import Token


class ParserRegistry:
    """Registry for available parser implementations.
    
    This class maintains a central registry of all available parser
    implementations, allowing for dynamic discovery and selection.
    """
    
    _parsers: Dict[str, Type[AbstractShellParser]] = {}
    _aliases: Dict[str, str] = {}  # Alias -> canonical name mapping
    
    @classmethod
    def register(cls, name: str, parser_class: Type[AbstractShellParser], 
                 aliases: Optional[List[str]] = None):
        """Register a parser implementation.
        
        Args:
            name: Canonical name for the parser
            parser_class: Parser class implementing AbstractShellParser
            aliases: Optional list of alternative names
        """
        if not issubclass(parser_class, AbstractShellParser):
            raise TypeError(f"{parser_class} must inherit from AbstractShellParser")
        
        cls._parsers[name] = parser_class
        
        # Register aliases
        if aliases:
            for alias in aliases:
                cls._aliases[alias] = name
    
    @classmethod
    def unregister(cls, name: str):
        """Remove a parser from the registry.
        
        Args:
            name: Parser name to remove
        """
        # Remove the parser
        if name in cls._parsers:
            del cls._parsers[name]
        
        # Remove any aliases pointing to this parser
        aliases_to_remove = [
            alias for alias, canonical in cls._aliases.items() 
            if canonical == name
        ]
        for alias in aliases_to_remove:
            del cls._aliases[alias]
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[AbstractShellParser]]:
        """Get a parser implementation by name.
        
        Args:
            name: Parser name or alias
            
        Returns:
            Parser class or None if not found
        """
        # Check if it's an alias
        canonical_name = cls._aliases.get(name, name)
        return cls._parsers.get(canonical_name)
    
    @classmethod
    def create(cls, name: str, **config) -> AbstractShellParser:
        """Create a parser instance with configuration.
        
        Args:
            name: Parser name or alias
            **config: Configuration options for the parser
            
        Returns:
            Configured parser instance
            
        Raises:
            ValueError: If parser not found
        """
        parser_class = cls.get(name)
        if not parser_class:
            raise ValueError(f"Unknown parser: {name}")
        
        parser = parser_class()
        if config:
            parser.configure(**config)
        
        return parser
    
    @classmethod
    def list_parsers(cls) -> List[str]:
        """List all registered parser names.
        
        Returns:
            List of canonical parser names
        """
        return list(cls._parsers.keys())
    
    @classmethod
    def list_all_names(cls) -> List[str]:
        """List all parser names including aliases.
        
        Returns:
            List of all names (canonical and aliases)
        """
        return list(cls._parsers.keys()) + list(cls._aliases.keys())
    
    @classmethod
    def get_canonical_name(cls, name: str) -> Optional[str]:
        """Get the canonical name for a parser (resolves aliases).
        
        Args:
            name: Parser name or alias
            
        Returns:
            Canonical parser name, or None if not found
        """
        # Check if it's an alias
        canonical_name = cls._aliases.get(name, name)
        # Verify the canonical name exists
        if canonical_name in cls._parsers:
            return canonical_name
        return None
    
    @classmethod
    def get_parser_info(cls, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get information about parsers.
        
        Args:
            name: Specific parser name, or None for all parsers
            
        Returns:
            List of parser information dictionaries
        """
        if name:
            parser_class = cls.get(name)
            if not parser_class:
                return []
            parsers = {name: parser_class}
        else:
            parsers = cls._parsers
        
        info = []
        for parser_name, parser_class in parsers.items():
            try:
                parser = parser_class()
                aliases = [
                    alias for alias, canonical in cls._aliases.items()
                    if canonical == parser_name
                ]
                
                info.append({
                    "name": parser_name,
                    "aliases": aliases,
                    "description": parser.get_description(),
                    "characteristics": parser.get_characteristics().to_dict(),
                    "configuration_options": parser.get_configuration_options(),
                    "grammar_available": parser.get_grammar_description() is not None
                })
            except Exception as e:
                # Handle parsers that fail to instantiate
                info.append({
                    "name": parser_name,
                    "error": str(e),
                    "description": "Failed to load parser"
                })
        
        return info
    
    @classmethod
    def clear(cls):
        """Clear all registered parsers (mainly for testing)."""
        cls._parsers.clear()
        cls._aliases.clear()


class ParserStrategy:
    """Strategy pattern for parser selection and execution.
    
    This class provides a consistent interface for parsing regardless
    of which parser implementation is selected.
    """
    
    def __init__(self, parser_name: str = "default", **config):
        """Initialize with a specific parser.
        
        Args:
            parser_name: Name of parser to use
            **config: Configuration options for the parser
        """
        self._parser_name = parser_name
        self._parser: Optional[AbstractShellParser] = None
        self._config = config
        self._load_parser()
    
    def _load_parser(self):
        """Load the selected parser implementation."""
        self._parser = ParserRegistry.create(self._parser_name, **self._config)
    
    @property
    def current_parser(self) -> str:
        """Get the name of the current parser."""
        return self._parser_name
    
    @property
    def current_parser_canonical(self) -> str:
        """Get the canonical name of the current parser (resolves aliases)."""
        canonical = ParserRegistry.get_canonical_name(self._parser_name)
        return canonical or self._parser_name
    
    @property
    def parser(self) -> AbstractShellParser:
        """Get the current parser instance."""
        if not self._parser:
            self._load_parser()
        return self._parser
    
    def parse(self, tokens: List[Token]) -> Any:
        """Parse tokens using the selected implementation.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            AST from the parser
        """
        return self.parser.parse(tokens)
    
    def parse_with_metrics(self, tokens: List[Token]) -> tuple:
        """Parse and collect performance metrics.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            Tuple of (AST, ParseMetrics)
        """
        self.parser.reset_metrics()
        
        # Start memory tracking
        tracemalloc.start()
        start_memory = tracemalloc.get_traced_memory()[0]
        
        # Time the parse
        start_time = time.perf_counter()
        ast = self.parser.parse(tokens)
        end_time = time.perf_counter()
        
        # Get memory usage
        end_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        
        # Update metrics
        metrics = self.parser.get_metrics()
        metrics.parse_time_ms = (end_time - start_time) * 1000
        metrics.memory_used_bytes = end_memory - start_memory
        
        return ast, metrics
    
    def switch_parser(self, parser_name: str, **config):
        """Switch to a different parser implementation.
        
        Args:
            parser_name: Name of parser to switch to
            **config: New configuration options
        """
        self._parser_name = parser_name
        self._config = config
        self._parser = None  # Force reload on next use
        self._load_parser()
    
    def configure(self, **config):
        """Update parser configuration.
        
        Args:
            **config: Configuration options to update
        """
        self._config.update(config)
        if self._parser:
            self._parser.configure(**config)
    
    def explain_parse(self, tokens: List[Token]) -> str:
        """Get educational explanation of parsing process.
        
        Args:
            tokens: Tokens to explain parsing for
            
        Returns:
            Explanation string
        """
        return self.parser.explain_parse(tokens)
    
    def compare_parsers(self, tokens: List[Token], 
                       parser_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare multiple parser implementations.
        
        Args:
            tokens: Tokens to parse
            parser_names: List of parsers to compare (None for all)
            
        Returns:
            Dictionary of comparison results
        """
        if parser_names is None:
            parser_names = ParserRegistry.list_parsers()
        
        results = {}
        
        for parser_name in parser_names:
            try:
                # Create temporary parser
                parser = ParserRegistry.create(parser_name)
                
                # Parse with metrics
                parser.reset_metrics()
                start_time = time.perf_counter()
                
                tracemalloc.start()
                start_memory = tracemalloc.get_traced_memory()[0]
                
                try:
                    ast = parser.parse(tokens.copy())
                    success = True
                    error = None
                except Exception as e:
                    ast = None
                    success = False
                    error = str(e)
                
                end_memory = tracemalloc.get_traced_memory()[0]
                tracemalloc.stop()
                
                end_time = time.perf_counter()
                
                # Collect results
                metrics = parser.get_metrics()
                metrics.parse_time_ms = (end_time - start_time) * 1000
                metrics.memory_used_bytes = end_memory - start_memory
                
                results[parser_name] = {
                    "success": success,
                    "error": error,
                    "ast_type": type(ast).__name__ if ast else None,
                    "metrics": metrics.to_dict(),
                    "characteristics": parser.get_characteristics().to_dict()
                }
                
            except Exception as e:
                results[parser_name] = {
                    "success": False,
                    "error": f"Failed to create parser: {e}"
                }
        
        return results


@contextmanager
def temporary_parser(parser_name: str, **config):
    """Context manager for temporarily using a different parser.
    
    Args:
        parser_name: Parser to use temporarily
        **config: Configuration for the temporary parser
        
    Yields:
        Configured parser instance
    """
    parser = ParserRegistry.create(parser_name, **config)
    yield parser
    # Parser is automatically cleaned up when context exits