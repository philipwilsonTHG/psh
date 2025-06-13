# Phase 6 Implementation Guide: Interactive Features

## Overview
Phase 6 focuses on extracting interactive shell features from shell.py into dedicated components. This includes line editing, command history, tab completion, prompt handling, and the interactive loop itself.

## Current State Analysis

### Interactive-Related Methods in shell.py
- `interactive_loop()` - Main REPL loop
- `_load_history()` - Load command history from file
- `_save_history()` - Save command history to file
- `_add_to_history()` - Add command to history
- `_format_prompt()` - Format PS1/PS2 prompts (if exists)
- Signal handlers (`_handle_sigint`, `_handle_sigchld`)

### Related Components
- `line_editor.py` - Line editing functionality
- `multiline_handler.py` - Multi-line command handling
- `prompt.py` - Prompt expansion
- `tab_completion.py` - Tab completion
- `keybindings.py` - Vi/Emacs keybindings

### History Management
- History file: `~/.psh_history`
- In-memory history list
- Max history size management
- Readline integration

## Step 1: Create Interactive Infrastructure

### Create `psh/interactive/base.py`:
```python
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
        from .repl_loop import REPLLoop
        
        self.history_manager = HistoryManager(shell)
        self.prompt_manager = PromptManager(shell)
        self.completion_manager = CompletionManager(shell)
        self.repl_loop = REPLLoop(shell)
        
        # Cross-component dependencies
        self.repl_loop.history_manager = self.history_manager
        self.repl_loop.prompt_manager = self.prompt_manager
        self.repl_loop.completion_manager = self.completion_manager
    
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
```

## Step 2: Extract History Management

### Create `psh/interactive/history_manager.py`:
```python
"""Command history management."""
import os
import readline
from typing import List
from .base import InteractiveComponent


class HistoryManager(InteractiveComponent):
    """Manages command history."""
    
    def execute(self, command: str = None, action: str = "add") -> None:
        """Execute history operations."""
        if action == "add" and command:
            self.add_to_history(command)
        elif action == "load":
            self.load_from_file()
        elif action == "save":
            self.save_to_file()
    
    def add_to_history(self, command: str) -> None:
        """Add a command to history."""
        # Don't add duplicates of the immediately previous command
        if not self.state.history or self.state.history[-1] != command:
            self.state.history.append(command)
            readline.add_history(command)
            # Trim history if it exceeds max size
            if len(self.state.history) > self.state.max_history_size:
                self.state.history = self.state.history[-self.state.max_history_size:]
    
    def load_from_file(self) -> None:
        """Load command history from file."""
        try:
            if os.path.exists(self.state.history_file):
                with open(self.state.history_file, 'r') as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if line:
                            self.state.history.append(line)
                            readline.add_history(line)
                # Trim to max size
                if len(self.state.history) > self.state.max_history_size:
                    self.state.history = self.state.history[-self.state.max_history_size:]
        except Exception:
            # Silently ignore history file errors
            pass
    
    def save_to_file(self) -> None:
        """Save command history to file."""
        try:
            with open(self.state.history_file, 'w') as f:
                # Save only the last max_history_size commands
                for cmd in self.state.history[-self.state.max_history_size:]:
                    f.write(cmd + '\n')
        except Exception:
            # Silently ignore history file errors
            pass
    
    def get_history(self) -> List[str]:
        """Get the command history."""
        return self.state.history.copy()
    
    def clear_history(self) -> None:
        """Clear command history."""
        self.state.history.clear()
        readline.clear_history()
```

## Step 3: Extract Prompt Management

### Create `psh/interactive/prompt_manager.py`:
```python
"""Prompt formatting and management."""
import os
import sys
from datetime import datetime
from .base import InteractiveComponent
from ..prompt import expand_prompt


class PromptManager(InteractiveComponent):
    """Manages shell prompts (PS1, PS2)."""
    
    def execute(self, prompt_type: str = "PS1") -> str:
        """Get formatted prompt."""
        if prompt_type == "PS1":
            return self.get_primary_prompt()
        elif prompt_type == "PS2":
            return self.get_continuation_prompt()
        return ""
    
    def get_primary_prompt(self) -> str:
        """Get the primary prompt (PS1)."""
        ps1 = self.state.variables.get('PS1', r'\u@\h:\w\$ ')
        return self.expand_prompt(ps1)
    
    def get_continuation_prompt(self) -> str:
        """Get the continuation prompt (PS2)."""
        ps2 = self.state.variables.get('PS2', '> ')
        return self.expand_prompt(ps2)
    
    def expand_prompt(self, prompt_string: str) -> str:
        """Expand prompt escape sequences."""
        # Use the existing prompt expansion function
        return expand_prompt(prompt_string, self.shell)
    
    def set_prompt(self, prompt_type: str, value: str) -> None:
        """Set a prompt value."""
        if prompt_type in ("PS1", "PS2"):
            self.state.variables[prompt_type] = value
```

## Step 4: Extract Tab Completion Management

### Create `psh/interactive/completion_manager.py`:
```python
"""Tab completion management."""
import readline
from typing import List, Optional
from .base import InteractiveComponent
from ..tab_completion import TabCompleter


class CompletionManager(InteractiveComponent):
    """Manages tab completion."""
    
    def __init__(self, shell):
        super().__init__(shell)
        self.tab_completer = None
    
    def execute(self, text: str, state: int) -> Optional[str]:
        """Execute tab completion."""
        if self.tab_completer:
            return self.tab_completer.complete(text, state)
        return None
    
    def setup_readline(self) -> None:
        """Configure readline for tab completion."""
        # Set up readline for better line editing
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims(' \t\n;|&<>')
        
        # Create and configure tab completer
        self.tab_completer = TabCompleter(self.shell)
        readline.set_completer(self.tab_completer.complete)
    
    def get_completions(self, text: str) -> List[str]:
        """Get all possible completions for text."""
        if self.tab_completer:
            # Collect all completions
            completions = []
            state = 0
            while True:
                comp = self.tab_completer.complete(text, state)
                if comp is None:
                    break
                completions.append(comp)
                state += 1
            return completions
        return []
```

## Step 5: Extract REPL Loop

### Create `psh/interactive/repl_loop.py`:
```python
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
```

## Step 6: Extract Signal Handlers

### Create `psh/interactive/signal_manager.py`:
```python
"""Signal handling for interactive shell."""
import os
import signal
from .base import InteractiveComponent
from ..job_control import JobState


class SignalManager(InteractiveComponent):
    """Manages signal handlers for interactive mode."""
    
    def execute(self, action: str = "setup"):
        """Execute signal management actions."""
        if action == "setup":
            self.setup_signal_handlers()
        elif action == "restore":
            self.restore_default_handlers()
    
    def setup_signal_handlers(self):
        """Set up signal handlers based on shell mode."""
        if self.state.is_script_mode:
            # Script mode: simpler signal handling
            signal.signal(signal.SIGINT, signal.SIG_DFL)  # Default SIGINT behavior
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)  # Default SIGTSTP behavior
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)  # Still ignore terminal output stops
            signal.signal(signal.SIGTTIN, signal.SIG_IGN)  # Still ignore terminal input stops
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)  # Default child handling
        else:
            # Interactive mode: full signal handling
            signal.signal(signal.SIGINT, self._handle_sigint)
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)  # Shell ignores SIGTSTP
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)  # Ignore terminal output stops
            signal.signal(signal.SIGTTIN, signal.SIG_IGN)  # Ignore terminal input stops
            signal.signal(signal.SIGCHLD, self._handle_sigchld)  # Track child status
    
    def restore_default_handlers(self):
        """Restore default signal handlers."""
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        signal.signal(signal.SIGTTOU, signal.SIG_DFL)
        signal.signal(signal.SIGTTIN, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    
    def _handle_sigint(self, signum, frame):
        """Handle Ctrl-C (SIGINT)"""
        # Just print a newline - the command loop will handle the rest
        print()
        # The signal will be delivered to the foreground process group
        # which is set in execute_pipeline
    
    def _handle_sigchld(self, signum, frame):
        """Handle child process state changes."""
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                
                job = self.job_manager.get_job_by_pid(pid)
                if job:
                    job.update_process_status(pid, status)
                    job.update_state()
                    
                    # Check if entire job is stopped
                    if job.state == JobState.STOPPED and job.foreground:
                        # Stopped foreground job - mark as not notified so it will be shown
                        job.notified = False
                        
                        # Return control to shell
                        try:
                            os.tcsetpgrp(0, os.getpgrp())
                        except OSError:
                            pass
                        
                        self.job_manager.set_foreground_job(None)
                        job.foreground = False
            except OSError:
                break
```

## Step 7: Update Shell Class

### Modify shell.py to use InteractiveManager:
```python
# Add import
from .interactive.base import InteractiveManager

# In __init__, add after script_manager:
self.interactive_manager = InteractiveManager(self)

# Move signal handler setup to use the manager
self.interactive_manager.signal_manager.setup_signal_handlers()

# Replace interactive_loop method:
def interactive_loop(self):
    """Run the interactive shell loop."""
    return self.interactive_manager.run_interactive_loop()

# Replace history methods:
def _load_history(self):
    """Load command history from file"""
    self.interactive_manager.load_history()

def _save_history(self):
    """Save command history to file"""
    self.interactive_manager.save_history()

def _add_to_history(self, command):
    """Add a command to history"""
    self.interactive_manager.history_manager.add_to_history(command)

# Replace signal handlers:
def _handle_sigint(self, signum, frame):
    """Handle Ctrl-C (SIGINT)"""
    self.interactive_manager.signal_manager._handle_sigint(signum, frame)

def _handle_sigchld(self, signum, frame):
    """Handle child process state changes."""
    self.interactive_manager.signal_manager._handle_sigchld(signum, frame)
```

## Implementation Order

1. **Start with Base Infrastructure**
   - Create interactive/base.py with InteractiveComponent and InteractiveManager
   - Add interactive_manager to Shell class

2. **Extract History Management**
   - Move history logic to HistoryManager
   - Update shell methods to delegate

3. **Extract Prompt Management**
   - Create PromptManager for PS1/PS2 handling
   - Integrate with existing prompt.py module

4. **Extract Tab Completion**
   - Create CompletionManager wrapper
   - Integrate with existing tab_completion.py

5. **Extract Signal Handling**
   - Move signal handlers to SignalManager
   - Handle both interactive and script modes

6. **Extract REPL Loop**
   - This is the most complex part
   - Move interactive_loop logic to REPLLoop
   - Coordinate all components

7. **Update Shell Methods**
   - Convert all interactive methods to delegation
   - Remove old method bodies

## Testing Strategy

### Unit Tests for Each Component
```python
# tests/test_history_manager.py
def test_add_to_history():
    shell = create_test_shell()
    history_mgr = HistoryManager(shell)
    history_mgr.add_to_history("echo test")
    assert "echo test" in shell.state.history

def test_history_deduplication():
    shell = create_test_shell()
    history_mgr = HistoryManager(shell)
    history_mgr.add_to_history("echo test")
    history_mgr.add_to_history("echo test")
    assert shell.state.history.count("echo test") == 1

def test_history_max_size():
    shell = create_test_shell()
    shell.state.max_history_size = 3
    history_mgr = HistoryManager(shell)
    for i in range(5):
        history_mgr.add_to_history(f"cmd{i}")
    assert len(shell.state.history) == 3
    assert shell.state.history == ["cmd2", "cmd3", "cmd4"]
```

### Integration Tests
- Test interactive loop with mock input
- Test signal handling
- Test multi-line command handling
- Test tab completion
- Test history persistence

### Mock Interactive Testing
```python
def test_interactive_loop_mock():
    shell = create_test_shell()
    # Mock stdin with commands
    with mock.patch('sys.stdin', StringIO("echo test\nexit\n")):
        shell.interactive_loop()
    # Verify commands were executed
```

## Common Pitfalls to Avoid

1. **Readline State Management**
   - Ensure readline is properly initialized
   - Handle readline exceptions gracefully
   - Clear readline state when needed

2. **Signal Handler Context**
   - Signal handlers run in signal context
   - Avoid complex operations in handlers
   - Use signal-safe functions only

3. **Multi-line Input State**
   - Properly reset state on errors
   - Handle Ctrl-C during multi-line input
   - Preserve partial input when appropriate

4. **History File Locking**
   - Handle concurrent access to history file
   - Don't fail on history file errors
   - Respect user's history preferences

5. **Tab Completion Performance**
   - Cache file listings when possible
   - Limit completion results
   - Handle large directories gracefully

## Validation Checklist

- [ ] Interactive loop works as before
- [ ] History is loaded and saved correctly
- [ ] Tab completion functions properly
- [ ] Multi-line commands work
- [ ] Signal handling (Ctrl-C, Ctrl-Z) works
- [ ] Prompts display correctly
- [ ] Background job notifications work
- [ ] Edit modes (vi/emacs) still function
- [ ] RC file loading still works
- [ ] All interactive tests pass

## Expected Results

### Lines of Code Impact
- Remove ~200 lines from shell.py
- Add ~400 lines across interactive modules
- Net increase due to better organization

### Benefits
- Clear separation of interactive vs script concerns
- Easier to test interactive features
- Better signal handling isolation
- Reusable components for different interfaces

## Integration Considerations

### Cross-Component Dependencies
- REPLLoop needs HistoryManager, PromptManager, CompletionManager
- SignalManager needs JobManager access
- MultiLineHandler needs PromptManager for PS2

### State Synchronization
- History state in ShellState
- Prompt variables (PS1, PS2) in variables dict
- Edit mode in ShellState

### Existing Module Integration
- line_editor.py - Used by REPLLoop
- multiline_handler.py - Used by REPLLoop
- prompt.py - Used by PromptManager
- tab_completion.py - Used by CompletionManager

## Next Steps After Phase 6

1. Phase 7: Final integration and cleanup
   - Remove remaining logic from shell.py
   - Optimize component interactions
   - Final documentation updates
   - Performance optimization
   - Code cleanup and consistency

2. Post-refactoring tasks:
   - Update documentation
   - Create architecture diagrams
   - Write developer guide
   - Performance benchmarking