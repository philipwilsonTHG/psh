"""Parser compatibility layer for test migration."""

import warnings
from typing import Union, Optional
from psh.state_machine_lexer import tokenize
from psh.parser import parse as parse_legacy
from psh.parser_refactored import parse as parse_refactored


# Control whether to use unified types globally for tests
USE_UNIFIED_TYPES = False


def set_unified_types(enabled: bool) -> None:
    """Enable or disable unified types globally for tests."""
    global USE_UNIFIED_TYPES
    USE_UNIFIED_TYPES = enabled


def parse_compat(code: str, use_unified: Optional[bool] = None) -> Union['TopLevel', 'CommandList']:
    """Parse code using appropriate parser based on configuration.
    
    Args:
        code: Shell code to parse
        use_unified: Override global setting if provided
        
    Returns:
        Parsed AST
    """
    tokens = tokenize(code)
    
    # Use provided value or global setting
    unified = use_unified if use_unified is not None else USE_UNIFIED_TYPES
    
    if unified:
        return parse_refactored(tokens, use_unified_types=True)
    else:
        return parse_legacy(tokens)


def suppress_deprecation_warnings():
    """Context manager to suppress deprecation warnings during tests."""
    # Filter out our custom deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="psh.deprecation")
    warnings.filterwarnings("ignore", message=".*is deprecated as of version.*")


# Import mappings for easy migration
try:
    from psh.ast_nodes import (
        # Unified types
        WhileLoop, ForLoop, CStyleForLoop, IfConditional,
        CaseConditional, SelectLoop, ArithmeticEvaluation,
        ExecutionContext
    )
    UNIFIED_TYPES_AVAILABLE = True
except ImportError:
    UNIFIED_TYPES_AVAILABLE = False


def get_expected_type(statement_type: str, command_type: str, use_unified: bool):
    """Get the expected AST node type based on configuration.
    
    Args:
        statement_type: Name of statement type (e.g., "IfStatement")
        command_type: Name of command type (e.g., "IfCommand")
        use_unified: Whether using unified types
        
    Returns:
        Expected type class
    """
    if use_unified and UNIFIED_TYPES_AVAILABLE:
        mapping = {
            ("IfStatement", "IfCommand"): IfConditional,
            ("WhileStatement", "WhileCommand"): WhileLoop,
            ("ForStatement", "ForCommand"): ForLoop,
            ("CStyleForStatement", "CStyleForCommand"): CStyleForLoop,
            ("CaseStatement", "CaseCommand"): CaseConditional,
            ("SelectStatement", "SelectCommand"): SelectLoop,
            ("ArithmeticCommand", "ArithmeticCommand"): ArithmeticEvaluation,
        }
        return mapping.get((statement_type, command_type))
    else:
        # Return the legacy type by importing it
        from psh import ast_nodes
        return getattr(ast_nodes, statement_type)