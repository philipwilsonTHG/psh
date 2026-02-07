"""Integration adapter for enhanced lexer components with existing lexer."""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from ..token_enhanced import TokenMetadata
from ..token_types import Token, TokenType
from .context_recognizer import ContextAwareRecognizer
from .enhanced_context import EnhancedLexerContext
from .modular_lexer import ModularLexer
from .parser_contract import EnhancedLexerInterface, LexerParserContract, TokenStreamQuality
from .position import LexerConfig
from .recognizers.assignment import AssignmentRecognizer
from .token_stream_validator import TokenStreamValidationResult, TokenStreamValidator


@dataclass
class EnhancementConfig:
    """Configuration for enhanced lexer features."""
    enable_validation: bool = True
    enable_context_tracking: bool = True
    enable_assignment_detection: bool = True
    enable_semantic_analysis: bool = True
    validation_level: str = "full"  # "minimal", "standard", "full"

    # Performance settings
    max_validation_time_ms: float = 100.0
    enable_performance_tracking: bool = True


class EnhancedModularLexer(EnhancedLexerInterface):
    """Enhanced wrapper around existing ModularLexer."""

    def __init__(
        self,
        base_lexer: Optional[ModularLexer] = None,
        enhancement_config: Optional[EnhancementConfig] = None
    ):
        self.base_lexer = base_lexer
        self.enhancement_config = enhancement_config or EnhancementConfig()

        # Enhanced components
        self.validator = TokenStreamValidator() if self.enhancement_config.enable_validation else None
        self.enhanced_context = EnhancedLexerContext() if self.enhancement_config.enable_context_tracking else None

        # Enhanced recognizers
        self.enhanced_recognizers = []
        if self.enhancement_config.enable_assignment_detection:
            self.enhanced_recognizers.append(AssignmentRecognizer())

        # Performance tracking
        self.performance_stats = {
            'total_time': 0.0,
            'base_lexer_time': 0.0,
            'enhancement_time': 0.0,
            'validation_time': 0.0,
            'token_count': 0,
            'enhancement_overhead': 0.0
        }

        # Validation results
        self.last_validation_result: Optional[TokenStreamValidationResult] = None
        self.last_contract: Optional[LexerParserContract] = None

    def tokenize_with_validation(
        self,
        text: str,
        validate: bool = True
    ) -> LexerParserContract:
        """Main enhanced tokenization entry point."""
        start_time = time.time()

        try:
            # 1. Get base tokens from existing lexer
            base_start = time.time()
            base_tokens = self._get_base_tokens(text)
            base_time = time.time() - base_start

            # 2. Convert to enhanced tokens
            enhance_start = time.time()
            enhanced_tokens = self._convert_to_enhanced_tokens(base_tokens, text)

            # 3. Apply enhanced recognizers
            if self.enhancement_config.enable_assignment_detection:
                enhanced_tokens = self._apply_enhanced_recognizers(enhanced_tokens, text)

            # 4. Add context information
            if self.enhancement_config.enable_context_tracking:
                self._add_context_information(enhanced_tokens, text)

            # 5. Add semantic types
            if self.enhancement_config.enable_semantic_analysis:
                self._add_semantic_types(enhanced_tokens)

            enhance_time = time.time() - enhance_start

            # 6. Validate token stream
            validation_start = time.time()
            validation_result = None
            if validate and self.validator and self.enhancement_config.enable_validation:
                validation_result = self._validate_with_timeout(enhanced_tokens, text)
            validation_time = time.time() - validation_start

            # 7. Create contract
            total_time = time.time() - start_time
            contract = self._create_contract(enhanced_tokens, validation_result, text, total_time * 1000)

            # 8. Update performance stats
            self._update_performance_stats(base_time, enhance_time, validation_time, total_time, len(enhanced_tokens))

            self.last_contract = contract
            return contract

        except Exception as e:
            # Fallback to compatibility mode on errors
            return self._create_fallback_contract(text, str(e))

    def _get_base_tokens(self, text: str) -> List[Token]:
        """Get tokens from base lexer or create minimal tokens."""
        if self.base_lexer:
            return self.base_lexer.tokenize()
        else:
            # Create minimal tokenization for standalone operation
            return self._minimal_tokenize(text)

    def _minimal_tokenize(self, text: str) -> List[Token]:
        """Minimal tokenization when no base lexer available."""
        tokens = []
        words = text.split()
        position = 0

        for word in words:
            # Skip whitespace
            while position < len(text) and text[position].isspace():
                position += 1

            if position >= len(text):
                break

            # Determine basic token type
            token_type = TokenType.WORD
            if word == '|':
                token_type = TokenType.PIPE
            elif word == ';':
                token_type = TokenType.SEMICOLON
            elif word == '&':
                token_type = TokenType.AMPERSAND
            elif word == '&&':
                token_type = TokenType.AND_AND
            elif word == '||':
                token_type = TokenType.OR_OR

            tokens.append(Token(
                type=token_type,
                value=word,
                position=position,
                end_position=position + len(word)
            ))

            position += len(word)

        # Add EOF token
        tokens.append(Token(
            type=TokenType.EOF,
            value='',
            position=len(text),
            end_position=len(text)
        ))

        return tokens

    def _convert_to_enhanced_tokens(self, base_tokens: List[Token], text: str) -> List[Token]:
        """Convert base tokens to enhanced tokens."""
        enhanced_tokens = []

        for token in base_tokens:
            # Convert to enhanced token
            enhanced = Token.from_token(token)

            # Add basic metadata
            if not enhanced.metadata:
                enhanced.metadata = TokenMetadata()

            enhanced.metadata.source_text = text
            enhanced.metadata.lexer_version = "enhanced_integrated_v1"

            enhanced_tokens.append(enhanced)

        return enhanced_tokens

    def _apply_enhanced_recognizers(self, tokens: List[Token], text: str) -> List[Token]:
        """Apply enhanced recognizers to detect patterns missed by base lexer."""
        if not self.enhanced_recognizers:
            return tokens

        enhanced_tokens = []

        for token in tokens:
            # Check if any enhanced recognizer can improve this token
            improved_token = token

            for recognizer in self.enhanced_recognizers:
                if isinstance(recognizer, ContextAwareRecognizer):
                    # Try to enhance with context-aware recognizer
                    if recognizer.can_recognize(token.value[0] if token.value else '',
                                               token.position, self.enhanced_context):

                        # Create enhanced version
                        enhanced_result = recognizer.recognize_with_context(
                            text, token.position, self.enhanced_context
                        )

                        if enhanced_result and enhanced_result.value == token.value:
                            # Replace with enhanced version
                            improved_token = enhanced_result
                            break

            enhanced_tokens.append(improved_token)

        return enhanced_tokens

    def _add_context_information(self, tokens: List[Token], text: str):
        """Add context information to tokens."""
        if not self.enhanced_context:
            return

        for i, token in enumerate(tokens):
            # Add current contexts to token
            current_contexts = self.enhanced_context.get_current_contexts()
            for context in current_contexts:
                token.add_context(context)

            # Set command position for first non-whitespace token
            if i == 0 or (i > 0 and tokens[i-1].type in {TokenType.SEMICOLON, TokenType.AND_AND, TokenType.OR_OR}):
                token.add_context('command_position')

    def _add_semantic_types(self, tokens: List[Token]):
        """Add semantic type information to tokens."""
        for token in tokens:
            # Basic semantic type assignment
            if token.type in {TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.FI,
                             TokenType.WHILE, TokenType.UNTIL, TokenType.DO, TokenType.DONE, TokenType.FOR}:
                token.set_semantic_type('keyword')
            elif token.type in {TokenType.PIPE, TokenType.AND_AND, TokenType.OR_OR,
                               TokenType.SEMICOLON, TokenType.AMPERSAND}:
                token.set_semantic_type('operator')
            elif token.type in {TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
                               TokenType.REDIRECT_APPEND, TokenType.HEREDOC}:
                token.set_semantic_type('redirect')
            elif hasattr(token, 'assignment_info'):
                token.set_semantic_type('assignment')
            elif token.type == TokenType.WORD:
                token.set_semantic_type('identifier')

    def _validate_with_timeout(
        self,
        tokens: List[Token],
        text: str
    ) -> Optional[TokenStreamValidationResult]:
        """Validate tokens with timeout protection."""
        if not self.validator:
            return None

        start_time = time.time()
        max_time = self.enhancement_config.max_validation_time_ms / 1000.0

        try:
            # Quick validation for performance
            if self.enhancement_config.validation_level == "minimal":
                return self._minimal_validation(tokens)
            elif self.enhancement_config.validation_level == "standard":
                return self.validator.validate_partial_stream(tokens[:50])  # Limit tokens
            else:
                # Full validation with timeout check
                result = self.validator.validate_token_stream(tokens, text)

                # Check if we exceeded timeout
                elapsed = time.time() - start_time
                if elapsed > max_time:
                    # Log timeout but return partial result
                    print(f"Validation timeout ({elapsed:.2f}s > {max_time:.2f}s)")

                return result

        except Exception:
            # Validation failed, return minimal result
            return TokenStreamValidationResult(
                is_valid=False,
                errors=[],
                warnings=[],
                infos=[],
                validated_tokens=tokens
            )

    def _minimal_validation(self, tokens: List[Token]) -> TokenStreamValidationResult:
        """Minimal validation for performance-critical scenarios."""
        errors = []
        warnings = []

        # Just check for basic syntax errors
        paren_depth = 0
        for token in tokens:
            if token.type == TokenType.LPAREN:
                paren_depth += 1
            elif token.type == TokenType.RPAREN:
                paren_depth -= 1
                if paren_depth < 0:
                    errors.append(f"Unmatched ')' at position {token.position}")

        if paren_depth > 0:
            errors.append(f"Unclosed '(' (depth: {paren_depth})")

        return TokenStreamValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            infos=[],
            validated_tokens=tokens
        )

    def _create_contract(
        self,
        tokens: List[Token],
        validation_result: Optional[TokenStreamValidationResult],
        text: str,
        processing_time_ms: float
    ) -> LexerParserContract:
        """Create lexer-parser contract."""
        contract = LexerParserContract(
            tokens=tokens,
            validation_result=validation_result,
            source_text=text,
            lexer_version="enhanced_modular_v2",
            processing_time_ms=processing_time_ms
        )

        # Add recovery hints if there are errors
        if validation_result and validation_result.errors:
            contract.error_recovery_hints = self._generate_recovery_hints(validation_result.errors)

        return contract

    def _create_fallback_contract(self, text: str, error: str) -> LexerParserContract:
        """Create fallback contract when enhancement fails."""
        # Use base lexer only
        enhanced_tokens = []
        base_lexer_failed = False

        try:
            base_tokens = self._get_base_tokens(text)
            enhanced_tokens = [Token.from_token(token) for token in base_tokens]
        except Exception:
            # Even base lexer failed - create minimal tokens
            base_lexer_failed = True
            enhanced_tokens = [Token(
                type=TokenType.WORD,
                value=text,
                position=0,
                end_position=len(text)
            )]
            # Add EOF token
            enhanced_tokens.append(Token(
                type=TokenType.EOF,
                value='',
                position=len(text),
                end_position=len(text)
            ))

        # Create validation result with error information
        from .token_stream_validator import TokenStreamValidationResult
        validation_result = TokenStreamValidationResult(
            is_valid=False,
            errors=[error],  # Always include the error that caused the fallback
            warnings=[],
            infos=[],
            validated_tokens=enhanced_tokens
        )

        return LexerParserContract(
            tokens=enhanced_tokens,
            validation_result=validation_result,
            source_text=text,
            stream_quality=TokenStreamQuality.ACCEPTABLE if not base_lexer_failed else TokenStreamQuality.POOR,
            error_recovery_hints=[f"Enhancement failed: {error}"],
            lexer_version="fallback_v2"
        )

    def _generate_recovery_hints(self, errors: List[str]) -> List[str]:
        """Generate recovery hints from validation errors."""
        hints = []
        for error in errors:
            if "unclosed" in error.lower():
                hints.append("Try adding missing closing delimiter")
            elif "unmatched" in error.lower():
                hints.append("Try balancing delimiters")
            elif "quote" in error.lower():
                hints.append("Try fixing quote pairing")
        return hints

    def _update_performance_stats(
        self,
        base_time: float,
        enhance_time: float,
        validation_time: float,
        total_time: float,
        token_count: int
    ):
        """Update performance statistics."""
        self.performance_stats.update({
            'total_time': total_time,
            'base_lexer_time': base_time,
            'enhancement_time': enhance_time,
            'validation_time': validation_time,
            'token_count': token_count,
            'enhancement_overhead': (enhance_time + validation_time) / total_time if total_time > 0 else 0
        })

    # EnhancedLexerInterface implementation
    def get_validation_result(self) -> Optional[TokenStreamValidationResult]:
        """Get the last validation result."""
        return self.last_validation_result

    # Compatibility mode removed - enhanced features are now standard

    def get_enhanced_tokens(self) -> List[Token]:
        """Get enhanced tokens from last tokenization."""
        if self.last_contract:
            return self.last_contract.tokens
        return []

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()

    def get_enhancement_config(self) -> EnhancementConfig:
        """Get current enhancement configuration."""
        return self.enhancement_config


class LexerIntegrationManager:
    """Manages integration between enhanced and base lexer systems."""

    def __init__(self):
        self.enhanced_lexers: Dict[str, EnhancedModularLexer] = {}
        self.performance_data: Dict[str, List[float]] = {}
        self.feature_usage: Dict[str, int] = {}

    def create_enhanced_lexer(
        self,
        lexer_id: str,
        base_lexer: Optional[ModularLexer] = None,
        config: Optional[EnhancementConfig] = None
    ) -> EnhancedModularLexer:
        """Create and register an enhanced lexer."""
        enhanced_lexer = EnhancedModularLexer(base_lexer, config)
        self.enhanced_lexers[lexer_id] = enhanced_lexer
        return enhanced_lexer

    def get_lexer(self, lexer_id: str) -> Optional[EnhancedModularLexer]:
        """Get an enhanced lexer by ID."""
        return self.enhanced_lexers.get(lexer_id)

    def tokenize_with_fallback(
        self,
        text: str,
        lexer_id: str = "default",
        fallback_to_base: bool = True
    ) -> Union[LexerParserContract, List[Token]]:
        """Tokenize with enhanced lexer, fallback to base lexer if needed."""
        enhanced_lexer = self.enhanced_lexers.get(lexer_id)

        if enhanced_lexer:
            try:
                contract = enhanced_lexer.tokenize_with_validation(text)

                # Track feature usage
                self._track_feature_usage(contract)

                # If quality is too poor, fallback to base lexer
                if contract.stream_quality == TokenStreamQuality.UNUSABLE and fallback_to_base:
                    return self._fallback_to_base_lexer(text, enhanced_lexer)

                return contract

            except Exception as e:
                if fallback_to_base:
                    print(f"Enhanced lexer failed: {e}, falling back to base lexer")
                    return self._fallback_to_base_lexer(text, enhanced_lexer)
                raise

        # No enhanced lexer available, use base lexer
        return self._fallback_to_base_lexer(text)

    def _fallback_to_base_lexer(
        self,
        text: str,
        enhanced_lexer: Optional[EnhancedModularLexer] = None
    ) -> List[Token]:
        """Fallback to base lexer tokenization."""
        if enhanced_lexer and enhanced_lexer.base_lexer:
            return enhanced_lexer.base_lexer.tokenize()
        else:
            # Use basic tokenization
            from . import tokenize
            return tokenize(text)

    def _track_feature_usage(self, contract: LexerParserContract):
        """Track usage of enhanced features."""
        if contract.validation_result:
            self.feature_usage['validation'] = self.feature_usage.get('validation', 0) + 1

            if contract.validation_result.errors:
                self.feature_usage['error_detection'] = self.feature_usage.get('error_detection', 0) + 1

            if contract.validation_result.warnings:
                self.feature_usage['warning_detection'] = self.feature_usage.get('warning_detection', 0) + 1

        # Track enhanced token usage
        enhanced_token_count = sum(1 for token in contract.tokens
                                  if hasattr(token, 'metadata') and token.metadata)
        if enhanced_token_count > 0:
            self.feature_usage['enhanced_tokens'] = self.feature_usage.get('enhanced_tokens', 0) + enhanced_token_count

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all lexers."""
        total_stats = {
            'total_tokenizations': 0,
            'average_processing_time': 0.0,
            'enhancement_overhead': 0.0,
            'feature_usage': self.feature_usage.copy()
        }

        if self.enhanced_lexers:
            processing_times = []
            overhead_ratios = []

            for lexer in self.enhanced_lexers.values():
                stats = lexer.get_performance_stats()
                if stats.get('total_time', 0) > 0:
                    processing_times.append(stats['total_time'])
                    overhead_ratios.append(stats.get('enhancement_overhead', 0))

            if processing_times:
                total_stats['total_tokenizations'] = len(processing_times)
                total_stats['average_processing_time'] = sum(processing_times) / len(processing_times)
                total_stats['enhancement_overhead'] = sum(overhead_ratios) / len(overhead_ratios)

        return total_stats


# Global integration manager instance
integration_manager = LexerIntegrationManager()


def create_integrated_lexer(
    input_string: str,
    base_config: Optional[LexerConfig] = None,
    enhancement_config: Optional[EnhancementConfig] = None
) -> EnhancedModularLexer:
    """Convenience function to create integrated enhanced lexer."""
    # Create base lexer
    base_lexer = ModularLexer(input_string, base_config)

    # Create enhanced wrapper
    return EnhancedModularLexer(base_lexer, enhancement_config)


def enhanced_tokenize(
    input_string: str,
    enable_enhancements: bool = True
) -> Union[LexerParserContract, List[Token]]:
    """Enhanced tokenization function (now the only implementation)."""
    if not enable_enhancements:
        # Use base lexer directly
        from . import tokenize
        return tokenize(input_string)

    # Create enhancement config with all features enabled by default
    config = EnhancementConfig(
        enable_validation=True,
        enable_context_tracking=True,
        enable_assignment_detection=True,
        enable_semantic_analysis=True
    )

    # Create a fresh enhanced lexer for each call to ensure proper base lexer setup
    enhanced_lexer = create_integrated_lexer(input_string, enhancement_config=config)

    # Use the enhanced lexer directly
    return enhanced_lexer.tokenize_with_validation(input_string)
