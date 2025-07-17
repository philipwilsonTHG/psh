"""Enhanced command parsing using token metadata."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .enhanced_base import EnhancedContextBaseParser, EnhancedParserConfig
from ..token_types import TokenType
from ..token_types import Token
from ..token_enhanced import TokenContext, SemanticType
from ..ast_nodes import SimpleCommand, TestExpression, BinaryTestExpression, ArrayAssignment


@dataclass
class AssignmentInfo:
    """Information extracted from assignment token."""
    variable: str
    value: str
    assignment_type: str = 'simple'  # simple, array, compound
    index: Optional[str] = None  # For array assignments
    operator: str = '='  # =, +=, -=, etc.
    position: int = 0


@dataclass
class Assignment:
    """Simple assignment representation for enhanced parser."""
    variable: str
    value: str
    assignment_type: str = 'simple'
    index: Optional[str] = None
    operator: str = '='
    position: int = 0


@dataclass 
class ComparisonExpression:
    """Simple comparison expression for enhanced parser."""
    left: Any
    operator: str
    right: Any


@dataclass
class Variable:
    """Simple variable representation."""
    name: str


@dataclass
class Literal:
    """Simple literal representation."""
    value: Any


class EnhancedSimpleCommandParser(EnhancedContextBaseParser):
    """Enhanced parser for simple commands using token metadata."""
    
    def parse_simple_command(self) -> SimpleCommand:
        """Parse simple command with enhanced features."""
        args = []
        redirects = []
        assignments = []
        
        # Parse leading assignments using enhanced detection
        while self.peek_enhanced() and self.peek_enhanced().is_assignment:
            assignment_token = self.expect_assignment()
            assignments.append(self._parse_assignment_from_token(assignment_token))
        
        # Parse command name
        if not self.match(TokenType.WORD, TokenType.STRING):
            if assignments:
                # Assignment-only command
                return SimpleCommand(
                    args=[],
                    redirects=redirects,
                    assignments=assignments
                )
            else:
                raise self._error("Expected command name")
        
        command_token = self.advance()
        
        # Validate command using semantic information
        if self.enhanced_config.enable_semantic_validation:
            self._validate_command_semantics(command_token)
        
        args.append(command_token.value)
        
        # Parse arguments and redirections
        while not self.at_end() and self._can_continue_command():
            if self.peek().type in self._redirection_types():
                redirect = self._parse_redirection_enhanced()
                redirects.append(redirect)
            else:
                arg_token = self.advance()
                args.append(arg_token.value)
        
        return SimpleCommand(
            args=args,
            redirects=redirects,
            assignments=assignments,
            enhanced_metadata=self._extract_command_metadata()
        )
    
    def _parse_assignment_from_token(self, token: Token) -> Assignment:
        """Parse assignment from enhanced token with metadata."""
        if hasattr(token, 'assignment_info'):
            info = token.assignment_info
            return Assignment(
                variable=info['variable'],
                value=info['value'],
                assignment_type=info.get('type', 'simple'),
                index=info.get('index'),  # For array assignments
                operator=info.get('operator', '='),  # For compound assignments
                position=token.position
            )
        else:
            # Fallback to basic parsing
            return self._parse_assignment_basic(token)
    
    def _parse_assignment_basic(self, token: Token) -> Assignment:
        """Basic assignment parsing fallback."""
        value = token.value
        if '=' not in value:
            raise self._error(f"Invalid assignment: {value}")
        
        parts = value.split('=', 1)
        variable = parts[0]
        assignment_value = parts[1] if len(parts) > 1 else ''
        
        # Check for array assignment
        if '[' in variable and variable.endswith(']'):
            # Extract array name and index
            bracket_pos = variable.find('[')
            array_name = variable[:bracket_pos]
            index = variable[bracket_pos+1:-1]
            return Assignment(
                variable=array_name,
                value=assignment_value,
                assignment_type='array',
                index=index,
                position=token.position
            )
        
        return Assignment(
            variable=variable,
            value=assignment_value,
            assignment_type='simple',
            position=token.position
        )
    
    def _validate_command_semantics(self, command_token: Token):
        """Validate command using semantic information."""
        if isinstance(command_token, Token):
            if command_token.metadata.semantic_type == SemanticType.BUILTIN:
                # Known builtin - no validation needed
                return
        
        # Check if command is in PATH or is a function
        if not self._is_executable_command(command_token.value):
            if hasattr(self.ctx, 'add_warning'):
                self.ctx.add_warning(f"Command '{command_token.value}' not found in PATH")
    
    def _is_executable_command(self, command: str) -> bool:
        """Check if command is executable."""
        # Simple implementation - could check PATH in real use
        common_commands = {
            'echo', 'cat', 'ls', 'grep', 'sed', 'awk', 'sort', 'head', 'tail',
            'find', 'xargs', 'cut', 'tr', 'wc', 'uniq', 'tee', 'touch', 'rm',
            'cp', 'mv', 'mkdir', 'rmdir', 'chmod', 'chown', 'ln', 'pwd'
        }
        return command in common_commands
    
    def _can_continue_command(self) -> bool:
        """Check if we can continue parsing the command."""
        current = self.peek()
        if not current:
            return False
        
        # Stop at command terminators
        terminators = {
            TokenType.SEMICOLON, TokenType.PIPE, TokenType.AND_AND, TokenType.OR_OR,
            TokenType.NEWLINE, TokenType.EOF, TokenType.RPAREN
        }
        
        return current.type not in terminators
    
    def _redirection_types(self) -> set:
        """Get set of redirection token types."""
        return {
            TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, TokenType.REDIRECT_APPEND,
            TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP,
            TokenType.HEREDOC, TokenType.HEREDOC_STRIP, TokenType.HERE_STRING
        }
    
    def _parse_redirection_enhanced(self):
        """Parse redirection with enhanced features."""
        # This would use existing redirection parsing but with enhanced validation
        # For now, delegate to base implementation
        redirect_token = self.advance()
        target_token = self.advance()
        
        # Could add enhanced validation here
        from ..ast_nodes import Redirection
        return Redirection(
            type=redirect_token.type,
            target=target_token.value,
            fd=None  # Could extract from enhanced metadata
        )
    
    def _extract_command_metadata(self) -> Dict[str, Any]:
        """Extract metadata for command from enhanced tokens."""
        enhanced_tokens = [t for t in self.ctx.tokens if isinstance(t, Token)]
        
        return {
            'has_assignments': bool([t for t in enhanced_tokens if t.is_assignment]),
            'has_redirections': bool([t for t in enhanced_tokens if t.is_redirect]),
            'complexity_score': self._calculate_complexity(),
            'semantic_types': [
                t.metadata.semantic_type.value for t in enhanced_tokens 
                if t.metadata.semantic_type
            ]
        }
    
    def _calculate_complexity(self) -> int:
        """Calculate command complexity score."""
        score = 0
        enhanced_tokens = [t for t in self.ctx.tokens if isinstance(t, Token)]
        
        for token in enhanced_tokens:
            if token.is_assignment:
                score += 1
            if token.is_redirect:
                score += 2
            if token.type in {TokenType.PIPE, TokenType.AND_AND, TokenType.OR_OR}:
                score += 3
        
        return score


class EnhancedTestParser(EnhancedContextBaseParser):
    """Enhanced parser for test expressions using context information."""
    
    def parse_test_expression(self) -> TestExpression:
        """Parse test expression using enhanced context validation."""
        # Expect opening [[ with test context
        self.expect_in_context(TokenType.DOUBLE_LBRACKET, TokenContext.TEST_EXPRESSION)
        
        expr = self._parse_test_or_expression()
        
        # Expect closing ]] with test context
        self.expect_in_context(TokenType.DOUBLE_RBRACKET, TokenContext.TEST_EXPRESSION)
        
        return TestExpression(expression=expr)
    
    def _parse_test_or_expression(self):
        """Parse OR expression in test context."""
        left = self._parse_test_and_expression()
        
        while self.match(TokenType.OR_OR):
            op = self.advance()
            right = self._parse_test_and_expression()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_test_and_expression(self):
        """Parse AND expression in test context."""
        left = self._parse_test_comparison()
        
        while self.match(TokenType.AND_AND):
            op = self.advance()
            right = self._parse_test_comparison()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_test_comparison(self) -> ComparisonExpression:
        """Parse comparison with context-aware operator recognition."""
        left = self._parse_test_primary()
        
        # Check for comparison operators in test context
        op_token = self.peek_enhanced()
        if op_token and self._is_test_comparison_operator(op_token):
            # Use context-specific token types for better error messages
            if op_token.type == TokenType.LESS_THAN_TEST:
                op = self.advance()
                right = self._parse_test_primary()
                return ComparisonExpression(left, '<', right)
            elif op_token.type == TokenType.GREATER_THAN_TEST:
                op = self.advance()
                right = self._parse_test_primary()
                return ComparisonExpression(left, '>', right)
            elif op_token.type in {TokenType.EQUAL, TokenType.NOT_EQUAL}:
                op = self.advance()
                right = self._parse_test_primary()
                return ComparisonExpression(left, op.value, right)
            # ... handle other test operators
        
        return left
    
    def _parse_test_primary(self):
        """Parse primary test expression."""
        # Handle unary operators
        if self.match(TokenType.BANG):
            op = self.advance()
            expr = self._parse_test_primary()
            from ..ast_nodes import UnaryOperation
            return UnaryOperation(operator=op.value, operand=expr)
        
        # Handle parentheses
        if self.match(TokenType.LPAREN):
            self.advance()
            expr = self._parse_test_or_expression()
            self.expect(TokenType.RPAREN)
            return expr
        
        # Handle file test operators (-f, -d, etc.)
        if self.peek().value.startswith('-') and len(self.peek().value) == 2:
            op = self.advance()
            operand = self._parse_test_primary()
            from ..ast_nodes import UnaryOperation
            return UnaryOperation(operator=op.value, operand=operand)
        
        # Handle variables and literals
        token = self.advance()
        from ..ast_nodes import Variable, Literal
        
        if token.type == TokenType.VARIABLE:
            return Variable(name=token.value)
        else:
            return Literal(value=token.value)
    
    def _is_test_comparison_operator(self, token: Token) -> bool:
        """Check if token is a comparison operator in test context."""
        if not isinstance(token, Token):
            return False
        
        if TokenContext.TEST_EXPRESSION not in token.metadata.contexts:
            return False
        
        return token.type in {
            TokenType.LESS_THAN_TEST, TokenType.GREATER_THAN_TEST,
            TokenType.LESS_EQUAL_TEST, TokenType.GREATER_EQUAL_TEST,
            TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.REGEX_MATCH
        }


class EnhancedArithmeticParser(EnhancedContextBaseParser):
    """Enhanced parser for arithmetic expressions using context information."""
    
    def parse_arithmetic_expression(self):
        """Parse arithmetic expression with enhanced context validation."""
        # Expect opening $(( with arithmetic context
        self.expect_in_context(TokenType.DOUBLE_LPAREN, TokenContext.ARITHMETIC_EXPRESSION)
        
        expr = self._parse_arithmetic_or()
        
        # Expect closing )) with arithmetic context
        self.expect_in_context(TokenType.DOUBLE_RPAREN, TokenContext.ARITHMETIC_EXPRESSION)
        
        return expr
    
    def _parse_arithmetic_or(self):
        """Parse OR expression in arithmetic context."""
        left = self._parse_arithmetic_and()
        
        while self.match(TokenType.PIPE):  # Bitwise OR
            op = self.advance()
            right = self._parse_arithmetic_and()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_arithmetic_and(self):
        """Parse AND expression in arithmetic context."""
        left = self._parse_arithmetic_equality()
        
        while self.match(TokenType.AMPERSAND):  # Bitwise AND
            op = self.advance()
            right = self._parse_arithmetic_equality()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_arithmetic_equality(self):
        """Parse equality expression in arithmetic context."""
        left = self._parse_arithmetic_relational()
        
        while self.match(TokenType.EQUAL, TokenType.NOT_EQUAL):
            op = self.advance()
            right = self._parse_arithmetic_relational()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_arithmetic_relational(self):
        """Parse relational expression in arithmetic context."""
        left = self._parse_arithmetic_additive()
        
        while self.match(TokenType.LESS_THAN, TokenType.GREATER_THAN,
                         TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL):
            op = self.advance()
            right = self._parse_arithmetic_additive()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_arithmetic_additive(self):
        """Parse additive expression in arithmetic context."""
        left = self._parse_arithmetic_multiplicative()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            right = self._parse_arithmetic_multiplicative()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_arithmetic_multiplicative(self):
        """Parse multiplicative expression in arithmetic context."""
        left = self._parse_arithmetic_unary()
        
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance()
            right = self._parse_arithmetic_unary()
            from ..ast_nodes import BinaryOperation
            left = BinaryOperation(left=left, operator=op.value, right=right)
        
        return left
    
    def _parse_arithmetic_unary(self):
        """Parse unary expression in arithmetic context."""
        if self.match(TokenType.PLUS, TokenType.MINUS, TokenType.BANG):
            op = self.advance()
            expr = self._parse_arithmetic_unary()
            from ..ast_nodes import UnaryOperation
            return UnaryOperation(operator=op.value, operand=expr)
        
        return self._parse_arithmetic_primary()
    
    def _parse_arithmetic_primary(self):
        """Parse primary arithmetic expression."""
        # Handle parentheses
        if self.match(TokenType.LPAREN):
            self.advance()
            expr = self._parse_arithmetic_or()
            self.expect(TokenType.RPAREN)
            return expr
        
        # Handle variables and numbers
        token = self.advance()
        from ..ast_nodes import Variable, Literal
        
        if token.type == TokenType.VARIABLE:
            return Variable(name=token.value)
        elif token.type == TokenType.NUMBER:
            return Literal(value=int(token.value))
        else:
            # Try to parse as number
            try:
                return Literal(value=int(token.value))
            except ValueError:
                return Variable(name=token.value)