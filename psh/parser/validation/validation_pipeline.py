"""Validation pipeline for orchestrating AST validation."""

from typing import List, Dict, Any, Set
from ...ast_nodes import *
from ...visitor import ASTVisitor
from .validation_rules import (
    ValidationRule, ValidationReport, ValidationContext, Issue, Severity,
    NoEmptyBodyRule, ValidRedirectRule, CorrectBreakContinueRule,
    FunctionNameRule, ValidArithmeticRule, ValidTestExpressionRule,
    ValidVariableNameRule
)


class ValidationPipeline(ASTVisitor[None]):
    """Pipeline of validation rules."""
    
    def __init__(self, custom_rules: List[ValidationRule] = None):
        super().__init__()
        self.rules: List[ValidationRule] = []
        self.context = ValidationContext()
        self.report = ValidationReport()
        
        # Load default rules
        self._load_default_rules()
        
        # Add any custom rules
        if custom_rules:
            self.rules.extend(custom_rules)
    
    def _load_default_rules(self):
        """Load default validation rules."""
        self.rules.extend([
            NoEmptyBodyRule(),
            ValidRedirectRule(),
            CorrectBreakContinueRule(),
            FunctionNameRule(),
            ValidArithmeticRule(),
            ValidTestExpressionRule(),
            ValidVariableNameRule(),
        ])
    
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule to the pipeline."""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove a validation rule by name."""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
    
    def validate(self, ast: ASTNode) -> ValidationReport:
        """Run all validation rules on AST."""
        # Reset state
        self.context = ValidationContext()
        self.report = ValidationReport()
        
        # Visit the AST to collect context and validate nodes
        self.visit(ast)
        
        return self.report
    
    def _validate_node(self, node: ASTNode):
        """Run all validation rules on a single node."""
        for rule in self.rules:
            try:
                issues = rule.validate(node, self.context)
                self.report.add_issues(issues)
            except Exception as e:
                # If a rule fails, add an issue about the rule failure
                self.report.add_issue(Issue(
                    f"Validation rule '{rule.name}' failed: {str(e)}",
                    getattr(node, 'position', 0),
                    Severity.WARNING,
                    f"Check rule implementation for '{rule.name}'",
                    "pipeline"
                ))
    
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """Visit function definition."""
        self.context.function_depth += 1
        self._validate_node(node)
        
        # Visit body
        if node.body:
            self.visit(node.body)
        
        self.context.function_depth -= 1
    
    def visit_WhileLoop(self, node: WhileLoop) -> None:
        """Visit while loop."""
        self.context.loop_depth += 1
        self._validate_node(node)
        
        # Visit condition and body
        if node.condition:
            self.visit(node.condition)
        if node.body:
            self.visit(node.body)
        
        self.context.loop_depth -= 1
    
    def visit_ForLoop(self, node: ForLoop) -> None:
        """Visit for loop."""
        self.context.loop_depth += 1
        self._validate_node(node)
        
        # Visit values and body
        if hasattr(node, 'values') and node.values:
            for value in node.values:
                self.visit(value)
        if node.body:
            self.visit(node.body)
        
        self.context.loop_depth -= 1
    
    
    def visit_CaseConditional(self, node: CaseConditional) -> None:
        """Visit case conditional."""
        self.context.case_depth += 1
        self._validate_node(node)
        
        # Visit word and cases
        if hasattr(node, 'word') and node.word:
            self.visit(node.word)
        if hasattr(node, 'cases') and node.cases:
            for case in node.cases:
                self.visit(case)
        
        self.context.case_depth -= 1
    
    def visit_IfConditional(self, node: IfConditional) -> None:
        """Visit if conditional."""
        self._validate_node(node)
        
        # Visit condition, then_part, and else_part
        if node.condition:
            self.visit(node.condition)
        if node.then_part:
            self.visit(node.then_part)
        if node.else_part:
            self.visit(node.else_part)
    
    def visit_ArithmeticEvaluation(self, node: ArithmeticEvaluation) -> None:
        """Visit arithmetic evaluation."""
        old_in_arithmetic = self.context.in_arithmetic
        self.context.in_arithmetic = True
        
        self._validate_node(node)
        
        # Visit expression
        if hasattr(node, 'expression') and node.expression:
            self.visit(node.expression)
        
        self.context.in_arithmetic = old_in_arithmetic
    
    def visit_TestExpression(self, node: TestExpression) -> None:
        """Visit test expression."""
        old_in_test = self.context.in_test_expression
        self.context.in_test_expression = True
        
        self._validate_node(node)
        
        # Visit expression
        if hasattr(node, 'expression') and node.expression:
            self.visit(node.expression)
        
        self.context.in_test_expression = old_in_test
    
    
    def visit_BreakStatement(self, node: BreakStatement) -> None:
        """Visit break statement."""
        self._validate_node(node)
    
    def visit_ContinueStatement(self, node: ContinueStatement) -> None:
        """Visit continue statement."""
        self._validate_node(node)
    
    
    def visit_Redirect(self, node: Redirect) -> None:
        """Visit redirection."""
        self._validate_node(node)
        
        # Visit target
        if hasattr(node, 'target') and node.target:
            self.visit(node.target)
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        """Visit simple command."""
        self._validate_node(node)
        
        # Visit array assignments
        if hasattr(node, 'array_assignments') and node.array_assignments:
            for assignment in node.array_assignments:
                self.visit(assignment)
        
        # Visit redirects
        if hasattr(node, 'redirects') and node.redirects:
            for redirect in node.redirects:
                self.visit(redirect)
    
    def visit_Pipeline(self, node: Pipeline) -> None:
        """Visit pipeline."""
        self._validate_node(node)
        
        # Visit commands
        if hasattr(node, 'commands') and node.commands:
            for command in node.commands:
                self.visit(command)
    
    def visit_CommandList(self, node: CommandList) -> None:
        """Visit command list."""
        self._validate_node(node)
        
        # Visit statements
        if hasattr(node, 'statements') and node.statements:
            for stmt in node.statements:
                self.visit(stmt)
    
    def visit_TopLevel(self, node: TopLevel) -> None:
        """Visit top-level node."""
        self._validate_node(node)
        
        # Visit items
        if hasattr(node, 'items') and node.items:
            for item in node.items:
                self.visit(item)
    
    # Default visitor for unhandled nodes
    def generic_visit(self, node: ASTNode) -> None:
        """Default visitor that validates node and visits children."""
        self._validate_node(node)
        
        # Visit all child nodes
        if hasattr(node, '__dict__'):
            for attr_name, attr_value in node.__dict__.items():
                if isinstance(attr_value, ASTNode):
                    self.visit(attr_value)
                elif isinstance(attr_value, list):
                    for item in attr_value:
                        if isinstance(item, ASTNode):
                            self.visit(item)


class ConfigurableValidationPipeline(ValidationPipeline):
    """Validation pipeline with configurable rule sets."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Don't load default rules yet
        super().__init__(custom_rules=[])
        
        # Load rules based on configuration
        self._load_configured_rules()
    
    def _load_configured_rules(self):
        """Load rules based on configuration."""
        # Default rules that are always enabled
        always_enabled = [
            ValidRedirectRule(),
            CorrectBreakContinueRule(),
            ValidVariableNameRule(),
        ]
        self.rules.extend(always_enabled)
        
        # Optional rules based on configuration
        if self.config.get('check_empty_bodies', True):
            self.rules.append(NoEmptyBodyRule())
        
        if self.config.get('check_function_names', True):
            self.rules.append(FunctionNameRule())
        
        if self.config.get('check_arithmetic', True):
            self.rules.append(ValidArithmeticRule())
        
        if self.config.get('check_test_expressions', True):
            self.rules.append(ValidTestExpressionRule())
    
    def enable_rule(self, rule_name: str):
        """Enable a rule by name."""
        # Remove if already present
        self.remove_rule(rule_name)
        
        # Add the rule
        rule_map = {
            'no_empty_body': NoEmptyBodyRule(),
            'function_name': FunctionNameRule(),
            'valid_arithmetic': ValidArithmeticRule(),
            'valid_test_expression': ValidTestExpressionRule(),
        }
        
        if rule_name in rule_map:
            self.rules.append(rule_map[rule_name])
    
    def disable_rule(self, rule_name: str):
        """Disable a rule by name."""
        self.remove_rule(rule_name)
    
    def get_enabled_rules(self) -> List[str]:
        """Get list of enabled rule names."""
        return [rule.name for rule in self.rules]