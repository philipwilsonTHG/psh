# PSH Debug Examples

This directory contains example scripts demonstrating PSH's debug capabilities.

## Debug Flags

PSH supports several debug flags for understanding shell behavior:

### Parser/Lexer Debug
- `--debug-ast` - Show parsed AST before execution
- `--debug-tokens` - Show lexer tokens before parsing
- `--debug-scopes` - Show variable scope operations

### Expansion Debug  
- `--debug-expansion` - Show expansions as they occur
- `--debug-expansion-detail` - Show detailed expansion steps

### Execution Debug
- `--debug-exec` - Show executor operations
- `--debug-exec-fork` - Show fork/exec details

## Usage Examples

### Debug Variable Expansion
```bash
psh --debug-expansion -c 'echo $HOME'
psh --debug-expansion-detail examples/debug_expansion.sh
```

### Debug Command Execution
```bash
psh --debug-exec -c 'ls | grep txt'
psh --debug-exec-fork examples/debug_execution.sh
```

### Combine Multiple Debug Flags
```bash
psh --debug-expansion --debug-exec -c 'echo $(date)'
psh --debug-ast --debug-tokens -c 'if [ -f file ]; then echo found; fi'
```

### Enable Debug at Runtime
```bash
psh
$ set -o debug-expansion
$ echo $PATH
$ set +o debug-expansion  # disable
```

### Show Current Debug Settings
```bash
psh -c 'set -o'  # Show all options
```

## Example Scripts

- `debug_expansion.sh` - Demonstrates various expansion types
- `debug_execution.sh` - Shows different command execution paths

Run with different debug flags to see internal operations:

```bash
# See all expansions in detail
psh --debug-expansion-detail debug_expansion.sh

# See fork/exec operations  
psh --debug-exec-fork debug_execution.sh

# Combine to see full picture
psh --debug-expansion --debug-exec debug_execution.sh
```