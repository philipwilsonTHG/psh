"""Integrated token stream validation for enhanced lexer."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum

from ..token_types import Token
from ..token_enhanced import LexerError, LexerErrorType
from .expansion_validator import ExpansionValidator, ExpansionValidationResult
from .quote_validator import QuoteValidator, QuoteValidationResult
from .bracket_tracker import BracketTracker, BracketValidationResult


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class TokenStreamValidationResult:
    """Result of token stream validation."""
    is_valid: bool
    errors: List[LexerError]
    warnings: List[LexerError]
    infos: List[LexerError]
    validated_tokens: List[Token]
    
    @property
    def all_issues(self) -> List[LexerError]:
        """Get all validation issues."""
        return self.errors + self.warnings + self.infos
    
    @property
    def has_issues(self) -> bool:
        """Check if there are any validation issues."""
        return len(self.all_issues) > 0


class TokenStreamValidator:
    """Integrates all validation components for token streams."""
    
    def __init__(self):
        self.expansion_validator = ExpansionValidator()
        self.quote_validator = QuoteValidator()
        self.bracket_tracker = BracketTracker()
        
        # Track validation statistics
        self.validation_stats = {
            'tokens_processed': 0,
            'expansions_validated': 0,
            'quotes_validated': 0,
            'brackets_validated': 0,
            'errors_found': 0,
            'warnings_issued': 0
        }
    
    def validate_token_stream(
        self,
        tokens: List[Token],
        source_text: Optional[str] = None
    ) -> TokenStreamValidationResult:
        """Validate a complete token stream."""
        errors = []
        warnings = []
        infos = []
        
        # Reset validation statistics
        self.validation_stats = {key: 0 for key in self.validation_stats}
        self.validation_stats['tokens_processed'] = len(tokens)
        
        # 1. Validate individual token expansions
        expansion_results = self._validate_expansions_in_tokens(tokens)
        errors.extend(expansion_results.errors)
        warnings.extend(expansion_results.warnings)
        
        # 2. Validate quote pairing across tokens
        quote_results = self._validate_quotes_in_stream(tokens, source_text)
        errors.extend(quote_results.errors)
        warnings.extend(quote_results.warnings)
        
        # 3. Validate bracket pairing across tokens
        bracket_results = self._validate_brackets_in_stream(tokens)
        errors.extend(bracket_results.errors)
        warnings.extend(bracket_results.warnings)
        
        # 4. Cross-validate interactions between different validation types
        interaction_issues = self._validate_cross_interactions(
            tokens, expansion_results, quote_results, bracket_results
        )
        errors.extend(interaction_issues['errors'])
        warnings.extend(interaction_issues['warnings'])
        infos.extend(interaction_issues['infos'])
        
        # 5. Validate token sequence coherence
        sequence_issues = self._validate_token_sequence(tokens)
        errors.extend(sequence_issues['errors'])
        warnings.extend(sequence_issues['warnings'])
        infos.extend(sequence_issues['infos'])
        
        # Update statistics
        self.validation_stats['errors_found'] = len(errors)
        self.validation_stats['warnings_issued'] = len(warnings)
        
        # Mark tokens with validation results
        validated_tokens = self._mark_tokens_with_issues(tokens, errors + warnings + infos)
        
        return TokenStreamValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            infos=infos,
            validated_tokens=validated_tokens
        )
    
    def _validate_expansions_in_tokens(self, tokens: List[Token]) -> QuoteValidationResult:
        """Validate expansions within tokens."""
        errors = []
        warnings = []
        
        for token in tokens:
            # Check if token contains expansions
            if self._token_contains_expansions(token):
                # Validate expansions in token value
                expansions = self.expansion_validator.find_all_expansions(token.value)
                
                for position, result in expansions:
                    self.validation_stats['expansions_validated'] += 1
                    
                    if not result.is_valid:
                        # Adjust position to be relative to full text
                        error = LexerError(
                            error_type=result.error_type or LexerErrorType.UNCLOSED_EXPANSION,
                            message=result.error_message or "Invalid expansion",
                            expected=result.expected_close,
                            suggestion=result.suggestion,
                            position=token.position + position
                        )
                        errors.append(error)
                        
                        # Mark token with error
                        if not token.metadata.error_info:
                            token.metadata.error_info = error
        
        return QuoteValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quote_info=[]
        )
    
    def _validate_quotes_in_stream(
        self,
        tokens: List[Token],
        source_text: Optional[str]
    ) -> QuoteValidationResult:
        """Validate quote pairing across the token stream."""
        # First validate individual tokens
        token_result = self.quote_validator.validate_quotes_in_tokens(tokens)
        
        self.validation_stats['quotes_validated'] = len(token_result.quote_info)
        
        # If we have source text, also validate the full text
        if source_text:
            text_result = self.quote_validator.validate_quotes_in_text(source_text)
            
            # Merge results (avoiding duplicates)
            combined_errors = token_result.errors[:]
            combined_warnings = token_result.warnings[:]
            
            # Add text-level errors that aren't covered by token-level validation
            for error in text_result.errors:
                if not self._is_duplicate_quote_error(error, combined_errors):
                    combined_errors.append(error)
            
            return QuoteValidationResult(
                is_valid=len(combined_errors) == 0,
                errors=combined_errors,
                warnings=combined_warnings,
                quote_info=token_result.quote_info + text_result.quote_info
            )
        
        return token_result
    
    def _validate_brackets_in_stream(self, tokens: List[Token]) -> BracketValidationResult:
        """Validate bracket pairing across the token stream."""
        # Process each token through the bracket tracker
        for i, token in enumerate(tokens):
            if self._token_affects_brackets(token):
                self.bracket_tracker.process_token(token, i)
                self.validation_stats['brackets_validated'] += 1
        
        # Finalize bracket validation
        return self.bracket_tracker.finalize(tokens)
    
    def _validate_cross_interactions(
        self,
        tokens: List[Token],
        expansion_results: QuoteValidationResult,
        quote_results: QuoteValidationResult,
        bracket_results: BracketValidationResult
    ) -> Dict[str, List[LexerError]]:
        """Validate interactions between different validation types."""
        errors = []
        warnings = []
        infos = []
        
        # Check for quotes inside unclosed expansions
        for error in expansion_results.errors:
            if error.error_type == LexerErrorType.UNCLOSED_EXPANSION:
                # Look for quote errors in the same region
                for quote_error in quote_results.errors:
                    if self._errors_overlap(error, quote_error):
                        infos.append(LexerError(
                            error_type="expansion_quote_interaction",
                            message="Quote error may be related to unclosed expansion",
                            severity="info",
                            suggestion="Fix the expansion closure first"
                        ))
        
        # Check for brackets inside unclosed quotes
        for quote_error in quote_results.errors:
            if quote_error.error_type == LexerErrorType.UNCLOSED_QUOTE:
                for bracket_error in bracket_results.errors:
                    if self._errors_overlap(quote_error, bracket_error):
                        warnings.append(LexerError(
                            error_type="quote_bracket_interaction",
                            message="Bracket error inside unclosed quote",
                            severity="warning",
                            suggestion="Close the quote before fixing bracket issues"
                        ))
        
        # Check for expansions inside test expressions
        for token in tokens:
            if (hasattr(token.metadata, 'contexts') and 
                'test' in token.metadata.contexts and
                self._token_contains_expansions(token)):
                # Test expressions with expansions might need special handling
                infos.append(LexerError(
                    error_type="expansion_in_test",
                    message="Expansion inside test expression",
                    severity="info",
                    suggestion="Ensure expansion is properly quoted if needed"
                ))
        
        return {
            'errors': errors,
            'warnings': warnings,
            'infos': infos
        }
    
    def _validate_token_sequence(self, tokens: List[Token]) -> Dict[str, List[LexerError]]:
        """Validate the coherence of the token sequence."""
        errors = []
        warnings = []
        infos = []
        
        for i, token in enumerate(tokens):
            # Check for suspicious token sequences
            if i > 0:
                prev_token = tokens[i - 1]
                
                # Check for assignment followed by pipe (usually an error)
                if (hasattr(prev_token, 'assignment_info') and 
                    token.type.name == 'PIPE'):
                    warnings.append(LexerError(
                        error_type="assignment_pipe_sequence",
                        message="Assignment followed by pipe (suspicious)",
                        severity="warning",
                        suggestion="Check if assignment should be in parentheses",
                        position=token.position
                    ))
                
                # Check for double redirections
                if (prev_token.type.name.startswith('REDIRECT') and 
                    token.type.name.startswith('REDIRECT')):
                    warnings.append(LexerError(
                        error_type="double_redirection",
                        message="Consecutive redirections (check syntax)",
                        severity="warning",
                        suggestion="Verify redirection syntax is correct",
                        position=token.position
                    ))
            
            # Check for tokens that should be in specific contexts
            if hasattr(token.metadata, 'semantic_type'):
                if (token.metadata.semantic_type == 'assignment' and
                    not hasattr(token.metadata, 'contexts') or
                    'command_position' not in token.metadata.contexts):
                    infos.append(LexerError(
                        error_type="assignment_context",
                        message="Assignment not in command position",
                        severity="info",
                        suggestion="Assignments are typically at command start",
                        position=token.position
                    ))
        
        return {
            'errors': errors,
            'warnings': warnings,
            'infos': infos
        }
    
    def _mark_tokens_with_issues(
        self,
        tokens: List[Token],
        issues: List[LexerError]
    ) -> List[Token]:
        """Mark tokens that have validation issues."""
        # Create a mapping of positions to issues
        position_issues = {}
        for issue in issues:
            if hasattr(issue, 'position') and issue.position is not None:
                if issue.position not in position_issues:
                    position_issues[issue.position] = []
                position_issues[issue.position].append(issue)
        
        # Mark tokens with issues
        for token in tokens:
            # Check if any issues fall within this token's range
            token_issues = []
            for pos in range(token.position, token.end_position):
                if pos in position_issues:
                    token_issues.extend(position_issues[pos])
            
            if token_issues:
                # Add issues to token metadata
                if not hasattr(token.metadata, 'validation_issues'):
                    token.metadata.validation_issues = []
                token.metadata.validation_issues.extend(token_issues)
                
                # Mark the most severe issue as the primary error
                errors = [issue for issue in token_issues if getattr(issue, 'severity', 'error') == 'error']
                if errors and not token.metadata.error_info:
                    token.metadata.error_info = errors[0]
        
        return tokens
    
    def _token_contains_expansions(self, token: Token) -> bool:
        """Check if a token contains shell expansions."""
        return any(marker in token.value for marker in ['$', '`', '<(', '>(' ])
    
    def _token_affects_brackets(self, token: Token) -> bool:
        """Check if a token affects bracket pairing."""
        bracket_chars = {'(', ')', '[', ']', '{', '}'}
        return any(char in token.value for char in bracket_chars)
    
    def _is_duplicate_quote_error(self, error: LexerError, existing_errors: List[LexerError]) -> bool:
        """Check if a quote error is a duplicate of existing errors."""
        for existing in existing_errors:
            if (existing.error_type == error.error_type and
                getattr(existing, 'position', None) == getattr(error, 'position', None)):
                return True
        return False
    
    def _errors_overlap(self, error1: LexerError, error2: LexerError) -> bool:
        """Check if two errors overlap in position."""
        pos1 = getattr(error1, 'position', None)
        pos2 = getattr(error2, 'position', None)
        
        if pos1 is None or pos2 is None:
            return False
        
        # Consider errors to overlap if they're within 10 characters of each other
        return abs(pos1 - pos2) <= 10
    
    def get_validation_statistics(self) -> Dict[str, int]:
        """Get validation statistics."""
        return self.validation_stats.copy()
    
    def reset_statistics(self):
        """Reset validation statistics."""
        self.validation_stats = {key: 0 for key in self.validation_stats}
    
    def validate_single_token(
        self,
        token: Token,
        position_in_stream: int = 0
    ) -> TokenStreamValidationResult:
        """Validate a single token (useful for incremental validation)."""
        return self.validate_token_stream([token])
    
    def validate_partial_stream(
        self,
        tokens: List[Token],
        start_index: int = 0,
        end_index: Optional[int] = None
    ) -> TokenStreamValidationResult:
        """Validate a portion of a token stream."""
        if end_index is None:
            end_index = len(tokens)
        
        partial_tokens = tokens[start_index:end_index]
        return self.validate_token_stream(partial_tokens)
    
    def suggest_fixes(
        self,
        validation_result: TokenStreamValidationResult
    ) -> List[Tuple[str, str, int]]:
        """Suggest fixes for validation issues."""
        fixes = []
        
        for error in validation_result.errors:
            if error.suggestion:
                position = getattr(error, 'position', 0)
                fixes.append((error.error_type, error.suggestion, position))
        
        # Sort fixes by position for easier application
        return sorted(fixes, key=lambda x: x[2])
    
    def get_error_summary(
        self,
        validation_result: TokenStreamValidationResult
    ) -> Dict[str, int]:
        """Get a summary of error types and counts."""
        summary = {}
        
        for error in validation_result.all_issues:
            error_type = error.error_type
            if error_type in summary:
                summary[error_type] += 1
            else:
                summary[error_type] = 1
        
        return summary