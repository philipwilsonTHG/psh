"""Parser integration for shell (enhanced features now standard)."""

from typing import Any, Optional, Dict
from dataclasses import dataclass

from .parser import parse_with_lexer_integration, ParserConfig
from .parser.base_context import ContextBaseParser


@dataclass
class ShellParserOptions:
    """Configuration for shell parsing features (enhanced features now standard)."""
    context_validation: bool = False
    semantic_validation: bool = False
    semantic_analysis: bool = False
    enhanced_error_recovery: bool = True
    performance_mode: str = "balanced"  # "performance", "balanced", "development"


class ShellParser:
    """Shell parser integration (enhanced features now standard)."""
    
    def __init__(self, shell):
        self.shell = shell
        self.parser_config = self._create_parser_config()
        self.options = self._get_parser_options()
    
    def parse_command(self, command_string: str) -> Any:
        """Parse command using enhanced lexer-parser pipeline (now standard)."""
        try:
            # Use enhanced pipeline (now the only implementation)
            return parse_with_lexer_integration(
                command_string,
                parser_config=self.parser_config
            )
        except Exception as e:
            # Enhanced parsing failed, re-raise with context
            if hasattr(self.shell, 'debug') and self.shell.debug:
                print(f"Enhanced parsing failed: {e}")
            raise
    
    def _create_parser_config(self) -> ParserConfig:
        """Create parser configuration from shell settings."""
        # Get shell options if available
        shell_options = {}
        if hasattr(self.shell, 'state') and hasattr(self.shell.state, 'options'):
            shell_options = self.shell.state.options
        
        # Determine performance mode
        performance_mode = shell_options.get('parser-mode', 'balanced')
        
        if performance_mode == 'development':
            return ParserConfig(
                use_enhanced_tokens=True,
                enable_context_validation=True,
                enable_semantic_validation=True,
                enable_semantic_analysis=True,
                strict_contract_validation=True,
                full_enhancement=True
            )
        elif performance_mode == 'performance':
            return ParserConfig(
                use_enhanced_tokens=True,
                enable_context_validation=False,
                enable_semantic_validation=False,
                enable_semantic_analysis=False,
                strict_contract_validation=False,
                full_enhancement=False
            )
        else:  # balanced
            return ParserConfig(
                use_enhanced_tokens=True,
                enable_context_validation=shell_options.get('validate-context', False),
                enable_semantic_validation=shell_options.get('validate-semantics', False),
                enable_semantic_analysis=shell_options.get('analyze-semantics', False),
                strict_contract_validation=False,
                full_enhancement=False
            )
    
    def _get_parser_options(self) -> ShellParserOptions:
        """Get parser options from shell configuration."""
        if hasattr(self.shell, 'state') and hasattr(self.shell.state, 'options'):
            options = self.shell.state.options
            return ShellParserOptions(
                context_validation=options.get('validate-context', False),
                semantic_validation=options.get('validate-semantics', False),
                semantic_analysis=options.get('analyze-semantics', False),
                enhanced_error_recovery=options.get('enhanced-error-recovery', True),
                performance_mode=options.get('parser-mode', 'balanced')
            )
        else:
            return ShellParserOptions()
    
    def get_parser_status(self) -> Dict[str, Any]:
        """Get status of parser integration."""
        return {
            'options': self.options.__dict__,
            'config': {
                'use_enhanced_tokens': self.parser_config.use_enhanced_tokens,
                'context_validation': self.parser_config.enable_context_validation,
                'semantic_validation': self.parser_config.enable_semantic_validation,
                'semantic_analysis': self.parser_config.enable_semantic_analysis,
                'full_enhancement': self.parser_config.full_enhancement
            }
        }
    
    def update_configuration(self, **options):
        """Update parser configuration."""
        # Update shell options
        if hasattr(self.shell, 'state') and hasattr(self.shell.state, 'options'):
            for key, value in options.items():
                if key in ['validate-context', 'validate-semantics', 
                          'analyze-semantics', 'enhanced-error-recovery', 'parser-mode']:
                    self.shell.state.options[key] = value
        
        # Recreate parser config
        self.parser_config = self._create_parser_config()
        self.options = self._get_parser_options()
    
    def analyze_command_semantics(self, command_string: str) -> Dict[str, Any]:
        """Analyze command semantics without executing."""
        try:
            from .parser import analyze_command_semantics
            return analyze_command_semantics(command_string)
        except Exception as e:
            return {"error": f"Semantic analysis failed: {e}"}
    
    def validate_command_syntax(self, command_string: str) -> Dict[str, Any]:
        """Validate command syntax using enhanced lexer-parser."""
        try:
            # Create development config for thorough validation
            validation_config = ParserConfig(
                use_enhanced_tokens=True,
                enable_context_validation=True,
                enable_semantic_validation=True,
                enable_semantic_analysis=True,
                strict_contract_validation=True
            )
            
            # Try to parse
            ast = parse_with_lexer_integration(command_string, parser_config=validation_config)
            
            return {
                "valid": True,
                "message": "Command syntax is valid",
                "ast_type": type(ast).__name__
            }
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"Syntax validation failed: {e}",
                "error_type": type(e).__name__
            }


def install_parser_integration(shell):
    """Install parser integration into shell (enhanced features now standard)."""
    # Create parser manager
    shell.parser = ShellParser(shell)
    
    # Add shell options if not present
    if hasattr(shell, 'state') and hasattr(shell.state, 'options'):
        default_options = {
            'validate-context': False,
            'validate-semantics': False,
            'analyze-semantics': False,
            'enhanced-error-recovery': True,
            'parser-mode': 'balanced'
        }
        
        for option, default_value in default_options.items():
            if option not in shell.state.options:
                shell.state.options[option] = default_value
    
    # Install parse method
    def parse_command(command_string: str):
        return shell.parser.parse_command(command_string)
    
    # Install the method
    shell.parse_command = parse_command
    
    return shell.parser


def create_shell(*args, **kwargs):
    """Create shell with parser integration (enhanced features now standard)."""
    from .shell import Shell
    
    # Create shell
    shell = Shell(*args, **kwargs)
    
    # Install parser integration
    install_parser_integration(shell)
    
    return shell


def enable_enhanced_features(shell, profile: str = "balanced"):
    """Enable enhanced features on existing shell (now standard)."""
    # Apply feature profile
    profiles = {
        "performance": {
            'validate-context': False,
            'validate-semantics': False,
            'analyze-semantics': False,
            'parser-mode': 'performance'
        },
        "balanced": {
            'validate-context': False,
            'validate-semantics': False,
            'analyze-semantics': False,
            'parser-mode': 'balanced'
        },
        "development": {
            'validate-context': True,
            'validate-semantics': True,
            'analyze-semantics': True,
            'parser-mode': 'development'
        },
        "full": {
            'validate-context': True,
            'validate-semantics': True,
            'analyze-semantics': True,
            'enhanced-error-recovery': True,
            'parser-mode': 'development'
        }
    }
    
    if profile not in profiles:
        raise ValueError(f"Unknown profile: {profile}. Available: {list(profiles.keys())}")
    
    # Install parser integration if not present
    if not hasattr(shell, 'parser'):
        install_parser_integration(shell)
    
    # Apply profile options
    shell.parser.update_configuration(**profiles[profile])


# Export main components
__all__ = [
    'ShellParser',
    'ShellParserOptions', 
    'install_parser_integration',
    'create_shell',
    'enable_enhanced_features'
]