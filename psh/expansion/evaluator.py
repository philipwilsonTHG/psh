"""Expansion evaluator for Word AST nodes.

This module evaluates expansion AST nodes to produce strings,
delegating to the existing VariableExpander and ExpansionManager
to avoid duplicating expansion logic.
"""

from typing import TYPE_CHECKING

from ..ast_nodes import (
    Expansion, VariableExpansion, CommandSubstitution,
    ParameterExpansion, ArithmeticExpansion
)

if TYPE_CHECKING:
    from ..shell import Shell


class ExpansionEvaluator:
    """Evaluates expansion AST nodes by delegating to VariableExpander."""

    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager

    def evaluate(self, expansion: Expansion) -> str:
        """Evaluate any expansion type.

        Reconstructs the canonical string form and delegates to
        VariableExpander.expand_variable() or ExpansionManager
        methods, avoiding duplicated logic.

        Args:
            expansion: The expansion AST node to evaluate

        Returns:
            The expanded string value

        Raises:
            ValueError: If expansion type is unknown
        """
        if isinstance(expansion, VariableExpansion):
            return self._evaluate_variable(expansion)
        elif isinstance(expansion, CommandSubstitution):
            return self._evaluate_command_sub(expansion)
        elif isinstance(expansion, ParameterExpansion):
            return self._evaluate_parameter(expansion)
        elif isinstance(expansion, ArithmeticExpansion):
            return self._evaluate_arithmetic(expansion)
        else:
            raise ValueError(f"Unknown expansion type: {type(expansion)}")

    def _evaluate_variable(self, expansion: VariableExpansion) -> str:
        """Evaluate simple variable expansion by delegating to VariableExpander."""
        return self.expansion_manager.variable_expander.expand_variable(
            f"${expansion.name}"
        )

    def _evaluate_command_sub(self, expansion: CommandSubstitution) -> str:
        """Evaluate command substitution."""
        if expansion.backtick_style:
            cmd_sub = f"`{expansion.command}`"
        else:
            cmd_sub = f"$({expansion.command})"
        return self.expansion_manager.command_sub.execute(cmd_sub)

    def _evaluate_parameter(self, expansion: ParameterExpansion) -> str:
        """Evaluate parameter expansion by delegating to VariableExpander."""
        # Reconstruct the ${...} expression string
        expr = "${" + expansion.parameter
        if expansion.operator:
            expr += expansion.operator
            if expansion.word:
                expr += expansion.word
        expr += "}"
        return self.expansion_manager.variable_expander.expand_variable(expr)

    def _evaluate_arithmetic(self, expansion: ArithmeticExpansion) -> str:
        """Evaluate arithmetic expansion."""
        result = self.expansion_manager.execute_arithmetic_expansion(
            f"$(({expansion.expression}))"
        )
        return str(result)
