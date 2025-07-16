"""Context-aware token recognizer base class."""

from abc import ABC, abstractmethod
from typing import Optional

from .enhanced_context import EnhancedLexerContext, ContextHint, get_context_hint
from ..token_enhanced import EnhancedToken, TokenContext, SemanticType
from ..token_types import Token, TokenType


class ContextAwareRecognizer(ABC):
    """Base class for context-aware token recognition."""
    
    def __init__(self, priority: int = 50):
        """Initialize with priority (higher = checked first)."""
        self.priority = priority
    
    @abstractmethod
    def can_recognize(
        self,
        char: str,
        position: int,
        context: EnhancedLexerContext
    ) -> bool:
        """Check if this recognizer can handle the current position."""
        pass
    
    @abstractmethod
    def recognize_basic(
        self,
        text: str,
        position: int,
        context: EnhancedLexerContext
    ) -> Optional[Token]:
        """Basic recognition without context enhancement."""
        pass
    
    def recognize_with_context(
        self,
        text: str,
        position: int,
        context: EnhancedLexerContext
    ) -> Optional[EnhancedToken]:
        """Recognize token with context information."""
        # Basic recognition first
        token = self.recognize_basic(text, position, context)
        if not token:
            return None
        
        # Enhance with context
        enhanced = EnhancedToken.from_token(token)
        
        # Add current contexts
        for ctx in context.get_current_contexts():
            enhanced.add_context(ctx)
        
        # Specific enhancements based on token type and context
        self._enhance_token(enhanced, context)
        
        return enhanced
    
    def _enhance_token(
        self,
        token: EnhancedToken,
        context: EnhancedLexerContext
    ):
        """Add context-specific enhancements to the token."""
        # Get context hint
        hint = get_context_hint(context)
        
        # Set semantic type based on token type and context
        if token.type in {TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.FI,
                         TokenType.WHILE, TokenType.DO, TokenType.DONE, TokenType.FOR,
                         TokenType.IN, TokenType.CASE, TokenType.ESAC, TokenType.SELECT,
                         TokenType.FUNCTION, TokenType.BREAK, TokenType.CONTINUE}:
            token.set_semantic_type(SemanticType.KEYWORD)
        
        elif token.type in {TokenType.PIPE, TokenType.AND_AND, TokenType.OR_OR,
                           TokenType.SEMICOLON, TokenType.AMPERSAND}:
            token.set_semantic_type(SemanticType.OPERATOR)
        
        elif token.type in {TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
                           TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR,
                           TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP,
                           TokenType.HEREDOC, TokenType.HEREDOC_STRIP}:
            token.set_semantic_type(SemanticType.REDIRECT)
        
        elif token.type in {TokenType.ASSIGNMENT_WORD, TokenType.ARRAY_ASSIGNMENT_WORD}:
            token.set_semantic_type(SemanticType.ASSIGNMENT)
        
        elif token.type in {TokenType.GLOB_STAR, TokenType.GLOB_QUESTION, 
                           TokenType.GLOB_BRACKET}:
            token.set_semantic_type(SemanticType.PATTERN)
        
        elif token.type in {TokenType.VARIABLE, TokenType.COMMAND_SUB,
                           TokenType.COMMAND_SUB_BACKTICK, TokenType.ARITH_EXPANSION,
                           TokenType.PROCESS_SUB_IN, TokenType.PROCESS_SUB_OUT}:
            token.set_semantic_type(SemanticType.EXPANSION)
        
        # Context-specific adjustments
        if hint == ContextHint.ASSIGNMENT and token.type == TokenType.WORD:
            # Check if this word could be an assignment
            if self._looks_like_assignment(token.value):
                # This might need to be re-tokenized as assignment
                token.add_context(TokenContext.COMMAND_POSITION)
        
        elif hint == ContextHint.PATTERN and token.type == TokenType.WORD:
            # Word in pattern context might be a glob pattern
            if self._looks_like_pattern(token.value):
                token.set_semantic_type(SemanticType.PATTERN)
        
        elif hint == ContextHint.COMMAND and token.type == TokenType.WORD:
            # Word in command position - could be builtin, function, or external
            token.add_context(TokenContext.COMMAND_POSITION)
            
            # Check if it's a known builtin
            if self._is_builtin(token.value):
                token.set_semantic_type(SemanticType.BUILTIN)
            elif self._is_likely_identifier(token.value):
                token.set_semantic_type(SemanticType.IDENTIFIER)
        
        # Expansion depth tracking
        if token.is_expansion:
            token.metadata.expansion_depth = context.get_nesting_depth()
        
        # Quote depth tracking (if applicable)
        # This would be set by quote-aware recognizers
    
    def _looks_like_assignment(self, value: str) -> bool:
        """Check if a value looks like an assignment pattern."""
        return '=' in value and not value.startswith('=')
    
    def _looks_like_pattern(self, value: str) -> bool:
        """Check if a value looks like a glob pattern."""
        return any(char in value for char in '*?[]{}')
    
    def _is_builtin(self, value: str) -> bool:
        """Check if a value is a known builtin command."""
        # Common shell builtins
        builtins = {
            'cd', 'pwd', 'echo', 'printf', 'read', 'test', 'true', 'false',
            'exit', 'return', 'source', '.', 'eval', 'exec', 'export',
            'unset', 'set', 'shift', 'declare', 'local', 'readonly',
            'alias', 'unalias', 'history', 'fc', 'jobs', 'bg', 'fg',
            'kill', 'wait', 'trap', 'umask', 'ulimit', 'times', 'type',
            'which', 'command', 'builtin', 'enable', 'help', 'let',
            'pushd', 'popd', 'dirs', 'getopts', 'complete', 'compgen'
        }
        return value in builtins
    
    def _is_likely_identifier(self, value: str) -> bool:
        """Check if a value looks like an identifier."""
        if not value:
            return False
        
        # Must start with letter or underscore
        if not (value[0].isalpha() or value[0] == '_'):
            return False
        
        # Must contain only alphanumeric and underscores
        return all(c.isalnum() or c == '_' for c in value)


class CompatibilityRecognizer(ContextAwareRecognizer):
    """Wrapper for non-context-aware recognizers."""
    
    def __init__(self, base_recognizer, priority: int = None):
        """Wrap a basic recognizer to make it context-aware."""
        super().__init__(priority or getattr(base_recognizer, 'priority', 50))
        self.base_recognizer = base_recognizer
    
    def can_recognize(
        self,
        char: str,
        position: int,
        context: EnhancedLexerContext
    ) -> bool:
        """Delegate to base recognizer."""
        # Try to use base recognizer's can_recognize if available
        if hasattr(self.base_recognizer, 'can_recognize'):
            return self.base_recognizer.can_recognize(char, position, context)
        
        # Fallback: assume it can recognize if it has a recognize method
        return hasattr(self.base_recognizer, 'recognize')
    
    def recognize_basic(
        self,
        text: str,
        position: int,
        context: EnhancedLexerContext
    ) -> Optional[Token]:
        """Delegate to base recognizer."""
        if hasattr(self.base_recognizer, 'recognize'):
            return self.base_recognizer.recognize(text, position, context)
        return None


def make_context_aware(recognizer, priority: int = None) -> ContextAwareRecognizer:
    """Convert a basic recognizer to context-aware."""
    if isinstance(recognizer, ContextAwareRecognizer):
        return recognizer
    
    return CompatibilityRecognizer(recognizer, priority)