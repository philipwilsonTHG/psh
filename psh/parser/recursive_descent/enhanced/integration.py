"""Enhanced parser integration for working with enhanced lexer output."""

from typing import List, Optional, Union, Any, Dict

from .base import EnhancedContextBaseParser, EnhancedParserConfig, create_enhanced_parser
from ...factory import EnhancedParserFactory, create_development_parser, create_production_parser
from .commands import EnhancedSimpleCommandParser, EnhancedTestParser
from ....token_types import Token
from ....token_types import Token
from ....lexer.parser_contract import LexerParserContract


def parse_with_enhanced_lexer(
    input_string: str,
    lexer_config: Optional[Any] = None,
    parser_config: Optional[EnhancedParserConfig] = None,
    use_enhanced_features: bool = True
) -> Any:
    """Parse using enhanced lexer-parser pipeline."""
    # Import here to avoid circular imports
    from ....lexer.enhanced_integration import enhanced_tokenize
    
    # Get tokens using enhanced lexer
    if use_enhanced_features:
        lexer_result = enhanced_tokenize(input_string, enable_enhancements=True)
    else:
        # Fallback to base lexer
        from ....lexer import tokenize
        lexer_result = tokenize(input_string)
    
    # Create enhanced parser
    parser = create_enhanced_parser(lexer_result, parser_config)
    
    # Parse
    return parser.parse()


def create_parser_from_contract(
    contract: LexerParserContract,
    parser_type: str = "production"
) -> EnhancedContextBaseParser:
    """Create parser from lexer contract with specified type."""
    if parser_type == "development":
        return create_development_parser(contract)
    elif parser_type == "production":
        return create_production_parser(contract)
    else:
        # Default to compatible parser
        return EnhancedParserFactory.create_compatible_parser(contract.tokens)


def migrate_parser_to_enhanced(
    existing_parser,
    enable_all_features: bool = False
) -> EnhancedContextBaseParser:
    """Migrate existing parser to enhanced version."""
    return EnhancedParserFactory.migrate_existing_parser(
        existing_parser,
        enable_enhancements=enable_all_features
    )


# Convenience functions for specific parsing tasks
def parse_simple_command_enhanced(
    tokens_or_contract: Union[List[Token], LexerParserContract]
) -> Any:
    """Parse simple command using enhanced features."""
    config = EnhancedParserConfig(
        use_enhanced_tokens=True,
        enable_context_validation=True,
        enable_semantic_validation=True
    )
    
    parser = create_enhanced_parser(tokens_or_contract, config)
    if hasattr(parser, 'parse_simple_command_enhanced'):
        return parser.parse_simple_command_enhanced()
    else:
        # Fallback to standard parsing
        return parser.parse()


def parse_test_expression_enhanced(
    tokens_or_contract: Union[List[Token], LexerParserContract]
) -> Any:
    """Parse test expression using enhanced features."""
    config = EnhancedParserConfig(
        use_enhanced_tokens=True,
        enable_context_validation=True
    )
    
    parser = create_enhanced_parser(tokens_or_contract, config)
    if hasattr(parser, 'parse_test_expression_enhanced'):
        return parser.parse_test_expression_enhanced()
    else:
        # Fallback to standard parsing
        return parser.parse()


def analyze_command_semantics(
    input_command: Union[str, List[Token], LexerParserContract]
) -> Dict[str, Any]:
    """Analyze command semantics using enhanced parser."""
    # Handle string input by tokenizing first
    if isinstance(input_command, str):
        from ....lexer.enhanced_integration import enhanced_tokenize
        tokens_or_contract = enhanced_tokenize(input_command, enable_enhancements=True)
    else:
        tokens_or_contract = input_command
    
    config = EnhancedParserConfig(
        use_enhanced_tokens=True,
        enable_semantic_analysis=True,
        enable_context_validation=True
    )
    
    parser = create_enhanced_parser(tokens_or_contract, config)
    
    # Get semantic analysis results
    if hasattr(parser, 'get_lexer_diagnostics'):
        diagnostics = parser.get_lexer_diagnostics()
    else:
        diagnostics = {}
    
    # Add parser-level analysis
    if hasattr(parser, 'semantic_analyzer') and parser.semantic_analyzer:
        enhanced_tokens = [t for t in parser.ctx.tokens if isinstance(t, Token)]
        variable_issues = parser.semantic_analyzer.analyze_variable_usage(enhanced_tokens)
        diagnostics['variable_issues'] = variable_issues
    
    return diagnostics


# Export the main components
__all__ = [
    'EnhancedContextBaseParser',
    'EnhancedParserConfig', 
    'EnhancedParserFactory',
    'EnhancedSimpleCommandParser',
    'EnhancedTestParser',
    'create_enhanced_parser',
    'create_development_parser',
    'create_production_parser',
    'parse_with_enhanced_lexer',
    'create_parser_from_contract',
    'migrate_parser_to_enhanced',
    'parse_simple_command_enhanced',
    'parse_test_expression_enhanced',
    'analyze_command_semantics'
]