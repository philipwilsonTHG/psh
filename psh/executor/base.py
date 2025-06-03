"""Base classes for executor components."""
from abc import ABC, abstractmethod
from ..core.state import ShellState

class ExecutorComponent(ABC):
    """Base class for all executor components."""
    
    def __init__(self, shell_state: ShellState):
        self.state = shell_state
    
    @abstractmethod
    def execute(self, node):
        """Execute the given AST node."""
        pass