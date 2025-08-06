"""Factory for creating parser contexts."""

from typing import List, Optional, Dict, Any
from ....token_types import Token
from ..context import ParserContext
from ...config import ParserConfig, ParsingMode, ErrorHandlingMode


class ParserContextFactory:
    """Factory for creating parser contexts with various configurations."""
    
    @staticmethod
    def create(tokens: List[Token], 
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
        
        ctx = ParserContext(
            tokens=tokens,
            config=config,
            source_text=source_text,
            trace_enabled=config.trace_parsing,
            **kwargs
        )
        
        return ctx
    
    @staticmethod
    def create_strict_posix(tokens: List[Token], 
                           source_text: Optional[str] = None) -> ParserContext:
        """Create context for strict POSIX parsing."""
        config = ParserConfig.strict_posix()
        return ParserContextFactory.create(tokens, config, source_text)
    
    @staticmethod
    def create_bash_compatible(tokens: List[Token],
                              source_text: Optional[str] = None) -> ParserContext:
        """Create context for Bash-compatible parsing."""
        config = ParserConfig.bash_compatible()
        return ParserContextFactory.create(tokens, config, source_text)
    
    @staticmethod
    def create_permissive(tokens: List[Token],
                         source_text: Optional[str] = None) -> ParserContext:
        """Create context for permissive parsing with error recovery."""
        config = ParserConfig.permissive()
        return ParserContextFactory.create(tokens, config, source_text)
    
    @staticmethod
    def create_educational(tokens: List[Token],
                          source_text: Optional[str] = None) -> ParserContext:
        """Create context for educational parsing with debugging."""
        config = ParserConfig.educational()
        return ParserContextFactory.create(tokens, config, source_text)
    
    @staticmethod
    def create_development(tokens: List[Token],
                          source_text: Optional[str] = None) -> ParserContext:
        """Create context for parser development with full debugging."""
        config = ParserConfig.development()
        return ParserContextFactory.create(tokens, config, source_text)
    
    @staticmethod
    def create_for_repl(initial_tokens: List[Token] = None) -> ParserContext:
        """Create context optimized for REPL use.
        
        REPL contexts are configured for:
        - Error collection instead of throwing
        - Error recovery for continued interaction
        - Interactive mode features
        """
        config = ParserConfig(
            parsing_mode=ParsingMode.BASH_COMPAT,
            error_handling=ErrorHandlingMode.COLLECT,
            collect_errors=True,
            enable_error_recovery=True,
            max_errors=20,
            interactive_parsing=True,
            show_error_suggestions=True
        )
        
        tokens = initial_tokens or []
        return ParserContextFactory.create(tokens, config)
    
    @staticmethod
    def create_shell_parser(tokens: List[Token],
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
            base_config = ParserConfig.bash_compatible()
        
        # Override with specific shell options
        config_overrides = {}
        
        # Error handling options
        if 'collect_errors' in shell_options:
            config_overrides['collect_errors'] = shell_options['collect_errors']
        
        if 'debug-parser' in shell_options:
            config_overrides['trace_parsing'] = shell_options['debug-parser']
        
        # Feature toggles
        if 'braceexpand' in shell_options:
            config_overrides['enable_brace_expansion'] = shell_options['braceexpand']
        
        if 'histexpand' in shell_options:
            config_overrides['enable_history_expansion'] = shell_options['histexpand']
        
        # Apply overrides
        if config_overrides:
            final_config = base_config.clone(**config_overrides)
        else:
            final_config = base_config
        
        return ParserContextFactory.create(tokens, final_config, source_text)
    
    @staticmethod
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
        sub_ctx = ParserContextFactory.create(
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
    
    @staticmethod
    def create_validation_context(tokens: List[Token],
                                 source_text: Optional[str] = None) -> ParserContext:
        """Create context optimized for validation without execution.
        
        This context is configured for:
        - Error collection to find all issues
        - Full validation enabled
        - No execution-related features
        """
        config = ParserConfig(
            parsing_mode=ParsingMode.PERMISSIVE,
            error_handling=ErrorHandlingMode.COLLECT,
            collect_errors=True,
            enable_error_recovery=True,
            max_errors=100,
            enable_validation=True,
            enable_semantic_analysis=True,
            enable_validation_rules=True,
            validate_ast=True
        )
        
        return ParserContextFactory.create(tokens, config, source_text)
    
    @staticmethod
    def create_performance_test_context(tokens: List[Token],
                                       source_text: Optional[str] = None) -> ParserContext:
        """Create context for performance testing.
        
        This context enables:
        - Performance profiling
        - Minimal debugging overhead
        - Fast parsing mode
        """
        config = ParserConfig(
            parsing_mode=ParsingMode.BASH_COMPAT,
            error_handling=ErrorHandlingMode.STRICT,
            profile_parsing=True,
            trace_parsing=False,
            show_error_suggestions=False,
            enable_validation=False
        )
        
        return ParserContextFactory.create(tokens, config, source_text)


class ContextConfiguration:
    """Helper class for advanced context configuration."""
    
    @staticmethod
    def configure_for_testing(ctx: ParserContext,
                             enable_debugging: bool = True,
                             collect_errors: bool = True) -> ParserContext:
        """Configure context for testing scenarios."""
        if collect_errors:
            ctx.config.collect_errors = True
            ctx.config.error_handling = ErrorHandlingMode.COLLECT
        
        if enable_debugging:
            ctx.config.trace_parsing = True
            ctx.trace_enabled = True
        
        return ctx
    
    @staticmethod
    def configure_for_production(ctx: ParserContext,
                                fast_mode: bool = True) -> ParserContext:
        """Configure context for production use."""
        if fast_mode:
            ctx.config.trace_parsing = False
            ctx.config.profile_parsing = False
            ctx.config.show_error_suggestions = False
            ctx.config.enable_validation = False
            ctx.trace_enabled = False
            ctx.profiler = None
        
        return ctx
    
    @staticmethod
    def enable_full_debugging(ctx: ParserContext) -> ParserContext:
        """Enable all debugging features."""
        ctx.config.trace_parsing = True
        ctx.config.profile_parsing = True
        ctx.config.show_token_stream = True
        ctx.config.validate_ast = True
        ctx.config.show_error_suggestions = True
        ctx.trace_enabled = True
        
        # Create profiler if not exists
        if not ctx.profiler:
            from ..context import ParserProfiler
            ctx.profiler = ParserProfiler(ctx.config)
        
        return ctx