"""Base classes for script handling components."""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, TYPE_CHECKING
from ..core.state import ShellState

if TYPE_CHECKING:
    from ..shell import Shell


class ScriptComponent(ABC):
    """Base class for script handling components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.executor_manager = shell.executor_manager
        self.expansion_manager = shell.expansion_manager
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> int:
        """Execute the script component functionality."""
        pass


class ScriptManager:
    """Manages all script handling components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize script components
        from .script_executor import ScriptExecutor
        from .script_validator import ScriptValidator
        from .shebang_handler import ShebangHandler
        from .source_processor import SourceProcessor
        
        self.script_executor = ScriptExecutor(shell)
        self.script_validator = ScriptValidator(shell)
        self.shebang_handler = ShebangHandler(shell)
        self.source_processor = SourceProcessor(shell)
    
    def run_script(self, script_path: str, script_args: List[str] = None) -> int:
        """Execute a script file with optional arguments."""
        return self.script_executor.run_script(script_path, script_args)
    
    def execute_from_source(self, input_source, add_to_history: bool = True) -> int:
        """Execute commands from an input source."""
        return self.source_processor.execute_from_source(input_source, add_to_history)