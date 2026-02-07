"""Semantic analyzer for PSH AST."""

from dataclasses import dataclass
from typing import List, Tuple

from ...ast_nodes import *
from ...visitor import ASTVisitor
from .symbol_table import SymbolTable
from .warnings import CommonWarnings, SemanticWarning, WarningSeverity


@dataclass
class SemanticError:
    """Error from semantic analysis."""
    message: str
    position: int
    severity: WarningSeverity = WarningSeverity.ERROR

    def __str__(self) -> str:
        """String representation of error."""
        return f"{self.severity.value}: {self.message}"


class SemanticAnalyzer(ASTVisitor[None]):
    """Perform semantic analysis on AST."""

    def __init__(self):
        super().__init__()
        self.errors: List[SemanticError] = []
        self.warnings: List[SemanticWarning] = []
        self.symbol_table = SymbolTable()

        # Track context for validation
        self._after_return = False
        self._after_exit = False

    def analyze(self, ast: ASTNode) -> Tuple[List[SemanticError], List[SemanticWarning]]:
        """Analyze AST and return errors/warnings."""
        self.errors.clear()
        self.warnings.clear()
        self.symbol_table = SymbolTable()
        self._after_return = False
        self._after_exit = False

        self.visit(ast)

        # Check for unused functions and variables
        self._check_unused_symbols()

        return self.errors, self.warnings

    def _add_error(self, message: str, position: int = 0):
        """Add semantic error."""
        self.errors.append(SemanticError(message, position, WarningSeverity.ERROR))

    def _add_warning(self, warning: SemanticWarning):
        """Add semantic warning."""
        self.warnings.append(warning)

    def _check_unused_symbols(self):
        """Check for unused functions and variables."""
        # Unused functions
        for func_info in self.symbol_table.get_unused_functions():
            self._add_warning(CommonWarnings.unused_function(
                func_info.definition.name,
                func_info.defined_at
            ))

        # Unused variables (skip this for now as it's very noisy in shell scripts)
        # for var_info in self.symbol_table.get_unused_variables():
        #     self._add_warning(CommonWarnings.unused_variable(
        #         var_info.name,
        #         var_info.defined_at
        #     ))

    def visit_TopLevel(self, node: TopLevel) -> None:
        """Visit top-level node."""
        # First pass: collect function definitions
        for item in node.items:
            if isinstance(item, FunctionDef):
                self.visit_FunctionDef(item)

        # Second pass: visit all other items
        for item in node.items:
            if not isinstance(item, FunctionDef):
                self.visit(item)

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """Validate function definition."""
        position = getattr(node, 'position', 0)

        # Check for duplicate function
        if self.symbol_table.has_function(node.name):
            self._add_error(f"Function '{node.name}' is already defined", position)
        else:
            self.symbol_table.add_function(node.name, node)

        # Check for empty function body
        if not node.body or (hasattr(node.body, 'statements') and not node.body.statements):
            self._add_warning(CommonWarnings.empty_function_body(node.name, position))

        # Enter function scope for body analysis
        self.symbol_table.enter_function()
        old_after_return = self._after_return
        self._after_return = False

        try:
            if node.body:
                self.visit(node.body)
        finally:
            self._after_return = old_after_return
            self.symbol_table.exit_function()

    def visit_BreakStatement(self, node: BreakStatement) -> None:
        """Validate break statement."""
        if not self.symbol_table.in_loop_context():
            position = getattr(node, 'position', 0)
            self._add_warning(CommonWarnings.break_continue_outside_loop("break", position))

    def visit_ContinueStatement(self, node: ContinueStatement) -> None:
        """Validate continue statement."""
        if not self.symbol_table.in_loop_context():
            position = getattr(node, 'position', 0)
            self._add_warning(CommonWarnings.break_continue_outside_loop("continue", position))

    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        """Validate simple command."""
        if not node.args:
            return

        command_name = None
        if node.args:
            command_name = node.args[0]

        # Check for return statement
        if command_name == "return":
            if not self.symbol_table.in_function_context():
                position = getattr(node, 'position', 0)
                self._add_warning(CommonWarnings.return_outside_function(position))
            self._after_return = True

        # Check for exit statement
        if command_name == "exit":
            self._after_exit = True

        # Check for function calls
        if command_name and self.symbol_table.has_function(command_name):
            self.symbol_table.use_function(command_name)

        # Check for variable assignments in array_assignments
        if hasattr(node, 'array_assignments') and node.array_assignments:
            for assignment in node.array_assignments:
                if hasattr(assignment, 'name'):
                    var_name = assignment.name
                    position = getattr(assignment, 'position', 0)

                    # Check if assigning to readonly variable
                    if self.symbol_table.is_variable_readonly(var_name):
                        self._add_warning(CommonWarnings.readonly_assignment(var_name, position))

                    # Add variable to symbol table
                    self.symbol_table.add_variable(var_name, position=position)

    def visit_WhileLoop(self, node: WhileLoop) -> None:
        """Validate while loop."""
        self.symbol_table.enter_loop()

        try:
            # Visit condition
            if node.condition:
                self.visit(node.condition)

            # Visit body
            if node.body:
                self.visit(node.body)
        finally:
            self.symbol_table.exit_loop()

    def visit_ForLoop(self, node: ForLoop) -> None:
        """Validate for loop."""
        self.symbol_table.enter_loop()

        try:
            # Add loop variable to scope
            if hasattr(node, 'variable') and node.variable:
                position = getattr(node, 'position', 0)
                self.symbol_table.add_variable(node.variable, position=position)

            # Visit values
            if hasattr(node, 'values') and node.values:
                for value in node.values:
                    self.visit(value)

            # Visit body
            if node.body:
                self.visit(node.body)
        finally:
            self.symbol_table.exit_loop()


    def visit_IfConditional(self, node: IfConditional) -> None:
        """Validate if conditional."""
        # Visit condition
        if node.condition:
            self.visit(node.condition)

        # Visit then branch
        old_after_return = self._after_return
        old_after_exit = self._after_exit

        if node.then_part:
            self._after_return = False
            self._after_exit = False
            self.visit(node.then_part)
            then_after_return = self._after_return
            then_after_exit = self._after_exit
        else:
            then_after_return = False
            then_after_exit = False

        # Visit else branch
        if node.else_part:
            self._after_return = False
            self._after_exit = False
            self.visit(node.else_part)
            else_after_return = self._after_return
            else_after_exit = self._after_exit
        else:
            else_after_return = False
            else_after_exit = False

        # We're after return/exit only if both branches are
        self._after_return = old_after_return or (then_after_return and else_after_return)
        self._after_exit = old_after_exit or (then_after_exit and else_after_exit)


    def visit_CommandList(self, node: CommandList) -> None:
        """Visit command list."""
        if hasattr(node, 'statements'):
            for stmt in node.statements:
                self.visit(stmt)

                # Check for unreachable code after return/exit
                if (self._after_return or self._after_exit) and stmt != node.statements[-1]:
                    # There are more statements after this one
                    next_stmt = node.statements[node.statements.index(stmt) + 1]
                    position = getattr(next_stmt, 'position', 0)
                    self._add_warning(CommonWarnings.unreachable_code(position))

    def visit_StatementList(self, node: StatementList) -> None:
        """Visit statement list."""
        if hasattr(node, 'statements'):
            for i, stmt in enumerate(node.statements):
                self.visit(stmt)

                # Check for unreachable code after return/exit
                if (self._after_return or self._after_exit) and i < len(node.statements) - 1:
                    # There are more statements after this one
                    next_stmt = node.statements[i + 1]
                    position = getattr(next_stmt, 'position', 0)
                    self._add_warning(CommonWarnings.unreachable_code(position))
                    break  # Only report the first unreachable statement

    def visit_AndOrList(self, node: AndOrList) -> None:
        """Visit AndOrList node."""
        # Visit the pipeline within AndOrList
        if hasattr(node, 'pipeline'):
            self.visit(node.pipeline)
        # AndOrList may have other attributes to visit
        self.generic_visit(node)

    def visit_Pipeline(self, node: Pipeline) -> None:
        """Visit pipeline."""
        if hasattr(node, 'commands'):
            for command in node.commands:
                self.visit(command)

    # Default visitor for unhandled nodes
    def generic_visit(self, node: ASTNode) -> None:
        """Visit all child nodes."""
        if hasattr(node, '__dict__'):
            for attr_name, attr_value in node.__dict__.items():
                if isinstance(attr_value, ASTNode):
                    self.visit(attr_value)
                elif isinstance(attr_value, list):
                    for item in attr_value:
                        if isinstance(item, ASTNode):
                            self.visit(item)
