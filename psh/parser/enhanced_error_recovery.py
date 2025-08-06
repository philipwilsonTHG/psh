"""Enhanced error recovery using lexer validation results."""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ..token_types import Token, TokenType
from ..token_enhanced import LexerError, TokenContext
from .enhanced_base import EnhancedContextBaseParser
from .recursive_descent.helpers import ParseError


class RecoveryStrategy(Enum):
    """Different error recovery strategies."""
    LEXER_GUIDED = "lexer_guided"
    CONTEXT_BASED = "context_based"
    SEMANTIC_BASED = "semantic_based"
    PATTERN_MATCHING = "pattern_matching"
    FALLBACK = "fallback"


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""
    success: bool
    strategy_used: RecoveryStrategy
    recovered_ast: Optional[Any] = None
    recovery_message: Optional[str] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class ErrorPattern:
    """Pattern for matching and recovering from specific errors."""
    name: str
    error_indicators: List[str]
    lexer_error_types: List[str]
    token_patterns: List[TokenType]
    recovery_action: str
    suggestion_template: str


class EnhancedErrorRecovery:
    """Enhanced error recovery using lexer validation results."""
    
    def __init__(self, parser: EnhancedContextBaseParser):
        self.parser = parser
        self.lexer_errors = getattr(parser, 'lexer_errors', [])
        self.lexer_warnings = getattr(parser, 'lexer_warnings', [])
        
        # Recovery strategies in order of preference
        self.recovery_strategies = [
            self._recover_from_lexer_errors,
            self._recover_using_token_contexts,
            self._recover_using_semantic_types,
            self._recover_using_common_patterns,
            self._fallback_recovery
        ]
        
        # Common error patterns
        self.error_patterns = self._initialize_error_patterns()
    
    def attempt_recovery(self, parse_error: ParseError) -> RecoveryResult:
        """Attempt to recover from parse error using enhanced information."""
        # Try each recovery strategy
        for strategy in self.recovery_strategies:
            try:
                result = strategy(parse_error)
                if result and result.success:
                    return result
            except Exception as recovery_error:
                # Recovery strategy failed, try next one
                continue
        
        # All strategies failed
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.FALLBACK,
            recovery_message="Could not recover from error",
            suggestions=["Check syntax near error position"]
        )
    
    def _recover_from_lexer_errors(self, parse_error: ParseError) -> Optional[RecoveryResult]:
        """Try to recover using lexer error information."""
        if not self.lexer_errors:
            return None
        
        # Find lexer errors near the parse error position
        error_position = getattr(parse_error, 'position', 0)
        nearby_errors = [
            error for error in self.lexer_errors
            if hasattr(error, 'position') and abs(error.position - error_position) <= 10
        ]
        
        if not nearby_errors:
            return None
        
        # Try to recover based on specific lexer error types
        for lexer_error in nearby_errors:
            if lexer_error.error_type == 'UNCLOSED_QUOTE':
                return self._recover_unclosed_quote(lexer_error, parse_error)
            elif lexer_error.error_type == 'UNCLOSED_EXPANSION':
                return self._recover_unclosed_expansion(lexer_error, parse_error)
            elif lexer_error.error_type == 'UNMATCHED_BRACKET':
                return self._recover_unmatched_bracket(lexer_error, parse_error)
            elif lexer_error.error_type == 'INVALID_ASSIGNMENT':
                return self._recover_invalid_assignment(lexer_error, parse_error)
        
        return None
    
    def _recover_unclosed_quote(self, lexer_error: LexerError, parse_error: ParseError) -> RecoveryResult:
        """Recover from unclosed quote error."""
        quote_type = getattr(lexer_error, 'expected', "'")
        
        # Suggest adding the missing quote
        suggestions = [
            f"Add closing {quote_type} quote",
            f"Check for escaped quotes in string",
            "Verify quote pairing throughout the command"
        ]
        
        # Try to continue parsing with a synthetic quote token
        recovery_message = f"Added synthetic closing {quote_type} quote"
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.LEXER_GUIDED,
            recovery_message=recovery_message,
            suggestions=suggestions
        )
    
    def _recover_unclosed_expansion(self, lexer_error: LexerError, parse_error: ParseError) -> RecoveryResult:
        """Recover from unclosed expansion error."""
        expected_close = getattr(lexer_error, 'expected', '}')
        
        suggestions = [
            f"Add closing {expected_close}",
            "Check parameter expansion syntax",
            "Verify nested expansions are properly closed"
        ]
        
        recovery_message = f"Added synthetic closing {expected_close}"
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.LEXER_GUIDED,
            recovery_message=recovery_message,
            suggestions=suggestions
        )
    
    def _recover_unmatched_bracket(self, lexer_error: LexerError, parse_error: ParseError) -> RecoveryResult:
        """Recover from unmatched bracket error."""
        expected_bracket = getattr(lexer_error, 'expected', ')')
        
        suggestions = [
            f"Add matching {expected_bracket}",
            "Check bracket pairing in subshells or functions",
            "Verify arithmetic expression brackets"
        ]
        
        recovery_message = f"Added synthetic {expected_bracket}"
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.LEXER_GUIDED,
            recovery_message=recovery_message,
            suggestions=suggestions
        )
    
    def _recover_invalid_assignment(self, lexer_error: LexerError, parse_error: ParseError) -> RecoveryResult:
        """Recover from invalid assignment error."""
        suggestions = [
            "Use VAR=value format for assignments",
            "Check for spaces around = in assignments",
            "Verify variable name is valid identifier"
        ]
        
        recovery_message = "Treated as regular word instead of assignment"
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.LEXER_GUIDED,
            recovery_message=recovery_message,
            suggestions=suggestions
        )
    
    def _recover_using_token_contexts(self, parse_error: ParseError) -> Optional[RecoveryResult]:
        """Use token context information for recovery."""
        current_token = self._get_current_enhanced_token()
        if not current_token or not hasattr(current_token, 'metadata'):
            return None
        
        contexts = current_token.metadata.contexts
        
        # Recovery based on context mismatches
        if TokenContext.TEST_EXPRESSION in contexts:
            return self._recover_in_test_context(current_token, parse_error)
        elif TokenContext.ARITHMETIC_EXPRESSION in contexts:
            return self._recover_in_arithmetic_context(current_token, parse_error)
        elif TokenContext.COMMAND_POSITION in contexts:
            return self._recover_in_command_context(current_token, parse_error)
        
        return None
    
    def _recover_in_test_context(self, token: Token, parse_error: ParseError) -> RecoveryResult:
        """Recover error in test expression context."""
        suggestions = [
            "Check test expression syntax [[ ... ]]",
            "Verify comparison operators (-eq, -ne, -lt, etc.)",
            "Ensure proper spacing around operators"
        ]
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.CONTEXT_BASED,
            recovery_message="Recovered in test expression context",
            suggestions=suggestions
        )
    
    def _recover_in_arithmetic_context(self, token: Token, parse_error: ParseError) -> RecoveryResult:
        """Recover error in arithmetic expression context."""
        suggestions = [
            "Check arithmetic expression syntax $(( ... ))",
            "Verify numeric values and operators",
            "Ensure variables are properly referenced"
        ]
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.CONTEXT_BASED,
            recovery_message="Recovered in arithmetic context",
            suggestions=suggestions
        )
    
    def _recover_in_command_context(self, token: Token, parse_error: ParseError) -> RecoveryResult:
        """Recover error in command context."""
        suggestions = [
            "Check command name spelling",
            "Verify command is in PATH",
            "Check argument syntax and quoting"
        ]
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.CONTEXT_BASED,
            recovery_message="Recovered in command context",
            suggestions=suggestions
        )
    
    def _recover_using_semantic_types(self, parse_error: ParseError) -> Optional[RecoveryResult]:
        """Use semantic type information for recovery."""
        current_token = self._get_current_enhanced_token()
        if not current_token or not hasattr(current_token.metadata, 'semantic_type'):
            return None
        
        semantic_type = current_token.metadata.semantic_type
        
        if semantic_type:
            suggestions = [
                f"Token '{current_token.value}' is {semantic_type.value}",
                "Check usage context for this token type",
                "Verify syntax for this semantic element"
            ]
            
            return RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.SEMANTIC_BASED,
                recovery_message=f"Recovered using semantic type: {semantic_type.value}",
                suggestions=suggestions
            )
        
        return None
    
    def _recover_using_common_patterns(self, parse_error: ParseError) -> Optional[RecoveryResult]:
        """Use common error patterns for recovery."""
        error_message = str(parse_error)
        
        for pattern in self.error_patterns:
            if self._matches_error_pattern(error_message, pattern):
                return self._apply_pattern_recovery(pattern, parse_error)
        
        return None
    
    def _matches_error_pattern(self, error_message: str, pattern: ErrorPattern) -> bool:
        """Check if error matches a known pattern."""
        # Check error message indicators
        for indicator in pattern.error_indicators:
            if indicator.lower() in error_message.lower():
                return True
        
        # Check lexer error types
        for lexer_error in self.lexer_errors:
            if lexer_error.error_type in pattern.lexer_error_types:
                return True
        
        return False
    
    def _apply_pattern_recovery(self, pattern: ErrorPattern, parse_error: ParseError) -> RecoveryResult:
        """Apply recovery action for matched pattern."""
        suggestions = [pattern.suggestion_template]
        
        # Add specific suggestions based on pattern
        if pattern.name == "missing_semicolon":
            suggestions.extend([
                "Add semicolon between commands",
                "Use newline to separate commands"
            ])
        elif pattern.name == "unclosed_subshell":
            suggestions.extend([
                "Add closing parenthesis )",
                "Check nested subshell syntax"
            ])
        
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.PATTERN_MATCHING,
            recovery_message=f"Applied {pattern.name} recovery",
            suggestions=suggestions
        )
    
    def _fallback_recovery(self, parse_error: ParseError) -> RecoveryResult:
        """Fallback recovery strategy."""
        # Provide generic suggestions
        suggestions = [
            "Check syntax near error position",
            "Verify command and argument structure",
            "Look for missing quotes, brackets, or operators",
            "Check for typos in command names"
        ]
        
        # Add lexer-specific suggestions if available
        if self.lexer_errors:
            suggestions.append("Review lexer warnings for additional context")
        
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.FALLBACK,
            recovery_message="Using fallback recovery",
            suggestions=suggestions
        )
    
    def _get_current_enhanced_token(self) -> Optional[Token]:
        """Get current token as enhanced token."""
        if hasattr(self.parser, 'peek_enhanced'):
            return self.parser.peek_enhanced()
        
        # Fallback
        token = self.parser.peek() if hasattr(self.parser, 'peek') else None
        if token and not isinstance(token, Token):
            return Token.from_token(token)
        return token
    
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize common error patterns."""
        return [
            ErrorPattern(
                name="missing_semicolon",
                error_indicators=["unexpected token", "expected semicolon"],
                lexer_error_types=[],
                token_patterns=[],
                recovery_action="insert_semicolon",
                suggestion_template="Add semicolon or newline between commands"
            ),
            ErrorPattern(
                name="unclosed_subshell",
                error_indicators=["expected ')'", "unclosed"],
                lexer_error_types=["UNMATCHED_BRACKET"],
                token_patterns=[TokenType.LPAREN],
                recovery_action="insert_closing_paren",
                suggestion_template="Add closing parenthesis"
            ),
            ErrorPattern(
                name="missing_then",
                error_indicators=["expected 'then'"],
                lexer_error_types=[],
                token_patterns=[TokenType.IF],
                recovery_action="insert_then",
                suggestion_template="Add 'then' after if condition"
            ),
            ErrorPattern(
                name="missing_do",
                error_indicators=["expected 'do'"],
                lexer_error_types=[],
                token_patterns=[TokenType.WHILE, TokenType.FOR],
                recovery_action="insert_do",
                suggestion_template="Add 'do' after loop condition"
            ),
            ErrorPattern(
                name="invalid_redirection",
                error_indicators=["invalid redirection"],
                lexer_error_types=["INVALID_REDIRECT"],
                token_patterns=[],
                recovery_action="fix_redirection",
                suggestion_template="Check redirection syntax"
            )
        ]


class ErrorRecoveryManager:
    """Manager for coordinating error recovery across parser components."""
    
    def __init__(self, parser: EnhancedContextBaseParser):
        self.parser = parser
        self.recovery_engine = EnhancedErrorRecovery(parser)
        self.recovery_history: List[RecoveryResult] = []
    
    def handle_parse_error(self, error: ParseError) -> RecoveryResult:
        """Handle a parse error with recovery attempt."""
        # Attempt recovery
        result = self.recovery_engine.attempt_recovery(error)
        
        # Record recovery attempt
        self.recovery_history.append(result)
        
        # Log recovery result
        if hasattr(self.parser.ctx, 'add_warning'):
            if result.success:
                self.parser.ctx.add_warning(
                    f"Recovered from error: {result.recovery_message}"
                )
                for suggestion in result.suggestions:
                    self.parser.ctx.add_warning(f"Suggestion: {suggestion}")
            else:
                self.parser.ctx.add_warning(
                    f"Could not recover from error: {error}"
                )
        
        return result
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get statistics about recovery attempts."""
        total_attempts = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r.success)
        
        strategy_usage = {}
        for result in self.recovery_history:
            strategy = result.strategy_used.value
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
        
        return {
            'total_attempts': total_attempts,
            'successful_recoveries': successful_recoveries,
            'success_rate': successful_recoveries / total_attempts if total_attempts > 0 else 0,
            'strategy_usage': strategy_usage,
            'recent_recoveries': self.recovery_history[-5:] if self.recovery_history else []
        }


def install_enhanced_error_recovery(parser: EnhancedContextBaseParser):
    """Install enhanced error recovery into parser."""
    if not hasattr(parser, 'error_recovery_manager'):
        parser.error_recovery_manager = ErrorRecoveryManager(parser)
        
        # Override error handling methods if they exist
        if hasattr(parser, '_error'):
            original_error = parser._error
            
            def enhanced_error(message: str, **kwargs):
                """Enhanced error method with recovery."""
                parse_error = ParseError(message, **kwargs)
                
                # Attempt recovery
                recovery_result = parser.error_recovery_manager.handle_parse_error(parse_error)
                
                if recovery_result.success:
                    # Recovery succeeded, continue parsing
                    return recovery_result.recovered_ast
                else:
                    # Recovery failed, raise original error
                    return original_error(message, **kwargs)
            
            parser._error_with_recovery = enhanced_error