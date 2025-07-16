"""Warning system for semantic analysis."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WarningSeverity(Enum):
    """Severity levels for warnings."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class SemanticWarning:
    """Warning from semantic analysis."""
    message: str
    position: int
    severity: WarningSeverity = WarningSeverity.WARNING
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of warning."""
        base = f"{self.severity.value}: {self.message}"
        if self.suggestion:
            base += f" (suggestion: {self.suggestion})"
        return base


class CommonWarnings:
    """Common semantic warnings."""
    
    @staticmethod
    def unreachable_code(position: int) -> SemanticWarning:
        """Warning for unreachable code."""
        return SemanticWarning(
            "Unreachable code detected",
            position,
            WarningSeverity.WARNING,
            suggestion="Remove code after 'return' or 'exit'"
        )
    
    @staticmethod
    def unused_function(name: str, position: int) -> SemanticWarning:
        """Warning for unused function."""
        return SemanticWarning(
            f"Function '{name}' is defined but never used",
            position,
            WarningSeverity.INFO,
            suggestion=f"Remove function '{name}' or call it somewhere"
        )
    
    @staticmethod
    def shadowed_variable(name: str, position: int) -> SemanticWarning:
        """Warning for variable shadowing."""
        return SemanticWarning(
            f"Variable '{name}' shadows an outer scope variable",
            position,
            WarningSeverity.INFO,
            suggestion=f"Use a different name for variable '{name}'"
        )
    
    @staticmethod
    def empty_function_body(name: str, position: int) -> SemanticWarning:
        """Warning for empty function body."""
        return SemanticWarning(
            f"Function '{name}' has an empty body",
            position,
            WarningSeverity.WARNING,
            suggestion="Add commands to the function body or remove the function"
        )
    
    @staticmethod
    def readonly_assignment(name: str, position: int) -> SemanticWarning:
        """Warning for assignment to readonly variable."""
        return SemanticWarning(
            f"Assignment to readonly variable '{name}'",
            position,
            WarningSeverity.ERROR,
            suggestion=f"Remove readonly attribute from '{name}' or use a different variable"
        )
    
    @staticmethod
    def break_continue_outside_loop(statement: str, position: int) -> SemanticWarning:
        """Warning for break/continue outside loop."""
        return SemanticWarning(
            f"{statement}: only meaningful in a 'for', 'while', or 'until' loop",
            position,
            WarningSeverity.WARNING,
            suggestion=f"Remove '{statement}' or move it inside a loop"
        )
    
    @staticmethod
    def return_outside_function(position: int) -> SemanticWarning:
        """Warning for return outside function."""
        return SemanticWarning(
            "return: can only be used within a function",
            position,
            WarningSeverity.WARNING,
            suggestion="Remove 'return' or move it inside a function"
        )