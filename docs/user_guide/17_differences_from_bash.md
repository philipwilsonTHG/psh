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
# Bash arrays are NOT supported in PSH
# This won't work:
declare -a array=(one two three)
echo ${array[0]}
echo ${array[@]}

# Workaround: Use positional parameters
set -- one two three
echo $1          # First element
echo "$@"        # All elements
shift            # Remove first element

# Or use separate variables
item1="one"
item2="two"
item3="three"

# Or process lists directly
for item in one two three; do
    echo "$item"
done
```

### Trap Command

```bash
# Bash trap command is NOT implemented
# This won't work:
trap 'echo "Cleaning up..."' EXIT
trap 'echo "Interrupted"' INT

# Workaround: Manual cleanup
cleanup() {
    echo "Cleaning up..."
    rm -f /tmp/tempfile.$$
}

# Call cleanup manually
do_work || { cleanup; exit 1; }
cleanup
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

### Other Missing Features

```bash
# Coprocesses are NOT implemented
coproc { command; }

# Programmable completion is NOT implemented
complete -F _my_completion mycommand

# Extended glob patterns need explicit enabling (partial support)
# These may not work as expected:
!(pattern)  # Anything except pattern
*(pattern)  # Zero or more occurrences
+(pattern)  # One or more occurrences
?(pattern)  # Zero or one occurrence
@(pattern)  # Exactly one occurrence

# Process substitution in variable assignment limitations
# May not work:
var=$(<(command))  # Use var=$(command) instead
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
# PSH cannot use control structures directly in pipelines with && or ||
# This won't work as expected:
if [ -f file.txt ]; then cat file.txt; fi && echo "Success"

# Workaround: Use functions or subshells
check_and_cat() {
    if [ -f file.txt ]; then
        cat file.txt
    fi
}
check_and_cat && echo "Success"

# Or use subshells
(if [ -f file.txt ]; then cat file.txt; fi) && echo "Success"
```

### Arithmetic Command Limitations

```bash
# Arithmetic commands cannot be used in pipelines with && or ||
# This won't work:
((x > 5)) && echo "Greater than 5"

# Workaround: Use if statement
if ((x > 5)); then
    echo "Greater than 5"
fi

# Or use arithmetic expansion with test
[ $((x > 5)) -eq 1 ] && echo "Greater than 5"
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
| **Variables** |
| Simple variables | ✅ | ✅ | Full support |
| Arrays | ✅ | ❌ | Not implemented |
| Associative arrays | ✅ | ❌ | Not implemented |
| Local variables | ✅ | ✅ | Full support |
| **Expansions** |
| Parameter expansion | ✅ | ✅ | All features |
| Command substitution | ✅ | ✅ | Both $() and `` |
| Arithmetic expansion | ✅ | ✅ | Full support |
| Brace expansion | ✅ | ✅ | Full support |
| Process substitution | ✅ | ✅ | Full support |
| Tilde expansion | ✅ | ✅ | Full support |
| **Control Structures** |
| if/then/else/fi | ✅ | ✅ | Full support |
| while/do/done | ✅ | ✅ | Full support |
| for/do/done | ✅ | ✅ | Full support |
| C-style for loops | ✅ | ✅ | Full support |
| case/esac | ✅ | ✅ | Full support |
| select | ✅ | ✅ | Full support (v0.34.0+) |
| **Functions** |
| Function definition | ✅ | ✅ | Both syntaxes |
| Local variables | ✅ | ✅ | Full support |
| Return values | ✅ | ✅ | Full support |
| **Job Control** |
| jobs command | ✅ | ✅ | Interactive only |
| fg/bg commands | ✅ | ✅ | Interactive only |
| Job specifications | ✅ | ✅ | Full support |
| disown | ✅ | ❌ | Not implemented |
| **Shell Options** |
| set -e (errexit) | ✅ | ✅ | Full support (v0.35.0+) |
| set -u (nounset) | ✅ | ✅ | Full support (v0.35.0+) |
| set -x (xtrace) | ✅ | ✅ | Full support (v0.35.0+) |
| set -o pipefail | ✅ | ✅ | Full support (v0.35.0+) |
| **Advanced Features** |
| Trap command | ✅ | ❌ | Not implemented |
| History expansion | ✅ | ✅ | Full support (v0.33.0+) |
| Coprocesses | ✅ | ❌ | Not implemented |
| Programmable completion | ✅ | ❌ | Not implemented |
| eval builtin | ✅ | ✅ | Full support (v0.36.0+) |
| **PSH-Specific** |
| --debug-ast | ❌ | ✅ | PSH only |
| --debug-tokens | ❌ | ✅ | PSH only |
| --debug-scopes | ❌ | ✅ | PSH only |

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
# PSH Script Compatibility Checklist

# ✅ DO use these features:
- Simple variables
- Basic control structures (if, while, for, case, select)
- C-style for loops: for ((i=0; i<10; i++))
- Functions with local variables
- Command substitution with $()
- Process substitution <() and >()
- All forms of I/O redirection
- Parameter expansion (all bash features)
- Job control (interactive only)
- Shell options: set -e, -u, -x, -o pipefail
- History expansion: !!, !n, !string
- eval builtin for dynamic execution

# ❌ DON'T use these features:
- Arrays or associative arrays
- trap command
- Coprocesses
- Deep recursion (>100 levels)

# ⚠️ BE CAREFUL with:
- Job control in scripts (won't work)
- Control structures in && || chains
- Arithmetic commands in conditionals
- Quote handling differences
```

## 17.8 Future Development

PSH continues to evolve with a focus on educational value.

### Planned Features

```bash
# Priority features for future versions:
1. Trap command for signal handling
2. Basic array support
3. Associative arrays
4. Extended glob patterns
5. Escaped glob patterns

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

1. **Implemented Features**: Core shell options, select statement, history expansion, eval builtin
2. **Remaining Unimplemented**: Arrays, trap command, coprocesses, extended patterns
3. **Architectural Limitations**: Recursion depth, pipeline restrictions
4. **Behavioral Differences**: Quote handling, variable assignment strictness  
5. **PSH-Specific Features**: Debug options and educational enhancements
6. **Compatibility Reference**: Quick lookup for feature support
7. **Portable Scripts**: Guidelines for cross-shell compatibility
8. **Migration Guide**: Moving scripts between shells
9. **Future Development**: Planned improvements

Key takeaways:
- PSH now implements most essential shell features including shell options
- Select statements and history expansion provide full bash compatibility
- Eval builtin enables sophisticated dynamic programming
- Debug features make PSH excellent for learning shell internals
- Most everyday shell tasks work identically to bash
- Scripts using core features are highly portable
- Understanding differences prevents frustration and enables effective use

PSH serves as both a practical shell and an educational tool, making shell programming concepts clear and accessible while maintaining compatibility with essential shell features.

---

[← Previous: Chapter 16 - Advanced Features](16_advanced_features.md) | [Next: Chapter 18 - Troubleshooting →](18_troubleshooting.md)