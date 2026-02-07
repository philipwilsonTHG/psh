"""Enhanced parser base classes with full metadata utilization."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from ....lexer.parser_contract import LexerParserContract, extract_legacy_tokens
from ....token_enhanced import LexerError, SemanticType, TokenContext
from ....token_types import Token, TokenType
from ...config import ParserConfig
from ..base_context import ContextBaseParser
from ..context import ParserContext


@dataclass
class ValidationIssue:
    """Represents a validation issue found during parsing."""
    type: str
    message: str
    suggestion: str
    position: int


@dataclass
class SemanticIssue:
    """Represents a semantic analysis issue."""
    type: str
    message: str
    suggestion: str
    position: int


@dataclass
class EnhancedParserConfig(ParserConfig):
    """Parser configuration with enhanced lexer support."""
    use_enhanced_tokens: bool = True
    enable_context_validation: bool = False
    enable_semantic_validation: bool = False
    enable_semantic_analysis: bool = False
    strict_contract_validation: bool = False
    full_enhancement: bool = False

    @classmethod
    def from_parser_config(cls, config: Optional[ParserConfig]) -> 'EnhancedParserConfig':
        """Create enhanced config from base parser config."""
        if config is None:
            return cls()

        enhanced = cls()
        # Copy base config attributes
        for attr in ['debug', 'error_handling', 'strict']:
            if hasattr(config, attr):
                setattr(enhanced, attr, getattr(config, attr))

        return enhanced


class ContextValidator:
    """Validates token contexts during parsing."""

    def validate_command_sequence(self, tokens: List[Token]) -> List[ValidationIssue]:
        """Validate command sequence contexts."""
        issues = []

        for i, token in enumerate(tokens):
            # Check command position tokens
            if TokenContext.COMMAND_POSITION in token.metadata.contexts:
                # Should be a command, builtin, or function
                if not (token.is_keyword or token.metadata.semantic_type in
                       {SemanticType.BUILTIN, SemanticType.KEYWORD}):
                    # Check if it's a known command
                    if not self._is_known_command(token.value):
                        issues.append(ValidationIssue(
                            type="unknown_command",
                            message=f"Unknown command: {token.value}",
                            suggestion="Check spelling or add to PATH",
                            position=token.position
                        ))

        return issues

    def validate_assignment_context(self, token: Token) -> Optional[ValidationIssue]:
        """Validate assignment in proper context."""
        if token.is_assignment:
            # Assignments should be in command position or after export/declare/local
            if TokenContext.COMMAND_POSITION not in token.metadata.contexts:
                return ValidationIssue(
                    type="assignment_position",
                    message="Assignment not in command position",
                    suggestion="Move assignment to beginning of command or use export/declare",
                    position=token.position
                )
        return None

    def _is_known_command(self, command: str) -> bool:
        """Check if command is known builtin or in PATH."""
        # Simple check - in real implementation would check PATH
        common_commands = {'echo', 'cat', 'ls', 'grep', 'sed', 'awk', 'sort', 'head', 'tail'}
        return command in common_commands


class SemanticAnalyzer:
    """Analyzes semantic meaning of enhanced tokens."""

    def analyze_variable_usage(self, tokens: List[Token]) -> List[SemanticIssue]:
        """Analyze variable assignments and usage."""
        issues = []
        assigned_vars = set()

        for token in tokens:
            # Track assignments
            if token.is_assignment and hasattr(token, 'assignment_info'):
                var_name = token.assignment_info.get('variable')
                if var_name:
                    assigned_vars.add(var_name)

            # Check variable expansions
            elif token.type in {TokenType.VARIABLE, TokenType.ARITH_EXPANSION}:
                # Extract variable name from $VAR or ${VAR}
                var_name = self._extract_variable_name(token.value)
                if var_name and var_name not in assigned_vars:
                    # Check if it's a special variable or environment variable
                    if not self._is_special_or_env_variable(var_name):
                        issues.append(SemanticIssue(
                            type="undefined_variable",
                            message=f"Variable '{var_name}' used before assignment",
                            suggestion=f"Initialize {var_name} before use or check spelling",
                            position=token.position
                        ))

        return issues

    def analyze_command_structure(self, ast_node, tokens: List[Token]) -> List[SemanticIssue]:
        """Analyze command structure using both AST and enhanced tokens."""
        issues = []

        # Find potential issues with command structure
        # e.g., redirections in wrong places, pipe to commands that don't read stdin

        return issues

    def _extract_variable_name(self, value: str) -> Optional[str]:
        """Extract variable name from expansion."""
        if value.startswith('${') and value.endswith('}'):
            return value[2:-1].split(':')[0].split('=')[0]  # Handle ${VAR:=default}
        elif value.startswith('$'):
            return value[1:]
        return None

    def _is_special_or_env_variable(self, var_name: str) -> bool:
        """Check if variable is special or likely environment variable."""
        special_vars = {'$', '?', '#', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                       'HOME', 'PATH', 'PWD', 'USER', 'SHELL', 'TERM', 'LANG'}
        return var_name in special_vars or var_name.isupper()


class EnhancedContextBaseParser(ContextBaseParser):
    """Enhanced base parser that fully utilizes enhanced tokens."""

    def __init__(
        self,
        ctx: ParserContext,
        enhanced_config: Optional[EnhancedParserConfig] = None
    ):
        super().__init__(ctx)
        self.enhanced_config = enhanced_config or EnhancedParserConfig()
        # Contract adapter removed - enhanced features are now standard

        # Enhanced parsing features
        self.context_validator = ContextValidator() if enhanced_config.enable_context_validation else None
        self.semantic_analyzer = SemanticAnalyzer() if enhanced_config.enable_semantic_analysis else None

        # Error context from lexer
        self.lexer_errors: List[LexerError] = []
        self.lexer_warnings: List[LexerError] = []

    def setup_from_lexer_output(
        self,
        lexer_output: Union[LexerParserContract, List[Token]]
    ):
        """Set up parser from various input types."""
        if isinstance(lexer_output, LexerParserContract):
            # Enhanced lexer contract
            self._setup_from_contract(lexer_output)
        elif isinstance(lexer_output, list):
            # Legacy token list
            self._setup_from_token_list(lexer_output)
        else:
            raise ValueError(f"Unsupported lexer output type: {type(lexer_output)}")

    def _setup_from_contract(self, contract: LexerParserContract):
        """Set up from enhanced lexer contract."""
        # Extract tokens based on parser configuration
        if self.enhanced_config.use_enhanced_tokens and contract.should_attempt_parsing():
            # Use enhanced tokens directly
            tokens = contract.tokens
            self.lexer_errors = contract.validation_result.errors if contract.validation_result else []
            self.lexer_warnings = contract.validation_result.warnings if contract.validation_result else []
        else:
            # Extract legacy-compatible tokens
            tokens = extract_legacy_tokens(contract)

            # Still collect errors for reporting
            if contract.validation_result:
                self.lexer_errors = contract.validation_result.errors
                self.lexer_warnings = contract.validation_result.warnings

        # Update parser context
        self.ctx.tokens = tokens
        self.ctx.current = 0

        # Add lexer issues to parser context if supported
        if hasattr(self.ctx, 'add_lexer_error'):
            for error in self.lexer_errors:
                self.ctx.add_lexer_error(error)

        if hasattr(self.ctx, 'add_warning'):
            for warning in self.lexer_warnings:
                self.ctx.add_warning(warning)


    def _setup_from_token_list(self, tokens: List[Token]):
        """Set up from token list (enhanced tokens are now standard)."""
        # Convert basic tokens to enhanced tokens
        enhanced_tokens = []
        for token in tokens:
            if isinstance(token, Token):
                enhanced_tokens.append(token)
            else:
                # Create enhanced token from basic token
                enhanced = Token.from_token(token)
                enhanced_tokens.append(enhanced)

        self.ctx.tokens = enhanced_tokens
        self.ctx.current = 0

    def _convert_to_basic_tokens(self, enhanced_tokens: List[Token]) -> List[Token]:
        """Convert enhanced tokens to basic tokens for legacy compatibility."""
        basic_tokens = []
        for enhanced in enhanced_tokens:
            basic = Token(
                type=enhanced.type,
                value=enhanced.value,
                position=enhanced.position,
                end_position=enhanced.end_position,
                quote_type=enhanced.quote_type,
                line=enhanced.line,
                column=enhanced.column
            )
            # Copy parts if they exist
            if hasattr(enhanced, 'parts'):
                basic.parts = enhanced.parts
            basic_tokens.append(basic)
        return basic_tokens

    def peek_enhanced(self, offset: int = 0) -> Optional[Token]:
        """Peek at current token as enhanced token."""
        token = self.ctx.peek(offset)

        if token is None:
            return None

        if isinstance(token, Token):
            return token

        # Convert basic token to enhanced for compatibility
        enhanced = Token.from_token(token)
        return enhanced

    def expect_assignment(self, message: Optional[str] = None) -> Token:
        """Expect an assignment token with metadata."""
        token = self.peek_enhanced()

        if not token or not token.is_assignment:
            raise self._error(message or f"Expected assignment, found {token.type if token else 'EOF'}")

        # Extract assignment metadata
        if hasattr(token, 'assignment_info'):
            if hasattr(self.ctx, 'current_assignment'):
                self.ctx.current_assignment = token.assignment_info

        return self.advance()

    def expect_in_context(
        self,
        token_type: TokenType,
        expected_context: TokenContext,
        message: Optional[str] = None
    ) -> Token:
        """Expect token in specific context with validation."""
        token = self.peek_enhanced()

        if not token or token.type != token_type:
            raise self._error(message or f"Expected {token_type}, found {token.type if token else 'EOF'}")

        if self.enhanced_config.enable_context_validation:
            if expected_context not in token.metadata.contexts:
                contexts_str = ', '.join(c.value for c in token.metadata.contexts)
                raise self._error(f"Expected {token_type} in {expected_context.value} context, "
                                f"found in {contexts_str} context")

        return self.advance()

    def expect_with_context(
        self,
        token_type: TokenType,
        expected_context: str = None,
        message: Optional[str] = None
    ) -> Token:
        """Expect token with optional context validation (backward compatibility)."""
        if not self.enhanced_config.enable_context_validation or not expected_context:
            # Standard expectation without context checking
            return self.ctx.consume(token_type, message)

        token = self.peek_enhanced()

        if token and hasattr(token.metadata, 'contexts'):
            # Check if token has expected context
            contexts = [ctx.value if hasattr(ctx, 'value') else str(ctx)
                       for ctx in token.metadata.contexts]

            if expected_context not in contexts:
                # Token type matches but context is wrong
                actual_contexts = ', '.join(contexts)
                error_msg = (message or
                           f"Expected {token_type} in {expected_context} context, "
                           f"but found it in {actual_contexts} context")
                raise self._error(error_msg)

        return self.ctx.consume(token_type, message)

    def validate_semantic_type(self, token: Token, expected_type: SemanticType) -> bool:
        """Validate token semantic type."""
        if not self.enhanced_config.enable_semantic_validation:
            return True

        return token.metadata.semantic_type == expected_type

    def get_enhanced_error_context(self, error_position: int) -> Dict[str, Any]:
        """Get enhanced error context using token metadata."""
        context = super().get_error_context(error_position) if hasattr(super(), 'get_error_context') else {}

        # Add enhanced context from surrounding tokens
        for i, token in enumerate(self.ctx.tokens):
            if isinstance(token, Token) and abs(token.position - error_position) <= 20:
                context.setdefault('enhanced_tokens', []).append({
                    'value': token.value,
                    'semantic_type': token.metadata.semantic_type.value if token.metadata.semantic_type else None,
                    'contexts': [c.value for c in token.metadata.contexts],
                    'distance': abs(token.position - error_position)
                })

        # Add lexer errors near this position
        nearby_lexer_errors = [
            error for error in self.lexer_errors
            if hasattr(error, 'position') and abs(error.position - error_position) <= 10
        ]
        if nearby_lexer_errors:
            context['related_lexer_errors'] = [
                {'message': error.message, 'suggestion': error.suggestion}
                for error in nearby_lexer_errors
            ]

        return context

    def get_lexer_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostics from lexer phase."""
        return {
            'errors': self.lexer_errors,
            'warnings': self.lexer_warnings,
            'error_count': len(self.lexer_errors),
            'warning_count': len(self.lexer_warnings),
            'has_issues': len(self.lexer_errors) > 0 or len(self.lexer_warnings) > 0
        }

    def parse(self):
        """Parse the tokens using enhanced parsing features (now the standard implementation).
        
        This method provides enhanced parsing that leverages token metadata,
        context validation, and semantic analysis.
        """

        # Use enhanced parsing with modular structure
        if hasattr(self, 'statements') and hasattr(self.statements, 'parse_command_list'):
            # Try enhanced parsing if available
            if hasattr(self.statements, 'parse_command_list_enhanced'):
                return self.statements.parse_command_list_enhanced()
            else:
                return self.statements.parse_command_list()

        # Direct enhanced parsing if no modular structure
        from ..parser import Parser

        # Convert our tokens to basic tokens if needed for fallback
        basic_tokens = self._convert_to_basic_tokens(self.ctx.tokens)

        # Create temporary parser and parse
        temp_parser = Parser(basic_tokens)
        return temp_parser.parse()


def create_enhanced_parser(
    tokens_or_contract: Union[List[Token], LexerParserContract],
    config: Optional[EnhancedParserConfig] = None
) -> EnhancedContextBaseParser:
    """Create an enhanced parser from various input types."""
    from ..support.context_factory import ParserContextFactory

    enhanced_config = config or EnhancedParserConfig()

    # Create base parser context (temporarily with empty tokens)
    base_config = ParserConfig()  # Convert enhanced config to base config
    base_config.__dict__.update({
        k: v for k, v in enhanced_config.__dict__.items()
        if hasattr(base_config, k)
    })

    ctx = ParserContextFactory.create(tokens=[], config=base_config)

    # Create enhanced parser
    parser = EnhancedContextBaseParser(ctx, enhanced_config)

    # Set up from input
    parser.setup_from_lexer_output(tokens_or_contract)

    return parser


def parse_with_enhanced_lexer(
    input_string: str,
    lexer_config: Optional[Any] = None,
    parser_config: Optional[EnhancedParserConfig] = None,
    use_enhanced_features: bool = True  # Now always true, parameter kept for backward compatibility
) -> Any:
    """Parse using enhanced lexer-parser pipeline (now the standard implementation)."""
    # Import here to avoid circular imports
    from ....lexer.enhanced_integration import enhanced_tokenize

    # Get tokens using enhanced lexer (now the only option)
    lexer_result = enhanced_tokenize(input_string, enable_enhancements=True)

    # Create enhanced parser
    parser = create_enhanced_parser(lexer_result, parser_config)

    # Parse
    return parser.parse()


class EnhancedParserFactory:
    """Factory for creating enhanced parsers with different configurations."""

    @staticmethod
    def create_compatible_parser(
        tokens_or_contract: Union[List[Token], LexerParserContract],
        enhanced_features: bool = True  # Now always true, parameter kept for backward compatibility
    ) -> EnhancedContextBaseParser:
        """Create parser with enhanced features (now the default)."""
        # Enhanced features are now always enabled
        config = EnhancedParserConfig(
            use_enhanced_tokens=True,
            enable_context_validation=False,  # Start conservative
            enable_semantic_validation=False,
            strict_contract_validation=False
        )

        return create_enhanced_parser(tokens_or_contract, config)

    @staticmethod
    def create_development_parser(
        tokens_or_contract: Union[List[Token], LexerParserContract]
    ) -> EnhancedContextBaseParser:
        """Create parser with all enhanced features for development."""
        config = EnhancedParserConfig(
            use_enhanced_tokens=True,
            enable_context_validation=True,
            enable_semantic_validation=True,
            enable_semantic_analysis=True,
            strict_contract_validation=True,
            full_enhancement=True
        )

        return create_enhanced_parser(tokens_or_contract, config)

    @staticmethod
    def create_production_parser(
        tokens_or_contract: Union[List[Token], LexerParserContract]
    ) -> EnhancedContextBaseParser:
        """Create parser optimized for production use."""
        config = EnhancedParserConfig(
            use_enhanced_tokens=True,
            enable_context_validation=False,  # Minimal overhead
            enable_semantic_validation=False,
            strict_contract_validation=False
        )

        return create_enhanced_parser(tokens_or_contract, config)
