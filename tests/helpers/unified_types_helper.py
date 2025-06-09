"""Helper for migrating tests to use unified types."""

import pytest
from psh.parser_refactored import parse as parse_refactored
from psh.state_machine_lexer import tokenize


def parse_with_unified_types(code: str, use_unified: bool = True):
    """Parse code with optional unified types support.
    
    Args:
        code: Shell code to parse
        use_unified: If True, use unified types. If False, use legacy types.
        
    Returns:
        AST with appropriate type nodes
    """
    tokens = tokenize(code)
    return parse_refactored(tokens, use_unified_types=use_unified)


# Fixture for parametrized tests
@pytest.fixture(params=[False, True], ids=["legacy_types", "unified_types"])
def both_type_modes(request):
    """Parametrized fixture that runs tests with both legacy and unified types."""
    return request.param


def get_type_name(use_unified: bool, statement_type: str, command_type: str) -> str:
    """Get the appropriate type name based on mode.
    
    Args:
        use_unified: Whether using unified types
        statement_type: Name of statement type (e.g., "WhileStatement")
        command_type: Name of command type (e.g., "WhileCommand")
        
    Returns:
        Type name to use
    """
    if use_unified:
        # Map to unified type name
        mapping = {
            ("WhileStatement", "WhileCommand"): "WhileLoop",
            ("ForStatement", "ForCommand"): "ForLoop",
            ("CStyleForStatement", "CStyleForCommand"): "CStyleForLoop",
            ("IfStatement", "IfCommand"): "IfConditional",
            ("CaseStatement", "CaseCommand"): "CaseConditional",
            ("SelectStatement", "SelectCommand"): "SelectLoop",
            ("ArithmeticCommand", "ArithmeticCommand"): "ArithmeticEvaluation",
        }
        return mapping.get((statement_type, command_type), statement_type)
    else:
        # Return original type
        return statement_type