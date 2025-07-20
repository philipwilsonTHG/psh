# PSH Parser Config Command Guide

## Overview

The `parser-config` command provides interactive control over PSH's parser configuration. This builtin command allows you to view and modify parser settings, switch between parsing modes, and enable or disable specific shell features during runtime.

## Quick Reference

```bash
# Show current configuration
parser-config show

# Switch parsing modes
parser-config mode posix        # Strict POSIX mode
parser-config mode bash         # Bash-compatible mode
parser-config mode permissive   # Permissive mode
parser-config mode educational  # Educational mode with debugging

# Quick mode shortcuts
parser-config strict      # Same as 'mode posix'
parser-config permissive  # Same as 'mode permissive'

# Enable/disable features
parser-config enable arrays
parser-config disable brace-expansion
```

## Command Syntax

```
parser-config [COMMAND] [OPTIONS]
```

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `show` | Display current parser configuration | `parser-config show` |
| `mode MODE` | Set parsing mode | `parser-config mode posix` |
| `strict` | Enable strict POSIX mode | `parser-config strict` |
| `permissive` | Enable permissive mode | `parser-config permissive` |
| `enable FEATURE` | Enable a parser feature | `parser-config enable arrays` |
| `disable FEATURE` | Disable a parser feature | `parser-config disable functions` |

## Parsing Modes

### POSIX Mode (strict)

Enforces strict POSIX.1-2017 compliance.

```bash
$ parser-config mode posix
Parser mode set to: posix

# Effects:
# - Disables bash-specific features
# - No brace expansion: {a,b,c}
# - No process substitution: <(cmd)
# - No arrays
# - Strict word splitting rules
```

### Bash Mode (compatible)

Default mode with bash compatibility.

```bash
$ parser-config mode bash
Parser mode set to: bash

# Effects:
# - All features enabled by default
# - Bash-style arrays and functions
# - Process substitution
# - Brace expansion
# - History expansion (if interactive)
```

### Permissive Mode

Maximum compatibility with error recovery.

```bash
$ parser-config mode permissive
Parser mode set to: permissive

# Effects:
# - Error collection instead of immediate failure
# - Attempts to parse invalid syntax
# - Useful for linting and analysis tools
# - More forgiving of syntax variations
```

### Educational Mode

Enhanced debugging and learning features.

```bash
$ parser-config mode educational
Parser mode set to: educational

# Effects:
# - Parser debugging enabled
# - Detailed error messages
# - Shows parsing steps
# - Helpful for understanding shell parsing
```

## Feature Control

### Available Features

| Feature Name | Aliases | Description |
|--------------|---------|-------------|
| `arithmetic` | - | Arithmetic evaluation `$((...))` |
| `arrays` | - | Array support `arr=(a b c)` |
| `functions` | - | Function definitions |
| `aliases` | - | Alias expansion |
| `brace-expand` | `brace-expansion` | Brace expansion `{a,b,c}` |
| `history-expand` | `history-expansion` | History expansion `!!` |
| `process-subst` | `process-substitution` | Process substitution `<(cmd)` |

### Enabling Features

```bash
# Enable array support
$ parser-config enable arrays
Arrays enabled

# Enable multiple features
$ parser-config enable arithmetic
$ parser-config enable process-substitution
```

### Disabling Features

```bash
# Disable brace expansion
$ parser-config disable brace-expand
Brace expansion disabled

# Create a restricted environment
$ parser-config disable functions
$ parser-config disable aliases
```

## Viewing Configuration

The `show` command displays the current parser configuration:

```bash
$ parser-config show
=== Parser Configuration ===
Mode: bash (default)

Enabled features:
  ✓ arithmetic
  ✓ arrays
  ✓ functions
  ✓ aliases
  ✓ brace-expansion
  ✗ history-expansion (disabled)
  ✓ process-substitution

Error handling: immediate
POSIX compliance: disabled
```

## Integration with Shell Options

The parser-config command modifies shell options that affect parsing:

```bash
# These are equivalent:
parser-config mode posix
set -o posix

# Feature flags map to shell options:
parser-config disable arrays
# Sets: no_arrays=true in shell options

parser-config enable brace-expand
# Sets: braceexpand=true in shell options
```

## Common Use Cases

### 1. Testing POSIX Compliance

```bash
# Switch to POSIX mode for testing
parser-config strict

# Run your script
./my-script.sh

# Check if it uses non-POSIX features
# Parser will error on bash-specific syntax
```

### 2. Creating a Restricted Shell

```bash
# Disable potentially dangerous features
parser-config disable functions
parser-config disable aliases
parser-config disable process-substitution

# Now the shell cannot:
# - Define functions
# - Use aliases
# - Use process substitution
```

### 3. Debugging Parser Issues

```bash
# Enable educational mode
parser-config mode educational

# Run problematic command
echo ${var:?error message}

# Parser will show detailed parsing steps
# and enhanced error messages
```

### 4. Script Analysis

```bash
# Use permissive mode for analyzing scripts
parser-config permissive

# Parse script with potential errors
source questionable-script.sh

# Parser collects errors instead of failing
# Good for linting tools
```

## Parser Mode Shortcut

The `parser-mode` command provides a quick way to switch modes:

```bash
# These commands are available:
parser-mode posix       # Strict POSIX
parser-mode bash        # Bash compatible
parser-mode permissive  # Error recovery
parser-mode educational # Debug mode

# Example:
$ parser-mode posix
Switched to POSIX parsing mode
```

## Examples in Practice

### Example 1: POSIX-Only Environment

```bash
# Configure for POSIX-only scripts
parser-config mode posix

# This now fails:
$ echo {a,b,c}
bash: brace expansion not supported in POSIX mode

# This works:
$ echo a b c
a b c
```

### Example 2: Analyzing Unknown Scripts

```bash
# Set up for analysis
parser-config mode permissive

# Try to parse a script with errors
$ source broken-script.sh
# Parser continues despite errors
# Errors are collected for review

# Check what failed
$ echo "Script had syntax errors but parsing continued"
```

### Example 3: Learning Shell Parsing

```bash
# Enable educational mode
parser-config mode educational

# Watch how commands are parsed
$ if [ -f file.txt ]; then echo "exists"; fi

# Parser shows:
# - Token recognition
# - AST construction
# - Parsing decisions
```

## Best Practices

1. **Default to Bash Mode**: Unless you need specific restrictions, bash mode provides the best compatibility

2. **Use POSIX Mode for Portability**: When writing portable scripts, enable POSIX mode to catch non-portable constructs

3. **Permissive Mode for Tools**: Use permissive mode when building tools that analyze shell scripts

4. **Feature-Specific Control**: Disable specific features rather than using strict mode when you need fine-grained control

5. **Save Configuration**: Document parser configuration requirements in your scripts:
   ```bash
   #!/usr/bin/env psh
   # Requires: parser-config mode posix
   ```

## Troubleshooting

### Configuration Not Taking Effect

```bash
# Verify current configuration
parser-config show

# Some features require specific modes
# Arrays won't work in POSIX mode regardless of enable command
```

### Unexpected Parsing Errors

```bash
# Check if you're in strict mode
parser-config show | grep Mode

# Try permissive mode for complex scripts
parser-config permissive
```

### Feature Not Available

```bash
# Some features have multiple names
parser-config enable brace-expansion  # or brace-expand
parser-config enable process-substitution  # or process-subst
```

## Summary

The `parser-config` command provides powerful runtime control over PSH's parsing behavior. Whether you need strict POSIX compliance, bash compatibility, or custom feature sets, this command allows you to configure the parser to meet your specific needs without restarting the shell.