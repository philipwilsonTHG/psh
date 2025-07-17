"""Enhanced lexer-parser contract for improved interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Iterator, Protocol
from enum import Enum

from ..token_types import Token
from ..token_enhanced import LexerError, TokenMetadata
from .token_stream_validator import TokenStreamValidator, TokenStreamValidationResult


class TokenStreamQuality(Enum):
    """Quality levels of token stream."""
    PERFECT = "perfect"        # No errors or warnings
    GOOD = "good"             # Minor warnings only
    ACCEPTABLE = "acceptable"  # Some recoverable errors
    POOR = "poor"             # Many errors, parsing may fail
    UNUSABLE = "unusable"     # Fatal errors, cannot parse


@dataclass
class LexerParserContract:
    """Contract between lexer and parser defining expectations."""
    
    # Token stream properties
    tokens: List[Token]
    validation_result: TokenStreamValidationResult
    source_text: Optional[str] = None
    
    # Quality assessment
    stream_quality: TokenStreamQuality = TokenStreamQuality.ACCEPTABLE
    
    # Parser guidance
    error_recovery_hints: List[str] = None
    
    # Metadata
    lexer_version: str = "enhanced_v2"  # Version updated for simplified contract
    processing_time_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.error_recovery_hints is None:
            self.error_recovery_hints = []
        
        # Assess stream quality based on validation results
        self.stream_quality = self._assess_quality()
    
    def _assess_quality(self) -> TokenStreamQuality:
        """Assess the quality of the token stream."""
        if not self.validation_result:
            return TokenStreamQuality.ACCEPTABLE
        
        error_count = len(self.validation_result.errors)
        warning_count = len(self.validation_result.warnings)
        
        if error_count == 0 and warning_count == 0:
            return TokenStreamQuality.PERFECT
        elif error_count == 0 and warning_count <= 2:
            return TokenStreamQuality.GOOD
        elif error_count <= 2 and warning_count <= 5:
            return TokenStreamQuality.ACCEPTABLE
        elif error_count <= 5:
            return TokenStreamQuality.POOR
        else:
            return TokenStreamQuality.UNUSABLE
    
    def get_parser_guidance(self) -> Dict[str, Any]:
        """Get guidance for parser based on token stream analysis."""
        guidance = {
            'quality': self.stream_quality,
            'error_count': len(self.validation_result.errors) if self.validation_result else 0,
            'warning_count': len(self.validation_result.warnings) if self.validation_result else 0,
            'recovery_hints': self.error_recovery_hints
        }
        
        # Add specific guidance based on errors
        if self.validation_result:
            guidance['syntax_errors'] = [
                error for error in self.validation_result.errors 
                if 'syntax' in error.error_type.lower()
            ]
            
            guidance['expansion_errors'] = [
                error for error in self.validation_result.errors
                if 'expansion' in error.error_type.lower()
            ]
            
            guidance['quote_errors'] = [
                error for error in self.validation_result.errors
                if 'quote' in error.error_type.lower()
            ]
            
            guidance['bracket_errors'] = [
                error for error in self.validation_result.errors
                if 'bracket' in error.error_type.lower()
            ]
        
        return guidance
    
    def should_attempt_parsing(self) -> bool:
        """Determine if parser should attempt to parse this stream."""
        return self.stream_quality in {
            TokenStreamQuality.PERFECT,
            TokenStreamQuality.GOOD,
            TokenStreamQuality.ACCEPTABLE
        }
    
    def get_error_recovery_strategy(self) -> str:
        """Get recommended error recovery strategy."""
        if self.stream_quality == TokenStreamQuality.UNUSABLE:
            return "abort"
        elif self.stream_quality == TokenStreamQuality.POOR:
            return "aggressive_recovery"
        elif self.stream_quality == TokenStreamQuality.ACCEPTABLE:
            return "selective_recovery"
        else:
            return "minimal_recovery"


class EnhancedLexerInterface(Protocol):
    """Protocol defining the enhanced lexer interface."""
    
    def tokenize_with_validation(
        self,
        text: str,
        validate: bool = True
    ) -> LexerParserContract:
        """Tokenize text and return enhanced contract."""
        ...
    
    def get_validation_result(self) -> Optional[TokenStreamValidationResult]:
        """Get the last validation result."""
        ...
    
    def set_compatibility_mode(self, enabled: bool):
        """Enable/disable compatibility mode for legacy parsers."""
        ...
    
    def get_enhanced_tokens(self) -> List[Token]:
        """Get the enhanced token stream."""
        ...


class ParserFeedback:
    """Feedback from parser to lexer about token quality."""
    
    def __init__(self):
        self.unexpected_tokens: List[Token] = []
        self.missing_tokens: List[str] = []
        self.context_mismatches: List[Tuple[Token, str]] = []
        self.successful_recoveries: List[str] = []
        self.failed_recoveries: List[str] = []
    
    def report_unexpected_token(self, token: Token, expected: str = None):
        """Report a token that was unexpected during parsing."""
        self.unexpected_tokens.append(token)
        if expected:
            self.missing_tokens.append(expected)
    
    def report_context_mismatch(self, token: Token, expected_context: str):
        """Report a token that was in wrong context."""
        self.context_mismatches.append((token, expected_context))
    
    def report_recovery_success(self, strategy: str):
        """Report successful error recovery."""
        self.successful_recoveries.append(strategy)
    
    def report_recovery_failure(self, strategy: str):
        """Report failed error recovery attempt."""
        self.failed_recoveries.append(strategy)
    
    def get_lexer_improvements(self) -> Dict[str, Any]:
        """Get suggestions for lexer improvements based on feedback."""
        improvements = {}
        
        # Analyze unexpected tokens
        if self.unexpected_tokens:
            token_types = {}
            for token in self.unexpected_tokens:
                if token.type not in token_types:
                    token_types[token.type] = 0
                token_types[token.type] += 1
            
            improvements['frequent_unexpected_tokens'] = token_types
        
        # Analyze context mismatches
        if self.context_mismatches:
            context_issues = {}
            for token, expected in self.context_mismatches:
                key = f"{token.type}->{expected}"
                if key not in context_issues:
                    context_issues[key] = 0
                context_issues[key] += 1
            
            improvements['context_recognition_issues'] = context_issues
        
        # Recovery analysis
        improvements['recovery_success_rate'] = (
            len(self.successful_recoveries) / 
            (len(self.successful_recoveries) + len(self.failed_recoveries))
            if (self.successful_recoveries or self.failed_recoveries) else 1.0
        )
        
        return improvements


# Legacy compatibility adapter removed - enhanced features are now standard

def extract_legacy_tokens(contract: LexerParserContract) -> List:
    """Extract legacy-format tokens from enhanced contract for backward compatibility."""
    from ..token_types import Token
    
    legacy_tokens = []
    for enhanced_token in contract.tokens:
        # Create basic token with essential properties
        legacy_token = Token(
            type=enhanced_token.type,
            value=enhanced_token.value,
            position=enhanced_token.position,
            end_position=enhanced_token.end_position,
            quote_type=enhanced_token.quote_type,
            parts=getattr(enhanced_token, 'parts', None)
        )
        legacy_tokens.append(legacy_token)
    
    return legacy_tokens


def get_error_summary_for_legacy(contract: LexerParserContract) -> str:
    """Get error summary in format expected by legacy parser."""
    if not contract.validation_result or not contract.validation_result.errors:
        return ""
    
    summaries = []
    for error in contract.validation_result.errors[:3]:  # Limit to first 3
        if isinstance(error, str):
            # Handle string errors from fallback paths
            summaries.append(f"Error: {error}")
        else:
            # Handle structured error objects
            summaries.append(f"{error.error_type}: {error.message}")
    
    if len(contract.validation_result.errors) > 3:
        summaries.append(f"... and {len(contract.validation_result.errors) - 3} more errors")
    
    return "; ".join(summaries)


class EnhancedLexerImplementation:
    """Reference implementation of enhanced lexer interface."""
    
    def __init__(self, base_lexer=None):
        self.base_lexer = base_lexer
        self.validator = TokenStreamValidator()
        self.compatibility_mode = False
        self.last_validation_result = None
        
        # Performance tracking
        self.processing_stats = {
            'tokenization_time': 0.0,
            'validation_time': 0.0,
            'enhancement_time': 0.0
        }
    
    def tokenize_with_validation(
        self,
        text: str,
        validate: bool = True
    ) -> LexerParserContract:
        """Main entry point for enhanced tokenization."""
        import time
        start_time = time.time()
        
        try:
            # 1. Basic tokenization (delegate to base lexer if available)
            tokenization_start = time.time()
            if self.base_lexer:
                basic_tokens = self.base_lexer.tokenize(text)
                # Convert to enhanced tokens
                enhanced_tokens = [Token.from_token(token) for token in basic_tokens]
            else:
                # Use minimal tokenization for demonstration
                enhanced_tokens = self._minimal_tokenize(text)
            
            self.processing_stats['tokenization_time'] = time.time() - tokenization_start
            
            # 2. Token enhancement
            enhancement_start = time.time()
            self._enhance_tokens(enhanced_tokens, text)
            self.processing_stats['enhancement_time'] = time.time() - enhancement_start
            
            # 3. Validation
            validation_start = time.time()
            validation_result = None
            if validate:
                validation_result = self.validator.validate_token_stream(enhanced_tokens, text)
                self.last_validation_result = validation_result
            self.processing_stats['validation_time'] = time.time() - validation_start
            
            # 4. Create contract
            total_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            contract = LexerParserContract(
                tokens=enhanced_tokens,
                validation_result=validation_result,
                source_text=text,
                compatibility_mode=self.compatibility_mode,
                processing_time_ms=total_time
            )
            
            # 5. Add error recovery hints
            if validation_result and validation_result.errors:
                contract.error_recovery_hints = self._generate_recovery_hints(validation_result)
            
            return contract
            
        except Exception as e:
            # Fallback for errors during enhanced processing
            fallback_tokens = [Token(
                type='ERROR',
                value=str(e),
                position=0,
                end_position=len(text)
            )]
            
            return LexerParserContract(
                tokens=fallback_tokens,
                validation_result=None,
                source_text=text,
                stream_quality=TokenStreamQuality.UNUSABLE,
                error_recovery_hints=[f"Lexer error: {str(e)}"]
            )
    
    def _minimal_tokenize(self, text: str) -> List[Token]:
        """Minimal tokenization for demonstration purposes."""
        # This is a placeholder - in real implementation, 
        # would delegate to the existing lexer
        tokens = []
        words = text.split()
        position = 0
        
        for word in words:
            tokens.append(Token(
                type='WORD',
                value=word,
                position=position,
                end_position=position + len(word)
            ))
            position += len(word) + 1  # +1 for space
        
        return tokens
    
    def _enhance_tokens(self, tokens: List[Token], source_text: str):
        """Add enhancements to basic tokens."""
        # This would apply context-aware recognizers, assignment detection, etc.
        # For now, just add basic metadata
        for token in tokens:
            if not token.metadata:
                token.metadata = TokenMetadata()
            
            # Add basic context information
            token.metadata.source_text = source_text
    
    def _generate_recovery_hints(self, validation_result: TokenStreamValidationResult) -> List[str]:
        """Generate error recovery hints for parser."""
        hints = []
        
        for error in validation_result.errors:
            if error.error_type == 'UNCLOSED_QUOTE':
                hints.append("Try inserting missing quote at end of line")
            elif error.error_type == 'UNCLOSED_EXPANSION':
                hints.append("Try inserting missing closing bracket for expansion")
            elif error.error_type == 'UNMATCHED_BRACKET':
                hints.append("Try balancing brackets or removing extra brackets")
        
        return hints
    
    def get_validation_result(self) -> Optional[TokenStreamValidationResult]:
        """Get the last validation result."""
        return self.last_validation_result
    
    def set_compatibility_mode(self, enabled: bool):
        """Enable/disable compatibility mode."""
        self.compatibility_mode = enabled
    
    def get_enhanced_tokens(self) -> List[Token]:
        """Get the enhanced token stream from last tokenization."""
        if self.last_validation_result:
            return self.last_validation_result.validated_tokens
        return []
    
    def get_processing_stats(self) -> Dict[str, float]:
        """Get processing time statistics."""
        return self.processing_stats.copy()


# Factory function for creating enhanced lexer
def create_enhanced_lexer(base_lexer=None) -> EnhancedLexerImplementation:
    """Create an enhanced lexer implementation."""
    return EnhancedLexerImplementation(base_lexer)


# Utility functions for parser integration
def extract_legacy_tokens(contract: LexerParserContract) -> List:
    """Extract legacy-compatible tokens from contract."""
    adapter = CompatibilityAdapter(contract)
    return adapter.get_legacy_tokens()


def should_use_enhanced_parsing(contract: LexerParserContract) -> bool:
    """Determine if enhanced parsing features should be used."""
    return (contract.lexer_version.startswith('enhanced') and 
            contract.stream_quality != TokenStreamQuality.UNUSABLE and
            not contract.compatibility_mode)


def get_parser_error_context(
    contract: LexerParserContract,
    error_position: int
) -> Dict[str, Any]:
    """Get context information for parser errors."""
    context = {
        'position': error_position,
        'surrounding_tokens': [],
        'validation_issues': [],
        'suggestions': []
    }
    
    # Find tokens around error position
    for token in contract.tokens:
        if abs(token.position - error_position) <= 50:  # Within 50 chars
            context['surrounding_tokens'].append({
                'type': token.type,
                'value': token.value,
                'distance': abs(token.position - error_position)
            })
    
    # Find related validation issues
    if contract.validation_result:
        for issue in contract.validation_result.all_issues:
            if hasattr(issue, 'position') and issue.position:
                if abs(issue.position - error_position) <= 20:
                    context['validation_issues'].append(issue)
                    if issue.suggestion:
                        context['suggestions'].append(issue.suggestion)
    
    return context