from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from abc import ABC


class ASTNode(ABC):
    pass


@dataclass
class Redirect(ASTNode):
    type: str  # '<', '>', '>>'
    target: str


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
class CommandList(ASTNode):
    pipelines: List[Pipeline] = field(default_factory=list)