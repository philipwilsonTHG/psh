"""Factory functions for creating configured parser instances.

This module provides convenient functions for creating Parser instances
with different configurations for various use cases.
"""

from typing import List, Optional

from ....token_types import Token
from ...config import ParserConfig, ParsingMode
from ..parser import Parser


def create_strict_posix_parser(tokens: List[Token],
                               source_text: Optional[str] = None) -> Parser:
    """Create a parser in strict POSIX mode."""
    config = ParserConfig.strict_posix()
    return Parser(tokens, source_text=source_text, config=config)


def create_permissive_parser(tokens: List[Token],
                             source_text: Optional[str] = None) -> Parser:
    """Create a parser in permissive mode."""
    config = ParserConfig.permissive()
    return Parser(tokens, source_text=source_text, config=config)


def create_custom_parser(tokens: List[Token],
                         source_text: Optional[str] = None,
                         base_config: Optional[ParserConfig] = None,
                         **config_overrides) -> Parser:
    """Create a parser with custom configuration.

    Args:
        tokens: List of tokens to parse
        source_text: Optional source text for error reporting
        base_config: Base configuration to start from
        **config_overrides: Configuration values to override

    Returns:
        Configured parser with custom settings
    """
    if base_config:
        config = base_config.clone(**config_overrides)
    else:
        config = ParserConfig(**{k: v for k, v in config_overrides.items()
                                 if k in ParserConfig.__dataclass_fields__})

    return Parser(tokens, source_text=source_text, config=config)


def create_shell_parser(tokens: List[Token],
                        source_text: Optional[str] = None,
                        shell_options: Optional[dict] = None) -> Parser:
    """Create a parser based on shell options.

    Args:
        tokens: List of tokens to parse
        source_text: Optional source text for error reporting
        shell_options: Dictionary of shell options

    Returns:
        Configured parser based on shell options
    """
    if not shell_options:
        shell_options = {}

    # Determine base config from shell options
    if shell_options.get('posix', False):
        config = ParserConfig.strict_posix()
    else:
        config = ParserConfig()

    # Override specific features based on shell options
    config_overrides = {}

    # Error handling options
    if shell_options.get('collect_errors', False):
        config_overrides['collect_errors'] = True

    # Debug options
    if shell_options.get('debug_parser', False):
        config_overrides.update({
            'trace_parsing': True,
            'profile_parsing': True,
            'validate_ast': True
        })

    # Apply overrides if any
    if config_overrides:
        config = config.clone(**config_overrides)

    return Parser(tokens, source_text=source_text, config=config)


def validate_config(config: ParserConfig) -> List[str]:
    """Validate configuration for consistency and return warnings.

    Args:
        config: Configuration to validate

    Returns:
        List of validation warnings
    """
    warnings = []

    # Check for performance concerns
    if config.trace_parsing and not config.profile_parsing:
        warnings.append(
            "Tracing is enabled without profiling - "
            "consider enabling profiling for better debugging"
        )

    # Check error handling consistency
    if (config.enable_error_recovery and
        config.error_handling == 'strict'):
        warnings.append(
            "Error recovery is enabled with strict error handling - "
            "recovery will not be attempted"
        )

    return warnings


def suggest_config(use_case: str) -> ParserConfig:
    """Suggest configuration for common use cases.

    Args:
        use_case: The intended use case

    Returns:
        Suggested configuration
    """
    use_case = use_case.lower()

    if 'posix' in use_case or 'strict' in use_case:
        return ParserConfig.strict_posix()
    elif 'permissive' in use_case or 'tolerant' in use_case:
        return ParserConfig.permissive()
    elif 'debug' in use_case or 'develop' in use_case:
        return ParserConfig(trace_parsing=True, profile_parsing=True,
                            validate_ast=True)
    elif 'learn' in use_case or 'teach' in use_case or 'education' in use_case:
        return ParserConfig(
            parsing_mode=ParsingMode.EDUCATIONAL,
            trace_parsing=True, validate_ast=True,
            show_error_suggestions=True)
    else:
        return ParserConfig()  # Default bash-compatible


# --- Compatibility shims ---
# Delegate to module-level functions so existing callers keep working.

class ParserFactory:
    """Compatibility shim — prefer the module-level functions directly."""

    create_strict_posix_parser = staticmethod(create_strict_posix_parser)
    create_permissive_parser = staticmethod(create_permissive_parser)
    create_custom_parser = staticmethod(create_custom_parser)
    create_shell_parser = staticmethod(create_shell_parser)


class ConfigurationValidator:
    """Compatibility shim — prefer the module-level functions directly."""

    validate_config = staticmethod(validate_config)
    suggest_config_for_use_case = staticmethod(suggest_config)
