#!/usr/bin/env python3
"""
Demonstration of Enhanced Parser Integration

This script shows the Week 1 implementation of enhanced parser integration
according to the ENHANCED_PARSER_INTEGRATION_PLAN.md
"""

def demo_enhanced_parser():
    """Demonstrate enhanced parser capabilities."""
    print("=== Enhanced Parser Integration Demo ===\n")
    
    # Import enhanced parser components
    from psh.lexer.enhanced_integration import enhanced_tokenize
    from psh.parser.enhanced_integration import (
        create_parser_from_contract,
        parse_with_enhanced_lexer,
        analyze_command_semantics
    )
    from psh.parser.enhanced_factory import (
        create_development_parser,
        create_production_parser,
        EnhancedParserConfigBuilder
    )
    from psh.lexer.parser_contract import extract_legacy_tokens
    from psh.parser import parse
    
    # Test commands
    test_commands = [
        "echo hello world",
        "VAR=value echo $VAR",
        "if [[ -f file ]]; then echo yes; fi",
        "echo 'partial quote",  # Error case
        "ls -la | grep test"
    ]
    
    print("1. Basic Enhanced Lexer → Enhanced Parser Pipeline")
    print("=" * 50)
    
    for cmd in test_commands[:3]:  # Skip error cases for basic demo
        print(f"\nCommand: {cmd}")
        try:
            # Enhanced lexer → enhanced parser
            tokens_or_contract = enhanced_tokenize(cmd, enable_enhancements=True)
            parser = create_production_parser(tokens_or_contract)
            
            print(f"  ✓ Enhanced parser created successfully")
            print(f"  ✓ Token count: {len(parser.ctx.tokens)}")
            
            # Check for enhanced tokens
            enhanced_count = sum(1 for t in parser.ctx.tokens 
                               if hasattr(t, 'metadata'))
            print(f"  ✓ Enhanced tokens: {enhanced_count}/{len(parser.ctx.tokens)}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n\n2. Enhanced Features Demonstration")
    print("=" * 50)
    
    # Show different parser configurations
    configs = [
        ("Production", "production"),
        ("Development", "development"), 
        ("Compatible", "compatible")
    ]
    
    test_cmd = "echo hello"
    tokens = enhanced_tokenize(test_cmd, enable_enhancements=True)
    
    for name, config_type in configs:
        print(f"\n{name} Parser Configuration:")
        try:
            if config_type == "production":
                parser = create_production_parser(tokens)
            elif config_type == "development":
                parser = create_development_parser(tokens)
            else:
                from psh.parser.enhanced_factory import create_compatible_parser
                parser = create_compatible_parser(tokens)
            
            config = parser.enhanced_config
            print(f"  ✓ Enhanced tokens: {config.use_enhanced_tokens}")
            print(f"  ✓ Context validation: {config.enable_context_validation}")
            print(f"  ✓ Semantic validation: {config.enable_semantic_validation}")
            print(f"  ✓ Semantic analysis: {config.enable_semantic_analysis}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n\n3. Enhanced vs Legacy Compatibility")
    print("=" * 50)
    
    test_cmd = "echo test command"
    print(f"Command: {test_cmd}")
    
    try:
        # Enhanced pipeline
        enhanced_tokens = enhanced_tokenize(test_cmd, enable_enhancements=True)
        enhanced_parser = create_production_parser(enhanced_tokens)
        print(f"  ✓ Enhanced pipeline: {len(enhanced_parser.ctx.tokens)} tokens")
        
        # Legacy compatibility
        if isinstance(enhanced_tokens, list):
            legacy_tokens = enhanced_tokens  # Already legacy format
        else:
            legacy_tokens = extract_legacy_tokens(enhanced_tokens)
        
        # Use existing PSH parser
        ast = parse(legacy_tokens)
        print(f"  ✓ Legacy compatibility: AST type {type(ast).__name__}")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print("\n\n4. Enhanced Token Properties")
    print("=" * 50)
    
    from psh.token_enhanced import Token, TokenContext, SemanticType
    from psh.token_types import TokenType
    
    # Create enhanced token with metadata
    enhanced_token = Token(
        type=TokenType.ASSIGNMENT_WORD,
        value="VAR=value",
        position=0,
        end_position=9
    )
    enhanced_token.set_semantic_type(SemanticType.ASSIGNMENT)
    enhanced_token.add_context(TokenContext.COMMAND_POSITION)
    
    print(f"Token: {enhanced_token.value}")
    print(f"  ✓ Is assignment: {enhanced_token.is_assignment}")
    print(f"  ✓ Is keyword: {enhanced_token.is_keyword}")
    print(f"  ✓ Is error: {enhanced_token.is_error}")
    print(f"  ✓ Has command context: {enhanced_token.has_context(TokenContext.COMMAND_POSITION)}")
    print(f"  ✓ Semantic type: {enhanced_token.metadata.semantic_type}")
    
    print("\n\n5. Parser Diagnostics")
    print("=" * 50)
    
    try:
        # Test with various commands
        diagnostic_commands = [
            "echo $UNDEFINED_VAR",
            "echo hello",
            "invalid_command test"
        ]
        
        for cmd in diagnostic_commands:
            print(f"\nAnalyzing: {cmd}")
            try:
                diagnostics = analyze_command_semantics(cmd)
                print(f"  ✓ Error count: {diagnostics.get('error_count', 0)}")
                print(f"  ✓ Warning count: {diagnostics.get('warning_count', 0)}")
                print(f"  ✓ Has issues: {diagnostics.get('has_issues', False)}")
                
            except Exception as e:
                print(f"  ✗ Analysis error: {e}")
                
    except Exception as e:
        print(f"  ✗ Diagnostics error: {e}")
    
    print("\n\n6. Configuration Builder")
    print("=" * 50)
    
    try:
        # Demonstrate configuration builder
        config = (EnhancedParserConfigBuilder()
                 .with_enhanced_tokens(True)
                 .with_context_validation(True)
                 .with_semantic_analysis(False)
                 .for_production()
                 .build())
        
        print("Custom Configuration:")
        print(f"  ✓ Enhanced tokens: {config.use_enhanced_tokens}")
        print(f"  ✓ Context validation: {config.enable_context_validation}")
        print(f"  ✓ Semantic validation: {config.enable_semantic_validation}")
        print(f"  ✓ Semantic analysis: {config.enable_semantic_analysis}")
        print(f"  ✓ Full enhancement: {config.full_enhancement}")
        
    except Exception as e:
        print(f"  ✗ Config builder error: {e}")
    
    print("\n\n=== Demo Complete ===")
    print("\nKey Achievements:")
    print("✓ Enhanced parser base classes with full metadata utilization")
    print("✓ Context validation and semantic analysis components")
    print("✓ Enhanced command parsing with assignment metadata")
    print("✓ Factory patterns for different parser configurations")
    print("✓ Complete backward compatibility with existing PSH parser")
    print("✓ Integration with enhanced lexer pipeline")
    print("\nWeek 1 of Enhanced Parser Integration Plan is complete!")


if __name__ == "__main__":
    demo_enhanced_parser()