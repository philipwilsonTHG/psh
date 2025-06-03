"""Read-Eval-Print Loop implementation."""
import sys
import signal
from .base import InteractiveComponent
from ..line_editor import LineEditor
from ..multiline_handler import MultiLineInputHandler


class REPLLoop(InteractiveComponent):
    """Implements the interactive shell loop."""
    
    def __init__(self, shell):
        super().__init__(shell)
        self.history_manager = None
        self.prompt_manager = None
        self.completion_manager = None
        self.line_editor = None
        self.multi_line_handler = None
    
    def execute(self):
        """Run the interactive loop."""
        return self.run()
    
    def setup(self):
        """Set up the REPL environment."""
        # Set up readline and tab completion
        self.completion_manager.setup_readline()
        
        # Set up line editor with current edit mode
        self.line_editor = LineEditor(
            self.state.history, 
            edit_mode=self.state.edit_mode
        )
        
        # Set up multi-line input handler
        self.multi_line_handler = MultiLineInputHandler(
            self.line_editor, 
            self.shell
        )
    
    def run(self):
        """Run the main interactive loop."""
        self.setup()
        
        while True:
            try:
                # Check for completed background jobs
                self.job_manager.notify_completed_jobs()
                
                # Check for stopped jobs (from Ctrl-Z)
                self.job_manager.notify_stopped_jobs()
                
                # Read command (possibly multi-line)
                command = self.multi_line_handler.read_command()
                
                if command is None:  # EOF (Ctrl-D)
                    print()  # New line before exit
                    break
                
                if command.strip():
                    self.shell.run_command(command)
                    
            except KeyboardInterrupt:
                # Ctrl-C pressed, cancel multi-line input and continue
                self.multi_line_handler.reset()
                print("^C")
                self.state.last_exit_code = 130  # 128 + SIGINT(2)
                continue
            except EOFError:
                # Ctrl-D pressed
                print()
                break
            except Exception as e:
                print(f"psh: {e}", file=sys.stderr)
                self.state.last_exit_code = 1
        
        # Save history on exit
        self.history_manager.save_to_file()