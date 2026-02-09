"""Validation rules for AST validation."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ...ast_nodes import *


class Severity(Enum):
    """Issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class Issue:
    """Validation issue."""
    message: str
    position: int
    severity: Severity
    suggestion: Optional[str] = None
    rule_name: str = ""

    def __str__(self) -> str:
        """String representation of issue."""
        base = f"{self.severity.value}: {self.message}"
        if self.suggestion:
            base += f" (suggestion: {self.suggestion})"
        if self.rule_name:
            base += f" [{self.rule_name}]"
        return base


@dataclass
class ValidationContext:
    """Context for validation rules."""
    loop_depth: int = 0
    function_depth: int = 0
    case_depth: int = 0
    in_arithmetic: bool = False
    in_test_expression: bool = False
    variables: Dict[str, Any] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = {}


class ValidationReport:
    """Report of validation results."""

    def __init__(self, issues: List[Issue] = None):
        self.issues = issues or []

    def add_issue(self, issue: Issue):
        """Add an issue to the report."""
        self.issues.append(issue)

    def add_issues(self, issues: List[Issue]):
        """Add multiple issues to the report."""
        self.issues.extend(issues)

    def add_errors(self, errors: List[Any]):
        """Add errors from semantic analyzer."""
        for error in errors:
            self.add_issue(Issue(
                message=str(error.message),
                position=error.position,
                severity=Severity.ERROR,
                rule_name="semantic"
            ))

    def add_warnings(self, warnings: List[Any]):
        """Add warnings from semantic analyzer."""
        for warning in warnings:
            severity = Severity.WARNING
            if hasattr(warning, 'severity'):
                if warning.severity.value == 'error':
                    severity = Severity.ERROR
                elif warning.severity.value == 'info':
                    severity = Severity.INFO

            self.add_issue(Issue(
                message=str(warning.message),
                position=warning.position,
                severity=severity,
                suggestion=getattr(warning, 'suggestion', None),
                rule_name="semantic"
            ))

    def get_errors(self) -> List[Issue]:
        """Get all error-level issues."""
        return [issue for issue in self.issues if issue.severity == Severity.ERROR]

    def get_warnings(self) -> List[Issue]:
        """Get all warning-level issues."""
        return [issue for issue in self.issues if issue.severity == Severity.WARNING]

    def get_info(self) -> List[Issue]:
        """Get all info-level issues."""
        return [issue for issue in self.issues if issue.severity == Severity.INFO]

    def has_errors(self) -> bool:
        """Check if report has any errors."""
        return len(self.get_errors()) > 0

    def __str__(self) -> str:
        """String representation of report."""
        if not self.issues:
            return "No validation issues found"

        lines = []
        for issue in sorted(self.issues, key=lambda i: (i.position, i.severity.value)):
            lines.append(str(issue))

        return "\n".join(lines)


class ValidationRule:
    """Base class for validation rules."""

    def __init__(self, name: str):
        self.name = name

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        """Validate node and return issues."""
        raise NotImplementedError


class NoEmptyBodyRule(ValidationRule):
    """Check for empty command bodies."""

    def __init__(self):
        super().__init__("no_empty_body")

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []
        position = getattr(node, 'position', 0)

        if isinstance(node, (WhileLoop, ForLoop)):
            if not node.body or (hasattr(node.body, 'statements') and not node.body.statements):
                issues.append(Issue(
                    f"Empty {type(node).__name__.lower()} body",
                    position,
                    Severity.WARNING,
                    "Add commands to the loop body or remove the loop",
                    self.name
                ))

        elif isinstance(node, IfConditional):
            if not node.then_part or (hasattr(node.then_part, 'statements') and not node.then_part.statements):
                issues.append(Issue(
                    "Empty 'then' clause in if statement",
                    position,
                    Severity.WARNING,
                    "Add commands to the 'then' clause",
                    self.name
                ))

        elif isinstance(node, CaseConditional):
            if not node.items:
                issues.append(Issue(
                    "Empty case statement",
                    position,
                    Severity.WARNING,
                    "Add case patterns or remove the case statement",
                    self.name
                ))

        return issues


class ValidRedirectRule(ValidationRule):
    """Validate redirections."""

    def __init__(self):
        super().__init__("valid_redirect")

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []

        if isinstance(node, Redirect):
            position = getattr(node, 'position', 0)

            # Check for invalid file descriptors
            if hasattr(node, 'fd') and node.fd is not None:
                if node.fd < 0 or node.fd > 9:
                    issues.append(Issue(
                        f"Invalid file descriptor: {node.fd}",
                        position,
                        Severity.ERROR,
                        "Use file descriptors 0-9",
                        self.name
                    ))

            # Check for missing target (skip fd-dup redirects and heredocs)
            if (not hasattr(node, 'target') or not node.target) and \
               not getattr(node, 'dup_fd', None) and \
               not (hasattr(node, 'type') and node.type and node.type.startswith('<<')):
                issues.append(Issue(
                    "Redirection missing target",
                    position,
                    Severity.ERROR,
                    "Specify a file or file descriptor for redirection",
                    self.name
                ))

        return issues


class CorrectBreakContinueRule(ValidationRule):
    """Validate break and continue statements."""

    def __init__(self):
        super().__init__("correct_break_continue")

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []
        position = getattr(node, 'position', 0)

        if isinstance(node, BreakStatement):
            if context.loop_depth == 0:
                issues.append(Issue(
                    "break: only meaningful in a 'for', 'while', or 'until' loop",
                    position,
                    Severity.ERROR,
                    "Remove 'break' or move it inside a loop",
                    self.name
                ))

        elif isinstance(node, ContinueStatement):
            if context.loop_depth == 0:
                issues.append(Issue(
                    "continue: only meaningful in a 'for', 'while', or 'until' loop",
                    position,
                    Severity.ERROR,
                    "Remove 'continue' or move it inside a loop",
                    self.name
                ))

        return issues


class FunctionNameRule(ValidationRule):
    """Validate function names."""

    def __init__(self):
        super().__init__("function_name")
        # Shell keywords that shouldn't be used as function names
        self.shell_keywords = {
            'if', 'then', 'else', 'elif', 'fi', 'case', 'esac',
            'for', 'while', 'until', 'do', 'done', 'function',
            'select', 'time', 'coproc', '{', '}', '[[', ']]'
        }

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []

        if isinstance(node, FunctionDef):
            position = getattr(node, 'position', 0)
            name = node.name

            # Check for reserved keywords
            if name in self.shell_keywords:
                issues.append(Issue(
                    f"Function name '{name}' conflicts with shell keyword",
                    position,
                    Severity.ERROR,
                    f"Use a different name for function '{name}'",
                    self.name
                ))

            # Check for invalid characters
            if not name.replace('_', '').replace('-', '').isalnum():
                issues.append(Issue(
                    f"Function name '{name}' contains invalid characters",
                    position,
                    Severity.ERROR,
                    "Use only alphanumeric characters, underscores, and hyphens",
                    self.name
                ))

            # Check for starting with number
            if name and name[0].isdigit():
                issues.append(Issue(
                    f"Function name '{name}' cannot start with a number",
                    position,
                    Severity.ERROR,
                    "Start function name with a letter or underscore",
                    self.name
                ))

        return issues


class ValidArithmeticRule(ValidationRule):
    """Validate arithmetic expressions."""

    def __init__(self):
        super().__init__("valid_arithmetic")

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []

        if isinstance(node, ArithmeticEvaluation):
            position = getattr(node, 'position', 0)

            # Check for empty arithmetic expression
            if not hasattr(node, 'expression') or not node.expression:
                issues.append(Issue(
                    "Empty arithmetic expression",
                    position,
                    Severity.WARNING,
                    "Add an arithmetic expression or remove $((...))",
                    self.name
                ))

        return issues


class ValidTestExpressionRule(ValidationRule):
    """Validate test expressions."""

    def __init__(self):
        super().__init__("valid_test_expression")

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []

        if isinstance(node, TestExpression):
            position = getattr(node, 'position', 0)

            # Check for empty test expression
            if not hasattr(node, 'expression') or not node.expression:
                issues.append(Issue(
                    "Empty test expression",
                    position,
                    Severity.WARNING,
                    "Add a test condition or remove [[ ]]",
                    self.name
                ))

        return issues


class ValidVariableNameRule(ValidationRule):
    """Validate variable names in assignments."""

    def __init__(self):
        super().__init__("valid_variable_name")

    def validate(self, node: ASTNode, context: ValidationContext) -> List[Issue]:
        issues = []

        # Check SimpleCommand for array assignments
        if isinstance(node, SimpleCommand) and hasattr(node, 'array_assignments'):
            for assignment in node.array_assignments or []:
                if hasattr(assignment, 'name'):
                    position = getattr(node, 'position', 0)
                    name = assignment.name

                    if name:
                        # Check for invalid variable name
                        if not (name[0].isalpha() or name[0] == '_') or not name.replace('_', '').isalnum():
                            issues.append(Issue(
                                f"Invalid variable name '{name}'",
                                position,
                                Severity.ERROR,
                                "Variable names must start with letter/underscore and contain only alphanumeric characters",
                                self.name
                            ))

                        # Check for starting with number
                        if name and name[0].isdigit():
                            issues.append(Issue(
                                f"Variable name '{name}' cannot start with a number",
                                position,
                                Severity.ERROR,
                                "Start variable name with a letter or underscore",
                                self.name
                            ))

        return issues
