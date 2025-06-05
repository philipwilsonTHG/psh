from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union
from abc import ABC


class ASTNode(ABC):
    pass


class Statement(ASTNode):
    """Base class for all statements that can appear in StatementList."""
    pass


@dataclass
class Redirect(ASTNode):
    type: str  # '<', '>', '>>', '<<', '<<-', '2>', '2>>', '2>&1', etc.
    target: str
    fd: Optional[int] = None  # File descriptor (None for stdin/stdout, 2 for stderr, etc.)
    dup_fd: Optional[int] = None  # For duplications like 2>&1
    heredoc_content: Optional[str] = None  # For here documents


@dataclass
class ProcessSubstitution(ASTNode):
    """Represents a process substitution <(...) or >(...)."""
    direction: str  # 'in' or 'out'
    command: str    # Command to execute
    
    def __str__(self):
        symbol = '<' if self.direction == 'in' else '>'
        return f"{symbol}({self.command})"


@dataclass
class Command(ASTNode):
    args: List[str] = field(default_factory=list)
    arg_types: List[str] = field(default_factory=list)  # Track if arg was quoted
    quote_types: List[Optional[str]] = field(default_factory=list)  # Track quote character used (' or " or None)
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False


@dataclass
class Pipeline(ASTNode):
    commands: List[Command] = field(default_factory=list)
    negated: bool = False  # True if pipeline is prefixed with !


@dataclass
class AndOrList(Statement):
    pipelines: List[Pipeline] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)  # '&&' or '||' between pipelines


@dataclass
class StatementList(ASTNode):
    """Container for statements (control structures, AndOrLists, etc)."""
    statements: List[Statement] = field(default_factory=list)
    
    # Backward compatibility properties
    @property
    def and_or_lists(self):
        """Backward compatibility: extract AndOrLists from statements."""
        return [s for s in self.statements if isinstance(s, AndOrList)]
    
    @property
    def pipelines(self):
        """Backward compatibility property for tests"""
        # Flatten all pipelines from all and_or_lists (skip control statements)
        pipelines = []
        for item in self.statements:
            if hasattr(item, 'pipelines'):  # It's an AndOrList
                pipelines.extend(item.pipelines)
        return pipelines


# Keep CommandList as an alias for backward compatibility
CommandList = StatementList


@dataclass
class FunctionDef(Statement):
    """Function definition."""
    name: str
    body: StatementList


@dataclass
class IfStatement(Statement):
    """If/then/else/fi conditional statement."""
    condition: StatementList  # The command list that determines truth/false
    then_part: StatementList  # Commands to execute if condition is true
    elif_parts: List[Tuple[StatementList, StatementList]] = field(default_factory=list)  # List of (condition, then_part) tuples
    else_part: Optional[StatementList] = None  # Commands to execute if all conditions are false
    redirects: List[Redirect] = field(default_factory=list)  # Redirections for the entire if statement


@dataclass
class WhileStatement(Statement):
    """While/do/done loop statement."""
    condition: StatementList  # The command list that determines continue/stop
    body: StatementList       # Commands to execute repeatedly while condition is true
    redirects: List[Redirect] = field(default_factory=list)  # Redirections for the entire while loop


@dataclass
class ForStatement(Statement):
    """For/in/do/done loop statement."""
    variable: str           # The loop variable name (e.g., "i", "file")
    iterable: List[str]     # List of items to iterate over (after expansion)
    body: StatementList       # Commands to execute for each iteration
    redirects: List[Redirect] = field(default_factory=list)  # Redirections for the entire for loop


@dataclass
class CStyleForStatement(Statement):
    """C-style for loop: for ((init; condition; update))"""
    init_expr: Optional[str] = None      # Initialization expression (can be empty)
    condition_expr: Optional[str] = None # Condition expression (can be empty)  
    update_expr: Optional[str] = None    # Update expression (can be empty)
    body: StatementList = field(default_factory=lambda: StatementList())  # Loop body
    redirects: List[Redirect] = field(default_factory=list)  # Redirections for the entire loop


@dataclass
class BreakStatement(Statement):
    """Break statement to exit loops."""
    level: int = 1  # Number of loops to break out of (default 1)


@dataclass
class ContinueStatement(Statement):
    """Continue statement to skip to next iteration."""
    level: int = 1  # Number of loops to continue to (default 1)


@dataclass
class CasePattern(ASTNode):
    """A single pattern in a case statement."""
    pattern: str


@dataclass
class CaseItem(ASTNode):
    """A case item: patterns + commands + terminator."""
    patterns: List[CasePattern] = field(default_factory=list)
    commands: StatementList = field(default_factory=lambda: StatementList())
    terminator: str = ';;'  # ';;', ';&', or ';;&'


@dataclass
class CaseStatement(Statement):
    """Case/esac statement."""
    expr: str  # The expression to match against
    items: List[CaseItem] = field(default_factory=list)
    redirects: List[Redirect] = field(default_factory=list)  # Redirections for the entire case statement


@dataclass
class ArithmeticCommand(Statement):
    """Arithmetic command ((expression))."""
    expression: str
    redirects: List[Redirect] = field(default_factory=list)


@dataclass
class TopLevel(ASTNode):
    """Root node that can contain functions and/or commands."""
    items: List[Union[Statement, StatementList]] = field(default_factory=list)  # List of Statement or StatementList


# Enhanced test expressions for [[ ]]
class TestExpression(ASTNode):
    """Base class for test expressions."""
    pass


@dataclass
class BinaryTestExpression(TestExpression):
    """Binary test expression like STRING1 < STRING2."""
    left: str
    operator: str  # =, !=, <, >, =~, -eq, -ne, etc.
    right: str


@dataclass
class UnaryTestExpression(TestExpression):
    """Unary test expression like -f FILE."""
    operator: str  # -f, -d, -z, -n, etc.
    operand: str


@dataclass
class CompoundTestExpression(TestExpression):
    """Compound test expression with && or ||."""
    left: TestExpression
    operator: str  # && or ||
    right: TestExpression


@dataclass
class NegatedTestExpression(TestExpression):
    """Negated test expression with !."""
    expression: TestExpression


@dataclass
class EnhancedTestStatement(Statement):
    """Enhanced test construct [[ ... ]]."""
    expression: TestExpression  # The test expression to evaluate
    redirects: List[Redirect] = field(default_factory=list)