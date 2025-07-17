"""Comprehensive integration manager for enhanced parser components."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .enhanced_base import EnhancedContextBaseParser, EnhancedParserConfig
from .enhanced_commands_integration import install_enhanced_command_parser
from .enhanced_control_structures import install_enhanced_control_structure_parser
from .enhanced_statements import install_enhanced_statement_parser
from .enhanced_error_recovery import install_enhanced_error_recovery
from ..token_types import Token


@dataclass
class EnhancementStatus:
    """Status of parser enhancements."""
    commands_enhanced: bool = False
    control_structures_enhanced: bool = False
    statements_enhanced: bool = False
    error_recovery_enhanced: bool = False
    integration_level: str = "none"  # none, partial, full


class EnhancedParserIntegrationManager:
    """Manager for comprehensive enhanced parser integration."""
    
    def __init__(self, parser):
        self.parser = parser
        self.enhancement_status = EnhancementStatus()
        self.original_methods = {}  # Store original methods for rollback
        
    def install_all_enhancements(self, config: Optional[EnhancedParserConfig] = None) -> bool:
        """Install all available parser enhancements."""
        try:
            # Set enhanced config if provided
            if config:
                self.parser.enhanced_config = config
            
            # For enhanced parsers, create compatibility sub-parsers if needed
            self._ensure_compatibility_structure()
            
            # Install command enhancements
            if hasattr(self.parser, 'commands'):
                install_enhanced_command_parser(self.parser)
                self.enhancement_status.commands_enhanced = True
            
            # Install control structure enhancements
            if hasattr(self.parser, 'control_structures'):
                install_enhanced_control_structure_parser(self.parser)
                self.enhancement_status.control_structures_enhanced = True
            
            # Install statement enhancements
            if hasattr(self.parser, 'statements'):
                install_enhanced_statement_parser(self.parser)
                self.enhancement_status.statements_enhanced = True
            
            # Install error recovery
            if isinstance(self.parser, EnhancedContextBaseParser):
                install_enhanced_error_recovery(self.parser)
                self.enhancement_status.error_recovery_enhanced = True
            
            # Determine integration level
            self._assess_integration_level()
            
            return True
            
        except Exception as e:
            # Rollback on failure
            self.rollback_enhancements()
            raise RuntimeError(f"Failed to install enhancements: {e}")
    
    def install_selective_enhancements(self, 
                                     commands: bool = True,
                                     control_structures: bool = True,
                                     statements: bool = True,
                                     error_recovery: bool = True) -> Dict[str, bool]:
        """Install selective parser enhancements."""
        results = {}
        
        try:
            # Ensure compatibility structure first
            self._ensure_compatibility_structure()
            
            if commands and hasattr(self.parser, 'commands'):
                install_enhanced_command_parser(self.parser)
                self.enhancement_status.commands_enhanced = True
                results['commands'] = True
            else:
                results['commands'] = False
            
            if control_structures and hasattr(self.parser, 'control_structures'):
                install_enhanced_control_structure_parser(self.parser)
                self.enhancement_status.control_structures_enhanced = True
                results['control_structures'] = True
            else:
                results['control_structures'] = False
            
            if statements and hasattr(self.parser, 'statements'):
                install_enhanced_statement_parser(self.parser)
                self.enhancement_status.statements_enhanced = True
                results['statements'] = True
            else:
                results['statements'] = False
            
            if error_recovery and isinstance(self.parser, EnhancedContextBaseParser):
                install_enhanced_error_recovery(self.parser)
                self.enhancement_status.error_recovery_enhanced = True
                results['error_recovery'] = True
            else:
                results['error_recovery'] = False
            
            self._assess_integration_level()
            return results
            
        except Exception as e:
            # Rollback and re-raise
            self.rollback_enhancements()
            raise RuntimeError(f"Failed to install selective enhancements: {e}")
    
    def rollback_enhancements(self):
        """Rollback all enhancements to original state."""
        # Restore original methods if stored
        for component, methods in self.original_methods.items():
            if hasattr(self.parser, component):
                component_obj = getattr(self.parser, component)
                for method_name, original_method in methods.items():
                    setattr(component_obj, method_name, original_method)
        
        # Remove enhanced attributes
        enhanced_attrs = [
            'enhanced_config', 'error_recovery_manager', 
            'context_validator', 'semantic_analyzer'
        ]
        
        for attr in enhanced_attrs:
            if hasattr(self.parser, attr):
                delattr(self.parser, attr)
        
        # Reset status
        self.enhancement_status = EnhancementStatus()
    
    def get_enhancement_status(self) -> Dict[str, Any]:
        """Get current enhancement status."""
        return {
            'commands_enhanced': self.enhancement_status.commands_enhanced,
            'control_structures_enhanced': self.enhancement_status.control_structures_enhanced,
            'statements_enhanced': self.enhancement_status.statements_enhanced,
            'error_recovery_enhanced': self.enhancement_status.error_recovery_enhanced,
            'integration_level': self.enhancement_status.integration_level,
            'has_enhanced_config': hasattr(self.parser, 'enhanced_config'),
            'enhanced_token_support': self._check_enhanced_token_support(),
            'lexer_integration': self._check_lexer_integration()
        }
    
    def validate_enhancements(self) -> List[str]:
        """Validate that enhancements are working correctly."""
        issues = []
        
        # Check enhanced token support
        if not self._check_enhanced_token_support():
            issues.append("Enhanced token support not available")
        
        # Check enhanced methods are installed
        if self.enhancement_status.commands_enhanced:
            if not hasattr(self.parser.commands, 'parse_command_enhanced'):
                issues.append("Enhanced command parsing not properly installed")
        
        if self.enhancement_status.control_structures_enhanced:
            if not hasattr(self.parser.control_structures, 'parse_control_structure_enhanced'):
                issues.append("Enhanced control structure parsing not properly installed")
        
        if self.enhancement_status.statements_enhanced:
            if not hasattr(self.parser.statements, 'parse_statement_enhanced'):
                issues.append("Enhanced statement parsing not properly installed")
        
        if self.enhancement_status.error_recovery_enhanced:
            if not hasattr(self.parser, 'error_recovery_manager'):
                issues.append("Enhanced error recovery not properly installed")
        
        # Check lexer integration
        if not self._check_lexer_integration():
            issues.append("Lexer integration issues detected")
        
        return issues
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for enhanced parsing."""
        metrics = {
            'enhancement_overhead': 'minimal',
            'features_enabled': 0,
            'error_recovery_attempts': 0,
            'context_validations': 0,
            'semantic_analyses': 0
        }
        
        # Count enabled features
        status = self.enhancement_status
        metrics['features_enabled'] = sum([
            status.commands_enhanced,
            status.control_structures_enhanced, 
            status.statements_enhanced,
            status.error_recovery_enhanced
        ])
        
        # Get error recovery stats if available
        if hasattr(self.parser, 'error_recovery_manager'):
            recovery_stats = self.parser.error_recovery_manager.get_recovery_statistics()
            metrics['error_recovery_attempts'] = recovery_stats.get('total_attempts', 0)
            metrics['recovery_success_rate'] = recovery_stats.get('success_rate', 0)
        
        # Get enhanced config metrics
        if hasattr(self.parser, 'enhanced_config'):
            config = self.parser.enhanced_config
            metrics['context_validation_enabled'] = config.enable_context_validation
            metrics['semantic_validation_enabled'] = config.enable_semantic_validation
            metrics['semantic_analysis_enabled'] = config.enable_semantic_analysis
        
        return metrics
    
    def create_enhancement_report(self) -> Dict[str, Any]:
        """Create comprehensive enhancement report."""
        return {
            'status': self.get_enhancement_status(),
            'validation_issues': self.validate_enhancements(),
            'performance_metrics': self.get_performance_metrics(),
            'integration_recommendations': self._get_integration_recommendations()
        }
    
    def _assess_integration_level(self):
        """Assess the level of integration achieved."""
        enabled_count = sum([
            self.enhancement_status.commands_enhanced,
            self.enhancement_status.control_structures_enhanced,
            self.enhancement_status.statements_enhanced,
            self.enhancement_status.error_recovery_enhanced
        ])
        
        if enabled_count == 0:
            self.enhancement_status.integration_level = "none"
        elif enabled_count < 3:
            self.enhancement_status.integration_level = "partial"
        else:
            self.enhancement_status.integration_level = "full"
    
    def _check_enhanced_token_support(self) -> bool:
        """Check if parser supports enhanced tokens."""
        # Check if parser can handle enhanced tokens
        if hasattr(self.parser, 'peek_enhanced'):
            return True
        
        # Check if parser context supports enhanced tokens
        if hasattr(self.parser, 'ctx') and hasattr(self.parser.ctx, 'tokens'):
            tokens = self.parser.ctx.tokens
            if tokens and isinstance(tokens[0], Token):
                return True
        
        return False
    
    def _check_lexer_integration(self) -> bool:
        """Check lexer integration status."""
        # Check for lexer errors/warnings
        has_lexer_errors = hasattr(self.parser, 'lexer_errors')
        has_lexer_warnings = hasattr(self.parser, 'lexer_warnings')
        
        # Check for enhanced token metadata
        has_enhanced_tokens = self._check_enhanced_token_support()
        
        return has_lexer_errors or has_lexer_warnings or has_enhanced_tokens
    
    def _get_integration_recommendations(self) -> List[str]:
        """Get recommendations for improving integration."""
        recommendations = []
        
        status = self.enhancement_status
        
        if not status.commands_enhanced:
            recommendations.append("Enable enhanced command parsing for better assignment detection")
        
        if not status.control_structures_enhanced:
            recommendations.append("Enable enhanced control structure parsing for better error messages")
        
        if not status.statements_enhanced:
            recommendations.append("Enable enhanced statement parsing for semantic analysis")
        
        if not status.error_recovery_enhanced:
            recommendations.append("Enable error recovery for better error handling")
        
        if not self._check_enhanced_token_support():
            recommendations.append("Use enhanced lexer tokens for full metadata support")
        
        if self.enhancement_status.integration_level == "partial":
            recommendations.append("Enable all enhancements for full integration benefits")
        
        return recommendations
    
    def _ensure_compatibility_structure(self):
        """Ensure enhanced parser has compatible sub-parser structure."""
        # Create compatibility sub-parsers for enhanced parsers that don't have them
        if isinstance(self.parser, EnhancedContextBaseParser):
            if not hasattr(self.parser, 'commands'):
                # Create a minimal compatibility commands parser
                from .enhanced_commands_integration import EnhancedCommandParser
                self.parser.commands = EnhancedCommandParser(self.parser)
            
            if not hasattr(self.parser, 'control_structures'):
                # Create a minimal compatibility control structures parser
                from .enhanced_control_structures import EnhancedControlStructureParser
                self.parser.control_structures = EnhancedControlStructureParser(self.parser)
            
            if not hasattr(self.parser, 'statements'):
                # Create a minimal compatibility statements parser  
                from .enhanced_statements import EnhancedStatementParser
                self.parser.statements = EnhancedStatementParser(self.parser)


def create_fully_enhanced_parser(tokens_or_contract, config: Optional[EnhancedParserConfig] = None):
    """Create a fully enhanced parser with all components integrated."""
    from .enhanced_integration import create_enhanced_parser
    
    # Create base enhanced parser
    parser = create_enhanced_parser(tokens_or_contract, config)
    
    # Install all enhancements
    integration_manager = EnhancedParserIntegrationManager(parser)
    integration_manager.install_all_enhancements(config)
    
    # Add integration manager to parser
    parser.integration_manager = integration_manager
    
    return parser


def upgrade_existing_parser(parser, config: Optional[EnhancedParserConfig] = None) -> bool:
    """Upgrade existing parser with enhanced capabilities."""
    try:
        # Install integration manager
        integration_manager = EnhancedParserIntegrationManager(parser)
        
        # Install all available enhancements
        success = integration_manager.install_all_enhancements(config)
        
        if success:
            parser.integration_manager = integration_manager
        
        return success
        
    except Exception:
        return False


def validate_enhanced_parser(parser) -> Dict[str, Any]:
    """Validate an enhanced parser's capabilities."""
    if hasattr(parser, 'integration_manager'):
        return parser.integration_manager.create_enhancement_report()
    else:
        return {
            'status': {'integration_level': 'none'},
            'validation_issues': ['No integration manager found'],
            'performance_metrics': {},
            'integration_recommendations': ['Install enhanced parser integration']
        }