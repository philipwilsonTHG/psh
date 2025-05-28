from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from abc import ABC


class ASTNode(ABC):
    pass


@dataclass
class Redirect(ASTNode):
    type: str  # '<', '>', '>>', '<<', '<<-', '2>', '2>>', '2>&1', etc.
    target: str
    fd: Optional[int] = None  # File descriptor (None for stdin/stdout, 2 for stderr, etc.)
    dup_fd: Optional[int] = None  # For duplications like 2>&1
    heredoc_content: Optional[str] = None  # For here documents


@dataclass
class Command(ASTNode):
    args: List[str] = field(default_factory=list)
    arg_types: List[str] = field(default_factory=list)  # Track if arg was quoted
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False


@dataclass
class Pipeline(ASTNode):
    commands: List[Command] = field(default_factory=list)


@dataclass
class AndOrList(ASTNode):
    pipelines: List[Pipeline] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)  # '&&' or '||' between pipelines


@dataclass
class CommandList(ASTNode):
    and_or_lists: List[AndOrList] = field(default_factory=list)
    
    @property
    def pipelines(self):
        """Backward compatibility property for tests"""
        # Flatten all pipelines from all and_or_lists
        pipelines = []
        for and_or_list in self.and_or_lists:
            pipelines.extend(and_or_list.pipelines)
        return pipelines


@dataclass
class FunctionDef(ASTNode):
    """Function definition."""
    name: str
    body: CommandList


@dataclass
class IfStatement(ASTNode):
    """If/then/else/fi conditional statement."""
    condition: CommandList  # The command list that determines truth/false
    then_part: CommandList  # Commands to execute if condition is true
    else_part: Optional[CommandList] = None  # Commands to execute if condition is false


@dataclass
class WhileStatement(ASTNode):
    """While/do/done loop statement."""
    condition: CommandList  # The command list that determines continue/stop
    body: CommandList       # Commands to execute repeatedly while condition is true


@dataclass
class ForStatement(ASTNode):
    """For/in/do/done loop statement."""
    variable: str           # The loop variable name (e.g., "i", "file")
    iterable: List[str]     # List of items to iterate over (after expansion)
    body: CommandList       # Commands to execute for each iteration


@dataclass
class TopLevel(ASTNode):
    """Root node that can contain functions and/or commands."""
    items: List[ASTNode] = field(default_factory=list)  # List of FunctionDef or CommandList