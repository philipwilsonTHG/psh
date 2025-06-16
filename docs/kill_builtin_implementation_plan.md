# PSH Kill Builtin Implementation Plan

## Overview
Implement a POSIX-compliant `kill` builtin command for PSH to send signals to processes and jobs. This will improve POSIX compliance and provide essential process management capabilities.

## POSIX Kill Builtin Requirements

### Syntax
```bash
kill -s signal_name pid...
kill -l [exit_status]
kill [-signal_name] pid...
kill [-signal_number] pid...
```

### Core Functionality
1. **Signal Sending**: Send signals to processes by PID
2. **Signal Listing**: List available signal names with `-l`
3. **Job Control Integration**: Support job specifications (%1, %+, %-, etc.)
4. **Signal Names/Numbers**: Support both signal names (TERM, KILL) and numbers (15, 9)

## Implementation Architecture

### 1. Create KillBuiltin Class
**File**: `psh/builtins/kill_command.py`

```python
@builtin
class KillBuiltin(Builtin):
    """Send signals to processes."""
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        # Parse options and arguments
        # Handle signal listing (-l)
        # Send signals to processes/jobs
        # Return appropriate exit codes
```

### 2. Signal Management System
**Features**:
- Signal name to number mapping (TERM→15, KILL→9, etc.)
- Signal number validation
- Cross-platform signal handling
- Default signal (SIGTERM/15) when none specified

### 3. Target Resolution
**Support**:
- Process IDs (positive integers)
- Job specifications (%1, %+, %-, %str)
- Process groups (negative numbers for -pid)
- Special cases (0 for current process group)

### 4. Integration Points
- **Job Manager**: Use existing job control system for %jobspecs
- **Error Handling**: POSIX-compliant exit codes and error messages
- **Permissions**: Handle permission denied scenarios gracefully

## Detailed Implementation Steps

### Step 1: Signal Mapping and Validation
```python
SIGNAL_NAMES = {
    'HUP': 1, 'INT': 2, 'QUIT': 3, 'KILL': 9, 'TERM': 15,
    'CONT': 18, 'STOP': 19, 'TSTP': 20, 'USR1': 10, 'USR2': 12
}

def parse_signal(signal_str: str) -> int:
    # Handle -SIG prefix, case insensitivity
    # Convert names to numbers
    # Validate signal numbers
```

### Step 2: Argument Parsing
```python
def parse_args(self, args: List[str]) -> Tuple[int, List[str], bool]:
    # Handle -l option for listing
    # Parse -s signal_name format
    # Parse -signal_name and -signal_number formats
    # Extract target PIDs/jobspecs
```

### Step 3: Target Resolution
```python
def resolve_targets(self, targets: List[str], shell: 'Shell') -> List[int]:
    # Convert job specs (%1, %+) to PIDs using JobManager
    # Validate PID format and existence
    # Handle process groups and special cases
    # Return list of actual PIDs to signal
```

### Step 4: Signal Delivery
```python
def send_signals(self, signal_num: int, pids: List[int]) -> int:
    # Use os.kill() for individual processes
    # Use os.killpg() for process groups
    # Handle permission errors gracefully
    # Track success/failure for exit code
```

### Step 5: Signal Listing (-l option)
```python
def list_signals(self, exit_status: Optional[int] = None) -> int:
    # Show all available signals by name
    # If exit_status provided, show corresponding signal
    # Format output to match POSIX requirements
```

## Error Handling and Exit Codes

### POSIX Exit Status Requirements
- **0**: All signals sent successfully
- **1**: Invalid arguments or permission denied
- **2**: Invalid signal name/number

### Error Scenarios
- Invalid signal names/numbers
- Non-existent PIDs
- Permission denied
- Invalid job specifications
- Invalid command line syntax

## Testing Strategy

### Unit Tests (`tests/test_kill_builtin.py`)
1. **Signal parsing tests**
   - Valid signal names and numbers
   - Invalid signal handling
   - Case insensitivity

2. **Argument parsing tests**
   - Various option formats (-l, -s, -9, -TERM)
   - Multiple PIDs
   - Invalid argument combinations

3. **Job specification tests**
   - %1, %+, %- job references
   - Non-existent job handling

4. **Signal sending tests**
   - Mock os.kill() calls
   - Permission error simulation
   - Process group signaling

5. **Integration tests**
   - Kill background jobs
   - Kill processes started by PSH
   - Signal listing functionality

### Bash Comparison Tests
Compare PSH kill behavior with bash:
- Signal name resolution
- Job specification handling
- Error message format
- Exit code behavior

## Integration with Existing PSH Components

### JobManager Integration
- Use `parse_job_spec()` for %jobspec resolution
- Access job PIDs through existing Job objects
- Handle job state updates after signaling

### Builtin Registry
- Add to `psh/builtins/__init__.py` imports
- Register with @builtin decorator
- Update help system with kill documentation

### Documentation Updates
- Add kill to POSIX compliance analysis
- Update user guide with kill examples
- Document signal handling capabilities

## Enhanced Features (Beyond POSIX)

### Optional PSH Extensions
1. **Enhanced job support**: Kill entire job pipelines
2. **Signal name completion**: Tab completion for signal names
3. **Verbose mode**: Show what signals are being sent
4. **Dry-run mode**: Show what would be killed without sending signals

## Security Considerations

### Permission Validation
- Only allow killing processes owned by user
- Gracefully handle permission denied
- No privilege escalation attempts

### Input Validation
- Sanitize all PID inputs
- Validate job specifications
- Prevent signal injection attacks

## Implementation Files

### New Files
- `psh/builtins/kill_command.py` - Main implementation
- `tests/test_kill_builtin.py` - Comprehensive test suite
- `docs/kill_builtin_implementation_plan.md` - This plan

### Modified Files
- `psh/builtins/__init__.py` - Add import
- `docs/posix/posix_compliance_analysis.md` - Update compliance
- `docs/user_guide/04_builtin_commands.md` - Add documentation

## Success Criteria

1. **POSIX Compliance**: Full POSIX kill functionality
2. **Test Coverage**: 100% test pass rate with comprehensive coverage
3. **Job Integration**: Seamless integration with PSH job control
4. **Error Handling**: Proper error messages and exit codes
5. **Documentation**: Complete user documentation and examples

This implementation will enhance PSH's process management capabilities while maintaining educational clarity and POSIX compliance.