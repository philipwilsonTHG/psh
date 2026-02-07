"""Adapter for the existing recursive descent parser.

This module adapts the existing hand-coded recursive descent parser
to the AbstractShellParser interface, allowing it to be used alongside
experimental parser implementations.
"""

import time
from typing import Any, Dict, List, Optional, Tuple, Union

from ...ast_nodes import ASTNode, CommandList, TopLevel
from ...token_types import Token
from ..abstract_parser import AbstractShellParser, ParserCharacteristics, ParserType
from ..abstract_parser import ParseError as AbstractParseError
from ..config import ParserConfig
from ..recursive_descent.helpers import ParseError
from ..recursive_descent.parser import Parser


class RecursiveDescentAdapter(AbstractShellParser):
    """Adapter for the existing recursive descent parser.
    
    This class wraps the existing Parser class to conform to the
    AbstractShellParser interface, allowing it to be used in the
    experimental parser framework.
    """

    def __init__(self):
        """Initialize the adapter."""
        super().__init__()
        self.config = ParserConfig()
        self._last_parser_instance = None

    def parse(self, tokens: List[Token]) -> Union[TopLevel, CommandList]:
        """Parse tokens using the existing recursive descent parser.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            AST from the parser
            
        Raises:
            ParseError: If parsing fails
        """
        # Reset metrics
        self.reset_metrics()
        start_time = time.perf_counter()

        try:
            # Create parser instance
            parser = Parser(tokens, config=self.config)
            self._last_parser_instance = parser

            # Track token consumption
            initial_position = parser.context.current_position if hasattr(parser.context, 'current_position') else 0

            # Parse
            ast = parser.parse()

            # Update metrics
            final_position = parser.context.current_position if hasattr(parser.context, 'current_position') else len(tokens)
            self.metrics.tokens_consumed = final_position - initial_position
            self.metrics.parse_time_ms = (time.perf_counter() - start_time) * 1000

            # Get additional metrics from context if available
            if hasattr(parser.context, 'rules_evaluated'):
                self.metrics.rules_evaluated = parser.context.rules_evaluated

            return ast

        except ParseError as e:
            # Convert to abstract parse error
            position = None
            token = None
            if hasattr(e, 'error_context'):
                if hasattr(e.error_context, 'position'):
                    position = e.error_context.position
                if hasattr(e.error_context, 'token'):
                    token = e.error_context.token
            raise AbstractParseError(str(e), position=position, token=token) from e

    def parse_partial(self, tokens: List[Token]) -> Tuple[Optional[ASTNode], int]:
        """Parse as much as possible from the token stream.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            Tuple of (AST node or None, position where parsing stopped)
        """
        try:
            # Try normal parse first
            ast = self.parse(tokens)
            # If successful, we parsed everything
            return ast, len(tokens)
        except AbstractParseError:
            # Try to parse with error recovery
            if self.config.enable_error_recovery:
                parser = Parser(tokens, config=self.config)
                try:
                    # Use error collection mode
                    result = parser.parse_with_error_collection()
                    if result.ast:
                        return result.ast, parser.context.current_position if hasattr(parser.context, 'current_position') else 0
                except Exception:
                    pass

            # Return how far we got
            if self._last_parser_instance:
                return None, self._last_parser_instance.context.current_position if hasattr(self._last_parser_instance.context, 'current_position') else 0
            return None, 0

    def can_parse(self, tokens: List[Token]) -> bool:
        """Check if tokens can be parsed.
        
        Args:
            tokens: List of tokens to check
            
        Returns:
            True if parseable
        """
        try:
            # Try a quick parse with minimal error handling
            parser = Parser(tokens, config=ParserConfig(collect_errors=True))
            parser.parse()
            return True
        except Exception:
            return False

    def get_name(self) -> str:
        """Return the parser name.
        
        Returns:
            Parser identifier
        """
        return "recursive_descent"

    def get_description(self) -> str:
        """Return parser description.
        
        Returns:
            Human-readable description
        """
        return (
            "Hand-coded recursive descent parser with excellent error messages. "
            "This is the primary PSH parser with full shell feature support, "
            "comprehensive error recovery, and educational error messages."
        )

    def get_characteristics(self) -> ParserCharacteristics:
        """Return parser characteristics.
        
        Returns:
            Parser characteristics
        """
        return ParserCharacteristics(
            parser_type=ParserType.RECURSIVE_DESCENT,
            complexity="medium",
            error_recovery=True,
            backtracking=True,  # Limited backtracking for some constructs
            memoization=False,
            left_recursion=False,
            ambiguity_handling="first",
            incremental=False,
            streaming=False,
            hand_coded=True,
            generated=False,
            functional=False
        )

    def get_configuration_options(self) -> Dict[str, Any]:
        """Return available configuration options.
        
        Returns:
            Configuration option descriptions
        """
        return {
            "parsing_mode": "Parsing mode: strict_posix, bash_compat, permissive, educational",
            "collect_errors": "Collect all errors instead of failing on first",
            "enable_error_recovery": "Attempt to recover from parse errors",
            "max_errors": "Maximum errors to collect (default: 10)",
            "enable_functions": "Allow function definitions",
            "enable_arrays": "Allow array syntax",
            "enable_arithmetic": "Allow arithmetic expressions",
            "enable_process_substitution": "Allow process substitution",
            "validate_names": "Validate identifier names",
            "trace_parsing": "Enable parse tracing for debugging"
        }

    def configure(self, **options):
        """Configure the parser.
        
        Args:
            **options: Configuration options
        """
        # Map options to ParserConfig attributes
        for key, value in options.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def explain_parse(self, tokens: List[Token]) -> str:
        """Explain how recursive descent parsing works.
        
        Args:
            tokens: Tokens to explain parsing for
            
        Returns:
            Educational explanation
        """
        explanation = [
            "=== Recursive Descent Parsing ===",
            "",
            "The recursive descent parser works by:",
            "1. Starting from the top-level grammar rule (e.g., 'program')",
            "2. Recursively calling parsing functions for each grammar rule",
            "3. Each function consumes tokens that match its rule",
            "4. Building the AST bottom-up as functions return",
            "",
            "For these tokens:",
            f"  {' '.join(t.value for t in tokens[:10])}{'...' if len(tokens) > 10 else ''}",
            "",
            "Parsing steps:",
        ]

        # Show simplified parsing steps
        if tokens:
            if tokens[0].type == 'IF':
                explanation.extend([
                    "  1. parse() -> parse_statement_list()",
                    "  2. parse_statement_list() -> parse_if_statement()",
                    "  3. parse_if_statement():",
                    "     - Expect 'if' keyword",
                    "     - Parse condition with parse_command_list()",
                    "     - Expect 'then' keyword",
                    "     - Parse then-body with parse_command_list()",
                    "     - Check for 'else' or 'fi'",
                    "  4. Return IfConditional AST node"
                ])
            elif any(t.type == 'PIPE' for t in tokens):
                explanation.extend([
                    "  1. parse() -> parse_statement_list()",
                    "  2. parse_statement_list() -> parse_pipeline()",
                    "  3. parse_pipeline():",
                    "     - Parse first command",
                    "     - While we see '|' tokens:",
                    "       - Consume '|'",
                    "       - Parse next command",
                    "     - Return Pipeline AST node"
                ])
            else:
                explanation.extend([
                    "  1. parse() -> parse_statement_list()",
                    "  2. parse_statement_list() -> parse_simple_command()",
                    "  3. parse_simple_command():",
                    "     - Collect command words",
                    "     - Check for redirections",
                    "     - Return SimpleCommand AST node"
                ])

        explanation.extend([
            "",
            "Key advantages:",
            "- Clear, readable code structure",
            "- Excellent error messages with context",
            "- Easy to debug and extend",
            "- Natural mapping from grammar to code"
        ])

        return "\n".join(explanation)

    def validate_grammar(self) -> List[str]:
        """Validate parser configuration.
        
        Returns:
            List of warnings
        """
        warnings = []

        if self.config.parsing_mode == "strict_posix" and self.config.enable_arrays:
            warnings.append("Arrays are enabled but not POSIX compliant")

        if self.config.collect_errors and self.config.max_errors < 1:
            warnings.append("Error collection enabled but max_errors < 1")

        return warnings
