# POSIX-Compliant `trap` Builtin Implementation Plan

## Overview
The `trap` builtin is a critical POSIX shell feature for signal handling and cleanup. It allows scripts to define actions to take when signals are received or when the shell exits. This implementation plan ensures full POSIX compliance while integrating with PSH's existing signal handling infrastructure.

## Current Signal Handling Analysis

### Existing Infrastructure:
1. **SignalManager** (`psh/interactive/signal_manager.py`):
   - Sets up signal handlers based on shell mode (script vs interactive)
   - Handles SIGINT, SIGTSTP, SIGTTOU, SIGTTIN, SIGCHLD
   - Stores original handlers for restoration
   - Different behavior for script vs interactive mode

2. **Executor Signal Handling** (`psh/visitor/executor_visitor.py`):
   - Resets signals to SIG_DFL in child processes
   - Handles process group management
   - Terminal control for foreground/background jobs

3. **Job Control Integration** (`psh/job_control.py`):
   - SIGCHLD handler for job state changes
   - Process group and terminal management

## POSIX `trap` Requirements

### Syntax:
```bash
trap [action] [condition...]
trap -l
trap -p [condition...]
```

### Key Features:
1. **Signal Trapping**: Catch and handle signals (INT, TERM, HUP, etc.)
2. **EXIT Trap**: Execute commands when shell exits
3. **DEBUG Trap**: Execute before each command (bash extension)
4. **ERR Trap**: Execute on command errors (bash extension)
5. **Signal Listing**: `trap -l` lists signal names
6. **Display Traps**: `trap -p` shows current traps
7. **Reset Traps**: `trap - signal` resets to default
8. **Ignore Signals**: `trap '' signal` ignores signal

## Implementation Architecture

### 1. Create TrapBuiltin Class
**File**: `psh/builtins/signal_handling.py`
```python
@builtin
class TrapBuiltin(Builtin):
    """Set signal handlers and exit traps."""
    
    def __init__(self):
        # Map signal names to numbers
        self.signal_map = {
            'HUP': signal.SIGHUP,
            'INT': signal.SIGINT,
            'QUIT': signal.SIGQUIT,
            'TERM': signal.SIGTERM,
            'EXIT': 'EXIT',  # Special pseudo-signal
            'DEBUG': 'DEBUG', # Bash extension
            'ERR': 'ERR',     # Bash extension
            # ... more signals
        }
        
    def execute(self, args: List[str], shell: 'Shell') -> int:
        # Parse options and arguments
        # Set/display/reset traps as needed
```

### 2. Trap Storage in ShellState
**Modify**: `psh/core/state.py`
```python
class ShellState:
    def __init__(self, ...):
        # ... existing code ...
        # Trap handlers: signal -> command string
        self.trap_handlers = {}
        # Original signal handlers for restoration
        self._original_signal_handlers = {}
```

### 3. Signal Handler Integration
**Create**: `psh/core/trap_manager.py`
```python
class TrapManager:
    """Manages trap handlers for the shell."""
    
    def __init__(self, shell):
        self.shell = shell
        self.state = shell.state
        
    def set_trap(self, action: str, signals: List[str]) -> int:
        """Set trap handler for signals."""
        
    def remove_trap(self, signals: List[str]) -> int:
        """Remove trap handlers."""
        
    def execute_trap(self, signal_name: str):
        """Execute trap handler for given signal."""
        
    def list_signals(self) -> List[str]:
        """List available signal names."""
        
    def show_traps(self, signals: List[str] = None) -> str:
        """Show current trap settings."""
```

### 4. Modify Signal Handling Flow

#### Update SignalManager
**Modify**: `psh/interactive/signal_manager.py`
- Check for user-defined traps before default handling
- Execute trap commands when signals are received
- Special handling for EXIT traps

#### Update Executor
**Modify**: `psh/visitor/executor_visitor.py`
- Don't reset signals that have traps in child processes
- Execute DEBUG traps before commands (if implemented)
- Execute ERR traps on command failures (if implemented)

### 5. EXIT Trap Implementation
- Store EXIT trap command in state
- Execute on:
  - `exit` builtin
  - End of script
  - Fatal signals
  - Normal shell termination

### 6. Signal Inheritance
- Child processes should NOT inherit traps (POSIX requirement)
- Subshells should inherit trap settings but not handlers
- Functions execute in current shell context (inherit traps)

## Implementation Steps

### Phase 1: Basic Infrastructure
1. Create `TrapBuiltin` class with basic parsing
2. Add trap storage to `ShellState`
3. Create `TrapManager` for trap operations
4. Implement `trap -l` (list signals)

### Phase 2: Signal Integration
1. Modify `SignalManager` to check for traps
2. Create trap execution mechanism
3. Test with basic signals (INT, TERM)
4. Implement `trap -p` (show traps)

### Phase 3: Special Traps
1. Implement EXIT trap handling
2. Add EXIT trap execution points
3. Handle trap inheritance rules
4. Add trap reset functionality (`trap -`)

### Phase 4: Advanced Features
1. Signal name/number conversion
2. Multiple signals per trap command
3. Proper quoting in trap display
4. Error handling and validation

### Phase 5: Testing & Documentation
1. Create comprehensive test suite
2. Test signal delivery and trap execution
3. Test inheritance and subshell behavior
4. Update documentation

## Test Plan

### Basic Tests:
```bash
# Set and execute trap
trap 'echo "Caught SIGINT"' INT
# Send SIGINT (Ctrl+C)

# EXIT trap
trap 'echo "Exiting"' EXIT
exit

# Remove trap
trap - INT

# Ignore signal
trap '' QUIT

# List signals
trap -l

# Show traps
trap -p
trap -p INT EXIT
```

### Advanced Tests:
- Trap in functions
- Trap in subshells
- Trap with command substitution
- Signal during trap execution
- Multiple traps for same signal

## Integration Points

1. **Job Control**: Coordinate with JobManager for SIGCHLD
2. **Script Execution**: Execute EXIT traps at script end
3. **Interactive Mode**: Handle Ctrl+C with traps
4. **Error Handling**: Optional ERR trap support

## Considerations

1. **Signal Safety**: Trap handlers must be signal-safe
2. **Reentrancy**: Handle signals during trap execution
3. **Portability**: Use standard signal names
4. **Performance**: Minimal overhead when no traps set
5. **Debugging**: Clear error messages for invalid signals

## Files to Create/Modify

### New Files:
- `psh/builtins/signal_handling.py` - TrapBuiltin implementation
- `psh/core/trap_manager.py` - Trap management logic
- `tests/test_trap_builtin.py` - Comprehensive tests
- `docs/trap_implementation.md` - Documentation

### Modified Files:
- `psh/core/state.py` - Add trap storage
- `psh/interactive/signal_manager.py` - Integrate trap execution
- `psh/visitor/executor_visitor.py` - Handle signal inheritance
- `psh/builtins/__init__.py` - Register trap builtin
- `psh/shell.py` - Initialize trap manager

This implementation will bring PSH significantly closer to full POSIX compliance and enable robust signal handling in shell scripts.