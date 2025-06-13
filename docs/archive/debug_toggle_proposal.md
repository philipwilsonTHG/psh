# Runtime Debug Toggle Proposal for PSH

## Overview
This proposal describes a mechanism for toggling `--debug-ast` and `--debug-tokens` options at runtime without restarting the shell.

## Current Implementation
- Debug flags are passed at startup: `psh --debug-ast --debug-tokens`
- Stored in `ShellState` as `self.state.debug_ast` and `self.state.debug_tokens`
- Used in `scripting/source_processor.py` during command execution
- Output printed to stderr before parsing/execution

## Proposed Solutions

### Option 1: Shell Options via `set` Builtin (Recommended)
Extend the existing `set` builtin to support shell options, following bash conventions:

```bash
# Enable debug options
set -o debug-ast      # or: set -o debugast
set -o debug-tokens   # or: set -o debugtokens

# Disable debug options
set +o debug-ast
set +o debug-tokens

# Show current options
set -o                # List all options
set +o                # Show as set commands
```

**Implementation**:
1. Add to `builtins/shell_state.py` in the `set` builtin
2. Create a mapping of option names to state attributes
3. Support both `-o` (enable) and `+o` (disable) syntax

**Pros**:
- Consistent with bash/POSIX shell option handling
- Uses existing builtin infrastructure
- Familiar to shell users
- Can be extended for other options (e.g., `set -x` for tracing)

**Cons**:
- Requires extending the `set` builtin

### Option 2: Dedicated `debug` Builtin
Create a new builtin specifically for debug control:

```bash
# Enable debug features
debug ast on
debug tokens on
debug all on

# Disable debug features
debug ast off
debug tokens off
debug all off

# Show status
debug status
debug
```

**Implementation**:
1. Create new `builtins/debug.py`
2. Register with `@builtin` decorator
3. Direct manipulation of `shell.state.debug_*` flags

**Pros**:
- Clear, dedicated interface
- Easy to discover and use
- Can be extended with more debug features

**Cons**:
- Adds a new builtin (increases surface area)
- Not standard shell behavior

### Option 3: Special Variables
Use special shell variables to control debug:

```bash
# Enable debug
PSH_DEBUG_AST=1
PSH_DEBUG_TOKENS=1

# Disable debug
PSH_DEBUG_AST=0
PSH_DEBUG_TOKENS=0

# Or using export
export PSH_DEBUG_AST=1
```

**Implementation**:
1. Check these variables in the execution path
2. Could check in `source_processor._execute_buffered_command()`

**Pros**:
- Simple implementation
- Can be set in scripts or RC files
- No new commands needed

**Cons**:
- Less discoverable
- Not standard practice for runtime options
- Requires checking variables on every command

## Recommended Approach: Option 1 (Shell Options)

I recommend implementing Option 1 using the `set` builtin because:

1. **Standards Compliance**: Follows established shell conventions
2. **Extensibility**: Framework can support future options
3. **Discoverability**: `set -o` shows all available options
4. **Integration**: Works with existing infrastructure
5. **User Familiarity**: Shell users expect `set -o` for options

## Implementation Details

### 1. Extend ShellState
Add option tracking:
```python
class ShellState:
    def __init__(self, ...):
        # ... existing code ...
        
        # Shell options
        self.shell_options = {
            'debug-ast': self.debug_ast,
            'debug-tokens': self.debug_tokens,
            # Future: 'xtrace': False, 'errexit': False, etc.
        }
```

### 2. Update Set Builtin
Add option handling to `builtins/shell_state.py`:
```python
def execute(self, args, shell):
    if len(args) > 0:
        if args[0] == '-o' and len(args) > 1:
            # Enable option
            option_name = args[1]
            if option_name in shell.state.shell_options:
                shell.state.shell_options[option_name] = True
                # Update the actual flag
                if option_name == 'debug-ast':
                    shell.state.debug_ast = True
                elif option_name == 'debug-tokens':
                    shell.state.debug_tokens = True
            else:
                print(f"set: {option_name}: invalid option name", file=sys.stderr)
                return 1
        elif args[0] == '+o' and len(args) > 1:
            # Disable option
            # ... similar logic ...
```

### 3. List Options
Support showing current options:
```python
elif args[0] == '-o' and len(args) == 1:
    # Show all options
    for name, value in sorted(shell.state.shell_options.items()):
        status = "on" if value else "off"
        print(f"{name:<20} {status}")
```

## Usage Examples

```bash
# Start shell normally
$ psh

# Enable AST debugging at runtime
$ set -o debug-ast

# Run a command - will show AST
$ echo hello
=== AST Debug Output ===
TopLevel:
  CommandList:
    Pipeline:
      Command: ['echo', 'hello']
======================
hello

# Disable AST debugging
$ set +o debug-ast

# Enable token debugging
$ set -o debug-tokens

# Show all options
$ set -o
debug-ast            off
debug-tokens         on

# Can be used in scripts or .pshrc
if [ "$DEBUG_MODE" = "1" ]; then
    set -o debug-ast
    set -o debug-tokens
fi
```

## Future Extensions

This framework can support additional shell options:
- `set -x` (xtrace): Print commands before execution
- `set -e` (errexit): Exit on error
- `set -u` (nounset): Error on undefined variables
- `set -o pipefail`: Pipeline fails if any command fails
- `set -o vi/emacs`: Editor mode (already supported via different mechanism)

## Testing

1. Test basic enable/disable functionality
2. Test persistence across commands
3. Test option listing
4. Test invalid option names
5. Test in scripts vs interactive mode
6. Test interaction with startup flags

## Documentation Updates

1. Update `--help` to mention runtime toggling
2. Add to CLAUDE.md shell options section
3. Update set builtin help text
4. Add examples to documentation