"""Word builder for creating Word AST nodes from tokens.

This module provides utilities for building Word nodes that properly
represent expansions within command arguments.
"""

from typing import List, Optional, Tuple
from ..token_types import Token, TokenType
from ..ast_nodes import (
    Word, WordPart, LiteralPart, ExpansionPart,
    VariableExpansion, CommandSubstitution, ParameterExpansion,
    ArithmeticExpansion, Expansion
)


class WordBuilder:
    """Builds Word AST nodes from tokens."""
    
    @staticmethod
    def parse_expansion_token(token: Token) -> Expansion:
        """Parse an expansion token into an Expansion AST node."""
        token_type = token.type
        value = token.value
        
        if token_type == TokenType.VARIABLE:
            # Simple variable like $USER or ${USER}
            # Remove $ and braces if present
            name = value
            if name.startswith('$'):
                name = name[1:]
            if name.startswith('{') and name.endswith('}'):
                name = name[1:-1]
            return VariableExpansion(name)
        
        elif token_type == TokenType.COMMAND_SUB:
            # Command substitution $(...)
            # Extract command from $(...)
            if value.startswith('$(') and value.endswith(')'):
                command = value[2:-1]
                return CommandSubstitution(command, backtick_style=False)
            else:
                # Shouldn't happen with proper lexing
                return CommandSubstitution(value, backtick_style=False)
        
        elif token_type == TokenType.COMMAND_SUB_BACKTICK:
            # Backtick command substitution `...`
            # Extract command from `...`
            if value.startswith('`') and value.endswith('`'):
                command = value[1:-1]
                return CommandSubstitution(command, backtick_style=True)
            else:
                return CommandSubstitution(value, backtick_style=True)
        
        elif token_type == TokenType.ARITH_EXPANSION:
            # Arithmetic expansion $((...)
            # Extract expression from $((...))
            if value.startswith('$((') and value.endswith('))'):
                expression = value[3:-2]
                return ArithmeticExpansion(expression)
            else:
                return ArithmeticExpansion(value)
        
        elif token_type == TokenType.PARAM_EXPANSION:
            # Complex parameter expansion ${var:-default} etc.
            return WordBuilder._parse_parameter_expansion(value)
        
        else:
            # Fallback - treat as variable
            return VariableExpansion(value)
    
    @staticmethod
    def _parse_parameter_expansion(value: str) -> ParameterExpansion:
        """Parse a parameter expansion like ${var:-default}."""
        # Remove ${ and }
        if value.startswith('${') and value.endswith('}'):
            inner = value[2:-1]
        else:
            inner = value
        
        # Check for operators
        # Order matters: check longer operators first
        operators = [':-', ':=', ':?', ':+', '##', '#', '%%', '%', '//', '/']
        
        for op in operators:
            if op in inner:
                # Find the first occurrence of the operator
                idx = inner.find(op)
                if idx > 0:  # Must have a variable name before operator
                    parameter = inner[:idx]
                    word = inner[idx + len(op):]
                    return ParameterExpansion(parameter, op, word)
        
        # Check for length operator ${#var}
        if inner.startswith('#'):
            return ParameterExpansion(inner[1:], '#', None)
        
        # No operator, just a variable
        return ParameterExpansion(inner, None, None)
    
    @staticmethod
    def build_word_from_token(token: Token, quote_type: Optional[str] = None) -> Word:
        """Build a Word from a single token."""
        if token.type in (TokenType.VARIABLE, TokenType.COMMAND_SUB, 
                          TokenType.COMMAND_SUB_BACKTICK, TokenType.ARITH_EXPANSION,
                          TokenType.PARAM_EXPANSION):
            # This is an expansion token
            expansion = WordBuilder.parse_expansion_token(token)
            return Word(parts=[ExpansionPart(expansion)], quote_type=quote_type)
        else:
            # This is a literal token
            return Word(parts=[LiteralPart(token.value)], quote_type=quote_type)
    
    @staticmethod
    def build_composite_word(tokens: List[Token], quote_type: Optional[str] = None) -> Word:
        """Build a Word from multiple tokens (for composite words)."""
        parts: List[WordPart] = []
        
        for token in tokens:
            if token.type in (TokenType.VARIABLE, TokenType.COMMAND_SUB,
                            TokenType.COMMAND_SUB_BACKTICK, TokenType.ARITH_EXPANSION,
                            TokenType.PARAM_EXPANSION):
                expansion = WordBuilder.parse_expansion_token(token)
                parts.append(ExpansionPart(expansion))
            else:
                parts.append(LiteralPart(token.value))
        
        return Word(parts=parts, quote_type=quote_type)
    
    @staticmethod
    def build_word_from_string(text: str, token_type: str = 'WORD', 
                             quote_type: Optional[str] = None) -> Word:
        """Build a Word from a string, parsing any embedded expansions.
        
        This is used when we have a string that might contain expansions
        that weren't tokenized separately (e.g., in quoted strings).
        """
        # For now, just create a literal word
        # TODO: Parse embedded expansions in quoted strings
        return Word.from_string(text, quote_type)