"""Base classes for interactive shell components."""
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING
from ..core.state import ShellState

if TYPE_CHECKING:
    from ..shell import Shell


class InteractiveComponent(ABC):
    """Base class for interactive shell components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.job_manager = shell.job_manager
        self.multi_line_handler = None  # Set by InteractiveManager
    
    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the interactive component functionality."""
        pass


class InteractiveManager:
    """Manages all interactive shell components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize interactive components
        from .history_manager import HistoryManager
        from .prompt_manager import PromptManager
        from .completion_manager import CompletionManager
        from .signal_manager import SignalManager
        from .repl_loop import REPLLoop
        
        self.history_manager = HistoryManager(shell)
        self.prompt_manager = PromptManager(shell)
        self.completion_manager = CompletionManager(shell)
        self.signal_manager = SignalManager(shell)
        self.repl_loop = REPLLoop(shell)
        
        # Cross-component dependencies
        self.repl_loop.history_manager = self.history_manager
        self.repl_loop.prompt_manager = self.prompt_manager
        self.repl_loop.completion_manager = self.completion_manager
        
        # Skip signal setup when running under pytest to avoid affecting subprocess tests
        import sys
        if 'pytest' not in sys.modules:
            # Ensure shell is in its own process group for job control
            self.signal_manager.ensure_foreground()
            
            # Set up signal handlers
            self.signal_manager.setup_signal_handlers()
    
    def run_interactive_loop(self):
        """Run the interactive shell loop."""
        return self.repl_loop.run()
    
    def setup_readline(self):
        """Configure readline for the shell."""
        self.completion_manager.setup_readline()
    
    def load_history(self):
        """Load command history from file."""
        self.history_manager.load_from_file()
    
    def save_history(self):
        """Save command history to file."""
        self.history_manager.save_to_file()