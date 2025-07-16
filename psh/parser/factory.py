"""Parser factory for creating configured parser instances.

This module provides convenient factory methods for creating Parser instances
with different configurations for various use cases.
"""

from typing import List, Optional
from ..token_types import Token
from .main import Parser
from .config import ParserConfig, ParsingMode


class ParserFactory:
    """Factory for creating configured parser instances."""
    
    @staticmethod
    def create_strict_posix_parser(tokens: List[Token], 
                                   source_text: Optional[str] = None) -> Parser:
        """Create a parser in strict POSIX mode.
        
        This parser enforces strict POSIX compliance and rejects
        Bash-specific extensions.
        
        Args:
            tokens: List of tokens to parse
            source_text: Optional source text for error reporting
            
        Returns:
            Configured parser in strict POSIX mode
        """
        config = ParserConfig.strict_posix()
        return Parser(tokens, source_text=source_text, config=config)
    
    @staticmethod
    def create_bash_compatible_parser(tokens: List[Token],
                                      source_text: Optional[str] = None) -> Parser:
        """Create a parser in Bash-compatible mode.
        
        This parser accepts most Bash extensions and features
        for maximum compatibility.
        
        Args:
            tokens: List of tokens to parse
            source_text: Optional source text for error reporting
            
        Returns:
            Configured parser in Bash-compatible mode
        """
        config = ParserConfig.bash_compatible()
        return Parser(tokens, source_text=source_text, config=config)
    
    @staticmethod
    def create_permissive_parser(tokens: List[Token],
                                 source_text: Optional[str] = None) -> Parser:
        """Create a parser in permissive mode.
        
        This parser is very forgiving and attempts to parse
        as much as possible, collecting errors for reporting.
        
        Args:
            tokens: List of tokens to parse
            source_text: Optional source text for error reporting
            
        Returns:
            Configured parser in permissive mode
        """
        config = ParserConfig.permissive()
        return Parser(tokens, source_text=source_text, config=config)
    
    @staticmethod
    def create_educational_parser(tokens: List[Token],
                                  source_text: Optional[str] = None) -> Parser:
        """Create a parser in educational mode.
        
        This parser provides detailed explanations and extra
        help for learning shell programming.
        
        Args:
            tokens: List of tokens to parse
            source_text: Optional source text for error reporting
            
        Returns:
            Configured parser in educational mode
        """
        config = ParserConfig.educational()
        return Parser(tokens, source_text=source_text, config=config)
    
    @staticmethod
    def create_development_parser(tokens: List[Token],
                                  source_text: Optional[str] = None) -> Parser:
        """Create a parser for development and debugging.
        
        This parser enables all debugging features for
        parser development and testing.
        
        Args:
            tokens: List of tokens to parse
            source_text: Optional source text for error reporting
            
        Returns:
            Configured parser for development use
        """
        config = ParserConfig.development()
        return Parser(tokens, source_text=source_text, config=config)
    
    @staticmethod
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
            config = ParserConfig(**config_overrides)
        
        return Parser(tokens, source_text=source_text, config=config)
    
    @staticmethod
    def create_shell_parser(tokens: List[Token],
                            source_text: Optional[str] = None,
                            shell_options: Optional[dict] = None) -> Parser:
        """Create a parser based on shell options.
        
        This method maps shell options to parser configuration
        for integration with the shell environment.
        
        Args:
            tokens: List of tokens to parse
            source_text: Optional source text for error reporting
            shell_options: Dictionary of shell options
            
        Returns:
            Configured parser based on shell options
        """
        if not shell_options:
            shell_options = {}
        
        # Start with default bash-compatible config
        config = ParserConfig.bash_compatible()
        
        # Apply shell option mappings
        if shell_options.get('posix', False):
            config = ParserConfig.strict_posix()
        elif shell_options.get('bash_compat', True):
            config = ParserConfig.bash_compatible()
        
        # Override specific features based on shell options
        config_overrides = {}
        
        # Error handling options
        if shell_options.get('collect_errors', False):
            config_overrides['collect_errors'] = True
            config_overrides['error_handling'] = 'collect'
        
        # Feature toggles
        if 'enable_aliases' in shell_options:
            config_overrides['enable_aliases'] = shell_options['enable_aliases']
        
        if 'enable_functions' in shell_options:
            config_overrides['enable_functions'] = shell_options['enable_functions']
        
        if 'enable_arithmetic' in shell_options:
            config_overrides['enable_arithmetic'] = shell_options['enable_arithmetic']
        
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


class ConfigurationValidator:
    """Validates parser configurations for consistency."""
    
    @staticmethod
    def validate_config(config: ParserConfig) -> List[str]:
        """Validate configuration for consistency and return warnings.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for incompatible combinations
        if (config.parsing_mode == ParsingMode.STRICT_POSIX and 
            config.allow_bash_arrays):
            warnings.append(
                "Bash arrays are enabled in strict POSIX mode - "
                "this may cause compatibility issues"
            )
        
        if (config.parsing_mode == ParsingMode.STRICT_POSIX and
            config.enable_process_substitution):
            warnings.append(
                "Process substitution is enabled in strict POSIX mode - "
                "this is not POSIX compliant"
            )
        
        if (config.require_semicolons and 
            config.parsing_mode == ParsingMode.PERMISSIVE):
            warnings.append(
                "Semicolon requirement in permissive mode may be too strict"
            )
        
        # Check for performance concerns
        if (config.trace_parsing and not config.profile_parsing):
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
    
    @staticmethod
    def suggest_config_for_use_case(use_case: str) -> ParserConfig:
        """Suggest configuration for common use cases.
        
        Args:
            use_case: The intended use case
            
        Returns:
            Suggested configuration
        """
        use_case = use_case.lower()
        
        if 'posix' in use_case or 'strict' in use_case:
            return ParserConfig.strict_posix()
        elif 'bash' in use_case or 'compat' in use_case:
            return ParserConfig.bash_compatible()
        elif 'learn' in use_case or 'teach' in use_case or 'education' in use_case:
            return ParserConfig.educational()
        elif 'debug' in use_case or 'develop' in use_case:
            return ParserConfig.development()
        elif 'permissive' in use_case or 'tolerant' in use_case:
            return ParserConfig.permissive()
        else:
            return ParserConfig.bash_compatible()  # Safe default