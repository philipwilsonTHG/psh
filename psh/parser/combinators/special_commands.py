"""Special command parsers for the shell parser combinator.

This module provides parsers for specialized shell syntax including
arithmetic commands, enhanced test expressions, array operations,
and process substitutions.
"""

from typing import List, Optional, Union
from ...token_types import Token, TokenType
from ...ast_nodes import (
    # Special commands
    ArithmeticEvaluation, EnhancedTestStatement, ProcessSubstitution,
    ArrayInitialization, ArrayElementAssignment,
    # Test expressions
    TestExpression, BinaryTestExpression, UnaryTestExpression,
    CompoundTestExpression, NegatedTestExpression,
    # Other
    ASTNode
)
from ..config import ParserConfig
from .core import Parser, ParseResult, ForwardParser
from .tokens import TokenParsers
from .commands import CommandParsers


class SpecialCommandParsers:
    """Parsers for special shell syntax.
    
    This class provides parsers for specialized command forms:
    - Arithmetic commands ((expression))
    - Enhanced test expressions [[ condition ]]
    - Array initialization and assignment
    - Process substitution <(cmd) and >(cmd)
    """
    
    def __init__(self, config: Optional[ParserConfig] = None,
                 token_parsers: Optional[TokenParsers] = None,
                 command_parsers: Optional[CommandParsers] = None):
        """Initialize special command parsers.
        
        Args:
            config: Parser configuration
            token_parsers: Token parsers to use
            command_parsers: Command parsers for nested commands
        """
        self.config = config or ParserConfig()
        self.tokens = token_parsers or TokenParsers()
        self.commands = command_parsers  # May be None initially
        
        self._initialize_parsers()
    
    def set_command_parsers(self, command_parsers: CommandParsers):
        """Set command parsers after initialization.
        
        This breaks the circular dependency between command and special parsers.
        
        Args:
            command_parsers: Command parsers to use
        """
        self.commands = command_parsers
    
    def _initialize_parsers(self):
        """Initialize all special command parsers."""
        # Arithmetic command parser
        self.arithmetic_command = self._build_arithmetic_command()
        
        # Enhanced test expression parser
        self.enhanced_test_statement = self._build_enhanced_test_statement()
        
        # Array parsers
        self.array_initialization = self._build_array_initialization()
        self.array_element_assignment = self._build_array_element_assignment()
        self.array_assignment = self._build_array_assignment()
        
        # Process substitution parser
        self.process_substitution = self._build_process_substitution()
        
        # Combined special command parser
        self.special_command = (
            self.arithmetic_command
            .or_else(self.enhanced_test_statement)
            .or_else(self.array_assignment)
            .or_else(self.process_substitution)
        )
    
    def _build_arithmetic_command(self) -> Parser[ArithmeticEvaluation]:
        """Build parser for arithmetic command ((expression)) syntax."""
        def parse_arithmetic_command(tokens: List[Token], pos: int) -> ParseResult[ArithmeticEvaluation]:
            """Parse arithmetic command."""
            # Check for opening ((
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected '((' for arithmetic command", position=pos)
            
            token = tokens[pos]
            if token.type.name != 'DOUBLE_LPAREN':
                return ParseResult(success=False, error=f"Expected '((', got {token.type.name}", position=pos)
            
            pos += 1  # Skip ((
            
            # Collect arithmetic expression until ))
            expr_tokens = []
            paren_depth = 0
            
            while pos < len(tokens):
                token = tokens[pos]
                
                # Check for closing ))
                if token.type.name == 'DOUBLE_RPAREN' and paren_depth == 0:
                    break
                elif token.type.name == 'LPAREN':
                    paren_depth += 1
                elif token.type.name == 'RPAREN':
                    paren_depth -= 1
                    if paren_depth < 0:
                        # Handle case of separate ) ) tokens
                        if (pos + 1 < len(tokens) and 
                            tokens[pos + 1].type.name == 'RPAREN'):
                            # Found ) ) pattern, this ends the arithmetic command
                            pos += 1  # Skip second )
                            break
                        else:
                            return ParseResult(success=False, 
                                             error="Unbalanced parentheses in arithmetic command", 
                                             position=pos)
                
                expr_tokens.append(token)
                pos += 1
            
            if pos >= len(tokens):
                return ParseResult(success=False, 
                                 error="Unterminated arithmetic command: expected '))'", 
                                 position=pos)
            
            # Skip the closing )) token if we found DOUBLE_RPAREN
            if pos < len(tokens) and tokens[pos].type.name == 'DOUBLE_RPAREN':
                pos += 1
            
            # Build expression string from tokens, preserving variable syntax
            expression_parts = []
            for token in expr_tokens:
                if token.type.name == 'VARIABLE':
                    # Add $ prefix for variables
                    expression_parts.append(f'${token.value}')
                else:
                    expression_parts.append(token.value)
            
            # Join with spaces and clean up extra whitespace
            expression = ' '.join(expression_parts)
            # Normalize multiple spaces to single spaces
            import re
            expression = re.sub(r'\s+', ' ', expression).strip()
            
            # Parse optional redirections (not common but valid)
            redirects = []
            # For now, skip redirection parsing to keep it simple
            
            return ParseResult(
                success=True,
                value=ArithmeticEvaluation(
                    expression=expression,
                    redirects=redirects,
                    background=False
                ),
                position=pos
            )
        
        return Parser(parse_arithmetic_command)
    
    def _build_enhanced_test_statement(self) -> Parser[EnhancedTestStatement]:
        """Build parser for enhanced test statement [[ expression ]] syntax."""
        def parse_enhanced_test(tokens: List[Token], pos: int) -> ParseResult[EnhancedTestStatement]:
            """Parse enhanced test expression."""
            # Check for opening [[
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected '[[' for enhanced test", position=pos)
            
            token = tokens[pos]
            if token.type.name != 'DOUBLE_LBRACKET':
                return ParseResult(success=False, error=f"Expected '[[', got {token.type.name}", position=pos)
            
            pos += 1  # Skip [[
            
            # Collect test expression tokens until ]]
            expr_tokens = []
            bracket_depth = 0
            
            while pos < len(tokens):
                token = tokens[pos]
                if token.type.name == 'DOUBLE_RBRACKET' and bracket_depth == 0:
                    break
                elif token.type.name == 'DOUBLE_LBRACKET':
                    bracket_depth += 1
                elif token.type.name == 'DOUBLE_RBRACKET':
                    bracket_depth -= 1
                
                expr_tokens.append(token)
                pos += 1
            
            # Check for closing ]]
            if pos >= len(tokens) or tokens[pos].type.name != 'DOUBLE_RBRACKET':
                return ParseResult(success=False, error="Expected ']]' to close enhanced test", position=pos)
            
            pos += 1  # Skip ]]
            
            # Parse the test expression from collected tokens
            test_expr = self._parse_test_expression(expr_tokens)
            if test_expr is None:
                return ParseResult(success=False, error="Invalid test expression", position=pos)
            
            return ParseResult(
                success=True,
                value=EnhancedTestStatement(expression=test_expr, redirects=[]),
                position=pos
            )
        
        return Parser(parse_enhanced_test)
    
    def _parse_test_expression(self, tokens: List[Token]) -> Optional[TestExpression]:
        """Parse test expression from a list of tokens.
        
        Args:
            tokens: List of tokens representing the test expression
            
        Returns:
            Parsed TestExpression or None if invalid
        """
        if not tokens:
            return None
        
        # Handle negation
        if tokens[0].value == '!':
            expr = self._parse_test_expression(tokens[1:])
            if expr:
                return NegatedTestExpression(expression=expr)
            return None
        
        # Handle simple binary operations: operand operator operand
        if len(tokens) == 3:
            left = self._format_test_operand(tokens[0])
            operator = tokens[1].value
            right = self._format_test_operand(tokens[2])
            
            # Support basic operators
            if operator in ['==', '!=', '=', '<', '>', '=~', 
                          '-eq', '-ne', '-lt', '-le', '-gt', '-ge']:
                return BinaryTestExpression(
                    left=left,
                    operator=operator,
                    right=right
                )
        
        # Handle unary operations: operator operand
        if len(tokens) == 2:
            operator = tokens[0].value
            operand = self._format_test_operand(tokens[1])
            
            # Support file test operators and string test operators
            if operator.startswith('-') and len(operator) == 2:
                return UnaryTestExpression(operator=operator, operand=operand)
        
        # Handle single operand (string test)
        if len(tokens) == 1:
            operand = self._format_test_operand(tokens[0])
            # Treat single operand as -n test (non-empty string test)
            return UnaryTestExpression(operator='-n', operand=operand)
        
        # For more complex expressions, return a simple binary test
        # This is simplified - full implementation would parse compound expressions
        if len(tokens) >= 3:
            left = self._format_test_operand(tokens[0])
            operator = tokens[1].value if len(tokens) > 1 else '=='
            right = ' '.join(self._format_test_operand(t) for t in tokens[2:])
            
            return BinaryTestExpression(left=left, operator=operator, right=right)
        
        return None
    
    def _format_test_operand(self, token: Token) -> str:
        """Format a test operand token for proper shell representation.
        
        Args:
            token: Token to format
            
        Returns:
            Formatted string representation
        """
        if token.type.name == 'VARIABLE':
            # Add $ prefix back for variables
            return f'${token.value}'
        elif token.type.name == 'STRING':
            # For strings, use the content as-is
            return token.value
        else:
            # For other token types, use the value as-is
            return token.value
    
    def _build_array_initialization(self) -> Parser[ArrayInitialization]:
        """Build parser for array initialization: arr=(element1 element2) syntax."""
        def parse_array_initialization(tokens: List[Token], pos: int) -> ParseResult[ArrayInitialization]:
            """Parse array initialization."""
            # We expect to be called when we've already identified an array pattern
            # Pattern: WORD = ( elements ) or arr=( elements )
            
            if pos >= len(tokens) or tokens[pos].type.name != 'WORD':
                return ParseResult(success=False, error="Expected array name", position=pos)
            
            word_token = tokens[pos]
            pos += 1
            
            # Handle case where arr= is combined in one token
            if word_token.value.endswith('=') or word_token.value.endswith('+='):
                is_append = word_token.value.endswith('+=')
                array_name = word_token.value[:-2] if is_append else word_token.value[:-1]
            else:
                # Handle separate tokens: arr = (
                array_name = word_token.value
                
                # Check for = or +=
                if pos >= len(tokens):
                    return ParseResult(success=False, error="Expected '=' after array name", position=pos)
                
                is_append = False
                if tokens[pos].type.name == 'WORD' and tokens[pos].value == '+=':
                    is_append = True
                    pos += 1
                elif tokens[pos].type.name == 'WORD' and tokens[pos].value == '=':
                    pos += 1
                else:
                    return ParseResult(success=False, error="Expected '=' or '+=' after array name", position=pos)
            
            # Check for opening parenthesis
            if pos >= len(tokens) or tokens[pos].type.name != 'LPAREN':
                return ParseResult(success=False, error="Expected '(' for array initialization", position=pos)
            
            pos += 1  # Skip (
            
            # Collect elements until closing parenthesis
            elements = []
            element_types = []
            element_quote_types = []
            
            while pos < len(tokens):
                token = tokens[pos]
                
                # Check for closing parenthesis
                if token.type.name == 'RPAREN':
                    break
                
                # Skip whitespace tokens
                if token.type.name in ['WHITESPACE', 'NEWLINE']:
                    pos += 1
                    continue
                
                # Collect element
                if token.type.name in ['WORD', 'STRING', 'VARIABLE', 'COMMAND_SUB', 
                                      'COMMAND_SUB_BACKTICK', 'PARAM_EXPANSION']:
                    # Format the element value
                    element_value = self._format_token_value(token)
                    
                    elements.append(element_value)
                    element_types.append(token.type.name)
                    
                    # Track quote type if applicable
                    quote_type = getattr(token, 'quote_type', None)
                    element_quote_types.append(quote_type)
                    
                    pos += 1
                else:
                    return ParseResult(success=False, 
                                     error=f"Unexpected token in array: {token.type.name}", 
                                     position=pos)
            
            # Check that we found the closing parenthesis
            if pos >= len(tokens) or tokens[pos].type.name != 'RPAREN':
                return ParseResult(success=False, 
                                 error="Expected ')' to close array initialization", 
                                 position=pos)
            
            pos += 1  # Skip )
            
            return ParseResult(
                success=True,
                value=ArrayInitialization(
                    name=array_name,
                    elements=elements,
                    element_types=element_types,
                    element_quote_types=element_quote_types,
                    is_append=is_append
                ),
                position=pos
            )
        
        return Parser(parse_array_initialization)
    
    def _build_array_element_assignment(self) -> Parser[ArrayElementAssignment]:
        """Build parser for array element assignment: arr[index]=value syntax."""
        def parse_array_element_assignment(tokens: List[Token], pos: int) -> ParseResult[ArrayElementAssignment]:
            """Parse array element assignment."""
            # Handle different patterns:
            # 1. All in one token: "arr[0]=value" or "arr[index]+=value"
            # 2. Separate tokens: "arr" "[" "0" "]" "=" "value"
            
            if pos >= len(tokens) or tokens[pos].type.name != 'WORD':
                return ParseResult(success=False, error="Expected array name", position=pos)
            
            word_token = tokens[pos]
            pos += 1
            
            # Case 1: All in one token "arr[index]=value" (must have value after =)
            if ('[' in word_token.value and ']' in word_token.value and 
                '=' in word_token.value and 
                not (word_token.value.endswith('=') or word_token.value.endswith('+='))):
                # Parse the combined token
                value = word_token.value
                
                # Find the brackets
                lbracket_pos = value.index('[')
                rbracket_pos = value.index(']')
                
                # Find the equals (could be += or =)
                equals_pos = value.index('+=') if '+=' in value else value.index('=')
                is_append = '+=' in value
                
                # Extract parts
                array_name = value[:lbracket_pos]
                index_str = value[lbracket_pos + 1:rbracket_pos]
                if is_append:
                    assigned_value = value[equals_pos + 2:]
                else:
                    assigned_value = value[equals_pos + 1:]
                
                # Determine value type (simplified)
                value_type = 'WORD'
                value_quote_type = None
                
                return ParseResult(
                    success=True,
                    value=ArrayElementAssignment(
                        name=array_name,
                        index=index_str,
                        value=assigned_value,
                        value_type=value_type,
                        value_quote_type=value_quote_type,
                        is_append=is_append
                    ),
                    position=pos
                )
            
            # Case 1b: Pattern "arr[index]=" followed by separate value token
            elif ('[' in word_token.value and ']' in word_token.value and 
                  (word_token.value.endswith('=') or word_token.value.endswith('+='))):
                # Parse the assignment token
                value = word_token.value
                
                # Find the brackets
                lbracket_pos = value.index('[')
                rbracket_pos = value.index(']')
                
                # Check for append assignment
                is_append = value.endswith('+=')
                
                # Extract parts
                array_name = value[:lbracket_pos]
                index_str = value[lbracket_pos + 1:rbracket_pos]
                
                # Get the value from the next token
                if pos >= len(tokens):
                    return ParseResult(success=False, error="Expected value after array assignment", position=pos)
                
                value_token = tokens[pos]
                pos += 1
                
                assigned_value = self._format_token_value(value_token)
                value_type = value_token.type.name
                value_quote_type = getattr(value_token, 'quote_type', None)
                
                return ParseResult(
                    success=True,
                    value=ArrayElementAssignment(
                        name=array_name,
                        index=index_str,
                        value=assigned_value,
                        value_type=value_type,
                        value_quote_type=value_quote_type,
                        is_append=is_append
                    ),
                    position=pos
                )
            
            # Case 2: Separate tokens
            else:
                array_name = word_token.value
                
                # Check for opening bracket
                if pos >= len(tokens) or tokens[pos].type.name != 'LBRACKET':
                    return ParseResult(success=False, error="Expected '[' for array index", position=pos)
                
                pos += 1  # Skip [
                
                # Collect index tokens until closing bracket
                index_tokens = []
                bracket_depth = 0
                
                while pos < len(tokens):
                    token = tokens[pos]
                    
                    # Handle nested brackets
                    if token.type.name == 'LBRACKET':
                        bracket_depth += 1
                    elif token.type.name == 'RBRACKET':
                        if bracket_depth == 0:
                            break
                        else:
                            bracket_depth -= 1
                    
                    index_tokens.append(token)
                    pos += 1
                
                # Check that we found the closing bracket
                if pos >= len(tokens) or tokens[pos].type.name != 'RBRACKET':
                    return ParseResult(success=False, error="Expected ']' to close array index", position=pos)
                
                pos += 1  # Skip ]
                
                # Build index string from tokens
                index_parts = []
                for token in index_tokens:
                    if token.type.name == 'VARIABLE':
                        index_parts.append(f'${token.value}')
                    else:
                        index_parts.append(token.value)
                
                index_str = ''.join(index_parts)
                
                # Check for = or +=
                if pos >= len(tokens):
                    return ParseResult(success=False, error="Expected '=' after array index", position=pos)
                
                is_append = False
                if tokens[pos].type.name == 'WORD' and tokens[pos].value == '+=':
                    is_append = True
                    pos += 1
                elif tokens[pos].type.name == 'WORD' and tokens[pos].value == '=':
                    pos += 1
                else:
                    return ParseResult(success=False, error="Expected '=' or '+=' after array index", position=pos)
                
                # Get the value
                if pos >= len(tokens):
                    return ParseResult(success=False, error="Expected value after '='", position=pos)
                
                value_token = tokens[pos]
                value = self._format_token_value(value_token)
                value_type = value_token.type.name
                value_quote_type = getattr(value_token, 'quote_type', None)
                
                pos += 1
                
                return ParseResult(
                    success=True,
                    value=ArrayElementAssignment(
                        name=array_name,
                        index=index_str,
                        value=value,
                        value_type=value_type,
                        value_quote_type=value_quote_type,
                        is_append=is_append
                    ),
                    position=pos
                )
        
        return Parser(parse_array_element_assignment)
    
    def _detect_array_pattern(self, tokens: List[Token], pos: int) -> str:
        """Detect what type of array pattern we have at the current position.
        
        Args:
            tokens: List of tokens
            pos: Current position
            
        Returns:
            'initialization' for arr=(elements)
            'element_assignment' for arr[index]=value
            'none' if no array pattern detected
        """
        if pos >= len(tokens) or tokens[pos].type.name != 'WORD':
            return 'none'
        
        word_token = tokens[pos]
        
        # Check for array element assignment patterns
        if '[' in word_token.value and ']' in word_token.value:
            # Check if this is all in one token: "arr[0]=value" or "arr[0]+=value"
            if '=' in word_token.value:
                equals_pos = word_token.value.index('+=') if '+=' in word_token.value else word_token.value.index('=')
                if word_token.value.index('[') < equals_pos:
                    return 'element_assignment'
            # Check for pattern: "arr[0]=" followed by value token
            elif word_token.value.endswith('=') or word_token.value.endswith('+='):
                if pos + 1 < len(tokens):  # Check if there's a value token after
                    return 'element_assignment'
            # Check for pattern: "arr[0]" followed by "=value"
            elif pos + 1 < len(tokens) and tokens[pos + 1].type.name == 'WORD':
                next_token = tokens[pos + 1]
                if next_token.value.startswith('=') or next_token.value.startswith('+='):
                    return 'element_assignment'
        
        # Check for array initialization patterns
        # Pattern 1: "arr=" followed by "("
        if (word_token.value.endswith('=') or word_token.value.endswith('+=')):
            if pos + 1 < len(tokens) and tokens[pos + 1].type.name == 'LPAREN':
                return 'initialization'
        
        # Pattern 2: "arr" followed by "=" followed by "("
        elif pos + 2 < len(tokens):
            if (tokens[pos + 1].type.name == 'WORD' and tokens[pos + 1].value in ['=', '+='] and 
                tokens[pos + 2].type.name == 'LPAREN'):
                return 'initialization'
        
        # Check for standalone array element assignment: "arr" followed by "["
        if pos + 1 < len(tokens) and tokens[pos + 1].type.name == 'LBRACKET':
            return 'element_assignment'
        
        return 'none'
    
    def _build_array_assignment(self) -> Parser[Union[ArrayInitialization, ArrayElementAssignment]]:
        """Build parser for any array assignment pattern."""
        def parse_array_assignment(tokens: List[Token], pos: int) -> ParseResult[Union[ArrayInitialization, ArrayElementAssignment]]:
            """Parse array assignment."""
            # Detect which pattern we have
            pattern = self._detect_array_pattern(tokens, pos)
            
            if pattern == 'initialization':
                return self._build_array_initialization().parse(tokens, pos)
            elif pattern == 'element_assignment':
                return self._build_array_element_assignment().parse(tokens, pos)
            else:
                return ParseResult(success=False, error="No array pattern detected", position=pos)
        
        return Parser(parse_array_assignment)
    
    def _build_process_substitution(self) -> Parser[ProcessSubstitution]:
        """Build parser for process substitution <(cmd) and >(cmd) syntax."""
        def parse_process_substitution(tokens: List[Token], pos: int) -> ParseResult[ProcessSubstitution]:
            """Parse process substitution."""
            if pos >= len(tokens):
                return ParseResult(success=False, error="Expected process substitution", position=pos)
            
            token = tokens[pos]
            if token.type.name == 'PROCESS_SUB_IN':
                direction = 'in'
            elif token.type.name == 'PROCESS_SUB_OUT':
                direction = 'out'
            else:
                return ParseResult(success=False, 
                                 error=f"Expected process substitution, got {token.type.name}", 
                                 position=pos)
            
            # Extract command from token value
            # Token value format: "<(command)" or ">(command)"
            token_value = token.value
            if len(token_value) >= 3 and token_value.startswith(('<(', '>(')):
                if token_value.endswith(')'):
                    # Complete process substitution
                    command = token_value[2:-1]  # Remove <( or >( and trailing )
                else:
                    # Incomplete process substitution (missing closing paren)
                    command = token_value[2:]  # Remove <( or >(
            else:
                return ParseResult(success=False, 
                                 error=f"Invalid process substitution format: {token_value}", 
                                 position=pos)
            
            return ParseResult(
                success=True,
                value=ProcessSubstitution(direction=direction, command=command),
                position=pos + 1
            )
        
        return Parser(parse_process_substitution)
    
    def _format_token_value(self, token: Token) -> str:
        """Format token value appropriately based on token type.
        
        Args:
            token: Token to format
            
        Returns:
            Formatted string representation
        """
        if token.type.name == 'VARIABLE':
            # Variables need the $ prefix
            return f"${token.value}"
        elif token.type.name in ['COMMAND_SUB', 'COMMAND_SUB_BACKTICK', 
                                 'ARITH_EXPANSION', 'PARAM_EXPANSION']:
            # These already include their delimiters
            return token.value
        elif token.type.name == 'STRING':
            # String content after quote processing
            return token.value
        else:
            # Everything else uses raw value
            return token.value


# Convenience functions

def create_special_command_parsers(config: Optional[ParserConfig] = None,
                                  token_parsers: Optional[TokenParsers] = None,
                                  command_parsers: Optional[CommandParsers] = None) -> SpecialCommandParsers:
    """Create and return a SpecialCommandParsers instance.
    
    Args:
        config: Optional parser configuration
        token_parsers: Optional token parsers
        command_parsers: Optional command parsers
        
    Returns:
        Initialized SpecialCommandParsers object
    """
    return SpecialCommandParsers(config, token_parsers, command_parsers)