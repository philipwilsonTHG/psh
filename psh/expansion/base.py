"""Base classes for expansion components."""
from abc import ABC, abstractmethod
from ..core.state import ShellState

class ExpansionComponent(ABC):
    """Base class for all expansion components."""
    
    def __init__(self, shell_state: ShellState):
        self.state = shell_state
    
    @abstractmethod
    def expand(self, value: str) -> str:
        """Expand the given value."""
        pass