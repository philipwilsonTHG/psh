"""Factory for creating enhanced parsers with different configurations."""

from typing import List, Optional, Union

from ....lexer.parser_contract import LexerParserContract
from ....lexer.token_stream_validator import TokenStreamValidationResult
from ....token_types import Token
from ...config import ParserConfig
from ..context import ParserContext
from .base import EnhancedContextBaseParser, EnhancedParserConfig


class EnhancedParserFactory:
    """Factory for creating enhanced parsers."""

    @staticmethod
    def create_from_lexer_contract(
        contract_or_tokens: Union[LexerParserContract, List[Token]],
        config: Optional[EnhancedParserConfig] = None
    ) -> EnhancedContextBaseParser:
        """Create enhanced parser from lexer contract or token list."""
        from .base import create_enhanced_parser

        enhanced_config = config or EnhancedParserConfig()

        # Use the base create_enhanced_parser which handles both cases
        return create_enhanced_parser(contract_or_tokens, enhanced_config)

    @staticmethod
    def create_compatible_parser(
        tokens: List[Token],
        config: Optional[ParserConfig] = None,
        enhanced_features: bool = True
    ) -> Union['Parser', EnhancedContextBaseParser]:
        """Create parser with optional enhancement."""
        if enhanced_features and all(isinstance(t, Token) for t in tokens):
            # Use enhanced parser
            enhanced_config = EnhancedParserConfig.from_parser_config(config)
            ctx = ParserContextFactory.create_enhanced(tokens, enhanced_config)
            return EnhancedContextBaseParser(ctx, enhanced_config)
        else:
            # Use standard parser
            from ..parser import Parser
            return Parser(tokens, config)

    @staticmethod
    def migrate_existing_parser(
        parser: 'Parser',
        enable_enhancements: bool = True
    ) -> Union['Parser', EnhancedContextBaseParser]:
        """Migrate existing parser to enhanced version."""
        if not enable_enhancements:
            return parser

        # Convert tokens to enhanced tokens if needed
        enhanced_tokens = []
        for token in parser.tokens if hasattr(parser, 'tokens') else []:
            if isinstance(token, Token):
                enhanced_tokens.append(token)
            else:
                enhanced_tokens.append(Token.from_token(token))

        # Create enhanced parser
        enhanced_config = EnhancedParserConfig()
        ctx = ParserContextFactory.create_enhanced(enhanced_tokens, enhanced_config)
        return EnhancedContextBaseParser(ctx, enhanced_config)


class ParserContextFactory:
    """Factory for creating enhanced parser contexts."""

    @staticmethod
    def create_enhanced(
        tokens: List[Token],
        config: EnhancedParserConfig,
        lexer_validation: Optional[TokenStreamValidationResult] = None
    ) -> ParserContext:
        """Create enhanced parser context."""
        from ..support.context_factory import ParserContextFactory as BaseFactory

        # Create base context
        base_config = ParserConfig()
        base_config.__dict__.update({k: v for k, v in config.__dict__.items()
                                   if hasattr(base_config, k)})

        ctx = BaseFactory.create(tokens, base_config)

        # Add enhanced features
        ctx.enhanced_config = config
        ctx.lexer_validation = lexer_validation

        # Add enhanced error handling
        if lexer_validation:
            for error in lexer_validation.errors:
                if hasattr(ctx, 'add_lexer_error'):
                    ctx.add_lexer_error(error)
            for warning in lexer_validation.warnings:
                if hasattr(ctx, 'add_warning'):
                    ctx.add_warning(warning)

        # Add enhanced token utilities
        ctx.peek_enhanced = lambda offset=0: ctx.peek(offset) if isinstance(ctx.peek(offset), Token) else None
        ctx.current_enhanced = lambda: ctx.peek_enhanced(0)

        return ctx


class FullyEnhancedParser(EnhancedContextBaseParser):
    """Parser with all enhanced features enabled."""

    def __init__(self, ctx: ParserContext, enhanced_config: EnhancedParserConfig):
        # Force all enhanced features on
        enhanced_config.use_enhanced_tokens = True
        enhanced_config.enable_context_validation = True
        enhanced_config.enable_semantic_validation = True
        enhanced_config.enable_semantic_analysis = True
        enhanced_config.strict_contract_validation = True
        enhanced_config.full_enhancement = True

        super().__init__(ctx, enhanced_config)

        # Initialize all enhancement components
        from .commands import EnhancedSimpleCommandParser, EnhancedTestParser
        self.command_parser = EnhancedSimpleCommandParser(ctx, enhanced_config)
        self.test_parser = EnhancedTestParser(ctx, enhanced_config)

    def parse_simple_command_enhanced(self):
        """Parse simple command using enhanced features."""
        return self.command_parser.parse_simple_command()

    def parse_test_expression_enhanced(self):
        """Parse test expression using enhanced features."""
        return self.test_parser.parse_test_expression()

    def parse_with_full_analysis(self):
        """Parse with complete semantic analysis."""
        # Perform pre-parse analysis
        if self.semantic_analyzer:
            enhanced_tokens = [t for t in self.ctx.tokens if isinstance(t, Token)]

            # Variable usage analysis
            variable_issues = self.semantic_analyzer.analyze_variable_usage(enhanced_tokens)
            for issue in variable_issues:
                if hasattr(self.ctx, 'add_warning'):
                    self.ctx.add_warning(f"Semantic: {issue.message}")

        # Perform context validation
        if self.context_validator:
            enhanced_tokens = [t for t in self.ctx.tokens if isinstance(t, Token)]

            # Command sequence validation
            command_issues = self.context_validator.validate_command_sequence(enhanced_tokens)
            for issue in command_issues:
                if hasattr(self.ctx, 'add_warning'):
                    self.ctx.add_warning(f"Context: {issue.message}")

            # Assignment context validation
            for token in enhanced_tokens:
                if token.is_assignment:
                    assignment_issue = self.context_validator.validate_assignment_context(token)
                    if assignment_issue and hasattr(self.ctx, 'add_warning'):
                        self.ctx.add_warning(f"Assignment: {assignment_issue.message}")

        # Perform standard parsing
        return self.parse()


class EnhancedParserConfigBuilder:
    """Builder for creating enhanced parser configurations."""

    def __init__(self):
        self.config = EnhancedParserConfig()

    def with_enhanced_tokens(self, enabled: bool = True) -> 'EnhancedParserConfigBuilder':
        """Enable enhanced token support."""
        self.config.use_enhanced_tokens = enabled
        return self

    def with_context_validation(self, enabled: bool = True) -> 'EnhancedParserConfigBuilder':
        """Enable context validation."""
        self.config.enable_context_validation = enabled
        return self

    def with_semantic_validation(self, enabled: bool = True) -> 'EnhancedParserConfigBuilder':
        """Enable semantic validation."""
        self.config.enable_semantic_validation = enabled
        return self

    def with_semantic_analysis(self, enabled: bool = True) -> 'EnhancedParserConfigBuilder':
        """Enable semantic analysis."""
        self.config.enable_semantic_analysis = enabled
        return self

    def with_strict_validation(self, enabled: bool = True) -> 'EnhancedParserConfigBuilder':
        """Enable strict contract validation."""
        self.config.strict_contract_validation = enabled
        return self

    def with_full_enhancement(self, enabled: bool = True) -> 'EnhancedParserConfigBuilder':
        """Enable all enhanced features."""
        if enabled:
            self.config.use_enhanced_tokens = True
            self.config.enable_context_validation = True
            self.config.enable_semantic_validation = True
            self.config.enable_semantic_analysis = True
            self.config.strict_contract_validation = True
            self.config.full_enhancement = True
        else:
            self.config.full_enhancement = False
        return self

    def for_development(self) -> 'EnhancedParserConfigBuilder':
        """Configure for development use (all features enabled)."""
        return self.with_full_enhancement(True)

    def for_production(self) -> 'EnhancedParserConfigBuilder':
        """Configure for production use (conservative features)."""
        self.config.use_enhanced_tokens = True
        self.config.enable_context_validation = False
        self.config.enable_semantic_validation = False
        self.config.enable_semantic_analysis = False
        self.config.strict_contract_validation = False
        self.config.full_enhancement = False
        return self

    def for_compatibility(self) -> 'EnhancedParserConfigBuilder':
        """Configure for maximum compatibility."""
        self.config.use_enhanced_tokens = False
        self.config.enable_context_validation = False
        self.config.enable_semantic_validation = False
        self.config.enable_semantic_analysis = False
        self.config.strict_contract_validation = False
        self.config.full_enhancement = False
        return self

    def build(self) -> EnhancedParserConfig:
        """Build the configuration."""
        return self.config


# Convenience functions for common configurations
def create_development_parser(tokens_or_contract) -> EnhancedContextBaseParser:
    """Create parser with all enhanced features for development."""
    config = EnhancedParserConfigBuilder().for_development().build()
    return EnhancedParserFactory.create_from_lexer_contract(tokens_or_contract, config)


def create_production_parser(tokens_or_contract) -> EnhancedContextBaseParser:
    """Create parser optimized for production use."""
    config = EnhancedParserConfigBuilder().for_production().build()
    return EnhancedParserFactory.create_from_lexer_contract(tokens_or_contract, config)


def create_compatible_parser(tokens_or_contract) -> EnhancedContextBaseParser:
    """Create parser with maximum compatibility."""
    config = EnhancedParserConfigBuilder().for_compatibility().build()
    return EnhancedParserFactory.create_from_lexer_contract(tokens_or_contract, config)
