#!/usr/bin/env python3
"""
PSH Token Analysis Demonstration
This script analyzes the demo_all_tokens.sh script to showcase the unified token system
with enhanced features in PSH v0.91.3+.
"""

import sys
import os
from collections import defaultdict, Counter
from typing import Dict, List, Set

# Add PSH to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from psh.lexer import tokenize
from psh.token_types import TokenType, Token


def analyze_token_usage(script_path: str) -> Dict[str, any]:
    """Analyze token usage in a shell script."""
    print(f"🔍 Analyzing token usage in: {script_path}")
    print("=" * 60)
    
    # Read the script
    try:
        with open(script_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Could not find {script_path}")
        return {}
    
    # Tokenize the script using PSH's unified lexer
    try:
        # Use PSH's unified tokenize function
        tokens = tokenize(content, strict=True)
        print(f"✅ Successfully tokenized {len(tokens)} tokens")
    except Exception as e:
        print(f"❌ Tokenization error: {e}")
        return {}
    
    # Analyze token statistics
    analysis = {
        'total_tokens': len(tokens),
        'token_type_counts': Counter(),
        'token_types_used': set(),
        'sample_tokens': defaultdict(list),
        'metadata_samples': [],
        'complex_tokens': []
    }
    
    # Analyze each token
    for i, token in enumerate(tokens):
        token_type = token.type
        analysis['token_type_counts'][token_type] += 1
        analysis['token_types_used'].add(token_type)
        
        # Collect sample tokens for each type (first 3)
        if len(analysis['sample_tokens'][token_type]) < 3:
            analysis['sample_tokens'][token_type].append({
                'value': token.value,
                'position': token.position,
                'line': getattr(token, 'line', None),
                'column': getattr(token, 'column', None)
            })
        
        # Collect metadata samples
        if hasattr(token, 'metadata') and token.metadata and i < 10:
            analysis['metadata_samples'].append({
                'type': token_type.name,
                'value': token.value,
                'metadata': str(token.metadata)
            })
        
        # Identify complex tokens
        if token_type in [TokenType.COMPOSITE, TokenType.COMMAND_SUB, 
                         TokenType.ARITH_EXPANSION, TokenType.PROCESS_SUB_IN, 
                         TokenType.PROCESS_SUB_OUT]:
            analysis['complex_tokens'].append({
                'type': token_type.name,
                'value': token.value[:50] + ('...' if len(token.value) > 50 else ''),
                'position': token.position,
                'parts': len(getattr(token, 'parts', []))
            })
    
    return analysis


def display_analysis(analysis: Dict[str, any]):
    """Display the token analysis results."""
    
    print("\n📊 TOKEN USAGE STATISTICS")
    print("=" * 40)
    print(f"Total tokens analyzed: {analysis['total_tokens']}")
    print(f"Unique token types used: {len(analysis['token_types_used'])}")
    
    # Show top 10 most frequent token types
    print(f"\n🔝 TOP 10 MOST FREQUENT TOKEN TYPES")
    print("-" * 40)
    for token_type, count in analysis['token_type_counts'].most_common(10):
        percentage = (count / analysis['total_tokens']) * 100
        print(f"{token_type.name:20} {count:4d} ({percentage:5.1f}%)")
    
    # Show all token types found
    print(f"\n📋 ALL TOKEN TYPES FOUND ({len(analysis['token_types_used'])} types)")
    print("-" * 50)
    
    # Group by category for better organization
    categories = {
        'Basic': [TokenType.WORD, TokenType.STRING, TokenType.VARIABLE, TokenType.NEWLINE, TokenType.EOF],
        'Operators': [TokenType.PIPE, TokenType.AND_AND, TokenType.OR_OR, TokenType.SEMICOLON, 
                     TokenType.AMPERSAND, TokenType.EXCLAMATION],
        'Redirections': [TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, TokenType.REDIRECT_APPEND,
                        TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP,
                        TokenType.HEREDOC, TokenType.HEREDOC_STRIP, TokenType.HERE_STRING],
        'Grouping': [TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACE, TokenType.RBRACE,
                    TokenType.LBRACKET, TokenType.RBRACKET, TokenType.DOUBLE_LPAREN, TokenType.DOUBLE_RPAREN,
                    TokenType.DOUBLE_LBRACKET, TokenType.DOUBLE_RBRACKET],
        'Keywords': [TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.FI, TokenType.ELIF,
                    TokenType.WHILE, TokenType.DO, TokenType.DONE, TokenType.FOR, TokenType.IN,
                    TokenType.CASE, TokenType.ESAC, TokenType.FUNCTION, TokenType.BREAK, TokenType.CONTINUE],
        'Expansions': [TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK, TokenType.ARITH_EXPANSION,
                      TokenType.PROCESS_SUB_IN, TokenType.PROCESS_SUB_OUT],
        'Assignments': [TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN, TokenType.MULT_ASSIGN,
                       TokenType.DIV_ASSIGN, TokenType.MOD_ASSIGN, TokenType.ASSIGNMENT_WORD, 
                       TokenType.ARRAY_ASSIGNMENT_WORD],
        'Test Operators': [TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.REGEX_MATCH,
                          TokenType.LESS_THAN_TEST, TokenType.GREATER_THAN_TEST],
        'Patterns': [TokenType.GLOB_STAR, TokenType.GLOB_QUESTION, TokenType.GLOB_BRACKET],
        'Special': [TokenType.COMPOSITE, TokenType.DOUBLE_SEMICOLON]
    }
    
    for category, token_types in categories.items():
        found_in_category = [tt for tt in token_types if tt in analysis['token_types_used']]
        if found_in_category:
            print(f"\n{category}:")
            for token_type in found_in_category:
                count = analysis['token_type_counts'][token_type]
                print(f"  ✓ {token_type.name:25} ({count:2d} occurrences)")
    
    # Show samples of interesting token types
    print(f"\n🔍 TOKEN SAMPLES")
    print("-" * 30)
    
    interesting_types = [
        TokenType.COMMAND_SUB, TokenType.ARITH_EXPANSION, TokenType.COMPOSITE,
        TokenType.ASSIGNMENT_WORD, TokenType.ARRAY_ASSIGNMENT_WORD, TokenType.REGEX_MATCH
    ]
    
    for token_type in interesting_types:
        if token_type in analysis['token_types_used']:
            samples = analysis['sample_tokens'][token_type]
            print(f"\n{token_type.name}:")
            for sample in samples:
                value_display = sample['value'][:40] + ('...' if len(sample['value']) > 40 else '')
                print(f"  '{value_display}' (pos: {sample['position']})")
    
    # Show complex token analysis
    if analysis['complex_tokens']:
        print(f"\n🧩 COMPLEX TOKENS WITH PARTS")
        print("-" * 35)
        for token in analysis['complex_tokens'][:5]:  # Show first 5
            print(f"{token['type']:15} '{token['value']}' (parts: {token['parts']})")
    
    # Show metadata capabilities (if available)
    if analysis['metadata_samples']:
        print(f"\n🏷️  TOKEN METADATA EXAMPLES")
        print("-" * 30)
        for sample in analysis['metadata_samples'][:3]:  # Show first 3
            print(f"{sample['type']:15} '{sample['value'][:20]}...'")
            print(f"                Metadata: {sample['metadata']}")


def check_token_coverage():
    """Check which token types are covered by the demo script."""
    print("\n🎯 TOKEN TYPE COVERAGE ANALYSIS")
    print("=" * 40)
    
    # Get all defined token types
    all_token_types = set(TokenType)
    
    # Analyze the demo script
    script_path = "demo_all_tokens.sh"
    analysis = analyze_token_usage(script_path)
    
    if not analysis:
        return
    
    used_types = analysis['token_types_used']
    unused_types = all_token_types - used_types
    
    coverage_percentage = (len(used_types) / len(all_token_types)) * 100
    
    print(f"Total token types defined: {len(all_token_types)}")
    print(f"Token types used in demo: {len(used_types)}")
    print(f"Coverage: {coverage_percentage:.1f}%")
    
    if unused_types:
        print(f"\n❌ UNUSED TOKEN TYPES ({len(unused_types)}):")
        for token_type in sorted(unused_types, key=lambda t: t.name):
            print(f"  - {token_type.name}")
    else:
        print(f"\n🎉 ALL TOKEN TYPES COVERED!")
    
    return analysis


def main():
    """Main analysis function."""
    print("🚀 PSH Unified Token System Analysis")
    print("=" * 50)
    print("Analyzing the token demonstration script to showcase")
    print("the enhanced features of PSH's unified lexer (v0.91.3+)")
    print()
    
    # Check if demo script exists
    demo_script = "demo_all_tokens.sh"
    if not os.path.exists(demo_script):
        print(f"❌ Demo script not found: {demo_script}")
        print("Please run this script from the PSH root directory.")
        return
    
    # Perform analysis
    analysis = check_token_coverage()
    
    if analysis:
        display_analysis(analysis)
    
    print(f"\n✨ UNIFIED TOKEN SYSTEM FEATURES")
    print("-" * 40)
    print("The PSH v0.91.3+ unified token system provides:")
    print("✓ Single Token class with built-in metadata")
    print("✓ Context tracking for semantic analysis")
    print("✓ Position and line/column information")
    print("✓ Rich token parts for composite tokens")
    print("✓ 30% API reduction through unification")
    print("✓ Enhanced features standard for all users")
    print("✓ No compatibility overhead")
    
    print(f"\n🏁 Analysis complete!")


if __name__ == "__main__":
    main()