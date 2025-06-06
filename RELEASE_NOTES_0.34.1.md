# PSH Release Notes - Version 0.34.1

**Release Date**: 2025-01-06

## Overview

This is a minor feature release that adds runtime toggling of the debug-scopes option through the `set` builtin command. Users can now enable or disable variable scope debugging during an interactive session without restarting the shell.

## New Features

### Runtime Debug-Scopes Toggle

- Added support for `set -o debug-scopes` to enable variable scope debugging
- Added support for `set +o debug-scopes` to disable variable scope debugging
- The option shows all variable scope operations when enabled:
  - Function scope push/pop operations
  - Local variable creation
  - Variable assignments and lookups
  - Variable unsetting
- Integrates with the existing ScopeManager debug functionality
- Complements the `--debug-scopes` command-line flag

## Technical Details

### Implementation
- Modified `SetBuiltin` in `builtins/environment.py` to handle the new option
- When enabled, calls `shell.state.scope_manager.enable_debug(True)`
- When disabled, calls `shell.state.scope_manager.enable_debug(False)`
- State is tracked in `shell.state.debug_scopes` for consistency
- Updated `set -o` display to show current debug-scopes status
- Updated help text to document the new option

### Example Usage

```bash
# Enable debug-scopes
$ set -o debug-scopes

# Variable operations now show debug output
$ x=42
[SCOPE] Setting variable in scope 'global': x = 42

# Function calls show scope operations
$ my_func() {
>     local y=10
>     z=20
> }
$ my_func
[SCOPE] Pushing scope for function: my_func
[SCOPE] Creating local variable: y = 10
[SCOPE] Setting variable in global scope: z = 20
[SCOPE] Popping scope: my_func (destroying variables: y)

# Check status
$ set -o
edit_mode            emacs
debug-ast            off
debug-tokens         off
debug-scopes         on

# Disable debug-scopes
$ set +o debug-scopes
```

## Testing

- Added comprehensive test suite in `test_debug_scopes_toggle.py`
- 10 new tests covering:
  - Default state verification
  - Enable/disable functionality
  - Output verification when enabled/disabled
  - Function scope tracking
  - Integration with `set -o` and `set +o` displays
  - Persistence across commands
- Created `examples/debug_scopes_demo.sh` demonstrating the feature

## Test Suite Status
- **Total tests**: 761
- **Passing**: 759 (up from 751 in v0.34.0)
- **Skipped**: 40
- **XFailed**: 3

## Breaking Changes
None - this is a backward-compatible enhancement.

## Migration Notes
No migration required. The feature is disabled by default and only activates when explicitly enabled with `set -o debug-scopes`.

## Known Issues
None identified in this release.

## Contributors
All code written by Claude Code using the Opus 4 model.