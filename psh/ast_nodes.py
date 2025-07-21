from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union, TYPE_CHECKING
from abc import ABC
from enum import Enum

if TYPE_CHECKING:
    from .token_types import Token


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
    quote_type: Optional[str] = None  # Quote type used (' or " or None) for here strings
    heredoc_quoted: bool = False  # Whether heredoc delimiter was quoted (disables variable expansion)


@dataclass
class ProcessSubstitution(ASTNode):
    """Represents a process substitution <(...) or >(...)."""
    direction: str  # 'in' or 'out'
    command: str    # Command to execute
    
    def __str__(self):
        symbol = '<' if self.direction == 'in' else '>'
        return f"{symbol}({self.command})"


# =============================================================================
# EXPANSION NODES
# =============================================================================

class Expansion(ASTNode):
    """Base class for all types of expansions."""
    pass


@dataclass
class CommandSubstitution(Expansion):
    """Represents command substitution $(...) or `...`."""
    command: str  # The command to execute
    backtick_style: bool = False  # True for `...`, False for $(...)
    
    def __str__(self):
        if self.backtick_style:
            return f"`{self.command}`"
        else:
            return f"$({self.command})"


@dataclass
class ParameterExpansion(Expansion):
    """Represents parameter expansion ${...}."""
    parameter: str  # Variable name
    operator: Optional[str] = None  # :-, :=, :?, :+, #, ##, %, %%, /, // etc.
    word: Optional[str] = None  # The word part for operators like ${var:-word}
    
    def __str__(self):
        if self.operator and self.word is not None:
            return f"${{{self.parameter}{self.operator}{self.word}}}"
        elif self.operator:
            return f"${{{self.operator}{self.parameter}}}"
        else:
            return f"${{{self.parameter}}}"


@dataclass
class VariableExpansion(Expansion):
    """Represents simple variable expansion $var."""
    name: str  # Variable name without $
    
    def __str__(self):
        return f"${self.name}"


@dataclass
class ArithmeticExpansion(Expansion):
    """Represents arithmetic expansion $((...))."""
    expression: str  # The arithmetic expression
    
    def __str__(self):
        return f"$(({self.expression}))"


# =============================================================================
# WORD NODES (for representing mixed literal/expansion content)
# =============================================================================

@dataclass
class WordPart(ASTNode):
    """A part of a word - either literal text or an expansion."""
    pass


@dataclass
class LiteralPart(WordPart):
    """Literal text part of a word."""
    text: str
    
    def __str__(self):
        return self.text


@dataclass
class ExpansionPart(WordPart):
    """Expansion part of a word."""
    expansion: Expansion
    
    def __str__(self):
        return str(self.expansion)


@dataclass
class Word(ASTNode):
    """A word that may contain expansions.
    
    Examples:
    - "hello" -> [LiteralPart("hello")]
    - "$USER" -> [ExpansionPart(VariableExpansion("USER"))]
    - "Hello $USER!" -> [LiteralPart("Hello "), ExpansionPart(VariableExpansion("USER")), LiteralPart("!")]
    - "${HOME}/bin" -> [ExpansionPart(ParameterExpansion("HOME")), LiteralPart("/bin")]
    """
    parts: List[WordPart] = field(default_factory=list)
    quote_type: Optional[str] = None  # None (unquoted), '"' (double), "'" (single)
    
    def __str__(self):
        content = ''.join(str(part) for part in self.parts)
        if self.quote_type:
            return f"{self.quote_type}{content}{self.quote_type}"
        return content
    
    @classmethod
    def from_string(cls, text: str, quote_type: Optional[str] = None) -> 'Word':
        """Create a Word from a literal string."""
        return cls(parts=[LiteralPart(text)], quote_type=quote_type)


# =============================================================================
# ARRAY ASSIGNMENT NODES (defined early for use in SimpleCommand)
# =============================================================================

@dataclass
class ArrayAssignment(ASTNode):
    """Base class for array assignments."""
    pass


@dataclass
class ArrayInitialization(ArrayAssignment):
    """Array initialization: arr=(one two three) or arr+=(four five)"""
    name: str
    elements: List[str]  # The elements inside parentheses
    element_types: List[str] = field(default_factory=list)  # Track element types (WORD, STRING, etc.)
    element_quote_types: List[Optional[str]] = field(default_factory=list)  # Track quote types
    is_append: bool = False  # True for += initialization


@dataclass
class ArrayElementAssignment(ArrayAssignment):
    """Array element assignment: arr[0]=value or arr[0]+=value"""
    name: str
    index: Union[str, List['Token']]  # The index expression (str for compatibility, List[Token] for late binding)
    value: str  # The value to assign
    value_type: str = 'WORD'  # Type of the value
    value_quote_type: Optional[str] = None  # Quote type if any
    is_append: bool = False  # True for += assignment


class Command(ASTNode):
    """Base class for all executable commands."""
    pass


@dataclass
class SimpleCommand(Command):
    """Traditional command with arguments (formerly Command class)."""
    args: List[str] = field(default_factory=list)
    arg_types: List[str] = field(default_factory=list)  # Track if arg was quoted
    quote_types: List[Optional[str]] = field(default_factory=list)  # Track quote character used (' or " or None)
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False
    array_assignments: List[ArrayAssignment] = field(default_factory=list)  # Array assignments before command
    
    # New field for storing Word objects (optional for backward compatibility)
    words: Optional[List[Word]] = None  # If set, represents args as Word objects with expansions


class CompoundCommand(Command):
    """Base class for control structures usable in pipelines."""
    pass


@dataclass
class SubshellGroup(CompoundCommand):
    """Represents a subshell group (...) that executes in an isolated environment."""
    statements: 'CommandList'
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False


@dataclass
class BraceGroup(CompoundCommand):
    """Represents a brace group {...} that executes in the current shell environment.
    
    Unlike subshells, brace groups:
    - Execute in the current shell process (no fork)
    - Variable assignments persist to the parent environment
    - Directory changes (cd) affect the parent shell
    - Are more efficient (no subprocess overhead)
    
    POSIX syntax requirements:
    - Must have space after opening brace: { command
    - Must have semicolon or newline before closing brace: command; }
    """
    statements: 'CommandList'
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False


@dataclass
class Pipeline(ASTNode):
    commands: List[Command] = field(default_factory=list)  # Now accepts both SimpleCommand and CompoundCommand
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


# Deprecated Statement types removed - use unified types instead


@dataclass
class BreakStatement(Statement, CompoundCommand):
    """Break statement to exit loops."""
    level: int = 1  # Number of loops to break out of (default 1)
    redirects: List[Redirect] = field(default_factory=list)  # Required for Command interface
    background: bool = False  # Required for Command interface


@dataclass
class ContinueStatement(Statement, CompoundCommand):
    """Continue statement to skip to next iteration."""
    level: int = 1  # Number of loops to continue to (default 1)
    redirects: List[Redirect] = field(default_factory=list)  # Required for Command interface
    background: bool = False  # Required for Command interface


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


# Deprecated Statement types removed - use unified types instead


# Deprecated Command types removed - use unified types instead


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
    left_quote_type: Optional[str] = None  # Quote type for left operand
    right_quote_type: Optional[str] = None  # Quote type for right operand


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


# =============================================================================
# UNIFIED CONTROL STRUCTURE TYPES (Phase 3 Refactoring)
# =============================================================================
# These unified types can serve as both Statement and Command depending on
# their execution context. They will eventually replace the dual Statement/Command
# types above.

from enum import Enum

class ExecutionContext(Enum):
    """Execution context for control structures."""
    STATEMENT = "statement"  # Execute in current shell process
    PIPELINE = "pipeline"    # Execute in subshell for pipeline


class UnifiedControlStructure(Statement, CompoundCommand):
    """Base class for unified control structures."""
    pass


@dataclass
class WhileLoop(UnifiedControlStructure):
    """Unified while loop that can be both Statement and Command."""
    condition: StatementList  # The command list that determines continue/stop
    body: StatementList       # Commands to execute repeatedly while condition is true
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: ExecutionContext = ExecutionContext.STATEMENT
    background: bool = False  # Only used in pipeline context


@dataclass
class ForLoop(UnifiedControlStructure):
    """Unified for loop that can be both Statement and Command."""
    variable: str           # The loop variable name
    items: List[str]        # List of items to iterate over
    body: StatementList     # Commands to execute for each iteration
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: ExecutionContext = ExecutionContext.STATEMENT
    background: bool = False  # Only used in pipeline context
    item_quote_types: List[Optional[str]] = field(default_factory=list)  # Quote types for items


@dataclass
class CStyleForLoop(UnifiedControlStructure):
    """Unified C-style for loop."""
    body: StatementList = field(default_factory=lambda: StatementList())
    init_expr: Optional[str] = None
    condition_expr: Optional[str] = None
    update_expr: Optional[str] = None
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: ExecutionContext = ExecutionContext.STATEMENT
    background: bool = False


@dataclass
class IfConditional(UnifiedControlStructure):
    """Unified if/then/else conditional."""
    condition: StatementList
    then_part: StatementList
    elif_parts: List[Tuple[StatementList, StatementList]] = field(default_factory=list)
    else_part: Optional[StatementList] = None
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: ExecutionContext = ExecutionContext.STATEMENT
    background: bool = False


@dataclass
class CaseConditional(UnifiedControlStructure):
    """Unified case statement."""
    expr: str
    items: List[CaseItem] = field(default_factory=list)
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: ExecutionContext = ExecutionContext.STATEMENT
    background: bool = False


@dataclass
class SelectLoop(UnifiedControlStructure):
    """Unified select statement."""
    variable: str
    items: List[str]
    body: StatementList
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: ExecutionContext = ExecutionContext.STATEMENT
    background: bool = False
    item_quote_types: List[Optional[str]] = field(default_factory=list)  # Quote types for items


@dataclass
class ArithmeticEvaluation(UnifiedControlStructure):
    """Unified arithmetic command."""
    expression: str
    redirects: List[Redirect] = field(default_factory=list)
    execution_context: ExecutionContext = ExecutionContext.STATEMENT
    background: bool = False


# Deprecated types have been removed - use unified types directly