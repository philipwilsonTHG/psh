"""Registry for token recognizers."""

from typing import List, Optional, Tuple, Dict, Type
from .base import TokenRecognizer
from ..state_context import LexerContext
from ...token_types import Token


class RecognizerRegistry:
    """Registry and dispatcher for token recognizers."""
    
    def __init__(self):
        """Initialize empty registry."""
        self._recognizers: List[TokenRecognizer] = []
        self._sorted = False
    
    def register(self, recognizer: TokenRecognizer) -> None:
        """
        Register a new token recognizer.
        
        Args:
            recognizer: The recognizer to register
        """
        self._recognizers.append(recognizer)
        self._sorted = False  # Need to re-sort by priority
    
    def register_class(self, recognizer_class: Type[TokenRecognizer], *args, **kwargs) -> None:
        """
        Register a recognizer class (instantiates it).
        
        Args:
            recognizer_class: The recognizer class to instantiate and register
            *args, **kwargs: Arguments to pass to the constructor
        """
        recognizer = recognizer_class(*args, **kwargs)
        self.register(recognizer)
    
    def unregister(self, recognizer: TokenRecognizer) -> bool:
        """
        Unregister a recognizer.
        
        Args:
            recognizer: The recognizer to remove
            
        Returns:
            True if the recognizer was found and removed
        """
        try:
            self._recognizers.remove(recognizer)
            return True
        except ValueError:
            return False
    
    def unregister_by_type(self, recognizer_type: Type[TokenRecognizer]) -> int:
        """
        Unregister all recognizers of a specific type.
        
        Args:
            recognizer_type: The type of recognizers to remove
            
        Returns:
            Number of recognizers removed
        """
        removed = 0
        self._recognizers = [
            r for r in self._recognizers 
            if not isinstance(r, recognizer_type) or (removed := removed + 1, False)[1]
        ]
        return removed
    
    def get_recognizers(self) -> List[TokenRecognizer]:
        """
        Get all registered recognizers, sorted by priority.
        
        Returns:
            List of recognizers sorted by priority (highest first)
        """
        if not self._sorted:
            self._recognizers.sort(key=lambda r: r.priority, reverse=True)
            self._sorted = True
        
        return self._recognizers.copy()
    
    def find_recognizer(self, recognizer_type: Type[TokenRecognizer]) -> Optional[TokenRecognizer]:
        """
        Find the first recognizer of a specific type.
        
        Args:
            recognizer_type: The type of recognizer to find
            
        Returns:
            The first matching recognizer, or None if not found
        """
        for recognizer in self._recognizers:
            if isinstance(recognizer, recognizer_type):
                return recognizer
        return None
    
    def recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> Optional[Tuple[Token, int, TokenRecognizer]]:
        """
        Try to recognize a token using registered recognizers.
        
        Args:
            input_text: The input string being lexed
            pos: Current position in the input
            context: Current lexer context/state
            
        Returns:
            Tuple of (token, new_position, recognizer) if recognized, None otherwise
        """
        recognizers = self.get_recognizers()
        
        for recognizer in recognizers:
            try:
                if recognizer.can_recognize(input_text, pos, context):
                    result = recognizer.recognize(input_text, pos, context)
                    if result is not None:
                        token, new_pos = result
                        return token, new_pos, recognizer
            except Exception as e:
                # Log error but continue with other recognizers
                # In production, you might want to use proper logging
                print(f"Error in recognizer {recognizer.name}: {e}")
                continue
        
        return None
    
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> List[TokenRecognizer]:
        """
        Find all recognizers that can potentially recognize at current position.
        
        Args:
            input_text: The input string being lexed
            pos: Current position in the input
            context: Current lexer context/state
            
        Returns:
            List of recognizers that claim they can recognize at this position
        """
        candidates = []
        recognizers = self.get_recognizers()
        
        for recognizer in recognizers:
            try:
                if recognizer.can_recognize(input_text, pos, context):
                    candidates.append(recognizer)
            except Exception as e:
                # Log error but continue
                print(f"Error checking recognizer {recognizer.name}: {e}")
                continue
        
        return candidates
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about registered recognizers.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_recognizers': len(self._recognizers),
            'recognizer_types': {}
        }
        
        for recognizer in self._recognizers:
            recognizer_type = type(recognizer).__name__
            stats['recognizer_types'][recognizer_type] = (
                stats['recognizer_types'].get(recognizer_type, 0) + 1
            )
        
        return stats
    
    def clear(self) -> None:
        """Remove all registered recognizers."""
        self._recognizers.clear()
        self._sorted = True
    
    def __len__(self) -> int:
        """Get the number of registered recognizers."""
        return len(self._recognizers)
    
    def __iter__(self):
        """Iterate over recognizers in priority order."""
        return iter(self.get_recognizers())


# Default registry instance
default_registry = RecognizerRegistry()


def get_default_registry() -> RecognizerRegistry:
    """Get the default registry instance."""
    return default_registry


def setup_default_recognizers() -> RecognizerRegistry:
    """Set up the default registry with standard recognizers."""
    from .operator import OperatorRecognizer
    from .keyword import KeywordRecognizer
    from .literal import LiteralRecognizer
    from .whitespace import WhitespaceRecognizer
    from .comment import CommentRecognizer
    from .process_sub import ProcessSubstitutionRecognizer
    
    registry = get_default_registry()
    registry.clear()
    
    # Register recognizers in order (priority determines actual order)
    registry.register(ProcessSubstitutionRecognizer())  # Priority 160
    registry.register(OperatorRecognizer())
    registry.register(KeywordRecognizer())
    registry.register(LiteralRecognizer())
    registry.register(WhitespaceRecognizer())
    registry.register(CommentRecognizer())
    
    return registry