# POSIX-compliant `exec` Builtin Implementation Plan

## Overview

The `exec` builtin has two main modes of operation:
1. **With command**: Replace the current shell process with the specified command
2. **Without command**: Only apply redirections to affect the current shell's file descriptors

## Implementation Details

### 1. Create the Exec Builtin Class

- **File**: `/Users/pwilson/src/psh/psh/builtins/core.py` (add to existing core builtins)
- **Class**: `ExecBuiltin` extending `Builtin` base class
- **Features**:
  - Handle both modes (with/without command)
  - Parse and apply redirections
  - Replace shell process using `os.execvp()` when command is provided
  - Proper error handling with exit codes 126/127

### 2. Key Behaviors to Implement

#### Mode 1: exec with command
```bash
exec command [args...]  # Replace shell with command
```
- Apply any redirections first
- Use `os.execvp()` to replace the current process
- Exit code 127 if command not found
- Exit code 126 if command found but not executable
- Never returns to the shell (process is replaced)

#### Mode 2: exec without command (redirections only)
```bash
exec 3< file      # Open file descriptor 3 for reading
exec 4> file      # Open file descriptor 4 for writing  
exec 5<&0         # Duplicate fd 0 to fd 5
exec 3<&-         # Close file descriptor 3
```
- Apply redirections to the current shell
- Changes persist for subsequent commands
- Returns 0 on success, 1-125 on redirection errors

### 3. Integration Points

#### Parser Integration
- No parser changes needed - exec is already a valid command
- Redirections are parsed as part of SimpleCommand AST

#### IOManager Integration
- Use existing `IOManager.apply_redirections()` method
- For mode 2, make redirections permanent by not restoring them

#### Variable Environment
- Environment variables set with exec (e.g., `VAR=value exec cmd`) must be passed to the new process
- Use existing variable assignment handling in SimpleCommand

### 4. Testing Strategy

#### Unit Tests (`tests/test_exec_builtin.py`)
1. Test exec with simple command
2. Test exec with command and arguments
3. Test exec with command not found (exit 127)
4. Test exec with non-executable file (exit 126)
5. Test exec with redirections and command
6. Test exec with environment variables
7. Test exec without command (redirections only)
8. Test various redirection types (input, output, append, dup, close)
9. Test error cases (bad file descriptors, permission denied)

#### Bash Comparison Tests (`tests/comparison/test_bash_exec.py`)
1. Compare exec behavior between PSH and bash
2. Test that exec replaces the shell process
3. Test file descriptor manipulation
4. Test environment variable passing

#### Manual Testing
```bash
# Test exec replaces shell
echo "before exec"
exec echo "after exec"
echo "this should not print"  # Shell is gone

# Test file descriptor operations
exec 3< /etc/passwd
exec 4> output.txt
exec 5<&0
exec 3<&-

# Test with redirections
exec > log.txt 2>&1
echo "all output redirected"
```

### 5. Implementation Steps

1. **Add ExecBuiltin class** to `psh/builtins/core.py`
2. **Implement execute() method** with two modes
3. **Handle redirections** using IOManager
4. **Handle command execution** using os.execvp()
5. **Add comprehensive error handling**
6. **Create unit tests** covering all scenarios
7. **Create bash comparison tests**
8. **Update documentation** (help text, user guide)

## Code Structure Preview

```python
@builtin
class ExecBuiltin(Builtin):
    """Execute commands and manipulate file descriptors."""
    
    @property
    def name(self) -> str:
        return "exec"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        # Parse command and redirections from args
        # If command provided:
        #   - Apply redirections
        #   - Apply environment variables
        #   - Use os.execvp() to replace process
        # If no command:
        #   - Apply redirections permanently
        #   - Return 0 or error code
```

## POSIX Compliance Notes

According to POSIX specification:
- `exec` is a special built-in utility
- With command: replaces the shell without creating a new process
- Without command: opens/closes/copies file descriptors
- Redirections affect the current shell execution environment
- Exit status:
  - If command specified: doesn't return (process replaced)
  - Command not found: 127
  - Command not executable: 126
  - Redirection error: 1-125
  - Success (no command): 0

## Example Implementation Approach

```python
def execute(self, args: List[str], shell: 'Shell') -> int:
    # Skip 'exec' itself
    args = args[1:]
    
    # Check if we have a command or just redirections
    # This requires parsing the SimpleCommand node to separate
    # redirections from the actual command
    
    # For now, we need to get access to the original AST node
    # to properly handle redirections. This might require
    # refactoring how builtins receive their arguments.
    
    # Alternative approach: exec builtin could be handled
    # specially in the executor before normal builtin dispatch
```

## Integration Considerations

1. **Special Handling Required**: Since exec needs access to the original AST node (for redirections), it may need special handling in the executor rather than being a regular builtin.

2. **Process Replacement**: When replacing the process with `os.execvp()`, we need to ensure:
   - All file descriptors are properly set up
   - Environment variables are correctly passed
   - Signal handlers are reset to defaults
   - No cleanup code runs after exec

3. **Permanent Redirections**: For exec without command, redirections must modify the shell's file descriptor table permanently, not just temporarily.

This implementation will provide full POSIX compliance for the exec builtin while integrating cleanly with PSH's existing architecture.