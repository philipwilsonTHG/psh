"""Factory functions for creating parser contexts."""

from typing import Any, Dict, List, Optional

from ....lexer.keyword_normalizer import KeywordNormalizer
from ....token_types import Token
from ...config import ErrorHandlingMode, ParserConfig, ParsingMode
from ..context import ParserContext


def create_context(tokens: List[Token],
                   config: Optional[ParserConfig] = None,
                   source_text: Optional[str] = None,
                   **kwargs) -> ParserContext:
    """Create parser context with configuration.

    Args:
        tokens: List of tokens to parse
        config: Parser configuration (creates default if not provided)
        source_text: Source text for better error messages
        **kwargs: Additional context options

    Returns:
        Configured ParserContext instance
    """
    config = config or ParserConfig()

    normalizer = KeywordNormalizer()
    normalized_tokens = normalizer.normalize(list(tokens))

    ctx = ParserContext(
        tokens=normalized_tokens,
        config=config,
        source_text=source_text,
        trace_enabled=config.trace_parsing,
        **kwargs
    )

    return ctx


def create_strict_posix_context(tokens: List[Token],
                                source_text: Optional[str] = None) -> ParserContext:
    """Create context for strict POSIX parsing."""
    config = ParserConfig.strict_posix()
    return create_context(tokens, config, source_text)


def create_permissive_context(tokens: List[Token],
                              source_text: Optional[str] = None) -> ParserContext:
    """Create context for permissive parsing with error recovery."""
    config = ParserConfig.permissive()
    return create_context(tokens, config, source_text)


def create_repl_context(initial_tokens: List[Token] = None) -> ParserContext:
    """Create context optimized for REPL use.

    REPL contexts are configured for:
    - Error collection instead of throwing
    - Error recovery for continued interaction
    """
    config = ParserConfig(
        parsing_mode=ParsingMode.BASH_COMPAT,
        error_handling=ErrorHandlingMode.COLLECT,
        collect_errors=True,
        enable_error_recovery=True,
        max_errors=20,
        show_error_suggestions=True
    )

    tokens = initial_tokens or []
    return create_context(tokens, config)


def create_shell_parser_context(tokens: List[Token],
                                source_text: Optional[str] = None,
                                shell_options: Optional[Dict[str, Any]] = None) -> ParserContext:
    """Create context based on shell options.

    Args:
        tokens: List of tokens to parse
        source_text: Source text for error messages
        shell_options: Dictionary of shell options (from shell state)

    Returns:
        ParserContext configured based on shell options
    """
    shell_options = shell_options or {}

    # Determine parsing mode based on shell options
    if shell_options.get('posix', False):
        base_config = ParserConfig.strict_posix()
    elif shell_options.get('collect_errors', False):
        base_config = ParserConfig.permissive()
    else:
        base_config = ParserConfig()

    # Override with specific shell options
    config_overrides = {}

    # Error handling options
    if 'collect_errors' in shell_options:
        config_overrides['collect_errors'] = shell_options['collect_errors']

    if 'debug-parser' in shell_options:
        config_overrides['trace_parsing'] = shell_options['debug-parser']

    # Apply overrides
    if config_overrides:
        final_config = base_config.clone(**config_overrides)
    else:
        final_config = base_config

    return create_context(tokens, final_config, source_text)


def create_sub_parser_context(parent_ctx: ParserContext,
                              sub_tokens: List[Token],
                              inherit_state: bool = True) -> ParserContext:
    """Create context for sub-parser (e.g., command substitution).

    Args:
        parent_ctx: Parent parser context
        sub_tokens: Tokens for sub-parser
        inherit_state: Whether to inherit parent state

    Returns:
        ParserContext for sub-parser
    """
    # Create base context with same configuration
    sub_ctx = create_context(
        tokens=sub_tokens,
        config=parent_ctx.config,
        source_text=parent_ctx.source_text
    )

    if inherit_state:
        # Inherit some state from parent
        sub_ctx.nesting_depth = parent_ctx.nesting_depth + 1
        sub_ctx.function_depth = parent_ctx.function_depth
        sub_ctx.loop_depth = parent_ctx.loop_depth
        sub_ctx.in_function_body = parent_ctx.in_function_body

        # Mark as command substitution
        sub_ctx.in_command_substitution = True

    return sub_ctx


def create_validation_context(tokens: List[Token],
                              source_text: Optional[str] = None) -> ParserContext:
    """Create context optimized for validation without execution."""
    config = ParserConfig(
        parsing_mode=ParsingMode.PERMISSIVE,
        error_handling=ErrorHandlingMode.COLLECT,
        collect_errors=True,
        enable_error_recovery=True,
        max_errors=100,
        enable_validation=True
    )

    return create_context(tokens, config, source_text)


def create_performance_test_context(tokens: List[Token],
                                    source_text: Optional[str] = None) -> ParserContext:
    """Create context for performance testing."""
    config = ParserConfig(
        parsing_mode=ParsingMode.BASH_COMPAT,
        error_handling=ErrorHandlingMode.STRICT,
        profile_parsing=True,
        trace_parsing=False,
        show_error_suggestions=False,
    )

    return create_context(tokens, config, source_text)
