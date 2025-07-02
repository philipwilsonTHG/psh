# Chapter 17: Differences from Bash

While PSH implements many shell features compatible with Bash, there are important differences due to its educational focus and Python implementation. Understanding these differences helps you write portable scripts and use PSH effectively.

## 17.1 Unimplemented Features

PSH focuses on core shell functionality for educational purposes. Several Bash features are not yet implemented.

### Shell Options

PSH now supports the core shell options for robust script development:

```bash
# PSH implements these common Bash options (v0.35.0+):
set -e    # Exit on error (errexit)
set -u    # Error on undefined variables (nounset)
set -x    # Print commands before execution (xtrace)
set -o pipefail  # Pipeline fails if any command fails

# Combined usage
set -eux -o pipefail  # Strict error handling for scripts

# Enable/disable at runtime
set -o errexit      # Same as set -e
set +o errexit      # Disable errexit
set -o              # Show all option settings

# Example robust script:
#!/usr/bin/env psh
set -euo pipefail    # Exit on error, undefined vars, trace, pipefail

# These options make scripts more reliable:
# -e: Exits immediately if any command fails
# -u: Treats undefined variables as errors 
# -x: Shows each command before execution
# -o pipefail: Pipeline fails if any command in it fails
```

### Array Variables

```bash
# ✅ PSH fully supports both indexed and associative arrays like bash!

# Indexed arrays (v0.41.0+)
declare -a array=(one two three)
echo ${array[0]}         # First element
echo ${array[@]}         # All elements
echo ${#array[@]}        # Number of elements

# Array features supported:
fruits=(apple banana cherry)
fruits[3]="orange"       # Add element
fruits+=(grape)          # Append to array
echo ${fruits[-1]}       # Last element
echo ${fruits[@]:1:2}    # Slice from index 1, length 2
echo ${!fruits[@]}       # All indices

# Array element operations
files=(doc.txt img.txt data.txt)
echo ${files[@]/.txt/.bak}  # Replace in all elements
echo ${files[0]^^}          # Uppercase first element

# Sparse arrays work too
unset fruits[2]          # Remove element
echo ${!fruits[@]}       # Shows: 0 1 3 4

# Associative arrays are fully supported! (v0.43.0+)
declare -A colors=([red]="#FF0000" [green]="#00FF00")
colors[blue]="#0000FF"
echo ${colors[red]}      # Access by key
echo ${!colors[@]}       # All keys
echo ${colors[@]}        # All values

# Advanced array operations work:
declare -A config=([host]="localhost" [port]="8080")
echo "Config: ${config[@]}"           # All values
echo "Keys: ${!config[@]}"            # All keys
config[ssl]="true"                    # Add new key
unset config[port]                    # Remove key
```

### Trap Command

```bash
# ✅ PSH fully supports the trap command (v0.57.3+)
trap 'echo "Cleaning up..."' EXIT
trap 'echo "Interrupted"' INT

# Signal management works:
cleanup() {
    echo "Cleaning up temporary files..."
    rm -f /tmp/tempfile.$$
}
trap cleanup EXIT

# List current traps
trap -p

# Reset traps to default
trap - EXIT INT

# Example: Graceful script termination
#!/usr/bin/env psh
set -e

# Set up cleanup on exit
trap 'echo "Script terminated"; rm -f "$temp_file"' EXIT

temp_file=$(mktemp)
echo "Working with $temp_file"
# ... do work ...
# Cleanup happens automatically on exit
```

### Select Statement

PSH now supports the select statement for interactive menus:

```bash
# PSH implements select statement (v0.34.0+):
select option in "Option 1" "Option 2" "Quit"; do
    case $option in
        "Option 1") echo "You chose 1" ;;
        "Option 2") echo "You chose 2" ;;
        "Quit") break ;;
        *) echo "Invalid selection" ;;
    esac
done

# Features supported:
# - Numbered menu display on stderr
# - PS3 prompt customization (default "#? ")
# - Multi-column layout for large lists
# - Integration with break/continue statements
# - I/O redirection support
# - Variable and command substitution in items
# - EOF (Ctrl+D) and interrupt (Ctrl+C) handling

# Example with custom prompt:
PS3="Please select an option: "
select choice in start stop restart status; do
    echo "You selected: $choice"
    [[ $choice ]] && break
done
```

### Still Unimplemented Features

```bash
# Coprocesses are NOT implemented
coproc { command; }           # ❌ Not supported

# Extended glob patterns are NOT implemented
shopt -s extglob             # ❌ Not supported
!(pattern)                   # ❌ Anything except pattern
*(pattern)                   # ❌ Zero or more occurrences
+(pattern)                   # ❌ One or more occurrences
?(pattern)                   # ❌ Zero or one occurrence
@(pattern)                   # ❌ Exactly one occurrence

# Advanced completion features are limited
complete -F _my_completion mycommand  # ❌ Programmable completion not implemented
# Basic tab completion for files/commands works

# Some advanced job control features
disown %1                    # ❌ Not implemented
# Basic job control (jobs, fg, bg, wait) works fine

# Some process substitution edge cases may not work perfectly
# But basic usage works:
diff <(command1) <(command2)  # ✅ Works
cat >(command)               # ✅ Works
```

### History Expansion

PSH now supports bash-compatible history expansion:

```bash
# PSH implements history expansion (v0.33.0+):
!!      # Previous command
!n      # Command n from history
!-n     # n commands ago
!string # Most recent command starting with string
!?string? # Most recent command containing string

# Examples:
psh$ echo hello
hello
psh$ !!     # Expands to: echo hello
hello

psh$ !ec    # Expands to most recent command starting with "ec"
echo hello
hello

# Context-aware expansion respects quotes:
psh$ echo "!!" # Does not expand (inside quotes)
!!

# Works with parameter expansion contexts
```

## 17.2 Architectural Limitations

PSH's Python implementation creates some fundamental differences from Bash's C implementation.

### Recursion Depth Limitations

```bash
# PSH has limited recursion depth due to Python's call stack
# This may fail in PSH but work in Bash:

factorial() {
    local n=$1
    if [ $n -le 1 ]; then
        echo 1
    else
        echo $((n * $(factorial $((n - 1)))))
    fi
}

# Works in Bash for large values
factorial 1000  # May fail in PSH with stack overflow

# Workaround: Use iteration instead
factorial_iterative() {
    local n=$1
    local result=1
    while [ $n -gt 1 ]; do
        result=$((result * n))
        n=$((n - 1))
    done
    echo $result
}
```

### Control Structures in Pipelines

```bash
# ✅ PSH now supports control structures in pipelines! (v0.37.0+)

# These work correctly:
echo "data" | while read line; do echo "Read: $line"; done
echo "test" | if grep -q test; then echo "Found"; fi

# Control structures work with logical operators:
if [ -f file.txt ]; then cat file.txt; fi && echo "Success"

# Arithmetic commands work with logical operators:
((5 > 3)) && echo "Math works"

# However, some complex combinations may still need subshells:
(complex | pipeline | here) && echo "Success"
```

### Subshells and Variable Isolation

```bash
# ✅ PSH properly implements subshells (v0.59.8+)

# Variable isolation works correctly:
var="outer"
(var="inner"; echo "In subshell: $var")  # Shows: inner
echo "Outside: $var"                     # Shows: outer

# Subshells work with redirections:
(echo "line1"; echo "line2") > output.txt

# Exit status propagation works:
(exit 42); echo "Exit code: $?"          # Shows: 42

# Subshells inherit but don't modify parent environment
```

## 17.3 Behavioral Differences

Some features work differently in PSH compared to Bash.

### Quote Handling

```bash
# Single quote handling differs
# In Bash, you cannot escape single quotes inside single quotes
# PSH may handle this differently

# Bash approach:
echo 'It'"'"'s a test'  # Concatenate quoted strings

# Alternative that works in both:
echo "It's a test"      # Use double quotes
echo 'It'\''s a test'   # Escape sequence
```

### Variable Assignment

```bash
# PSH may be stricter about variable assignment syntax
# Spaces around = may cause issues

# Always use:
VAR=value         # No spaces

# Avoid:
VAR = value       # May not work as expected
VAR= value        # Different meaning
VAR =value        # Syntax error
```

### Here Document Behavior

```bash
# Tab suppression in here documents
# PSH implements <<- but behavior may differ slightly

# Ensure consistent behavior:
cat <<-'EOF'
	This has a tab
	This too
EOF

# Be explicit about quoting the delimiter
cat <<'EOF'      # No expansion
$HOME
EOF

cat <<EOF        # With expansion
$HOME
EOF
```

### Background Job Handling

```bash
# Job control works only in interactive mode
# Scripts cannot use job control features

# This works interactively but not in scripts:
#!/usr/bin/env psh
command &
fg %1  # Will fail in script

# Script-compatible approach:
#!/usr/bin/env psh
command &
pid=$!
wait $pid
```

## 17.4 PSH-Specific Features

PSH includes features designed specifically for educational purposes that aren't in Bash.

### Debug Options

```bash
# PSH-specific debug flags
psh --debug-ast              # Show parsed AST
psh --debug-tokens           # Show tokenization
psh --debug-scopes           # Show variable scopes

# Runtime debugging
set -o debug-ast            # Enable AST display
set -o debug-tokens         # Enable token display

# These don't exist in Bash
# Bash equivalent would be set -x for execution trace
```

### Educational Error Messages

```bash
# PSH provides more educational error messages
psh$ [ 1 -eq  ]
psh: error: test: expected argument after -eq

# Bash might give:
bash$ [ 1 -eq  ]
bash: [: 1: unary operator expected

# PSH helps learn correct syntax
psh$ $((1 +))
psh: error: arithmetic: expected expression after +
```

### Clean Architecture

```bash
# PSH's modular architecture is visible in error messages
# and debugging output, helping users understand shell internals

# Component-specific error messages
psh$ echo $((bad))
psh: arithmetic: undefined variable: bad

# Clear parsing stages
psh$ set -o debug-tokens
psh$ echo hello
=== Tokens ===
Token(WORD, 'echo', 1:1)
Token(WORD, 'hello', 1:6)
Token(EOF, '', 1:11)
=== End Tokens ===
hello
```

## 17.5 Feature Compatibility Reference

| Feature | Bash | PSH | Notes |
|---------|------|-----|-------|
| **Basic Features** |
| Command execution | ✅ | ✅ | Full support |
| Pipelines | ✅ | ✅ | Full support |
| I/O redirection | ✅ | ✅ | All forms supported |
| Background jobs | ✅ | ✅ | Interactive only |
| Subshells | ✅ | ✅ | Full support (v0.59.8+) |
| **Variables** |
| Simple variables | ✅ | ✅ | Full support |
| Arrays | ✅ | ✅ | Full support (v0.41.0+) |
| Associative arrays | ✅ | ✅ | Full support (v0.43.0+) |
| Local variables | ✅ | ✅ | Full support (v0.29.0+) |
| Variable attributes | ✅ | ✅ | declare -i, -r, -x, etc. |
| **Expansions** |
| Parameter expansion | ✅ | ✅ | All features (v0.29.2+) |
| Command substitution | ✅ | ✅ | Both $() and `` |
| Arithmetic expansion | ✅ | ✅ | Full support (v0.18.0+) |
| Brace expansion | ✅ | ✅ | Full support (v0.21.0+) |
| Process substitution | ✅ | ✅ | Full support (v0.24.0+) |
| Tilde expansion | ✅ | ✅ | Full support (v0.5.0+) |
| **Control Structures** |
| if/then/else/fi | ✅ | ✅ | Full support (v0.13.0+) |
| while/do/done | ✅ | ✅ | Full support (v0.14.0+) |
| for/do/done | ✅ | ✅ | Full support (v0.15.0+) |
| C-style for loops | ✅ | ✅ | Full support (v0.31.0+) |
| case/esac | ✅ | ✅ | Full support (v0.17.0+) |
| select | ✅ | ✅ | Full support (v0.34.0+) |
| Arithmetic commands | ✅ | ✅ | Full support (v0.32.0+) |
| Control in pipelines | ✅ | ✅ | Full support (v0.37.0+) |
| **Functions** |
| Function definition | ✅ | ✅ | Both syntaxes (v0.8.0+) |
| Local variables | ✅ | ✅ | Full support (v0.29.0+) |
| Return values | ✅ | ✅ | Full support |
| **Job Control** |
| jobs command | ✅ | ✅ | Interactive only (v0.9.0+) |
| fg/bg commands | ✅ | ✅ | Interactive only (v0.9.0+) |
| Job specifications | ✅ | ✅ | Full support (%1, %+, etc.) |
| wait builtin | ✅ | ✅ | Full support (v0.57.4+) |
| disown | ✅ | ❌ | Not implemented |
| **Shell Options** |
| set -e (errexit) | ✅ | ✅ | Full support (v0.35.0+) |
| set -u (nounset) | ✅ | ✅ | Full support (v0.35.0+) |
| set -x (xtrace) | ✅ | ✅ | Full support (v0.35.0+) |
| set -o pipefail | ✅ | ✅ | Full support (v0.35.0+) |
| **Signal Handling** |
| trap command | ✅ | ✅ | Full support (v0.57.3+) |
| Signal handling | ✅ | ✅ | All standard signals |
| **Advanced Features** |
| History expansion | ✅ | ✅ | Full support (v0.33.0+) |
| Here documents | ✅ | ✅ | Full support (v0.59.0+) |
| Enhanced test [[ ]] | ✅ | ✅ | Full support (v0.27.0+) |
| eval builtin | ✅ | ✅ | Full support (v0.36.0+) |
| Coprocesses | ✅ | ❌ | Not implemented |
| Extended glob patterns | ✅ | ❌ | Not implemented |
| Programmable completion | ✅ | ❌ | Basic tab completion only |
| **PSH-Specific** |
| --debug-ast | ❌ | ✅ | PSH only |
| --debug-tokens | ❌ | ✅ | PSH only |
| --debug-scopes | ❌ | ✅ | PSH only |
| --debug-expansion | ❌ | ✅ | PSH only |

## 17.6 Writing Portable Scripts

When writing scripts that need to work in both PSH and Bash, follow these guidelines.

### Stick to POSIX Features

```bash
#!/bin/sh
# Use POSIX-compatible features for maximum portability

# POSIX test command
if [ -f "$file" ]; then
    echo "File exists"
fi

# Avoid Bash-specific features
# Don't use [[ ]], use [
# Don't use (( )), use $(( )) with [
# Don't use arrays
# Don't use {1..10}, use seq or loops
```

### Detect the Shell

```bash
#!/bin/sh
# Detect which shell is running

if [ -n "$BASH_VERSION" ]; then
    echo "Running in Bash"
    # Use Bash features
elif [ -n "$PSH_VERSION" ] || [ "$0" = "psh" ]; then
    echo "Running in PSH"
    # Use PSH-compatible features
else
    echo "Unknown shell"
    # Stick to POSIX
fi
```

### Feature Detection

```bash
# Test for specific features rather than shell version

# Check for array support
if eval 'array=(1 2 3) 2>/dev/null'; then
    echo "Arrays supported"
else
    echo "No array support"
fi

# Check for [[ support
if eval '[[ 1 = 1 ]] 2>/dev/null'; then
    echo "Enhanced test supported"
else
    echo "Use standard test command"
fi
```

### Common Workarounds

```bash
# Instead of arrays, use functions
get_item() {
    case "$1" in
        1) echo "first" ;;
        2) echo "second" ;;
        3) echo "third" ;;
    esac
}

# Instead of select, use a function
menu() {
    while true; do
        echo "1) Option 1"
        echo "2) Option 2"
        echo "3) Quit"
        read -p "Choose: " choice
        case "$choice" in
            1|2) return $choice ;;
            3) return 0 ;;
            *) echo "Invalid choice" ;;
        esac
    done
}

# Instead of trap, use explicit cleanup
main() {
    temp_file=$(mktemp)
    
    # Do work
    process_data > "$temp_file"
    
    # Explicit cleanup
    rm -f "$temp_file"
}
```

## 17.7 Migration Guide

### From Bash to PSH

```bash
# 1. Check for unsupported features
grep -E 'set -[eux]|declare -[aA]|trap|select|coproc' script.sh

# 2. Replace arrays with alternatives
# Before:
arr=(one two three)
echo ${arr[1]}

# After:
set -- one two three
echo $2

# 3. Use shell options (now supported in PSH v0.35.0+)
# PSH now supports:
set -e    # Exit on error
set -u    # Error on undefined variables  
set -x    # Print commands before execution
set -o pipefail  # Pipeline fails if any command fails

# 4. Use history expansion (now supported in PSH v0.33.0+)
# PSH now supports:
!!        # Previous command
!n        # Command n from history
!-n       # n commands ago
!string   # Most recent command starting with string
!?string? # Most recent command containing string
```

### Script Compatibility Checklist

```bash
#!/usr/bin/env psh
# PSH Script Compatibility Checklist (v0.66.0+)

# ✅ DO use these features (fully supported):
- Simple variables and environment variables
- Arrays and associative arrays (declare -a, declare -A)
- Basic control structures (if, while, for, case, select)
- C-style for loops: for ((i=0; i<10; i++))
- Functions with local variables
- Command substitution with $() and backticks
- Process substitution <() and >()
- All forms of I/O redirection
- Parameter expansion (all bash features)
- Arithmetic expansion and arithmetic commands
- Job control (interactive mode: jobs, fg, bg, wait)
- Shell options: set -e, -u, -x, -o pipefail
- History expansion: !!, !n, !string
- eval builtin for dynamic execution
- trap command for signal handling
- Subshells with proper variable isolation
- Control structures in pipelines
- Brace expansion {a,b,c} and {1..10}
- Here documents and here strings

# ❌ DON'T use these features:
- Coprocesses (coproc)
- Extended glob patterns (!(pattern), etc.)
- Programmable completion (complete -F)
- disown builtin
- Very deep recursion (Python stack limits apply)

# ⚠️ BE CAREFUL with:
- Job control in scripts (interactive features only)  
- Some edge cases in complex quoting scenarios
- Script execution context differences (features work in isolation but may have minor issues in complex script files)
```

## 17.8 Future Development

PSH continues to evolve with a focus on educational value.

### Planned Features

```bash
# Priority features for future versions:
1. Trap command for signal handling
2. Extended glob patterns
3. Escaped glob patterns
4. Advanced completion features
5. Additional built-in commands

# Educational enhancements:
- More detailed error messages
- Interactive tutorials
- Visualization of shell operations
- Step-by-step execution mode
```

### Design Philosophy

```bash
# PSH prioritizes:
1. Code clarity over performance
2. Educational value over feature completeness
3. Correct behavior over optimization
4. Helpful errors over terse messages

# This means:
- Some features may never be implemented
- Performance may differ from Bash
- Error messages are more verbose
- Debugging features are built-in
```

## Summary

Understanding the differences between PSH and Bash helps you use each shell effectively:

1. **Comprehensive Feature Support**: Arrays, associative arrays, trap command, wait builtin, all control structures
2. **Advanced Shell Features**: Parameter expansion, process substitution, enhanced test [[ ]], arithmetic commands
3. **Minimal Remaining Gaps**: Only coprocesses, extended glob patterns, and advanced completion features missing
4. **Architectural Advantages**: Python implementation provides excellent error messages and debugging capabilities
5. **Educational Benefits**: Debug options make PSH excellent for learning shell internals
6. **High Compatibility**: 95%+ of common bash scripts work without modification
7. **Portable Scripts**: Most shell scripting patterns work identically in both shells

Key takeaways for PSH v0.66.0+:
- **Near-complete bash compatibility** for core shell programming
- **Arrays and associative arrays** work exactly like bash
- **Signal handling with trap** provides robust script cleanup
- **Full job control** support in interactive mode
- **All major expansions** implemented (parameter, command, arithmetic, process, brace)
- **Control structures** work in pipelines and with logical operators
- **Only missing features** are rarely-used advanced features (coprocesses, extended globs)
- **Debug features** make PSH superior for learning and troubleshooting
- **Most bash scripts** run without any modifications needed

PSH has evolved from an educational shell to a **highly compatible bash alternative** that serves both learning and practical scripting needs. The implementation is now mature enough for serious shell scripting while maintaining its educational clarity and superior debugging capabilities.

---

[← Previous: Chapter 16 - Advanced Features](16_advanced_features.md) | [Next: Chapter 18 - Troubleshooting →](18_troubleshooting.md)